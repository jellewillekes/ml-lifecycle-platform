from __future__ import annotations

import json
from pathlib import Path

import mlflow
import pandas as pd
import pytest
import yaml

import ml_lifecycle_platform.pipeline.ingest as ingest_mod
import ml_lifecycle_platform.pipeline.validate_data as validate_data_mod
from ml_lifecycle_platform.common.constants import (
    ART_VALIDATION_REPORT_JSON,
    STEP_VALIDATE_DATA,
    TAG_STEP,
)

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_demo_spec(
    tmp_path: Path,
    *,
    model_name: str,
    validation: dict[str, object] | None = None,
) -> Path:
    source = REPO_ROOT / "configs/models/breast_cancer_demo.yaml"
    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    payload["model_name"] = model_name
    if validation is not None:
        payload["validation"] = validation
    spec_path = tmp_path / f"{model_name}.yaml"
    spec_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return spec_path


def _configure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    model_name: str,
    validation: dict[str, object] | None = None,
) -> Path:
    experiment_name = "integration-validate-data"
    artifact_root = tmp_path / "mlflow-artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    mlflow.create_experiment(experiment_name, artifact_location=artifact_root.as_uri())
    mlflow.set_experiment(experiment_name)

    art_dir = tmp_path / "artifacts"
    monkeypatch.setenv("EXPERIMENT_NAME", experiment_name)
    monkeypatch.setenv("MLP_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("MLP_ARTIFACTS_DIR", str(art_dir))
    monkeypatch.setenv(
        "MLP_MODEL_SPEC_PATH",
        str(_write_demo_spec(tmp_path, model_name=model_name, validation=validation)),
    )
    return art_dir


def _latest_step_run(experiment_name: str, step: str) -> pd.DataFrame:
    exp = mlflow.get_experiment_by_name(experiment_name)
    assert exp is not None
    runs = mlflow.search_runs(
        experiment_ids=[exp.experiment_id],
        filter_string=f"tags.{TAG_STEP} = '{step}'",
        max_results=1,
    )
    assert isinstance(runs, pd.DataFrame)
    return runs


def test_validate_data_passes_and_attaches_report(
    mlflow_sqlite: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    art_dir = _configure(tmp_path, monkeypatch, model_name="validate_data_pass")

    ingest_mod.main()
    validate_data_mod.main()

    report = json.loads(
        (art_dir / ART_VALIDATION_REPORT_JSON).read_text(encoding="utf-8")
    )
    assert report["passed"] is True
    assert report["row_count"] > 0
    assert not _latest_step_run("integration-validate-data", STEP_VALIDATE_DATA).empty


def test_validate_data_aborts_on_too_few_rows(
    mlflow_sqlite: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    art_dir = _configure(
        tmp_path,
        monkeypatch,
        model_name="validate_data_fail",
        validation={"min_rows": 100_000},
    )

    ingest_mod.main()
    with pytest.raises(RuntimeError, match="Data validation failed"):
        validate_data_mod.main()

    report = json.loads(
        (art_dir / ART_VALIDATION_REPORT_JSON).read_text(encoding="utf-8")
    )
    assert report["passed"] is False
    assert any(
        check["name"] == "min_rows" and not check["passed"]
        for check in report["checks"]
    )
