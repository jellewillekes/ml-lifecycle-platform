from __future__ import annotations

import json
from typing import Any

import pytest

from ml_lifecycle_platform.backends.gcp.bigquery_event_sink import (
    BigQueryPredictionEventSink,
    event_to_bq_row,
)
from ml_lifecycle_platform.contracts.model_ref import ModelRef
from ml_lifecycle_platform.contracts.prediction_event import (
    EventEnvelope,
    PredictionEvent,
)

pytestmark = pytest.mark.unit


def _event() -> PredictionEvent:
    return PredictionEvent(
        corr_id="req-1",
        event_time_ns=1_700_000_000_000_000_000,
        ingest_time_ns=1_700_000_000_000_000_100,
        model_ref=ModelRef(model_name="binance_btc_1m", alias="prod", version="3"),
        features={"ret_1": 0.5},
        prediction=1,
        latency_ns=4200,
        envelope=EventEnvelope(service="serving", env="staging", git_sha="abc"),
    )


class _StubClient:
    def __init__(self, errors: list[Any] | None = None) -> None:
        self.errors = errors or []
        self.calls: list[tuple[str, list[dict[str, Any]], list[str]]] = []

    def insert_rows_json(
        self, table: str, rows: list[dict[str, Any]], row_ids: list[str]
    ) -> list[Any]:
        self.calls.append((table, rows, row_ids))
        return self.errors


def test_event_to_bq_row_flattens_and_jsonifies() -> None:
    row = event_to_bq_row(_event())
    assert row["model_name"] == "binance_btc_1m"
    assert row["env"] == "staging"
    assert row["event_time"].startswith("2023-")  # derived TIMESTAMP partition col
    assert row["event_time_ns"] == 1_700_000_000_000_000_000
    assert json.loads(row["features"]) == {"ret_1": 0.5}
    assert json.loads(row["model_ref"])["model_name"] == "binance_btc_1m"


def test_write_batch_success_uses_idempotency_key() -> None:
    client = _StubClient()
    sink = BigQueryPredictionEventSink("p.d.t", client=client)
    event = _event()
    sink.write(event)
    assert len(client.calls) == 1
    table, _rows, row_ids = client.calls[0]
    assert table == "p.d.t"
    assert row_ids == [event.idempotency_key]


def test_write_batch_row_errors_raise() -> None:
    client = _StubClient(errors=[{"index": 0, "errors": ["bad row"]}])
    sink = BigQueryPredictionEventSink("p.d.t", client=client)
    with pytest.raises(RuntimeError, match="rejected"):
        sink.write(_event())


def test_write_batch_empty_is_noop() -> None:
    client = _StubClient()
    sink = BigQueryPredictionEventSink("p.d.t", client=client)
    sink.write_batch([])
    assert client.calls == []
