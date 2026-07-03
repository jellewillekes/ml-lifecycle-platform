"""Runtime port Protocols: structural types for the artifact store, event
store, job runner, secrets, and runtime metadata. Backend adapters (local,
hosted) implement these without inheritance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Mapping, Protocol, Sequence, runtime_checkable

if TYPE_CHECKING:
    import pandas as pd

    from ml_lifecycle_platform.contracts.prediction_event import PredictionEvent


@runtime_checkable
class ArtifactStore(Protocol):
    """Store artifacts by relative path."""

    def write_bytes(self, path: str, content: bytes) -> None:
        """Write one artifact blob."""

    def read_bytes(self, path: str) -> bytes:
        """Read one artifact blob."""


@runtime_checkable
class EventStore(Protocol):
    """Append structured events."""

    def append_event(self, event_type: str, payload: Mapping[str, object]) -> None:
        """Append one event."""


@runtime_checkable
class PredictionEventSink(Protocol):
    """Cold write path for prediction logging — the event plane.

    The destination for one prediction's inputs, output, latency, and model
    reference. Adapters (local JSONL, BigQuery, future S3/Parquet) implement
    this structurally so serving and runtime depend only on the port; this is
    the data-capture / prediction-logging component every managed ML platform
    has. Drift, replay, and feedback read from whatever this writes."""

    def write(self, event: PredictionEvent) -> None:
        """Persist one prediction event."""

    def write_batch(self, events: Sequence[PredictionEvent]) -> None:
        """Persist a batch of prediction events."""

    def flush(self, timeout_s: float) -> None:
        """Block until buffered events are persisted or the timeout elapses."""

    def close(self) -> None:
        """Flush remaining events and release resources."""


@runtime_checkable
class BatchEventReader(Protocol):
    """Read a model's prediction events in a time window for batch analysis.

    The cold-path read counterpart to ``PredictionEventSink``: drift, replay,
    and feedback read events back through this port. Adapters (local DuckDB over
    JSONL, BigQuery hosted) return one row per event with the event's features
    expanded into columns plus an ``event_time_ns`` column."""

    def read_window(self, model_name: str, start_ns: int, end_ns: int) -> pd.DataFrame:
        """Return events for ``model_name`` with event_time_ns in [start, end)."""


@runtime_checkable
class DataSource(Protocol):
    """Produce a model-ready labeled dataframe for one training run.

    The returned frame holds exactly the features declared in the model spec's
    feature contract plus the int {0, 1} label column. Adapters implement this
    structurally (no inheritance); the resolver maps a spec's source kind to
    the concrete adapter."""

    def fetch(self) -> pd.DataFrame:
        """Return the labeled dataset."""


@runtime_checkable
class JobRunner(Protocol):
    """Run one Python module and return its exit code."""

    def run_module(
        self,
        module: str,
        *,
        args: Sequence[str] | None = None,
        env: Mapping[str, str] | None = None,
    ) -> int:
        """Run one module."""


@runtime_checkable
class Secrets(Protocol):
    """Read named secrets."""

    def get(self, name: str, *, default: str | None = None) -> str | None:
        """Return one secret value."""


@dataclass(frozen=True)
class RuntimeMetadata:
    """Tracking and registry settings shared across one runtime."""

    environment: str
    tracking_uri: str
    registry_uri: str
    source: str = "bootstrap"
