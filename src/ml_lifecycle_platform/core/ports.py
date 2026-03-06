from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence, runtime_checkable


@runtime_checkable
class ArtifactStore(Protocol):
    """Portable artifact persistence boundary."""

    def write_bytes(self, path: str, content: bytes) -> None:
        """Persist raw bytes under a backend-specific path."""

    def read_bytes(self, path: str) -> bytes:
        """Load raw bytes from a backend-specific path."""


@runtime_checkable
class EventStore(Protocol):
    """Portable event append/query boundary."""

    def append_event(self, event_type: str, payload: Mapping[str, object]) -> None:
        """Append a typed event to durable storage."""


@runtime_checkable
class JobRunner(Protocol):
    """Portable boundary for one-shot control-plane jobs."""

    def run_module(
        self,
        module: str,
        *,
        args: Sequence[str] | None = None,
        env: Mapping[str, str] | None = None,
    ) -> int:
        """Run a Python module and return an exit code."""


@runtime_checkable
class Secrets(Protocol):
    """Portable secret retrieval boundary."""

    def get(self, name: str, *, default: str | None = None) -> str | None:
        """Return a secret value by logical name."""


@dataclass(frozen=True)
class RuntimeMetadata:
    """Runtime identity shared across command paths."""

    environment: str
    tracking_uri: str
    registry_uri: str
    source: str = "bootstrap"
