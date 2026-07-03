"""BigQuery ``BatchEventReader`` over ``prediction_events_v1`` (UP-32).

Runs a partition-pruned window query (filtering the ``event_time`` TIMESTAMP
partition column plus the exact ``event_time_ns`` bounds) and expands the
``features`` JSON column into DataFrame columns — the hosted parity for the
DuckDB reader.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

try:  # pragma: no cover - exercised only in the hosted image
    from google.cloud import bigquery
except Exception:  # pragma: no cover
    bigquery = None  # type: ignore[assignment]

EVENT_TIME_COLUMN = "event_time_ns"

_QUERY = """
SELECT event_time_ns, TO_JSON_STRING(features) AS features_json
FROM `{table}`
WHERE model_name = @model_name
  AND event_time >= TIMESTAMP_MICROS(@start_us)
  AND event_time < TIMESTAMP_MICROS(@end_us)
  AND event_time_ns >= @start_ns
  AND event_time_ns < @end_ns
ORDER BY event_time_ns
"""


class BigQueryEventReader:
    """Read prediction events from the BigQuery events table."""

    def __init__(self, table: str, *, client: Any | None = None) -> None:
        if client is None:
            if bigquery is None:
                raise RuntimeError("google-cloud-bigquery is not installed")
            client = bigquery.Client()
        self._client = client
        self._table = table

    def read_window(self, model_name: str, start_ns: int, end_ns: int) -> pd.DataFrame:
        if bigquery is None:
            raise RuntimeError("google-cloud-bigquery is not installed")
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("model_name", "STRING", model_name),
                # Partition pruning: widen to whole microseconds around the window.
                bigquery.ScalarQueryParameter("start_us", "INT64", start_ns // 1000),
                bigquery.ScalarQueryParameter("end_us", "INT64", -(-end_ns // 1000)),
                bigquery.ScalarQueryParameter("start_ns", "INT64", start_ns),
                bigquery.ScalarQueryParameter("end_ns", "INT64", end_ns),
            ]
        )
        result = self._client.query(
            _QUERY.format(table=self._table), job_config=job_config
        ).result()
        records: list[dict[str, Any]] = []
        for row in result:
            raw = row["features_json"]
            features = json.loads(raw) if raw else {}
            record: dict[str, Any] = {str(k): v for k, v in features.items()}
            record[EVENT_TIME_COLUMN] = int(row["event_time_ns"])
            records.append(record)
        return pd.DataFrame(records)
