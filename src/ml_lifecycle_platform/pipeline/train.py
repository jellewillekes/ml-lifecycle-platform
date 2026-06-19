"""Train the pipeline defined by the model spec, log metrics and
reproducibility evidence to MLflow, and write the training run id for
downstream steps."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Mapping

import joblib
import mlflow
import pandas as pd
from mlflow.models.signature import infer_signature
from sklearn.base import BaseEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

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
from ml_lifecycle_platform.runtime.mlflow import ensure_experiment
from ml_lifecycle_platform.core.batch_contracts import validate_labeled_dataset
from ml_lifecycle_platform.pipeline.metrics import compute_binary_metrics
from ml_lifecycle_platform.contracts.dataset_fingerprint import (
    DatasetFingerprint,
    compute_fingerprint,
    write_fingerprint_json,
)
from ml_lifecycle_platform.contracts.repro_contract import ReproContract
from ml_lifecycle_platform.core.model_spec_types import (
    LightGBMTrainerSpec,
    ModelSpec,
)
from ml_lifecycle_platform.core.model_specs import load_model_spec
from ml_lifecycle_platform.runtime.bootstrap import (
    configure_mlflow,
    get_runtime_context,
)

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_text(payload: str) -> str:
    return sha256_bytes(payload.encode("utf-8"))


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def get_uv_lock_path() -> Path:
    path = REPO_ROOT / "uv.lock"
    if not path.exists():
        raise RuntimeError(f"uv.lock not found at expected repo root path: {path}")
    return path


def get_uv_lock_hash() -> str:
    return sha256_file(get_uv_lock_path())


PROBE_INPUT_LIMIT: Final[int] = 10
REPRO_INPUTS_ARTIFACT_PATH: Final[str] = f"{MLFLOW_ARTIFACT_PATH_REPRO}/inputs"
REPRO_OUTPUTS_ARTIFACT_PATH: Final[str] = f"{MLFLOW_ARTIFACT_PATH_REPRO}/outputs"
REPRO_ENV_ARTIFACT_PATH: Final[str] = f"{MLFLOW_ARTIFACT_PATH_REPRO}/env"


@dataclass
class TrainingInputs:
    train_df: pd.DataFrame
    test_df: pd.DataFrame
    preprocessor: BaseEstimator


@dataclass
class TrainingResult:
    pipeline: Pipeline
    metrics: dict[str, float]
    probe_inputs: pd.DataFrame
    expected_probabilities: list[float]


def config_hash_for_spec(spec: ModelSpec | Mapping[str, Any]) -> str:
    payload = spec.to_dict() if isinstance(spec, ModelSpec) else dict(spec)
    return sha256_text(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def trainer_params_for_spec(spec: ModelSpec) -> dict[str, str | int | float]:
    if isinstance(spec.trainer, LightGBMTrainerSpec):
        return {
            "model_type": "lightgbm",
            "n_estimators": spec.trainer.n_estimators,
            "learning_rate": spec.trainer.learning_rate,
            "num_leaves": spec.trainer.num_leaves,
            "max_depth": spec.trainer.max_depth,
            "min_child_samples": spec.trainer.min_child_samples,
            "class_weight": spec.trainer.class_weight,
            "random_state": spec.trainer.random_state,
        }
    return {
        "model_type": "logreg",
        "max_iter": spec.trainer.max_iter,
        "solver": spec.trainer.solver,
        "class_weight": spec.trainer.class_weight,
        "random_state": spec.trainer.random_state,
    }


def build_estimator(spec: ModelSpec) -> BaseEstimator:
    if isinstance(spec.trainer, LightGBMTrainerSpec):
        # Imported lazily: the native OpenMP dependency (libgomp) is only
        # needed when a spec actually selects the lightgbm trainer, so the
        # logreg path and `make check` never pay for it.
        from lightgbm import LGBMClassifier

        return LGBMClassifier(
            n_estimators=spec.trainer.n_estimators,
            learning_rate=spec.trainer.learning_rate,
            num_leaves=spec.trainer.num_leaves,
            max_depth=spec.trainer.max_depth,
            min_child_samples=spec.trainer.min_child_samples,
            class_weight=spec.trainer.class_weight,
            random_state=spec.trainer.random_state,
            # Single-threaded + deterministic so the reproduce step can replay
            # the probe predictions bit-for-bit.
            n_jobs=1,
            deterministic=True,
            force_col_wise=True,
            verbose=-1,
        )
    return LogisticRegression(
        max_iter=spec.trainer.max_iter,
        solver=spec.trainer.solver,
        class_weight=spec.trainer.class_weight,
        random_state=spec.trainer.random_state,
    )


def load_training_inputs(
    data_dir: Path | None = None,
    artifacts_dir: Path | None = None,
) -> TrainingInputs:
    ctx = get_runtime_context()
    data_dir = ctx.data_dir if data_dir is None else data_dir
    artifacts_dir = ctx.artifacts_dir if artifacts_dir is None else artifacts_dir
    spec = load_model_spec(ctx.model_spec_path)
    train_df = pd.read_csv(data_dir / TRAIN_CSV)
    test_df = pd.read_csv(data_dir / TEST_CSV)
    train_df = validate_labeled_dataset(
        train_df,
        spec=spec,
        stage="train",
        dataset_name="train",
    )
    test_df = validate_labeled_dataset(
        test_df,
        spec=spec,
        stage="train",
        dataset_name="test",
    )
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
    X_train = inputs.train_df.drop(columns=[spec.label_column])
    y_train = inputs.train_df[spec.label_column].astype(int)

    X_test = inputs.test_df.drop(columns=[spec.label_column])
    y_test = inputs.test_df[spec.label_column].astype(int)

    clf = build_estimator(spec)
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


def _log_training_tags(
    *,
    run_id: str,
    spec: ModelSpec,
    config_hash: str,
    params: Mapping[str, Any],
) -> None:
    mlflow.set_tag(TAG_STEP, STEP_TRAIN)
    mlflow.set_tag(TAG_MODEL_NAME, spec.model_name)
    mlflow.set_tag(TAG_TRAINING_RUN_ID, run_id)
    mlflow.set_tag(TAG_CONFIG_HASH, config_hash)
    mlflow.set_tag(TAG_DETERMINISTIC_SEED, str(params["random_state"]))


def _compute_fingerprint_and_tags(
    inputs: TrainingInputs,
    data_source_uri: str,
) -> tuple[DatasetFingerprint, str]:
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
    return fp, dataset_fingerprint_hash


def _record_repro_contract(
    *,
    art_dir: Path,
    data_dir: Path,
    result: TrainingResult,
    repro_contract: ReproContract,
    fp: DatasetFingerprint,
) -> tuple[Path, Path]:
    fp_path = art_dir / ART_DATASET_FINGERPRINT_JSON
    write_fingerprint_json(fp, fp_path)
    mlflow.log_artifact(str(fp_path), artifact_path=MLFLOW_ARTIFACT_PATH_REPORTS)

    summary_path = art_dir / ART_TRAIN_SUMMARY_JSON
    _write_json(summary_path, result.metrics)
    mlflow.log_artifact(str(summary_path), artifact_path=MLFLOW_ARTIFACT_PATH_REPORTS)

    contract_path = art_dir / ART_REPRO_CONTRACT_JSON
    contract_path.write_text(repro_contract.to_json(), encoding="utf-8")
    mlflow.log_artifact(str(contract_path), artifact_path=MLFLOW_ARTIFACT_PATH_REPRO)

    probe_inputs_path = art_dir / ART_REPRO_PROBE_INPUTS_CSV
    result.probe_inputs.to_csv(probe_inputs_path, index=False)
    mlflow.log_artifact(
        str(probe_inputs_path), artifact_path=REPRO_INPUTS_ARTIFACT_PATH
    )

    expected_predictions_path = art_dir / ART_REPRO_EXPECTED_PREDICTIONS_JSON
    _write_json(
        expected_predictions_path,
        {"probabilities": result.expected_probabilities},
    )
    mlflow.log_artifact(
        str(expected_predictions_path), artifact_path=REPRO_OUTPUTS_ARTIFACT_PATH
    )

    mlflow.log_artifact(str(get_uv_lock_path()), artifact_path=REPRO_ENV_ARTIFACT_PATH)
    mlflow.log_artifact(
        str(data_dir / TRAIN_CSV), artifact_path=REPRO_INPUTS_ARTIFACT_PATH
    )
    mlflow.log_artifact(
        str(data_dir / TEST_CSV), artifact_path=REPRO_INPUTS_ARTIFACT_PATH
    )
    mlflow.log_artifact(
        str(art_dir / ART_PREPROCESSOR), artifact_path=REPRO_INPUTS_ARTIFACT_PATH
    )
    return fp_path, contract_path


def main() -> None:
    ctx = get_runtime_context()
    logging.basicConfig(level=ctx.log_level)
    configure_mlflow()

    ensure_experiment(ctx.experiment_name)
    mlflow.set_experiment(ctx.experiment_name)

    spec = load_model_spec(ctx.model_spec_path)
    data_source_uri = spec.data_source_uri()
    params = trainer_params_for_spec(spec)
    config_hash = config_hash_for_spec(spec)
    inputs = load_training_inputs()

    with mlflow.start_run(run_name="train") as run:
        _log_training_tags(
            run_id=run.info.run_id,
            spec=spec,
            config_hash=config_hash,
            params=params,
        )
        fp, dataset_fingerprint_hash = _compute_fingerprint_and_tags(
            inputs, data_source_uri
        )
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

        art_dir = ctx.artifacts_dir
        art_dir.mkdir(parents=True, exist_ok=True)

        fp_path, contract_path = _record_repro_contract(
            art_dir=art_dir,
            data_dir=ctx.data_dir,
            result=result,
            repro_contract=repro_contract,
            fp=fp,
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
