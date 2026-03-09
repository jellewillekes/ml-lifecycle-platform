from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ml_lifecycle_platform.core.ports import (
    ArtifactStore,
    EventStore,
    JobRunner,
    RuntimeMetadata,
    Secrets,
)


@dataclass(frozen=True)
class RuntimeContext:
    """Container for runtime wiring.

    UP-02 keeps this structural only. Concrete adapters are introduced in UP-03.
    """

    metadata: RuntimeMetadata
    model_name: str
    model_spec_path: str
    experiment_name: str
    log_level: str
    data_dir: Path
    artifacts_dir: Path
    artifact_store: ArtifactStore
    event_store: EventStore
    job_runner: JobRunner
    secrets: Secrets
