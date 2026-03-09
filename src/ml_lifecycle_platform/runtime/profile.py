from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]


def _resolve_path(value: str, *, base: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (base / path).resolve()


def _require_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Profile field {key!r} must be a non-empty string.")
    return value


def _require_int(data: dict[str, Any], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int):
        raise ValueError(f"Profile field {key!r} must be an integer.")
    return value


@dataclass(frozen=True)
class RuntimeProfile:
    environment: str
    tracking_uri: str
    registry_uri: str
    experiment_name: str
    model_name: str
    model_spec_path: str
    log_level: str
    data_dir: Path
    artifacts_dir: Path
    event_log_path: Path
    python_executable: str
    canary_pct: int
    s3_endpoint_url: str
    aws_access_key_id: str
    aws_secret_access_key: str
    compose_file: Path
    compose_tracking_uri: str
    compose_registry_uri: str
    compose_s3_endpoint_url: str
    compose_aws_access_key_id: str
    compose_aws_secret_access_key: str
    compose_serve_url: str
    mlflow_host: str
    mlflow_port: int
    backend_store_uri: str
    artifact_root: str


def _profile_from_dict(data: dict[str, Any], *, base: Path) -> RuntimeProfile:
    return RuntimeProfile(
        environment=_require_str(data, "environment"),
        tracking_uri=_require_str(data, "tracking_uri"),
        registry_uri=_require_str(data, "registry_uri"),
        experiment_name=_require_str(data, "experiment_name"),
        model_name=_require_str(data, "model_name"),
        model_spec_path=_require_str(data, "model_spec_path"),
        log_level=_require_str(data, "log_level"),
        data_dir=_resolve_path(_require_str(data, "data_dir"), base=base),
        artifacts_dir=_resolve_path(_require_str(data, "artifacts_dir"), base=base),
        event_log_path=_resolve_path(_require_str(data, "event_log_path"), base=base),
        python_executable=_require_str(data, "python_executable"),
        canary_pct=_require_int(data, "canary_pct"),
        s3_endpoint_url=_require_str(data, "s3_endpoint_url"),
        aws_access_key_id=_require_str(data, "aws_access_key_id"),
        aws_secret_access_key=_require_str(data, "aws_secret_access_key"),
        compose_file=_resolve_path(_require_str(data, "compose_file"), base=base),
        compose_tracking_uri=_require_str(data, "compose_tracking_uri"),
        compose_registry_uri=_require_str(data, "compose_registry_uri"),
        compose_s3_endpoint_url=_require_str(data, "compose_s3_endpoint_url"),
        compose_aws_access_key_id=_require_str(data, "compose_aws_access_key_id"),
        compose_aws_secret_access_key=_require_str(
            data, "compose_aws_secret_access_key"
        ),
        compose_serve_url=_require_str(data, "compose_serve_url"),
        mlflow_host=_require_str(data, "mlflow_host"),
        mlflow_port=_require_int(data, "mlflow_port"),
        backend_store_uri=_require_str(data, "backend_store_uri"),
        artifact_root=_require_str(data, "artifact_root"),
    )


def _read_profile_file(profile_path: Path) -> RuntimeProfile:
    raw = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Profile at {profile_path} must contain a YAML mapping.")
    return _profile_from_dict(raw, base=REPO_ROOT)


def _apply_env_overrides(profile: RuntimeProfile) -> RuntimeProfile:
    data_dir_override = os.getenv("MLP_DATA_DIR")
    artifacts_dir_override = os.getenv("MLP_ARTIFACTS_DIR")
    event_log_override = os.getenv("MLP_EVENT_LOG_PATH")

    data_dir = _resolve_path(data_dir_override or str(profile.data_dir), base=REPO_ROOT)
    artifacts_dir = _resolve_path(
        artifacts_dir_override or str(profile.artifacts_dir),
        base=REPO_ROOT,
    )
    if event_log_override:
        event_log_path = _resolve_path(event_log_override, base=REPO_ROOT)
    elif artifacts_dir_override:
        event_log_path = artifacts_dir / profile.event_log_path.name
    else:
        event_log_path = _resolve_path(str(profile.event_log_path), base=REPO_ROOT)

    return RuntimeProfile(
        environment=os.getenv("MLP_ENV", profile.environment),
        tracking_uri=os.getenv("MLFLOW_TRACKING_URI", profile.tracking_uri),
        registry_uri=os.getenv("MLFLOW_REGISTRY_URI", profile.registry_uri),
        experiment_name=os.getenv("EXPERIMENT_NAME", profile.experiment_name),
        model_name=os.getenv("MODEL_NAME", profile.model_name),
        model_spec_path=os.getenv("MLP_MODEL_SPEC_PATH", profile.model_spec_path),
        log_level=os.getenv("LOG_LEVEL", profile.log_level),
        data_dir=data_dir,
        artifacts_dir=artifacts_dir,
        event_log_path=event_log_path,
        python_executable=os.getenv("PYTHON_EXECUTABLE", profile.python_executable),
        canary_pct=int(os.getenv("CANARY_PCT", str(profile.canary_pct))),
        s3_endpoint_url=os.getenv("MLFLOW_S3_ENDPOINT_URL", profile.s3_endpoint_url),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", profile.aws_access_key_id),
        aws_secret_access_key=os.getenv(
            "AWS_SECRET_ACCESS_KEY", profile.aws_secret_access_key
        ),
        compose_file=_resolve_path(
            os.getenv("MLP_COMPOSE_FILE", str(profile.compose_file)),
            base=REPO_ROOT,
        ),
        compose_tracking_uri=os.getenv(
            "MLP_COMPOSE_TRACKING_URI", profile.compose_tracking_uri
        ),
        compose_registry_uri=os.getenv(
            "MLP_COMPOSE_REGISTRY_URI", profile.compose_registry_uri
        ),
        compose_s3_endpoint_url=os.getenv(
            "MLP_COMPOSE_S3_ENDPOINT_URL", profile.compose_s3_endpoint_url
        ),
        compose_aws_access_key_id=os.getenv(
            "AWS_ACCESS_KEY_ID", profile.compose_aws_access_key_id
        ),
        compose_aws_secret_access_key=os.getenv(
            "AWS_SECRET_ACCESS_KEY", profile.compose_aws_secret_access_key
        ),
        compose_serve_url=os.getenv(
            "MLP_COMPOSE_SERVE_URL",
            os.getenv("SERVE_URL", profile.compose_serve_url),
        ),
        mlflow_host=os.getenv("MLFLOW_HOST", profile.mlflow_host),
        mlflow_port=int(os.getenv("MLFLOW_PORT", str(profile.mlflow_port))),
        backend_store_uri=os.getenv("BACKEND_STORE_URI", profile.backend_store_uri),
        artifact_root=os.getenv("ARTIFACT_ROOT", profile.artifact_root),
    )


def resolve_profile_path(
    env_name: str | None = None,
    profile_path: str | Path | None = None,
) -> Path:
    if profile_path is not None:
        return Path(profile_path).resolve()

    explicit_path = os.getenv("MLP_PROFILE_PATH")
    if explicit_path:
        return Path(explicit_path).resolve()

    selected_env = env_name or os.getenv("MLP_ENV", "local")
    return (REPO_ROOT / "configs" / "env" / f"{selected_env}.yaml").resolve()


@lru_cache(maxsize=8)
def load_runtime_profile(
    env_name: str | None = None,
    profile_path: str | Path | None = None,
) -> RuntimeProfile:
    path = resolve_profile_path(env_name=env_name, profile_path=profile_path)
    return _apply_env_overrides(_read_profile_file(path))


def reset_runtime_profile_cache() -> None:
    load_runtime_profile.cache_clear()
