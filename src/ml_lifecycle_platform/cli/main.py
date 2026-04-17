from __future__ import annotations

import argparse
from dataclasses import replace
import os
from pathlib import Path
import socket
import subprocess
import sys

from ml_lifecycle_platform.runtime.profile import RuntimeProfile, load_runtime_profile

SVC_INFRA = ("postgres", "minio", "minio-init", "mlflow-server")
SVC_IMAGES = ("mlflow-server", "pipeline", "promote", "rollback", "serving", "smoke")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _git_sha() -> str:
    try:
        output = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=_repo_root(),
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.SubprocessError, OSError):
        return "dev"
    return output.decode("utf-8").strip()


def _profile_env(profile: RuntimeProfile) -> dict[str, str]:
    return {
        "MLP_ENV": profile.environment,
        "MLFLOW_TRACKING_URI": profile.tracking_uri,
        "MLFLOW_REGISTRY_URI": profile.registry_uri,
        "EXPERIMENT_NAME": profile.experiment_name,
        "MODEL_NAME": profile.model_name,
        "MLP_MODEL_SPEC_PATH": profile.model_spec_path,
        "LOG_LEVEL": profile.log_level,
        "MLP_DATA_DIR": str(profile.data_dir),
        "MLP_ARTIFACTS_DIR": str(profile.artifacts_dir),
        "MLP_EVENT_LOG_PATH": str(profile.event_log_path),
        "PYTHON_EXECUTABLE": profile.python_executable,
        "CANARY_PCT": str(profile.canary_pct),
        "MLFLOW_S3_ENDPOINT_URL": profile.s3_endpoint_url,
        "AWS_ACCESS_KEY_ID": profile.aws_access_key_id,
        "MLP_COMPOSE_FILE": str(profile.compose_file),
        "MLP_COMPOSE_TRACKING_URI": profile.compose_tracking_uri,
        "MLP_COMPOSE_REGISTRY_URI": profile.compose_registry_uri,
        "MLP_COMPOSE_S3_ENDPOINT_URL": profile.compose_s3_endpoint_url,
        "MLP_COMPOSE_SERVE_URL": profile.compose_serve_url,
        "MLFLOW_HOST": profile.mlflow_host,
        "MLFLOW_PORT": str(profile.mlflow_port),
        "BACKEND_STORE_URI": profile.backend_store_uri,
        "ARTIFACT_ROOT": profile.artifact_root,
        "GIT_SHA": os.getenv("GIT_SHA", _git_sha()),
        "SERVE_URL": profile.compose_serve_url,
    }


def _command_env(
    profile: RuntimeProfile,
    overrides: dict[str, str] | None = None,
) -> dict[str, str]:
    env = _profile_env(profile)
    env.update(os.environ)
    if overrides:
        env.update(overrides)
    return env


def _run(command: list[str], env: dict[str, str]) -> int:
    completed = subprocess.run(
        command,
        check=False,
        cwd=_repo_root(),
        env=env,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)
    return int(completed.returncode)


def _compose_cmd(profile: RuntimeProfile, *args: str) -> list[str]:
    return ["docker", "compose", "-f", str(profile.compose_file), *args]


def _python_module_cmd(module: str, *args: str) -> list[str]:
    return [sys.executable, "-m", module, *args]


def _port_is_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _with_local_serving_host_port(
    env: dict[str, str], *, allow_ephemeral: bool
) -> dict[str, str]:
    if env.get("MLP_ENV") != "local":
        return env

    configured_port = env.get("MLP_HOST_SERVE_PORT", "").strip()
    if configured_port:
        return env

    if _port_is_available(8000):
        return env

    env = dict(env)
    if allow_ephemeral:
        env["MLP_HOST_SERVE_PORT"] = "0"
        print("Local port 8000 is busy; using an ephemeral host port for serving.")
        return env

    raise SystemExit(
        "Local serving needs host port 8000, but it is already in use. "
        "Re-run with MLP_HOST_SERVE_PORT=<free-port> make serve."
    )


def _local_host_port(env_var: str, default: str) -> str:
    return os.getenv(env_var, "").strip() or default


def _serving_api_message(host_port: str) -> str:
    if host_port == "0":
        return (
            "Serving API started on an ephemeral host port. "
            "Run `docker compose -f deployments/local/docker-compose.yml port serving 8000` "
            "to inspect it."
        )
    return f"Serving API: http://localhost:{host_port} (GET /health, POST /predict)"


def _with_local_e2e_host_ports(env: dict[str, str]) -> dict[str, str]:
    if env.get("MLP_ENV") != "local":
        return env

    env = dict(env)
    applied: list[str] = []
    for env_var, description in (
        ("MLP_HOST_MLFLOW_PORT", "MLflow"),
        ("MLP_HOST_MINIO_PORT", "MinIO API"),
        ("MLP_HOST_MINIO_CONSOLE_PORT", "MinIO console"),
        ("MLP_HOST_SERVE_PORT", "serving"),
    ):
        if env.get(env_var, "").strip():
            continue
        env[env_var] = "0"
        applied.append(description)

    if applied:
        print("Local e2e is using ephemeral host ports for " + ", ".join(applied) + ".")
    return env


