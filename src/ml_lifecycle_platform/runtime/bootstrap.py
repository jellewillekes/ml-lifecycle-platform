"""Build the process-local RuntimeContext from the active runtime profile and
configure MLflow tracking/registry URIs for CLI and pipeline entrypoints."""

from __future__ import annotations

from functools import lru_cache

try:
    import mlflow
except Exception:  # pragma: no cover
    mlflow = None  # type: ignore[assignment]

from ml_lifecycle_platform.hosted_ci.mlflow_cloud_run_auth import (
    configure_mlflow_cloud_run_auth,
)
from ml_lifecycle_platform.backends.local.artifact_store import LocalArtifactStore
from ml_lifecycle_platform.backends.local.event_store import LocalEventStore
from ml_lifecycle_platform.backends.local.job_runner import LocalJobRunner
from ml_lifecycle_platform.backends.local.secrets import EnvSecrets
from ml_lifecycle_platform.core.ports import RuntimeMetadata
from ml_lifecycle_platform.runtime.context import RuntimeContext
from ml_lifecycle_platform.runtime.profile import (
    load_runtime_profile,
    reset_runtime_profile_cache,
)


def build_runtime_context() -> RuntimeContext:
    """Build runtime objects from the selected profile."""

    profile = load_runtime_profile()
    return RuntimeContext(
        metadata=RuntimeMetadata(
            environment=profile.environment,
            tracking_uri=profile.tracking_uri,
            registry_uri=profile.registry_uri,
            source="profile-bootstrap",
        ),
        model_name=profile.model_name,
        model_spec_path=profile.model_spec_path,
        experiment_name=profile.experiment_name,
        log_level=profile.log_level,
        data_dir=profile.data_dir,
        artifacts_dir=profile.artifacts_dir,
        artifact_store=LocalArtifactStore(profile.artifacts_dir),
        event_store=LocalEventStore(profile.event_log_path),
        job_runner=LocalJobRunner(python_executable=profile.python_executable),
        secrets=EnvSecrets(),
    )


@lru_cache(maxsize=1)
def get_runtime_context() -> RuntimeContext:
    return build_runtime_context()


def reset_runtime_context() -> None:
    get_runtime_context.cache_clear()
    reset_runtime_profile_cache()


def configure_mlflow(context: RuntimeContext | None = None) -> None:
    if mlflow is None:
        return
    # Most callers rely on process-global MLflow settings.
    runtime = context or get_runtime_context()
    configure_mlflow_cloud_run_auth()
    mlflow.set_tracking_uri(runtime.metadata.tracking_uri)
    mlflow.set_registry_uri(runtime.metadata.registry_uri)
