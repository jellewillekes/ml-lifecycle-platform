from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import mlflow
import pandas as pd
import pytest
import yaml
from sklearn.dummy import DummyClassifier

import ml_lifecycle_platform.pipeline.validate_model as validate_model_mod
from ml_lifecycle_platform.common.constants import (
    ART_MODEL_VALIDATION_REPORT_JSON,
    ART_TRAIN_RUN_ID,
    MLFLOW_ARTIFACT_PATH_MODEL,
    STEP_VALIDATE_MODEL,
    TAG_MODEL_NAME,
    TAG_STEP,
    TEST_CSV,
)

pytestmark = pytest.mark.integration

EXPERIMENT_NAME = "integration-validate-model"


def _spec_payload(model_name: str, model_validation: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "model_spec/v1",
        "model_name": model_name,
        "task": "binary_classifier",
        "label_column": "target",
        "source": {"kind": "sklearn_demo", "dataset_name": "breast_cancer"},
        "split": {"test_size": 0.2, "random_state": 42, "stratify": True},
        "preprocessor": {"kind": "standard_scaler"},
        "trainer": {
            "kind": "logistic_regression",
            "max_iter": 2000,
            "solver": "lbfgs",
            "class_weight": "balanced",
            "random_state": 42,
        },
        "evaluation": {
            "metrics": ["accuracy", "f1", "roc_auc"],
            "gate": {"metric": "roc_auc", "threshold": 0.5},
        },
        "feature_contract": {
            "version": "validate_model_it.input/v1",
            "allow_unknown_fields": False,
            "features": [
                {"name": "f1", "dtype": "float"},
                {"name": "f2", "dtype": "float"},
            ],
        },
        "model_validation": model_validation,
    }


def _write_spec(
    tmp_path: Path, model_name: str, model_validation: dict[str, Any]
) -> Path:
    spec_path = tmp_path / f"{model_name}.yaml"
    spec_path.write_text(
        yaml.safe_dump(_spec_payload(model_name, model_validation), sort_keys=False),
        encoding="utf-8",
    )
    return spec_path


def _write_test_csv(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(
        {
            "f1": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
            "f2": [1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0],
            "target": [0, 1, 0, 1, 0, 1, 0, 1],
        }
    )
    frame.to_csv(data_dir / TEST_CSV, index=False)


def _log_train_run(model_name: str, art_dir: Path) -> None:
    model = DummyClassifier(strategy="most_frequent")
    model.fit([[0.0, 1.0], [1.0, 0.0], [2.0, 1.0], [3.0, 0.0]], [0, 1, 0, 1])
    with mlflow.start_run(run_name="train") as run:
        mlflow.set_tag(TAG_MODEL_NAME, model_name)
        mlflow.sklearn.log_model(model, artifact_path=MLFLOW_ARTIFACT_PATH_MODEL)
        run_id = run.info.run_id
    art_dir.mkdir(parents=True, exist_ok=True)
    (art_dir / ART_TRAIN_RUN_ID).write_text(run_id, encoding="utf-8")


def _configure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    model_name: str,
    model_validation: dict[str, Any],
) -> Path:
    artifact_root = tmp_path / "mlflow-artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    mlflow.create_experiment(EXPERIMENT_NAME, artifact_location=artifact_root.as_uri())
    mlflow.set_experiment(EXPERIMENT_NAME)

    data_dir = tmp_path / "data"
    art_dir = tmp_path / "artifacts"
    _write_test_csv(data_dir)

    monkeypatch.setenv("EXPERIMENT_NAME", EXPERIMENT_NAME)
    monkeypatch.setenv("MLP_DATA_DIR", str(data_dir))
    monkeypatch.setenv("MLP_ARTIFACTS_DIR", str(art_dir))
    monkeypatch.setenv(
        "MLP_MODEL_SPEC_PATH",
        str(_write_spec(tmp_path, model_name, model_validation)),
    )
    _log_train_run(model_name, art_dir)
    return art_dir


def _latest_validate_model_run() -> pd.DataFrame:
    exp = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
    assert exp is not None
    runs = mlflow.search_runs(
        experiment_ids=[exp.experiment_id],
        filter_string=f"tags.{TAG_STEP} = '{STEP_VALIDATE_MODEL}'",
        max_results=1,
    )
    assert isinstance(runs, pd.DataFrame)
    return runs


def test_validate_model_passes_and_attaches_report(
    mlflow_sqlite: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    art_dir = _configure(
        tmp_path,
        monkeypatch,
        model_name="validate_model_pass",
        model_validation={"metric": "roc_auc", "min_overall": 0.4},
    )

    validate_model_mod.main()

    report = json.loads(
        (art_dir / ART_MODEL_VALIDATION_REPORT_JSON).read_text(encoding="utf-8")
    )
    assert report["passed"] is True
    assert report["overall_value"] == pytest.approx(0.5)
    assert not _latest_validate_model_run().empty


def test_validate_model_aborts_when_overall_below_floor(
    mlflow_sqlite: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    art_dir = _configure(
        tmp_path,
        monkeypatch,
        model_name="validate_model_fail",
        model_validation={"metric": "roc_auc", "min_overall": 0.9},
    )

    with pytest.raises(RuntimeError, match="Model validation failed"):
        validate_model_mod.main()

    report = json.loads(
        (art_dir / ART_MODEL_VALIDATION_REPORT_JSON).read_text(encoding="utf-8")
    )
    assert report["passed"] is False
    assert any(
        check["name"] == "overall" and not check["passed"] for check in report["checks"]
    )
