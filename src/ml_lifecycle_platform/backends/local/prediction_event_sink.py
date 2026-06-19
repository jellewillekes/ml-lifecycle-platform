"""Local JSONL ``PredictionEventSink`` — the dev/CI write path for the event
plane. Appends one prediction event per line; DuckDB reads it back for local
parity with the BigQuery adapter. fsync is configurable for durability tests."""

from __future__ import annotations

import json
import os
import threading
from collections.abc import Sequence
from pathlib import Path

from ml_lifecycle_platform.contracts.prediction_event import PredictionEvent


class LocalPredictionEventSink:
    """Append-only JSONL sink for prediction events.

    One JSON object per line, sorted keys for diffability. A lock serialises
    concurrent writers. Writes are synchronous, so ``flush`` and ``close`` are
    no-ops; fsync is off by default for throughput.
    """

    def __init__(self, path: Path, *, fsync: bool = False) -> None:
        self._path = path
        self._fsync = fsync
        self._lock = threading.Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    def write(self, event: PredictionEvent) -> None:
        self.write_batch([event])

    def write_batch(self, events: Sequence[PredictionEvent]) -> None:
        if not events:
            return
        payload = "".join(
            json.dumps(event.to_dict(), sort_keys=True) + "\n" for event in events
        )
        with self._lock, self._path.open("a", encoding="utf-8") as fh:
            fh.write(payload)
            if self._fsync:
                fh.flush()
                os.fsync(fh.fileno())

    def flush(self, timeout_s: float) -> None:
        return None

    def close(self) -> None:
        return None
