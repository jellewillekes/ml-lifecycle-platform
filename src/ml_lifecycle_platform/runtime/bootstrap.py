from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import sys

try:
    import mlflow
except Exception:  # pragma: no cover
    mlflow = None  # type: ignore[assignment]

from ml_lifecycle_platform.backends.local.artifact_store import LocalArtifactStore
from ml_lifecycle_platform.backends.local.event_store import LocalEventStore
from ml_lifecycle_platform.backends.local.job_runner import LocalJobRunner
from ml_lifecycle_platform.backends.local.secrets import EnvSecrets
from ml_lifecycle_platform.core.ports import RuntimeMetadata
from ml_lifecycle_platform.runtime.context import RuntimeContext

DEFAULT_TRACKING_URI = "http://localhost:5050"
DEFAULT_EXPERIMENT_NAME = "breast-cancer-platform"
DEFAULT_MODEL_NAME = "breast_cancer_clf"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_DATA_DIR = Path("/app/data")
DEFAULT_ARTIFACTS_DIR = Path("/app/artifacts")


def _secret_or_default(
    secrets: EnvSecrets,
    name: str,
    default: str,
) -> str:
    return str(secrets.get(name, default=default))


def build_runtime_context() -> RuntimeContext:
    """Build the local runtime context from environment-backed settings."""

    secrets = EnvSecrets()
    tracking_uri = _secret_or_default(
        secrets, "MLFLOW_TRACKING_URI", DEFAULT_TRACKING_URI
    )
    registry_uri = _secret_or_default(secrets, "MLFLOW_REGISTRY_URI", tracking_uri)
    experiment_name = _secret_or_default(
        secrets, "EXPERIMENT_NAME", DEFAULT_EXPERIMENT_NAME
    )
    model_name = _secret_or_default(secrets, "MODEL_NAME", DEFAULT_MODEL_NAME)
    log_level = _secret_or_default(secrets, "LOG_LEVEL", DEFAULT_LOG_LEVEL)

    data_dir = Path(_secret_or_default(secrets, "MLP_DATA_DIR", str(DEFAULT_DATA_DIR)))
    artifacts_dir = Path(
        _secret_or_default(secrets, "MLP_ARTIFACTS_DIR", str(DEFAULT_ARTIFACTS_DIR))
    )
    event_log_path = Path(
        _secret_or_default(
            secrets,
            "MLP_EVENT_LOG_PATH",
            str(artifacts_dir / "runtime-events.jsonl"),
        )
    )
    python_executable = _secret_or_default(secrets, "PYTHON_EXECUTABLE", sys.executable)

    return RuntimeContext(
        metadata=RuntimeMetadata(
            environment="local",
            tracking_uri=tracking_uri,
            registry_uri=registry_uri,
            source="local-runtime-bootstrap",
        ),
        model_name=model_name,
        experiment_name=experiment_name,
        log_level=log_level,
        data_dir=data_dir,
        artifacts_dir=artifacts_dir,
        artifact_store=LocalArtifactStore(artifacts_dir),
        event_store=LocalEventStore(event_log_path),
        job_runner=LocalJobRunner(python_executable=python_executable),
        secrets=secrets,
    )


@lru_cache(maxsize=1)
def get_runtime_context() -> RuntimeContext:
    return build_runtime_context()


def reset_runtime_context() -> None:
    get_runtime_context.cache_clear()


def configure_mlflow(context: RuntimeContext | None = None) -> None:
    if mlflow is None:
        return
    runtime = context or get_runtime_context()
    mlflow.set_tracking_uri(runtime.metadata.tracking_uri)
    mlflow.set_registry_uri(runtime.metadata.registry_uri)
