from __future__ import annotations

import json
from pathlib import Path

import mlflow
import pytest
import yaml
from mlflow.tracking import MlflowClient

import ml_lifecycle_platform.pipeline.evaluate as evaluate_mod
import ml_lifecycle_platform.pipeline.featurize as featurize_mod
import ml_lifecycle_platform.pipeline.ingest as ingest_mod
import ml_lifecycle_platform.pipeline.train as train_mod
import ml_lifecycle_platform.registry.promote as promote_mod
import ml_lifecycle_platform.registry.register as register_mod
import ml_lifecycle_platform.registry.reproduce as reproduce_mod
from ml_lifecycle_platform.common.constants import (
    ALIAS_CANDIDATE,
    ALIAS_CHAMPION,
    ALIAS_PROD,
    ART_GATE_OK,
    ART_REGISTERED_VERSION,
    ART_REPRO_REPORT_JSON,
    ART_TRAIN_RUN_ID,
    STEP_TRAIN,
    TAG_DETERMINISTIC_SEED,
    TAG_ENV_LOCK_HASH,
    TAG_PROMOTED_FROM_ALIAS,
    TAG_REPRO_SCHEMA_VERSION,
    TAG_RELEASE_STATUS,
    TAG_SOURCE_RUN_ID,
    TAG_STEP,
)

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]


def _latest_train_run_id(experiment_id: str) -> str:
    runs = mlflow.search_runs(
        experiment_ids=[experiment_id],
        filter_string=f"tags.{TAG_STEP} = '{STEP_TRAIN}'",
        order_by=["attributes.start_time DESC"],
        max_results=1,
    )
    if hasattr(runs, "empty") and hasattr(runs, "iloc"):
        assert not runs.empty
        return str(runs.iloc[0]["run_id"])
    assert isinstance(runs, list)
    return str(runs[0].info.run_id)


def _configure_local_pipeline_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path]:
    data_dir = tmp_path / "data"
    art_dir = tmp_path / "artifacts"

    monkeypatch.setattr(ingest_mod, "DATA_DIR", data_dir)
    monkeypatch.setattr(featurize_mod, "DATA_DIR", data_dir)
    monkeypatch.setattr(featurize_mod, "ART_DIR", art_dir)
    monkeypatch.setattr(train_mod, "DATA_DIR", data_dir)
    monkeypatch.setattr(train_mod, "ART_DIR", art_dir)
    monkeypatch.setattr(evaluate_mod, "DATA_DIR", data_dir)
    monkeypatch.setattr(evaluate_mod, "ART_DIR", art_dir)
    monkeypatch.setattr(register_mod, "ART_DIR", art_dir)

    return data_dir, art_dir


def _run_pipeline_and_register_candidate(
    *,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_spec_path: str = "configs/models/breast_cancer_demo.yaml",
    model_name: str = "integration_reproduce_model",
) -> tuple[MlflowClient, str, str]:
    experiment_name = "integration-reproduce"
    artifact_root = tmp_path / "mlflow-artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)

    mlflow.create_experiment(experiment_name, artifact_location=artifact_root.as_uri())
    mlflow.set_experiment(experiment_name)
    monkeypatch.setenv("EXPERIMENT_NAME", experiment_name)
    monkeypatch.setenv(
        "MLP_MODEL_SPEC_PATH",
        str(
            _write_model_spec(
                tmp_path, source_spec_path=source_spec_path, model_name=model_name
            )
        ),
    )

    _, art_dir = _configure_local_pipeline_paths(tmp_path, monkeypatch)

    ingest_mod.main()
    featurize_mod.main()
    train_mod.main()

    exp = mlflow.get_experiment_by_name(experiment_name)
    assert exp is not None
    train_run_id = _latest_train_run_id(exp.experiment_id)
    (art_dir / ART_TRAIN_RUN_ID).write_text(train_run_id, encoding="utf-8")

    evaluate_mod.main()
    assert (art_dir / ART_GATE_OK).read_text(encoding="utf-8").strip() == "true"

    register_mod.main()
    assert (art_dir / ART_REGISTERED_VERSION).read_text(encoding="utf-8").strip() == "1"

    client = MlflowClient()
    candidate = client.get_model_version_by_alias(model_name, ALIAS_CANDIDATE)
    assert candidate.tags[TAG_SOURCE_RUN_ID] == train_run_id
    assert candidate.tags[TAG_ENV_LOCK_HASH]
    assert candidate.tags[TAG_DETERMINISTIC_SEED] == "42"
    assert candidate.tags[TAG_REPRO_SCHEMA_VERSION]
    return client, model_name, str(candidate.version)


