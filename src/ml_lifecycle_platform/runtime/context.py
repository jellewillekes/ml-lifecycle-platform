from __future__ import annotations

from dataclasses import dataclass

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
    artifact_store: ArtifactStore | None = None
    event_store: EventStore | None = None
    job_runner: JobRunner | None = None
    secrets: Secrets | None = None
