from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Mapping


class LocalEventStore:
    """Append-only JSONL event log for local runtime use."""

    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def append_event(self, event_type: str, payload: Mapping[str, object]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event_type": event_type,
            "payload": dict(payload),
        }
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True))
            fh.write("\n")
