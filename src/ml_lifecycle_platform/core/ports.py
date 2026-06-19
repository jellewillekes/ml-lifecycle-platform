"""Runtime port Protocols: structural types for the artifact store, event
store, job runner, secrets, and runtime metadata. Backend adapters (local,
hosted) implement these without inheritance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Mapping, Protocol, Sequence, runtime_checkable

if TYPE_CHECKING:
    import pandas as pd


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
