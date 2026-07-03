"""Integration smoke test for the BigQuery event reader.

Skipped unless ``GCP_PROJECT_ID`` is set and BigQuery credentials are available.
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.integration

_PROJECT = os.getenv("GCP_PROJECT_ID")


@pytest.mark.skipif(not _PROJECT, reason="requires GCP_PROJECT_ID and BigQuery access")
def test_bigquery_event_reader_runs_a_window_query() -> None:
    pytest.importorskip("google.cloud.bigquery")

    from ml_lifecycle_platform.backends.gcp.bigquery_event_reader import (
        BigQueryEventReader,
    )

    table = os.getenv(
        "MLP_EVENT_BQ_TABLE", f"{_PROJECT}.mlp_events.prediction_events_v1"
    )
    reader = BigQueryEventReader(table)
    # A wide window; the query must run (the frame may be empty).
    df = reader.read_window("binance_btc_1m", 0, 9_000_000_000_000_000_000)
    assert df is not None