def _handle_infra_up(args: argparse.Namespace, profile: RuntimeProfile) -> int:
    env = _command_env(profile)
    _run(_compose_cmd(profile, "up", "-d", *SVC_INFRA), env)
    print(
        f"MLflow UI: http://localhost:{_local_host_port('MLP_HOST_MLFLOW_PORT', '5050')}"
    )
    print(
        "MinIO Console: http://localhost:"
        f"{_local_host_port('MLP_HOST_MINIO_CONSOLE_PORT', '9001')}"
    )
    return 0


def _handle_infra_down(args: argparse.Namespace, profile: RuntimeProfile) -> int:
    return _run(_compose_cmd(profile, "down", "-v"), _command_env(profile))


def _handle_infra_logs(args: argparse.Namespace, profile: RuntimeProfile) -> int:
    return _run(
        _compose_cmd(profile, "logs", "-f", "--tail=200"), _command_env(profile)
    )


def _handle_infra_build(args: argparse.Namespace, profile: RuntimeProfile) -> int:
    command = ["build"]
    if args.no_cache:
        command.append("--no-cache")
    command.extend(SVC_IMAGES)
    return _run(_compose_cmd(profile, *command), _command_env(profile))


def _handle_pipeline_run(args: argparse.Namespace, profile: RuntimeProfile) -> int:
    env_overrides: dict[str, str] = {}
    if args.model_spec:
        env_overrides["MLP_MODEL_SPEC_PATH"] = args.model_spec
    env = _command_env(profile, env_overrides)
    _run(_compose_cmd(profile, "build", *SVC_IMAGES), env)
    return _run(
        _compose_cmd(profile, "run", "--rm", "--use-aliases", "pipeline"),
        env,
    )


def _handle_registry_promote(args: argparse.Namespace, profile: RuntimeProfile) -> int:
    env_overrides: dict[str, str] = {}
    if args.model_name:
        env_overrides["MODEL_NAME"] = args.model_name
    env = _command_env(profile, env_overrides)
    command = _compose_cmd(profile, "run", "--rm", "--use-aliases", "promote")
    if args.dry_run:
        command.extend(
            [
                "python",
                "-m",
                "ml_lifecycle_platform.registry.promote",
                "--dry-run",
                "--format",
                args.format,
            ]
        )
    return _run(command, env)


def _handle_registry_rollback(args: argparse.Namespace, profile: RuntimeProfile) -> int:
    env_overrides: dict[str, str] = {}
    if args.model_name:
        env_overrides["MODEL_NAME"] = args.model_name
    return _run(
        _compose_cmd(profile, "run", "--rm", "--use-aliases", "rollback"),
        _command_env(profile, env_overrides),
    )


def _handle_registry_reproduce(
    args: argparse.Namespace, profile: RuntimeProfile
) -> int:
    env_overrides: dict[str, str] = {}
    if args.model_name:
        env_overrides["MODEL_NAME"] = args.model_name

    command = _python_module_cmd(
        "ml_lifecycle_platform.registry.reproduce",
        "--report-path",
        args.report_path,
        "--format",
        args.format,
    )
    if args.model_name:
        command.extend(["--model-name", args.model_name])
    if args.model_version:
        command.extend(["--model-version", args.model_version])
    elif args.alias:
        command.extend(["--alias", args.alias])
    else:
        raise SystemExit("registry reproduce requires --model-version or --alias")

    return _run(command, _command_env(profile, env_overrides))


def _handle_serve_api(args: argparse.Namespace, profile: RuntimeProfile) -> int:
    env_overrides: dict[str, str] = {}
    if args.model_name:
        env_overrides["MODEL_NAME"] = args.model_name
    if args.model_spec:
        env_overrides["MLP_MODEL_SPEC_PATH"] = args.model_spec
    env = _with_local_serving_host_port(
        _command_env(profile, env_overrides),
        allow_ephemeral=False,
    )
    _run(_compose_cmd(profile, "build", *SVC_IMAGES), env)
    _run(_compose_cmd(profile, "up", "-d", "--build", "serving"), env)
    print(_serving_api_message(_local_host_port("MLP_HOST_SERVE_PORT", "8000")))
    return 0


def _handle_serve_smoke(args: argparse.Namespace, profile: RuntimeProfile) -> int:
    env_overrides: dict[str, str] = {}
    if args.model_name:
        env_overrides["MODEL_NAME"] = args.model_name
    if args.model_spec:
        env_overrides["MLP_MODEL_SPEC_PATH"] = args.model_spec
    return _run(
        _compose_cmd(
            profile,
            "run",
            "--rm",
            "--no-deps",
            "--use-aliases",
            "--build",
            "smoke",
        ),
        _command_env(profile, env_overrides),
    )


