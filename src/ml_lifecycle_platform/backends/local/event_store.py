"""Append-only JSONL `EventStore` used by the local runtime to log validated
`RuntimeEvent` records for later inspection or replay."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, cast

from pydantic import JsonValue

from ml_lifecycle_platform.contracts.runtime_event import RuntimeEvent


class LocalEventStore:
    """Append-only JSONL event log for local runtime use."""

    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def append_event(self, event_type: str, payload: Mapping[str, object]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        entry = RuntimeEvent(
            event_type=event_type,
            payload=cast(dict[str, JsonValue], dict(payload)),
        ).to_dict()
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True))
            fh.write("\n")
