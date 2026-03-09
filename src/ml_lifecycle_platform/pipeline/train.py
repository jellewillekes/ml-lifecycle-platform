from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Mapping

import joblib
import mlflow
import pandas as pd
from mlflow.models.signature import infer_signature
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.pipeline import Pipeline

from ml_lifecycle_platform.common.config import (
    get_experiment_name,
    get_log_level,
    get_model_spec_path,
)
from ml_lifecycle_platform.common.constants import (
    ART_DATASET_FINGERPRINT_JSON,
    ART_PREPROCESSOR,
    ART_REPRO_CONTRACT_JSON,
    ART_REPRO_EXPECTED_PREDICTIONS_JSON,
    ART_REPRO_PROBE_INPUTS_CSV,
    ART_TRAIN_SUMMARY_JSON,
    ART_UV_LOCK,
    MLFLOW_ARTIFACT_PATH_MODEL,
    MLFLOW_ARTIFACT_PATH_REPRO,
    MLFLOW_ARTIFACT_PATH_REPORTS,
    STEP_TRAIN,
    TAG_CONFIG_HASH,
    TAG_DATASET_FINGERPRINT,
    TAG_DETERMINISTIC_SEED,
    TAG_ENV_LOCK_HASH,
    TAG_MODEL_NAME,
    TAG_REPRO_SCHEMA_VERSION,
    TAG_STEP,
    TAG_TRAINING_RUN_ID,
    TEST_CSV,
    TRAIN_CSV,
)
from ml_lifecycle_platform.common.mlflow_utils import ensure_experiment
from ml_lifecycle_platform.common.repro import (
    get_uv_lock_hash,
    get_uv_lock_path,
    sha256_text,
)
from ml_lifecycle_platform.contracts.dataset_fingerprint import (
    DatasetFingerprint,
    compute_fingerprint,
    write_fingerprint_json,
)
from ml_lifecycle_platform.contracts.repro_contract import ReproContract
from ml_lifecycle_platform.core.model_specs import ModelSpec, load_model_spec
from ml_lifecycle_platform.runtime.bootstrap import configure_mlflow

logger = logging.getLogger(__name__)

DATA_DIR: Final[Path] = Path("/app/data")
ART_DIR: Final[Path] = Path("/app/artifacts")
PROBE_INPUT_LIMIT: Final[int] = 10
REPRO_INPUTS_ARTIFACT_PATH: Final[str] = f"{MLFLOW_ARTIFACT_PATH_REPRO}/inputs"
REPRO_OUTPUTS_ARTIFACT_PATH: Final[str] = f"{MLFLOW_ARTIFACT_PATH_REPRO}/outputs"
REPRO_ENV_ARTIFACT_PATH: Final[str] = f"{MLFLOW_ARTIFACT_PATH_REPRO}/env"


@dataclass
class TrainingInputs:
    train_df: pd.DataFrame
    test_df: pd.DataFrame
    preprocessor: Any


@dataclass
class TrainingResult:
    pipeline: Pipeline
    metrics: dict[str, float]
    probe_inputs: pd.DataFrame
    expected_probabilities: list[float]