def _write_model_spec(
    tmp_path: Path,
    *,
    source_spec_path: str,
    model_name: str,
) -> Path:
    source_path = REPO_ROOT / source_spec_path
    payload = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    payload["model_name"] = model_name
    source_cfg = payload.get("source")
    if isinstance(source_cfg, dict) and source_cfg.get("kind") == "csv":
        raw_path = source_cfg.get("path")
        if isinstance(raw_path, str):
            source_cfg["path"] = str((source_path.parent / raw_path).resolve())
    spec_path = tmp_path / f"{model_name}.yaml"
    spec_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return spec_path


def test_reproduce_from_registered_model_version_matches_training_run(
    mlflow_sqlite: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, model_name, version = _run_pipeline_and_register_candidate(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )
    report_path = tmp_path / ART_REPRO_REPORT_JSON

    with pytest.raises(SystemExit) as exc:
        reproduce_mod.main(
            [
                "--model-name",
                model_name,
                "--model-version",
                version,
                "--report-path",
                str(report_path),
                "--format",
                "json",
            ]
        )

    assert exc.value.code == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "matched"
    assert report["checks"]["prediction_parity"]["matched"] is True
    assert report["checks"]["env_lock_hash"]["matched"] is True


def test_reproduce_fails_with_precise_reason_when_env_lock_does_not_match(
    mlflow_sqlite: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, model_name, version = _run_pipeline_and_register_candidate(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )
    report_path = tmp_path / ART_REPRO_REPORT_JSON
    monkeypatch.setattr(reproduce_mod, "get_uv_lock_hash", lambda: "tampered-lock-hash")

    with pytest.raises(SystemExit) as exc:
        reproduce_mod.main(
            [
                "--model-name",
                model_name,
                "--model-version",
                version,
                "--report-path",
                str(report_path),
                "--format",
                "json",
            ]
        )

    assert exc.value.code == 2
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "failed"
    assert report["reason"] == "env_lock_mismatch"


def test_csv_model_spec_trains_and_registers(
    mlflow_sqlite: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, model_name, version = _run_pipeline_and_register_candidate(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        source_spec_path="configs/models/local_csv_binary_classifier.yaml",
        model_name="integration_csv_model",
    )

    candidate = client.get_model_version(model_name, version)
    assert candidate.tags[TAG_SOURCE_RUN_ID]


def test_demo_model_spec_passes_registration_and_promotion_flow(
    mlflow_sqlite: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, model_name, version = _run_pipeline_and_register_candidate(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        source_spec_path="configs/models/breast_cancer_demo.yaml",
        model_name="integration_demo_model",
    )

    promote_mod.main(["--model-name", model_name, "--format", "json"])

    candidate = client.get_model_version(model_name, version)
    prod = client.get_model_version_by_alias(model_name, ALIAS_PROD)
    champion = client.get_model_version_by_alias(model_name, ALIAS_CHAMPION)

    assert str(prod.version) == version
    assert str(champion.version) == version
    assert candidate.tags[TAG_RELEASE_STATUS] == ALIAS_PROD
    assert candidate.tags[TAG_PROMOTED_FROM_ALIAS] == ALIAS_CANDIDATE
