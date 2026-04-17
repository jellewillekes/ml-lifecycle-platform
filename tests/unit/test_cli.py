from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, cast

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
        model_spec_path="configs/models/breast_cancer_demo.yaml",
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
    assert (
        captured_env["MLP_MODEL_SPEC_PATH"] == "configs/models/breast_cancer_demo.yaml"
    )


def test_cli_infra_up_prints_overridden_local_ports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli_main, "load_runtime_profile", lambda env_name=None: _profile(tmp_path)
    )
    monkeypatch.setenv("MLP_HOST_MLFLOW_PORT", "5051")
    monkeypatch.setenv("MLP_HOST_MINIO_CONSOLE_PORT", "9002")
    monkeypatch.setattr(cli_main, "_run", lambda command, env: 0)

    assert cli_main.main(["--env", "local", "infra", "up"]) == 0
    stdout = capsys.readouterr().out
    assert "http://localhost:5051" in stdout
    assert "http://localhost:9002" in stdout


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
    envs: list[dict[str, str]] = []
    monkeypatch.setattr(
        cli_main, "load_runtime_profile", lambda env_name=None: _profile(tmp_path)
    )
    monkeypatch.setattr(cli_main, "_port_is_available", lambda port: True)

    def fake_run(command: list[str], env: dict[str, str]) -> int:
        commands.append(command)
        envs.append(dict(env))
        return 0

    monkeypatch.setattr(cli_main, "_run", fake_run)

    assert (
        cli_main.main(["--env", "local", "serve", "api", "--model-name", "csv-model"])
        == 0
    )
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
    assert envs[-1]["MODEL_NAME"] == "csv-model"


def test_cli_serve_api_passes_model_spec_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    envs: list[dict[str, str]] = []
    monkeypatch.setattr(
        cli_main, "load_runtime_profile", lambda env_name=None: _profile(tmp_path)
    )
    monkeypatch.setattr(cli_main, "_port_is_available", lambda port: True)

    def fake_run(command: list[str], env: dict[str, str]) -> int:
        envs.append(dict(env))
        return 0

    monkeypatch.setattr(cli_main, "_run", fake_run)

    assert (
        cli_main.main(
            [
                "--env",
                "local",
                "serve",
                "api",
                "--model-spec",
                "configs/models/local_csv_binary_classifier.yaml",
            ]
        )
        == 0
    )
    assert (
        envs[-1]["MLP_MODEL_SPEC_PATH"]
        == "configs/models/local_csv_binary_classifier.yaml"
    )


def test_cli_serve_api_respects_host_port_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    envs: list[dict[str, str]] = []
    monkeypatch.setattr(
        cli_main, "load_runtime_profile", lambda env_name=None: _profile(tmp_path)
    )
    monkeypatch.setenv("MLP_HOST_SERVE_PORT", "8011")

    def fake_run(command: list[str], env: dict[str, str]) -> int:
        envs.append(dict(env))
        return 0

    monkeypatch.setattr(cli_main, "_run", fake_run)

    assert cli_main.main(["--env", "local", "serve", "api"]) == 0
    assert envs[-1]["MLP_HOST_SERVE_PORT"] == "8011"
    assert "http://localhost:8011" in capsys.readouterr().out


def test_cli_serve_api_fails_fast_when_default_port_is_busy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cli_main, "load_runtime_profile", lambda env_name=None: _profile(tmp_path)
    )
    monkeypatch.setattr(cli_main, "_port_is_available", lambda port: False)

    with pytest.raises(SystemExit) as error:
        cli_main.main(["--env", "local", "serve", "api"])

    assert error.value.code == (
        "Local serving needs host port 8000, but it is already in use. "
        "Re-run with MLP_HOST_SERVE_PORT=<free-port> make serve."
    )


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


def test_run_e2e_uses_ephemeral_host_ports_for_local_services(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    commands: list[list[str]] = []
    envs: list[dict[str, str]] = []
    teardown_envs: list[dict[str, str]] = []
    profile = _profile(tmp_path)

    def fake_run(command: list[str], env: dict[str, str]) -> int:
        commands.append(command)
        envs.append(dict(env))
        return 0

    def fake_subprocess_run(
        command: list[str],
        **kwargs: Any,
    ) -> subprocess.CompletedProcess[bytes]:
        if kwargs.get("stdout") is not None:
            return subprocess.CompletedProcess(command, 0, stdout=b"deadbeef")
        teardown_envs.append(dict(kwargs.get("env") or {}))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(cli_main, "_run", fake_run)
    monkeypatch.setattr(cli_main.subprocess, "run", fake_subprocess_run)

    assert cli_main._run_e2e(profile, keep_stack=False) == 0
    assert commands
    for env in envs:
        assert env["MLP_HOST_MLFLOW_PORT"] == "0"
        assert env["MLP_HOST_MINIO_PORT"] == "0"
        assert env["MLP_HOST_MINIO_CONSOLE_PORT"] == "0"
        assert env["MLP_HOST_SERVE_PORT"] == "0"
    assert teardown_envs[-1]["MLP_HOST_SERVE_PORT"] == "0"
    assert "ephemeral host ports for MLflow, MinIO API, MinIO console, serving" in (
        capsys.readouterr().out
    )
