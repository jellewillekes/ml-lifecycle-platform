from __future__ import annotations

import json
from pathlib import Path

import pytest

from ml_lifecycle_platform.backends.local.artifact_store import LocalArtifactStore
from ml_lifecycle_platform.backends.local.event_store import LocalEventStore
from ml_lifecycle_platform.backends.local.job_runner import LocalJobRunner
from ml_lifecycle_platform.backends.local.secrets import EnvSecrets
from ml_lifecycle_platform.common.constants import RUNTIME_EVENT_SCHEMA_VERSION
from ml_lifecycle_platform.runtime.bootstrap import get_runtime_context

pytestmark = pytest.mark.integration


def test_local_runtime_context_uses_local_adapters_and_env_overrides(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_dir = tmp_path / "data"
    artifacts_dir = tmp_path / "artifacts"
    tracking_uri = f"sqlite:///{tmp_path / 'mlflow.db'}"

    monkeypatch.setenv("MLFLOW_TRACKING_URI", tracking_uri)
    monkeypatch.setenv("MLFLOW_REGISTRY_URI", tracking_uri)
    monkeypatch.setenv("EXPERIMENT_NAME", "runtime-bootstrap-exp")
    monkeypatch.setenv("MODEL_NAME", "runtime-bootstrap-model")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("MLP_DATA_DIR", str(data_dir))
    monkeypatch.setenv("MLP_ARTIFACTS_DIR", str(artifacts_dir))

    runtime = get_runtime_context()

    assert runtime.metadata.environment == "local"
    assert runtime.metadata.tracking_uri == tracking_uri
    assert runtime.metadata.registry_uri == tracking_uri
    assert runtime.experiment_name == "runtime-bootstrap-exp"
    assert runtime.model_name == "runtime-bootstrap-model"
    assert runtime.log_level == "DEBUG"
    assert runtime.data_dir == data_dir
    assert runtime.artifacts_dir == artifacts_dir
    assert isinstance(runtime.artifact_store, LocalArtifactStore)
    assert isinstance(runtime.event_store, LocalEventStore)
    assert isinstance(runtime.job_runner, LocalJobRunner)
    assert isinstance(runtime.secrets, EnvSecrets)

    runtime.artifact_store.write_bytes("reports/test.txt", b"ok")
    assert (artifacts_dir / "reports" / "test.txt").read_text(encoding="utf-8") == "ok"

    runtime.event_store.append_event("runtime_bootstrap_test", {"status": "ok"})
    event_log = artifacts_dir / "runtime-events.jsonl"
    payload = json.loads(event_log.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert payload["schema_version"] == RUNTIME_EVENT_SCHEMA_VERSION
    assert payload["event_type"] == "runtime_bootstrap_test"
    assert payload["payload"] == {"status": "ok"}

    assert (
        runtime.job_runner.run_module(
            "ml_lifecycle_platform.cli.main",
            args=["--help"],
        )
        == 0
    )
