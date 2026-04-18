from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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
    ART_PROMOTION_DECISION_JSON,
    ART_RELEASE_MANIFEST_JSON,
    ART_ROLLBACK_TARGET_JSON,
    ART_REGISTERED_VERSION,
    ART_TRAIN_RUN_ID,
    GATE_PASSED,
    MLFLOW_ARTIFACT_PATH_MODEL,
    TAG_PREVIOUS_PROD_VERSION,
    TAG_CONFIG_HASH,
    TAG_DATASET_FINGERPRINT,
    TAG_GATE,
    TAG_GIT_SHA,
    TAG_MODEL_NAME,
    TAG_RELEASE_MANIFEST_PATH,
    TAG_PROMOTED_FROM_ALIAS,
    TAG_RELEASE_STATUS,
    TAG_SOURCE_RUN_ID,
    TAG_TRAINING_RUN_ID,
)
from ml_lifecycle_platform.hosted_ci.hosted_model_alias_verifier import (
    HostedModelAliasVerificationConfig,
    verify_model_alias,
)
from ml_lifecycle_platform.registry.promote import main as promote_main
from ml_lifecycle_platform.registry.release_evidence import artifact_root
from ml_lifecycle_platform.registry.rollback import rollback_prod

pytestmark = pytest.mark.integration


def _create_training_run(model_name: str = "integration_registry_model") -> str:
    model = DummyClassifier(strategy="most_frequent")
    model.fit([[0.0], [1.0], [0.0], [1.0]], [0, 1, 0, 1])

    with mlflow.start_run(run_name="integration-train") as run:
        run_id = run.info.run_id
        mlflow.set_tag(TAG_MODEL_NAME, model_name)
        mlflow.set_tag(TAG_DATASET_FINGERPRINT, "dataset-fingerprint")
        mlflow.set_tag(TAG_GIT_SHA, "deadbeef")
        mlflow.set_tag(TAG_CONFIG_HASH, "config-hash")
        mlflow.set_tag(TAG_TRAINING_RUN_ID, run_id)
        mlflow.sklearn.log_model(model, artifact_path=MLFLOW_ARTIFACT_PATH_MODEL)
        return run_id


def _download_json_artifact(
    client: MlflowClient,
    *,
    run_id: str,
    artifact_path: str,
) -> dict[str, Any]:
    downloaded = client.download_artifacts(run_id=run_id, path=artifact_path)
    return json.loads(Path(downloaded).read_text(encoding="utf-8"))


def test_register_then_promote_flow_uses_local_mlflow_registry(
    mlflow_sqlite: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    experiment_name = "integration-registry-flow"
    model_name = "integration_registry_model"
    artifact_root_path = tmp_path / "mlflow-artifacts"
    artifact_root_path.mkdir(parents=True, exist_ok=True)

    mlflow.create_experiment(
        experiment_name,
        artifact_location=artifact_root_path.as_uri(),
    )
    mlflow.set_experiment(experiment_name)

    monkeypatch.setenv("EXPERIMENT_NAME", experiment_name)
    monkeypatch.setenv("MODEL_NAME", model_name)

    train_run_id = _create_training_run(model_name)

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
    resolved_prod_version = verify_model_alias(
        HostedModelAliasVerificationConfig(
            tracking_uri=mlflow.get_tracking_uri(),
            tracking_token="local-test-token",
            model_name=model_name,
        )
    )

    assert str(prod.version) == str(candidate.version)
    assert str(champion.version) == str(candidate.version)
    assert resolved_prod_version == str(candidate.version)
    assert promoted.tags[TAG_RELEASE_STATUS] == ALIAS_PROD
    assert promoted.tags[TAG_PROMOTED_FROM_ALIAS] == ALIAS_CANDIDATE
    assert promoted.tags[TAG_RELEASE_MANIFEST_PATH] == (
        f"{artifact_root(operation='promote', model_name=model_name, model_version=str(candidate.version))}/"
        f"{ART_RELEASE_MANIFEST_JSON}"
    )

    release_root = artifact_root(
        operation="promote",
        model_name=model_name,
        model_version=str(candidate.version),
    )
    manifest = _download_json_artifact(
        client,
        run_id=train_run_id,
        artifact_path=f"{release_root}/{ART_RELEASE_MANIFEST_JSON}",
    )
    decision = _download_json_artifact(
        client,
        run_id=train_run_id,
        artifact_path=f"{release_root}/{ART_PROMOTION_DECISION_JSON}",
    )
    rollback_target = _download_json_artifact(
        client,
        run_id=train_run_id,
        artifact_path=f"{release_root}/{ART_ROLLBACK_TARGET_JSON}",
    )

    assert manifest["model_name"] == model_name
    assert manifest["model_version"] == str(candidate.version)
    assert manifest["current_prod_version"] == str(candidate.version)
    assert manifest["previous_prod_version"] is None
    assert decision["policy_outcome"]["allowed"] is True
    assert rollback_target["target_version"] is None


def test_rollback_uses_manifest_recorded_previous_prod(
    mlflow_sqlite: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    experiment_name = "integration-rollback-flow"
    model_name = "integration_rollback_model"
    artifact_root_path = tmp_path / "mlflow-artifacts"
    artifact_root_path.mkdir(parents=True, exist_ok=True)

    mlflow.create_experiment(
        experiment_name,
        artifact_location=artifact_root_path.as_uri(),
    )
    mlflow.set_experiment(experiment_name)

    monkeypatch.setenv("EXPERIMENT_NAME", experiment_name)
    monkeypatch.setenv("MODEL_NAME", model_name)

    art_dir = tmp_path / "pipeline-artifacts"
    art_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(register_mod, "ART_DIR", art_dir)

    first_run_id = _create_training_run(model_name)
    (art_dir / ART_TRAIN_RUN_ID).write_text(first_run_id, encoding="utf-8")
    (art_dir / ART_GATE_OK).write_text("true", encoding="utf-8")
    register_mod.main()
    promote_main(["--model-name", model_name, "--format", "json"])

    client = MlflowClient()
    first_prod = client.get_model_version_by_alias(model_name, ALIAS_PROD)
    assert str(first_prod.version) == "1"

    second_run_id = _create_training_run(model_name)
    (art_dir / ART_TRAIN_RUN_ID).write_text(second_run_id, encoding="utf-8")
    register_mod.main()
    promote_main(["--model-name", model_name, "--format", "json"])

    second_prod = client.get_model_version_by_alias(model_name, ALIAS_PROD)
    assert str(second_prod.version) == "2"

    release_root = artifact_root(
        operation="promote",
        model_name=model_name,
        model_version=str(second_prod.version),
    )
    manifest = _download_json_artifact(
        client,
        run_id=second_run_id,
        artifact_path=f"{release_root}/{ART_RELEASE_MANIFEST_JSON}",
    )
    assert manifest["previous_prod_version"] == "1"

    client.set_model_version_tag(
        name=model_name,
        version=str(second_prod.version),
        key=TAG_PREVIOUS_PROD_VERSION,
        value="999",
    )

    rollback_prod(client, model_name)

    rolled_back = client.get_model_version_by_alias(model_name, ALIAS_PROD)
    assert str(rolled_back.version) == "1"
