from __future__ import annotations

from pathlib import Path

import pytest

from ml_lifecycle_platform.backends.local.event_reader import DuckDBEventReader
from ml_lifecycle_platform.backends.local.prediction_event_sink import (
    LocalPredictionEventSink,
)
from ml_lifecycle_platform.contracts.model_ref import ModelRef
from ml_lifecycle_platform.contracts.prediction_event import (
    EventEnvelope,
    PredictionEvent,
)

pytestmark = pytest.mark.unit


def _event(model_name: str, event_time_ns: int, ret: float) -> PredictionEvent:
    return PredictionEvent(
        corr_id="c",
        event_time_ns=event_time_ns,
        ingest_time_ns=event_time_ns + 1,
        model_ref=ModelRef(model_name=model_name, alias="prod", version="1"),
        features={"ret_1": ret, "vol": 2.0},
        prediction=1,
        latency_ns=10,
        envelope=EventEnvelope(service="serving", env="local"),
    )


def test_reads_window_for_model(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    sink = LocalPredictionEventSink(path)
    sink.write_batch(
        [
            _event("m1", 100, 0.1),
            _event("m1", 200, 0.2),
            _event("m1", 300, 0.3),  # outside [100, 300)
            _event("m2", 150, 9.9),  # other model
        ]
    )

    df = DuckDBEventReader(path).read_window("m1", 100, 300)

    assert len(df) == 2
    assert {"ret_1", "vol", "event_time_ns"} <= set(df.columns)
    assert sorted(df["ret_1"].tolist()) == [0.1, 0.2]


def test_missing_file_returns_empty(tmp_path: Path) -> None:
    reader = DuckDBEventReader(tmp_path / "nope.jsonl")
    assert reader.read_window("m1", 0, 10).empty
