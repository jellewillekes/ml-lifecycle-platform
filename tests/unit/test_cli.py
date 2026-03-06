from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from ml_lifecycle_platform.cli import main as cli_main
from ml_lifecycle_platform.runtime.profile import RuntimeProfile

pytestmark = pytest.mark.unit


def _profile(tmp_path: Path) -> RuntimeProfile:
    return RuntimeProfile(
        environment="local",
        tracking_uri="http://localhost:5050",
        registry_uri="http://localhost:5050",
        experiment_name="breast-cancer-platform",
        model_name="breast_cancer_clf",
        log_level="INFO",
        data_dir=tmp_path / "data",
        artifacts_dir=tmp_path / "artifacts",
        event_log_path=tmp_path / "artifacts" / "runtime-events.jsonl",
        python_executable="python",
        canary_pct=10,
        s3_endpoint_url="http://localhost:9000",
        aws_access_key_id="minioadmin",
        aws_secret_access_key="minioadmin",
        compose_file=tmp_path / "deployments" / "local" / "docker-compose.yml",
        compose_tracking_uri="http://mlflow-server:5000",
        compose_registry_uri="http://mlflow-server:5000",
        compose_s3_endpoint_url="http://minio:9000",
        compose_aws_access_key_id="minioadmin",
        compose_aws_secret_access_key="minioadmin",
        compose_serve_url="http://serving:8000",
        mlflow_host="0.0.0.0",
        mlflow_port=5000,
        backend_store_uri="postgresql://mlflow:mlflow@postgres:5432/mlflow",
        artifact_root="s3://mlflow/",
    )


def test_cli_infra_up_routes_to_compose(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_command: list[str] = []
    captured_env: dict[str, str] = {}
    monkeypatch.setattr(
        cli_main, "load_runtime_profile", lambda env_name=None: _profile(tmp_path)
    )

    def fake_run(command: list[str], env: dict[str, str]) -> int:
        captured_command[:] = command
        captured_env.update(env)
        return 0

    monkeypatch.setattr(cli_main, "_run", fake_run)

    assert cli_main.main(["--env", "local", "infra", "up"]) == 0
    assert captured_command == [
        "docker",
        "compose",
        "-f",
        str(_profile(tmp_path).compose_file),
        "up",
        "-d",
        "postgres",
        "minio",
        "minio-init",
        "mlflow-server",
    ]
    assert captured_env["MLP_ENV"] == "local"
    assert captured_env["MLP_COMPOSE_TRACKING_URI"] == "http://mlflow-server:5000"


def test_cli_pipeline_run_builds_then_runs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []
    monkeypatch.setattr(
        cli_main, "load_runtime_profile", lambda env_name=None: _profile(tmp_path)
    )

    def fake_run(command: list[str], env: dict[str, str]) -> int:
        commands.append(command)
        return 0

    monkeypatch.setattr(cli_main, "_run", fake_run)

    assert cli_main.main(["--env", "local", "pipeline", "run"]) == 0
    assert commands == [
        [
            "docker",
            "compose",
            "-f",
            str(_profile(tmp_path).compose_file),
            "build",
            "mlflow-server",
            "pipeline",
            "promote",
            "rollback",
            "serving",
            "smoke",
        ],
        [
            "docker",
            "compose",
            "-f",
            str(_profile(tmp_path).compose_file),
            "run",
            "--rm",
            "--use-aliases",
            "pipeline",
        ],
    ]


def test_cli_registry_promote_dry_run_routes_to_promote_module(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_command: list[str] = []
    monkeypatch.setattr(
        cli_main, "load_runtime_profile", lambda env_name=None: _profile(tmp_path)
    )

    def fake_run(command: list[str], env: dict[str, str]) -> int:
        captured_command[:] = command
        return 0

    monkeypatch.setattr(cli_main, "_run", fake_run)

    assert (
        cli_main.main(
            [
                "--env",
                "local",
                "registry",
                "promote",
                "--dry-run",
                "--format",
                "json",
            ]
        )
        == 0
    )
    assert captured_command == [
        "docker",
        "compose",
        "-f",
        str(_profile(tmp_path).compose_file),
        "run",
        "--rm",
        "--use-aliases",
        "promote",
        "python",
        "-m",
        "ml_lifecycle_platform.registry.promote",
        "--dry-run",
        "--format",
        "json",
    ]


def test_cli_serve_api_builds_and_starts_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []
    monkeypatch.setattr(
        cli_main, "load_runtime_profile", lambda env_name=None: _profile(tmp_path)
    )

    def fake_run(command: list[str], env: dict[str, str]) -> int:
        commands.append(command)
        return 0

    monkeypatch.setattr(cli_main, "_run", fake_run)

    assert cli_main.main(["--env", "local", "serve", "api"]) == 0
    assert commands == [
        [
            "docker",
            "compose",
            "-f",
            str(_profile(tmp_path).compose_file),
            "build",
            "mlflow-server",
            "pipeline",
            "promote",
            "rollback",
            "serving",
            "smoke",
        ],
        [
            "docker",
            "compose",
            "-f",
            str(_profile(tmp_path).compose_file),
            "up",
            "-d",
            "--build",
            "serving",
        ],
    ]


def test_cli_e2e_delegates_to_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        cli_main, "load_runtime_profile", lambda env_name=None: _profile(tmp_path)
    )

    def fake_run_e2e(profile: RuntimeProfile, *, keep_stack: bool) -> int:
        captured["profile"] = profile
        captured["keep_stack"] = keep_stack
        return 0

    monkeypatch.setattr(cli_main, "_run_e2e", fake_run_e2e)

    assert cli_main.main(["--env", "local", "e2e", "--keep-stack"]) == 0
    captured_profile = cast(RuntimeProfile, captured["profile"])
    assert captured_profile.environment == "local"
    assert captured["keep_stack"] is True
