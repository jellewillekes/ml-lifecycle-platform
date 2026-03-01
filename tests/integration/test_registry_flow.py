from __future__ import annotations

from pathlib import Path

import mlflow
import pytest
from mlflow.tracking import MlflowClient
from sklearn.dummy import DummyClassifier

import ml_lifecycle_platform.registry.register as register_mod
from ml_lifecycle_platform.common.constants import (
    ALIAS_CANDIDATE,
    ALIAS_CHAMPION,
    ALIAS_PROD,
    ART_GATE_OK,
    ART_REGISTERED_VERSION,
    ART_TRAIN_RUN_ID,
    GATE_PASSED,
    MLFLOW_ARTIFACT_PATH_MODEL,
    TAG_CONFIG_HASH,
    TAG_DATASET_FINGERPRINT,
    TAG_GATE,
    TAG_GIT_SHA,
    TAG_PROMOTED_FROM_ALIAS,
    TAG_RELEASE_STATUS,
    TAG_SOURCE_RUN_ID,
    TAG_TRAINING_RUN_ID,
)
from ml_lifecycle_platform.registry.promote import main as promote_main

pytestmark = pytest.mark.integration


def _create_training_run() -> str:
    model = DummyClassifier(strategy="most_frequent")
    model.fit([[0.0], [1.0], [0.0], [1.0]], [0, 1, 0, 1])

    with mlflow.start_run(run_name="integration-train") as run:
        run_id = run.info.run_id
        mlflow.set_tag(TAG_DATASET_FINGERPRINT, "dataset-fingerprint")
        mlflow.set_tag(TAG_GIT_SHA, "deadbeef")
        mlflow.set_tag(TAG_CONFIG_HASH, "config-hash")
        mlflow.set_tag(TAG_TRAINING_RUN_ID, run_id)
        mlflow.sklearn.log_model(model, artifact_path=MLFLOW_ARTIFACT_PATH_MODEL)
        return run_id


def test_register_then_promote_flow_uses_local_mlflow_registry(
    mlflow_sqlite: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    experiment_name = "integration-registry-flow"
    model_name = "integration_registry_model"
    artifact_root = tmp_path / "mlflow-artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)

    mlflow.create_experiment(experiment_name, artifact_location=artifact_root.as_uri())
    mlflow.set_experiment(experiment_name)

    monkeypatch.setenv("EXPERIMENT_NAME", experiment_name)
    monkeypatch.setenv("MODEL_NAME", model_name)

    train_run_id = _create_training_run()

    art_dir = tmp_path / "pipeline-artifacts"
    art_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(register_mod, "ART_DIR", art_dir)

    (art_dir / ART_TRAIN_RUN_ID).write_text(train_run_id, encoding="utf-8")
    (art_dir / ART_GATE_OK).write_text("true", encoding="utf-8")

    register_mod.main()

    client = MlflowClient()
    candidate = client.get_model_version_by_alias(model_name, ALIAS_CANDIDATE)

    assert str(candidate.version) == "1"
    assert candidate.tags[TAG_SOURCE_RUN_ID] == train_run_id
    assert candidate.tags[TAG_TRAINING_RUN_ID] == train_run_id
    assert candidate.tags[TAG_DATASET_FINGERPRINT] == "dataset-fingerprint"
    assert candidate.tags[TAG_GIT_SHA] == "deadbeef"
    assert candidate.tags[TAG_CONFIG_HASH] == "config-hash"
    assert candidate.tags[TAG_GATE] == GATE_PASSED
    assert candidate.tags[TAG_RELEASE_STATUS] == ALIAS_CANDIDATE
    assert (art_dir / ART_REGISTERED_VERSION).read_text(encoding="utf-8").strip() == "1"

    promote_main(["--model-name", model_name, "--format", "json"])

    prod = client.get_model_version_by_alias(model_name, ALIAS_PROD)
    champion = client.get_model_version_by_alias(model_name, ALIAS_CHAMPION)
    promoted = client.get_model_version(model_name, prod.version)

    assert str(prod.version) == str(candidate.version)
    assert str(champion.version) == str(candidate.version)
    assert promoted.tags[TAG_RELEASE_STATUS] == ALIAS_PROD
    assert promoted.tags[TAG_PROMOTED_FROM_ALIAS] == ALIAS_CANDIDATE
