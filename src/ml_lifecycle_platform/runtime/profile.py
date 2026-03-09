from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, ValidationInfo
from pydantic import field_validator
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]

_NON_EMPTY_STR_FIELDS = (
    "environment",
    "tracking_uri",
    "registry_uri",
    "experiment_name",
    "model_name",
    "model_spec_path",
    "log_level",
    "python_executable",
    "s3_endpoint_url",
    "aws_access_key_id",
    "aws_secret_access_key",
    "compose_tracking_uri",
    "compose_registry_uri",
    "compose_s3_endpoint_url",
    "compose_aws_access_key_id",
    "compose_aws_secret_access_key",
    "compose_serve_url",
    "mlflow_host",
    "backend_store_uri",
    "artifact_root",
)

_PATH_FIELDS = ("data_dir", "artifacts_dir", "event_log_path", "compose_file")


def _resolve_path(value: str | Path, *, base: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (base / path).resolve()


class RuntimeProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

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
    canary_pct: int = Field(ge=0, le=100)
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
    mlflow_port: int = Field(ge=1, le=65535)
    backend_store_uri: str
    artifact_root: str

    @field_validator(*_NON_EMPTY_STR_FIELDS)
    @classmethod
    def _validate_non_empty_string(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must be a non-empty string")
        return stripped

    @field_validator(*_PATH_FIELDS, mode="before")
    @classmethod
    def _resolve_runtime_path(cls, value: str | Path, info: ValidationInfo) -> Path:
        base = info.context.get("base", REPO_ROOT) if info.context else REPO_ROOT
        return _resolve_path(value, base=base)


def _read_profile_yaml(profile_path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Profile at {profile_path} must contain a YAML mapping.")
    return dict(raw)


def _apply_env_overrides(payload: dict[str, Any]) -> dict[str, Any]:
    merged = dict(payload)

    data_dir_override = os.getenv("MLP_DATA_DIR")
    artifacts_dir_override = os.getenv("MLP_ARTIFACTS_DIR")
    event_log_override = os.getenv("MLP_EVENT_LOG_PATH")

    if data_dir_override:
        merged["data_dir"] = data_dir_override
    if artifacts_dir_override:
        merged["artifacts_dir"] = artifacts_dir_override

    if event_log_override:
        merged["event_log_path"] = event_log_override
    elif artifacts_dir_override:
        current_name = Path(
            str(merged.get("event_log_path", "artifacts/runtime-events.jsonl"))
        ).name
        merged["event_log_path"] = str(Path(artifacts_dir_override) / current_name)

    overrides = {
        "environment": os.getenv("MLP_ENV"),
        "tracking_uri": os.getenv("MLFLOW_TRACKING_URI"),
        "registry_uri": os.getenv("MLFLOW_REGISTRY_URI"),
        "experiment_name": os.getenv("EXPERIMENT_NAME"),
        "model_name": os.getenv("MODEL_NAME"),
        "model_spec_path": os.getenv("MLP_MODEL_SPEC_PATH"),
        "log_level": os.getenv("LOG_LEVEL"),
        "python_executable": os.getenv("PYTHON_EXECUTABLE"),
        "canary_pct": os.getenv("CANARY_PCT"),
        "s3_endpoint_url": os.getenv("MLFLOW_S3_ENDPOINT_URL"),
        "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
        "compose_file": os.getenv("MLP_COMPOSE_FILE"),
        "compose_tracking_uri": os.getenv("MLP_COMPOSE_TRACKING_URI"),
        "compose_registry_uri": os.getenv("MLP_COMPOSE_REGISTRY_URI"),
        "compose_s3_endpoint_url": os.getenv("MLP_COMPOSE_S3_ENDPOINT_URL"),
        "compose_aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
        "compose_aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
        "compose_serve_url": os.getenv("MLP_COMPOSE_SERVE_URL")
        or os.getenv("SERVE_URL"),
        "mlflow_host": os.getenv("MLFLOW_HOST"),
        "mlflow_port": os.getenv("MLFLOW_PORT"),
        "backend_store_uri": os.getenv("BACKEND_STORE_URI"),
        "artifact_root": os.getenv("ARTIFACT_ROOT"),
    }

    for key, value in overrides.items():
        if value is not None:
            merged[key] = value

    return merged


def _format_validation_error(
    profile_path: Path,
    error: ValidationError,
) -> ValueError:
    details = []
    for issue in error.errors(include_url=False):
        location = ".".join(str(part) for part in issue["loc"])
        details.append(f"{location}: {issue['msg']}")
    message = "; ".join(details)
    return ValueError(f"Profile at {profile_path} is invalid: {message}")


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
    raw = _read_profile_yaml(path)
    merged = _apply_env_overrides(raw)
    try:
        return RuntimeProfile.model_validate(merged, context={"base": REPO_ROOT})
    except ValidationError as error:
        raise _format_validation_error(path, error) from error


def reset_runtime_profile_cache() -> None:
    load_runtime_profile.cache_clear()
