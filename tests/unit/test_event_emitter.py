from __future__ import annotations

import threading
from collections.abc import Sequence
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
from ml_lifecycle_platform.serving.event_emitter import (
    PredictionEventEmitter,
    build_event_sink,
)
from ml_lifecycle_platform.serving.settings import Settings

pytestmark = pytest.mark.unit


def _event(corr_id: str = "req-1") -> PredictionEvent:
    return PredictionEvent(
        corr_id=corr_id,
        event_time_ns=1_700_000_000_000_000_000,
        ingest_time_ns=1_700_000_000_000_000_100,
        model_ref=ModelRef(model_name="m", alias="prod", version="1"),
        features={"f": 1.0},
        prediction=1,
        latency_ns=10,
        envelope=EventEnvelope(service="serving", env="local"),
    )


class _BlockingSink:
    """Records writes; blocks the first write until released, so the queue
    fills deterministically while the worker is busy."""

    def __init__(self) -> None:
        self.entered = threading.Event()
        self.release = threading.Event()
        self.written: list[PredictionEvent] = []

    def write(self, event: PredictionEvent) -> None:
        self.write_batch([event])

    def write_batch(self, events: Sequence[PredictionEvent]) -> None:
        self.entered.set()
        self.release.wait(timeout=5)
        self.written.extend(events)

    def flush(self, timeout_s: float) -> None:
        return None

    def close(self) -> None:
        return None


def test_emit_drops_when_queue_full() -> None:
    sink = _BlockingSink()
    emitter = PredictionEventEmitter(sink, max_queue=1, batch_size=1)

    emitter.emit([_event("1")])  # worker dequeues this and blocks in write_batch
    assert sink.entered.wait(timeout=5)
    emitter.emit([_event("2")])  # fills the single queue slot
    emitter.emit([_event("3")])  # dropped
    emitter.emit([_event("4")])  # dropped

    sink.release.set()
    emitter.close()

    # Only the in-flight event and the one queued slot survive.
    assert len(sink.written) == 2


def test_emit_flushes_all_on_close() -> None:
    sink = _BlockingSink()
    sink.release.set()  # never block
    emitter = PredictionEventEmitter(sink, max_queue=100)
    emitter.emit([_event("a"), _event("b"), _event("c")])
    emitter.close()
    assert len(sink.written) == 3


def test_sink_error_does_not_crash_worker() -> None:
    class _BoomSink(_BlockingSink):
        def write_batch(self, events: Sequence[PredictionEvent]) -> None:
            raise RuntimeError("boom")

    sink = _BoomSink()
    sink.release.set()
    emitter = PredictionEventEmitter(sink, max_queue=100)
    emitter.emit([_event("a")])
    emitter.close()  # must return cleanly despite the sink raising


def test_build_event_sink_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MLP_EVENT_SINK", "none")
    assert build_event_sink(Settings()) is None


def test_build_event_sink_jsonl(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("MLP_EVENT_SINK", "jsonl")
    monkeypatch.setenv("MLP_EVENT_JSONL_PATH", str(tmp_path / "events.jsonl"))
    assert isinstance(build_event_sink(Settings()), LocalPredictionEventSink)


def test_build_event_sink_bigquery_requires_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MLP_EVENT_SINK", "bigquery")
    monkeypatch.delenv("MLP_EVENT_BQ_TABLE", raising=False)
    with pytest.raises(RuntimeError, match="MLP_EVENT_BQ_TABLE"):
        build_event_sink(Settings())


def test_build_event_sink_unknown_kind(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MLP_EVENT_SINK", "kafka")
    with pytest.raises(RuntimeError, match="unknown"):
        build_event_sink(Settings())
