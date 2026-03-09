from __future__ import annotations

from pathlib import Path

import pytest

from ml_lifecycle_platform.runtime.profile import (
    load_runtime_profile,
    reset_runtime_profile_cache,
)

pytestmark = pytest.mark.unit


def _write_profile(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "environment: local",
                "tracking_uri: http://localhost:5050",
                "registry_uri: http://localhost:5050",
                "experiment_name: breast-cancer-platform",
                "model_name: breast_cancer_clf",
                "model_spec_path: configs/models/breast_cancer_demo.yaml",
                "log_level: INFO",
                "data_dir: data",
                "artifacts_dir: artifacts",
                "event_log_path: artifacts/runtime-events.jsonl",
                "python_executable: python",
                "canary_pct: 10",
                "s3_endpoint_url: http://localhost:9000",
                "aws_access_key_id: minioadmin",
                "aws_secret_access_key: minioadmin",
                "compose_file: deployments/local/docker-compose.yml",
                "compose_tracking_uri: http://mlflow-server:5000",
                "compose_registry_uri: http://mlflow-server:5000",
                "compose_s3_endpoint_url: http://minio:9000",
                "compose_aws_access_key_id: minioadmin",
                "compose_aws_secret_access_key: minioadmin",
                "compose_serve_url: http://serving:8000",
                "mlflow_host: 0.0.0.0",
                "mlflow_port: 5000",
                "backend_store_uri: postgresql://mlflow:mlflow@postgres:5432/mlflow",
                "artifact_root: s3://mlflow/",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_load_runtime_profile_reads_yaml(tmp_path: Path) -> None:
    profile_path = tmp_path / "local.yaml"
    _write_profile(profile_path)

    profile = load_runtime_profile(profile_path=profile_path)

    assert profile.environment == "local"
    assert profile.model_name == "breast_cancer_clf"
    assert profile.model_spec_path == "configs/models/breast_cancer_demo.yaml"
    assert profile.compose_file.name == "docker-compose.yml"
    assert profile.mlflow_port == 5000


def test_load_runtime_profile_env_overrides_take_precedence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile_path = tmp_path / "local.yaml"
    _write_profile(profile_path)
    monkeypatch.setenv("MODEL_NAME", "override-model")
    monkeypatch.setenv(
        "MLP_MODEL_SPEC_PATH", "configs/models/local_csv_binary_classifier.yaml"
    )
    monkeypatch.setenv("CANARY_PCT", "25")
    monkeypatch.setenv("MLP_COMPOSE_SERVE_URL", "http://override-serving:9000")
    monkeypatch.setenv("MLP_ARTIFACTS_DIR", str(tmp_path / "override-artifacts"))

    profile = load_runtime_profile(profile_path=profile_path)

    assert profile.model_name == "override-model"
    assert profile.model_spec_path == "configs/models/local_csv_binary_classifier.yaml"
    assert profile.canary_pct == 25
    assert profile.compose_serve_url == "http://override-serving:9000"
    assert profile.event_log_path == (
        tmp_path / "override-artifacts" / "runtime-events.jsonl"
    )


def test_load_runtime_profile_rejects_missing_required_field(tmp_path: Path) -> None:
    profile_path = tmp_path / "invalid.yaml"
    profile_path.write_text(
        "environment: local\ntracking_uri: http://localhost:5050\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="registry_uri"):
        load_runtime_profile(profile_path=profile_path)


def test_all_committed_runtime_profiles_load() -> None:
    profile_paths = sorted(Path("configs/env").glob("*.yaml"))

    assert profile_paths

    for profile_path in profile_paths:
        reset_runtime_profile_cache()
        profile = load_runtime_profile(profile_path=profile_path)
        assert profile.environment
        assert profile.model_name
        assert profile.model_spec_path
        assert profile.compose_file.exists()
        assert profile.event_log_path.name


def teardown_function() -> None:
    reset_runtime_profile_cache()
