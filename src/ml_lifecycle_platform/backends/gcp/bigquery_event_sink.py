"""BigQuery ``PredictionEventSink`` — the hosted cold write path for the event
plane. Maps each ``PredictionEvent`` onto the Terraform-managed
``prediction_events_v1`` table and streams it with a batched JSON insert.

The table schema is authored in Terraform (not derived from the Pydantic
model): ``event_time`` is a derived TIMESTAMP partition column, ``model_name``
and ``env`` are flattened top-level cluster keys, and ``model_ref`` /
``features`` / ``prediction`` are JSON columns. ``google-cloud-bigquery`` is
imported lazily so this module stays importable in minimal environments.
Row-level rejects and 5xx-after-retries raise; the serving emitter counts the
drop (the DLQ itself lands in UP-41).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

from ml_lifecycle_platform.contracts.prediction_event import PredictionEvent

try:  # pragma: no cover - exercised only in the hosted image
    from google.api_core import exceptions as gcp_exceptions
    from google.cloud import bigquery
except Exception:  # pragma: no cover
    bigquery = None  # type: ignore[assignment]
    gcp_exceptions = None  # type: ignore[assignment]


def _ns_to_timestamp(event_time_ns: int) -> str:
    """RFC3339 UTC timestamp for the partition column (µs precision is fine;
    the exact nanosecond value is preserved in ``event_time_ns``)."""
    seconds = event_time_ns / 1_000_000_000
    return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat()


def event_to_bq_row(event: PredictionEvent) -> dict[str, Any]:
    """Map a ``PredictionEvent`` onto one ``prediction_events_v1`` row."""
    return {
        "event_id": str(event.event_id),
        "corr_id": event.corr_id,
        "schema_version": event.schema_version,
        "event_time": _ns_to_timestamp(event.event_time_ns),
        "event_time_ns": event.event_time_ns,
        "ingest_time_ns": event.ingest_time_ns,
        "latency_ns": event.latency_ns,
        "model_name": event.model_ref.model_name,
        "env": event.envelope.env,
        "service": event.envelope.service,
        "git_sha": event.envelope.git_sha,
        "run_id": event.envelope.run_id,
        "model_ref": json.dumps(event.model_ref.to_dict(), sort_keys=True),
        "features": json.dumps(event.features, sort_keys=True),
        "prediction": json.dumps(event.prediction),
    }


def _retryable_exceptions() -> tuple[type[BaseException], ...]:
    if gcp_exceptions is None:
        return ()
    return (gcp_exceptions.ServerError,)


class BigQueryPredictionEventSink:
    """Batched streaming-insert sink for the ``prediction_events_v1`` table."""

    def __init__(
        self,
        table: str,
        *,
        client: Any | None = None,
        max_attempts: int = 3,
    ) -> None:
        if client is None:
            if bigquery is None:
                raise RuntimeError("google-cloud-bigquery is not installed")
            client = bigquery.Client()
        self._client = client
        self._table = table
        self._max_attempts = max_attempts

    def write(self, event: PredictionEvent) -> None:
        self.write_batch([event])

    def write_batch(self, events: Sequence[PredictionEvent]) -> None:
        if not events:
            return
        rows = [event_to_bq_row(event) for event in events]
        # event_id is the insert id, so retried inserts dedup best-effort.
        row_ids = [event.idempotency_key for event in events]
        retryable = _retryable_exceptions()
        last_error: object = None
        for _ in range(self._max_attempts):
            try:
                errors = self._client.insert_rows_json(
                    self._table, rows, row_ids=row_ids
                )
            except retryable as exc:  # 5xx — transient, retry
                last_error = exc
                continue
            if not errors:
                return
            # Row-level rejects are data/schema errors, not transient.
            raise RuntimeError(
                f"BigQuery rejected {len(errors)} of {len(rows)} rows: {errors}"
            )
        raise RuntimeError(
            f"BigQuery insert failed after {self._max_attempts} attempts: {last_error}"
        )

    def flush(self, timeout_s: float) -> None:
        # insert_rows_json is synchronous; nothing is buffered in this object.
        return None

    def close(self) -> None:
        closer = getattr(self._client, "close", None)
        if callable(closer):
            closer()
