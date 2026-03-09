from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from ml_lifecycle_platform.backends.local.event_store import LocalEventStore
from ml_lifecycle_platform.common.constants import RUNTIME_EVENT_SCHEMA_VERSION
from ml_lifecycle_platform.contracts.runtime_event import RuntimeEvent

pytestmark = pytest.mark.unit


def test_runtime_event_round_trips_json_payload() -> None:
    envelope = RuntimeEvent(
        event_type="release.promoted",
        payload={
            "model_name": "demo",
            "model_version": "7",
            "nested": {"ok": True},
        },
    )

    payload = envelope.to_dict()
    event_payload = cast(dict[str, object], payload["payload"])

    assert payload["schema_version"] == RUNTIME_EVENT_SCHEMA_VERSION
    assert payload["event_type"] == "release.promoted"
    assert event_payload["nested"] == {"ok": True}


def test_runtime_event_rejects_non_json_payload(tmp_path: Path) -> None:
    store = LocalEventStore(tmp_path / "events.jsonl")

    with pytest.raises(ValueError, match="payload"):
        store.append_event("release.promoted", {"bad": {1, 2, 3}})
