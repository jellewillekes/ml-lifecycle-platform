"""Integration test for the BigQuery event sink.

Skipped unless ``GCP_PROJECT_ID`` is set and BigQuery credentials are available.
Inserts one row into the Terraform-managed ``mlp_events.prediction_events_v1``
table; override the target with ``MLP_EVENT_BQ_TABLE``.
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.integration

_PROJECT = os.getenv("GCP_PROJECT_ID")


@pytest.mark.skipif(not _PROJECT, reason="requires GCP_PROJECT_ID and BigQuery access")
def test_bigquery_event_sink_inserts_row() -> None:
    pytest.importorskip("google.cloud.bigquery")

    from ml_lifecycle_platform.backends.gcp.bigquery_event_sink import (
        BigQueryPredictionEventSink,
    )
    from ml_lifecycle_platform.contracts.model_ref import ModelRef
    from ml_lifecycle_platform.contracts.prediction_event import (
        EventEnvelope,
        PredictionEvent,
    )

    table = os.getenv(
        "MLP_EVENT_BQ_TABLE", f"{_PROJECT}.mlp_events.prediction_events_v1"
    )
    sink = BigQueryPredictionEventSink(table)
    event = PredictionEvent(
        corr_id="integration-test",
        event_time_ns=1_700_000_000_000_000_000,
        ingest_time_ns=1_700_000_000_000_000_100,
        model_ref=ModelRef(model_name="integration_test", alias="prod", version="1"),
        features={"f": 1.0},
        prediction=1,
        latency_ns=10,
        envelope=EventEnvelope(service="serving", env="staging"),
    )

    # insert_rows_json raises on schema/permission failure; a clean return means
    # the row was accepted into the streaming buffer.
    sink.write(event)
    sink.close()
