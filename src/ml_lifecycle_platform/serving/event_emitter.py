"""Non-blocking prediction-event emission for serving.

A bounded queue plus one daemon worker decouples the cold event sink from the
predict path: the request enqueues with ``put_nowait`` and never blocks. On a
full queue the event is dropped and counted — the drop-on-full ring-buffer
behaviour that protects p95. The worker batches events to the active
``PredictionEventSink``; sink failures are counted, never raised into the
request path.
"""

from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Sequence
from pathlib import Path

from ml_lifecycle_platform.backends.gcp.bigquery_event_sink import (
    BigQueryPredictionEventSink,
)
from ml_lifecycle_platform.backends.local.prediction_event_sink import (
    LocalPredictionEventSink,
)
from ml_lifecycle_platform.contracts.prediction_event import PredictionEvent
from ml_lifecycle_platform.core.ports import PredictionEventSink

from .metrics import record_event_dropped
from .settings import Settings

logger = logging.getLogger("serving")

_SHUTDOWN = object()


def build_event_sink(settings: Settings) -> PredictionEventSink | None:
    """Resolve the configured cold sink, or ``None`` when emission is off."""
    kind = settings.event_sink.strip().lower()
    if kind in ("", "none"):
        return None
    if kind == "jsonl":
        return LocalPredictionEventSink(
            Path(settings.event_jsonl_path), fsync=settings.event_fsync
        )
    if kind == "bigquery":
        if not settings.event_bq_table:
            raise RuntimeError(
                "MLP_EVENT_BQ_TABLE is required when MLP_EVENT_SINK=bigquery"
            )
        return BigQueryPredictionEventSink(settings.event_bq_table)
    raise RuntimeError(f"unknown MLP_EVENT_SINK={settings.event_sink!r}")


class PredictionEventEmitter:
    """Owns the queue and the background worker draining it to the sink."""

    def __init__(
        self,
        sink: PredictionEventSink,
        *,
        max_queue: int,
        batch_size: int = 100,
    ) -> None:
        self._sink = sink
        self._batch_size = batch_size
        self._queue: queue.Queue[object] = queue.Queue(maxsize=max_queue)
        self._worker = threading.Thread(
            target=self._run, name="event-emitter", daemon=True
        )
        self._worker.start()

    def emit(self, events: Sequence[PredictionEvent]) -> None:
        """Enqueue events without blocking; drop and count on a full queue."""
        for event in events:
            try:
                self._queue.put_nowait(event)
            except queue.Full:
                record_event_dropped("queue_full")

    def _run(self) -> None:
        while True:
            item = self._queue.get()
            if item is _SHUTDOWN:
                return
            batch = [item]
            while len(batch) < self._batch_size:
                try:
                    nxt = self._queue.get_nowait()
                except queue.Empty:
                    break
                if nxt is _SHUTDOWN:
                    self._flush_batch(batch)
                    return
                batch.append(nxt)
            self._flush_batch(batch)

    def _flush_batch(self, batch: list[object]) -> None:
        events = [item for item in batch if isinstance(item, PredictionEvent)]
        if not events:
            return
        try:
            self._sink.write_batch(events)
        except Exception as exc:  # a sink failure must not kill the worker
            record_event_dropped("sink_error", len(events))
            logger.warning("prediction event sink write failed: %s", exc)

    def close(self, timeout_s: float = 5.0) -> None:
        self._queue.put(_SHUTDOWN)
        self._worker.join(timeout=timeout_s)
        try:
            self._sink.flush(timeout_s)
        finally:
            self._sink.close()