def config_hash_for_spec(spec: ModelSpec | Mapping[str, Any]) -> str:
    payload = spec.to_dict() if isinstance(spec, ModelSpec) else dict(spec)
    return sha256_text(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def trainer_params_for_spec(spec: ModelSpec) -> dict[str, str | int]:
    return {
        "model_type": "logreg",
        "max_iter": spec.trainer.max_iter,
        "solver": spec.trainer.solver,
        "class_weight": spec.trainer.class_weight,
        "random_state": spec.trainer.random_state,
    }


def compute_binary_metrics(
    *,
    metric_names: tuple[str, ...],
    y_true: pd.Series,
    pred: Any,
    proba: Any,
    prefix: str,
) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for metric_name in metric_names:
        if metric_name == "accuracy":
            value = accuracy_score(y_true, pred)
        elif metric_name == "f1":
            value = f1_score(y_true, pred)
        elif metric_name == "roc_auc":
            value = roc_auc_score(y_true, proba)
        else:  # pragma: no cover
            raise ValueError(f"Unsupported metric: {metric_name}")
        metrics[f"{prefix}_{metric_name}"] = float(value)
    return metrics


def load_training_inputs(
    data_dir: Path | None = None,
    artifacts_dir: Path | None = None,
) -> TrainingInputs:
    data_dir = DATA_DIR if data_dir is None else data_dir
    artifacts_dir = ART_DIR if artifacts_dir is None else artifacts_dir
    train_df = pd.read_csv(data_dir / TRAIN_CSV)
    test_df = pd.read_csv(data_dir / TEST_CSV)
    preprocessor = joblib.load(artifacts_dir / ART_PREPROCESSOR)
    return TrainingInputs(
        train_df=train_df,
        test_df=test_df,
        preprocessor=preprocessor,
    )


def train_from_inputs(
    inputs: TrainingInputs,
    spec: ModelSpec,
) -> TrainingResult:
    params = trainer_params_for_spec(spec)
    X_train = inputs.train_df.drop(columns=[spec.label_column])
    y_train = inputs.train_df[spec.label_column].astype(int)

    X_test = inputs.test_df.drop(columns=[spec.label_column])
    y_test = inputs.test_df[spec.label_column].astype(int)

    clf = LogisticRegression(
        max_iter=int(params["max_iter"]),
        solver=str(params["solver"]),
        class_weight=str(params["class_weight"]),
        random_state=int(params["random_state"]),
    )
    pipeline = Pipeline(steps=[("pre", inputs.preprocessor), ("clf", clf)])
    pipeline.fit(X_train, y_train)

    proba = pipeline.predict_proba(X_test)[:, 1]
    pred = (proba >= 0.5).astype(int)
    probe_inputs = X_test.head(PROBE_INPUT_LIMIT).reset_index(drop=True)
    expected_probabilities = [
        float(v) for v in pipeline.predict_proba(probe_inputs)[:, 1]
    ]

    metrics = compute_binary_metrics(
        metric_names=spec.evaluation.metrics,
        y_true=y_test,
        pred=pred,
        proba=proba,
        prefix="test",
    )
    return TrainingResult(
        pipeline=pipeline,
        metrics=metrics,
        probe_inputs=probe_inputs,
        expected_probabilities=expected_probabilities,
    )


def build_repro_contract(
    *,
    training_run_id: str,
    spec: ModelSpec,
    dataset_fingerprint: DatasetFingerprint,
    dataset_fingerprint_hash: str,
    config_hash: str,
    params: Mapping[str, Any],
    data_source_uri: str,
) -> ReproContract:
    env_lock_hash = get_uv_lock_hash()
    seed = int(params["random_state"])
    return ReproContract(
        training_run_id=training_run_id,
        model_name=spec.model_name,
        model_spec=spec.to_dict(),
        git_sha=dataset_fingerprint.git_sha,
        config_hash=config_hash,
        dataset_fingerprint=dataset_fingerprint_hash,
        data_source_uri=data_source_uri,
        env_lock_hash=env_lock_hash,
        deterministic_seed=seed,
        params=dict(params),
        train_dataset_artifact=f"{REPRO_INPUTS_ARTIFACT_PATH}/{TRAIN_CSV}",
        test_dataset_artifact=f"{REPRO_INPUTS_ARTIFACT_PATH}/{TEST_CSV}",
        preprocessor_artifact=f"{REPRO_INPUTS_ARTIFACT_PATH}/{ART_PREPROCESSOR}",
        probe_inputs_artifact=f"{REPRO_INPUTS_ARTIFACT_PATH}/{ART_REPRO_PROBE_INPUTS_CSV}",
        expected_predictions_artifact=(
            f"{REPRO_OUTPUTS_ARTIFACT_PATH}/{ART_REPRO_EXPECTED_PREDICTIONS_JSON}"
        ),
        uv_lock_artifact=f"{REPRO_ENV_ARTIFACT_PATH}/{ART_UV_LOCK}",
    )


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    logging.basicConfig(level=get_log_level())
    configure_mlflow()

    experiment_name = get_experiment_name()
    ensure_experiment(experiment_name)
    mlflow.set_experiment(experiment_name)

    spec = load_model_spec(get_model_spec_path())
    data_source_uri = spec.data_source_uri()
    params = trainer_params_for_spec(spec)
    config_hash = config_hash_for_spec(spec)
    inputs = load_training_inputs()

    with mlflow.start_run(run_name="train") as run:
        mlflow.set_tag(TAG_STEP, STEP_TRAIN)
        mlflow.set_tag(TAG_MODEL_NAME, spec.model_name)
        mlflow.set_tag(TAG_TRAINING_RUN_ID, run.info.run_id)
        mlflow.set_tag(TAG_CONFIG_HASH, config_hash)
        mlflow.set_tag(TAG_DETERMINISTIC_SEED, str(params["random_state"]))

        fp = compute_fingerprint(
            train_df=inputs.train_df,
            test_df=inputs.test_df,
            data_source_uri=data_source_uri,
            index_cols=None,
        )
        dataset_fingerprint_hash = sha256_text(fp.to_json())

        mlflow.set_tags(fp.as_tags())
        mlflow.set_tag(TAG_DATASET_FINGERPRINT, dataset_fingerprint_hash)
        mlflow.set_tag(TAG_ENV_LOCK_HASH, get_uv_lock_hash())

        result = train_from_inputs(inputs, spec)
        repro_contract = build_repro_contract(
            training_run_id=run.info.run_id,
            spec=spec,
            dataset_fingerprint=fp,
            dataset_fingerprint_hash=dataset_fingerprint_hash,
            config_hash=config_hash,
            params=params,
            data_source_uri=data_source_uri,
        )
        mlflow.set_tag(TAG_REPRO_SCHEMA_VERSION, repro_contract.schema_version)

        fp_path = ART_DIR / ART_DATASET_FINGERPRINT_JSON
        write_fingerprint_json(fp, fp_path)
        mlflow.log_artifact(str(fp_path), artifact_path=MLFLOW_ARTIFACT_PATH_REPORTS)

        summary_path = ART_DIR / ART_TRAIN_SUMMARY_JSON
        _write_json(summary_path, result.metrics)
        mlflow.log_artifact(
            str(summary_path), artifact_path=MLFLOW_ARTIFACT_PATH_REPORTS
        )

        contract_path = ART_DIR / ART_REPRO_CONTRACT_JSON
        contract_path.write_text(repro_contract.to_json(), encoding="utf-8")
        mlflow.log_artifact(
            str(contract_path), artifact_path=MLFLOW_ARTIFACT_PATH_REPRO
        )

        probe_inputs_path = ART_DIR / ART_REPRO_PROBE_INPUTS_CSV
        result.probe_inputs.to_csv(probe_inputs_path, index=False)
        mlflow.log_artifact(
            str(probe_inputs_path), artifact_path=REPRO_INPUTS_ARTIFACT_PATH
        )

        expected_predictions_path = ART_DIR / ART_REPRO_EXPECTED_PREDICTIONS_JSON
        _write_json(
            expected_predictions_path,
            {"probabilities": result.expected_probabilities},
        )
        mlflow.log_artifact(
            str(expected_predictions_path), artifact_path=REPRO_OUTPUTS_ARTIFACT_PATH
        )

        uv_lock_path = get_uv_lock_path()
        mlflow.log_artifact(str(uv_lock_path), artifact_path=REPRO_ENV_ARTIFACT_PATH)
        mlflow.log_artifact(
            str(DATA_DIR / TRAIN_CSV), artifact_path=REPRO_INPUTS_ARTIFACT_PATH
        )
        mlflow.log_artifact(
            str(DATA_DIR / TEST_CSV), artifact_path=REPRO_INPUTS_ARTIFACT_PATH
        )
        mlflow.log_artifact(
            str(ART_DIR / ART_PREPROCESSOR), artifact_path=REPRO_INPUTS_ARTIFACT_PATH
        )

        mlflow.log_params(dict(params))

        input_example = result.probe_inputs.head(5)
        signature = infer_signature(
            input_example,
            result.pipeline.predict_proba(input_example)[:, 1],
        )
        mlflow.sklearn.log_model(
            sk_model=result.pipeline,
            artifact_path=MLFLOW_ARTIFACT_PATH_MODEL,
            signature=signature,
            input_example=input_example,
            registered_model_name=None,
        )
        mlflow.log_metrics(result.metrics)

        logger.info("run_id=%s", run.info.run_id)
        logger.info("dataset_fingerprint=%s", fp_path)
        logger.info("repro_contract=%s", contract_path)
        logger.info("metrics=%s", result.metrics)


if __name__ == "__main__":
    main()
