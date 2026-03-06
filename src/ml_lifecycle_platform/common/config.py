from pathlib import Path

from ml_lifecycle_platform.runtime.bootstrap import get_runtime_context


def env(name: str, default: str | None = None) -> str:
    runtime = get_runtime_context()
    v = runtime.secrets.get(name, default=default)
    if v is None:
        raise RuntimeError(f"Missing required env var: {name}")
    return str(v)


def get_tracking_uri() -> str:
    return get_runtime_context().metadata.tracking_uri


def get_registry_uri() -> str:
    return get_runtime_context().metadata.registry_uri


def get_experiment_name() -> str:
    return get_runtime_context().experiment_name


def get_model_name() -> str:
    return get_runtime_context().model_name


def get_log_level() -> str:
    return get_runtime_context().log_level


def get_data_dir() -> Path:
    return get_runtime_context().data_dir


def get_artifacts_dir() -> Path:
    return get_runtime_context().artifacts_dir
