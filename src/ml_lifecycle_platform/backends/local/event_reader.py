"""Local DuckDB ``BatchEventReader`` over the JSONL event file (UP-32).

DuckDB reads the newline-delimited events, filters to one model and time window
in SQL, and returns the features expanded into columns — the local parity for
the BigQuery reader. This is the read counterpart to the JSONL sink.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

EVENT_TIME_COLUMN = "event_time_ns"

_QUERY = """
SELECT event_time_ns, to_json(features) AS features_json
FROM read_json_auto(?, format='newline_delimited')
WHERE model_ref.model_name = ?
  AND event_time_ns >= ?
  AND event_time_ns < ?
ORDER BY event_time_ns
"""


class DuckDBEventReader:
    """Read prediction events from a JSONL file via DuckDB."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def read_window(self, model_name: str, start_ns: int, end_ns: int) -> pd.DataFrame:
        if not self._path.exists():
            return pd.DataFrame()
        connection = duckdb.connect(database=":memory:")
        try:
            rows = connection.execute(
                _QUERY, [str(self._path), model_name, start_ns, end_ns]
            ).fetchall()
        finally:
            connection.close()
        return _rows_to_frame(rows)


def _rows_to_frame(rows: list[Any]) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for event_time_ns, features_json in rows:
        features = json.loads(features_json) if features_json else {}
        record: dict[str, Any] = {str(key): value for key, value in features.items()}
        record[EVENT_TIME_COLUMN] = int(event_time_ns)
        records.append(record)
    return pd.DataFrame(records)
