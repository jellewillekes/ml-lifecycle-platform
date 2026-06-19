from __future__ import annotations

import json
from pathlib import Path

import pytest

from ml_lifecycle_platform.backends.local.prediction_event_sink import (
    LocalPredictionEventSink,
)
from ml_lifecycle_platform.contracts.model_ref import ModelRef
from ml_lifecycle_platform.contracts.prediction_event import (
    EventEnvelope,
    PredictionEvent,
)

pytestmark = pytest.mark.unit


def _event(corr_id: str = "req-1") -> PredictionEvent:
    return PredictionEvent(
        corr_id=corr_id,
        event_time_ns=1_700_000_000_000_000_000,
        ingest_time_ns=1_700_000_000_000_000_100,
        model_ref=ModelRef(model_name="binance_btc_1m", alias="prod", version="3"),
        features={"ret_1": 0.5, "vol": 12.0},
        prediction=1,
        latency_ns=4200,
        envelope=EventEnvelope(service="serving", env="local", git_sha="abc"),
    )


def _lines(path: Path) -> list[str]:
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_write_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    sink = LocalPredictionEventSink(path)
    event = _event()
    sink.write(event)
    lines = _lines(path)
    assert len(lines) == 1
    assert PredictionEvent.from_dict(json.loads(lines[0])) == event


def test_write_batch_appends_each(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    sink = LocalPredictionEventSink(path)
    sink.write_batch([_event("a"), _event("b")])
    sink.write(_event("c"))
    assert len(_lines(path)) == 3


def test_empty_batch_is_noop(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    sink = LocalPredictionEventSink(path)
    sink.write_batch([])
    assert not path.exists()


def test_fsync_flag_writes(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    sink = LocalPredictionEventSink(path, fsync=True)
    sink.write(_event())
    sink.flush(1.0)
    sink.close()
    assert len(_lines(path)) == 1