def _run_e2e(profile: RuntimeProfile, *, keep_stack: bool) -> int:
    env = _with_local_e2e_host_ports(_command_env(profile))
    try:
        _run(_compose_cmd(profile, "build", *SVC_IMAGES), env)
        _run(_compose_cmd(profile, "up", "-d", *SVC_INFRA), env)
        _run(_compose_cmd(profile, "run", "--rm", "--use-aliases", "pipeline"), env)
        _run(
            _compose_cmd(
                profile,
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
            ),
            env,
        )
        _run(_compose_cmd(profile, "run", "--rm", "--use-aliases", "promote"), env)
        _run(_compose_cmd(profile, "up", "-d", "--build", "serving"), env)
        _run(
            _compose_cmd(profile, "run", "--rm", "--use-aliases", "--build", "smoke"),
            env,
        )
    finally:
        if not keep_stack:
            subprocess.run(
                _compose_cmd(profile, "down", "-v"),
                check=False,
                cwd=_repo_root(),
                env=env,
            )
    return 0


def _handle_e2e(args: argparse.Namespace, profile: RuntimeProfile) -> int:
    if args.model_spec:
        profile = replace(profile, model_spec_path=args.model_spec)
    return _run_e2e(profile, keep_stack=args.keep_stack)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mlp",
        description="ML Lifecycle Platform CLI",
    )
    parser.add_argument(
        "--env",
        default="local",
        help="Runtime profile to use from configs/env/<name>.yaml",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    infra = subparsers.add_parser("infra", help="Infrastructure commands")
    infra_sub = infra.add_subparsers(dest="infra_command", required=True)
    infra_up = infra_sub.add_parser("up", help="Start local infra")
    infra_up.set_defaults(handler=_handle_infra_up)
    infra_down = infra_sub.add_parser("down", help="Stop local infra")
    infra_down.set_defaults(handler=_handle_infra_down)
    infra_logs = infra_sub.add_parser("logs", help="Tail local logs")
    infra_logs.set_defaults(handler=_handle_infra_logs)
    infra_build = infra_sub.add_parser("build", help="Build local images")
    infra_build.add_argument("--no-cache", action="store_true")
    infra_build.set_defaults(handler=_handle_infra_build)

    pipeline = subparsers.add_parser("pipeline", help="Pipeline commands")
    pipeline_sub = pipeline.add_subparsers(dest="pipeline_command", required=True)
    pipeline_run = pipeline_sub.add_parser("run", help="Run the local pipeline")
    pipeline_run.add_argument("--model-spec")
    pipeline_run.set_defaults(handler=_handle_pipeline_run)

    registry = subparsers.add_parser("registry", help="Registry commands")
    registry_sub = registry.add_subparsers(dest="registry_command", required=True)
    registry_promote = registry_sub.add_parser("promote", help="Promote candidate")
    registry_promote.add_argument("--dry-run", action="store_true")
    registry_promote.add_argument("--format", choices=["json", "text"], default="json")
    registry_promote.add_argument("--model-name")
    registry_promote.set_defaults(handler=_handle_registry_promote)
    registry_rollback = registry_sub.add_parser("rollback", help="Rollback prod")
    registry_rollback.add_argument("--model-name")
    registry_rollback.set_defaults(handler=_handle_registry_rollback)
    registry_reproduce = registry_sub.add_parser(
        "reproduce", help="Reproduce a registered model"
    )
    registry_reproduce.add_argument("--model-name")
    selector = registry_reproduce.add_mutually_exclusive_group(required=True)
    selector.add_argument("--model-version")
    selector.add_argument("--alias")
    registry_reproduce.add_argument("--report-path", default="reproduce_report.json")
    registry_reproduce.add_argument(
        "--format", choices=["json", "text"], default="json"
    )
    registry_reproduce.set_defaults(handler=_handle_registry_reproduce)

    serve = subparsers.add_parser("serve", help="Serving commands")
    serve_sub = serve.add_subparsers(dest="serve_command", required=True)
    serve_api = serve_sub.add_parser("api", help="Start serving API")
    serve_api.add_argument("--model-name")
    serve_api.add_argument("--model-spec")
    serve_api.set_defaults(handler=_handle_serve_api)
    serve_smoke = serve_sub.add_parser("smoke", help="Run serving smoke test")
    serve_smoke.add_argument("--model-name")
    serve_smoke.add_argument("--model-spec")
    serve_smoke.set_defaults(handler=_handle_serve_smoke)

    e2e = subparsers.add_parser("e2e", help="Run the local golden path")
    e2e.add_argument("--keep-stack", action="store_true")
    e2e.add_argument("--model-spec")
    e2e.set_defaults(handler=_handle_e2e)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    profile = load_runtime_profile(env_name=args.env)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0
    return int(handler(args, profile))


if __name__ == "__main__":
    raise SystemExit(main())
