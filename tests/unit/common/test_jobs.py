from __future__ import annotations

import logging
import re

import pytest

from ml_lifecycle_platform.common.jobs import start_job
from ml_lifecycle_platform.common.telemetry import reset_for_tests

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _reset():
    reset_for_tests()
    yield
    reset_for_tests()


def test_start_job_uses_mlp_run_id_env(monkeypatch, caplog):
    monkeypatch.setenv("MLP_RUN_ID", "fixed-run")
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

    caplog.set_level(logging.INFO)
    with start_job("promote") as run_id:
        assert run_id == "fixed-run"

    starts = [r for r in caplog.records if r.getMessage() == "job.start"]
    assert starts, "expected a job.start log record"
    assert getattr(starts[0], "job_name", None) == "promote"
    assert getattr(starts[0], "run_id", None) == "fixed-run"


def test_start_job_generates_run_id_when_unset(monkeypatch):
    monkeypatch.delenv("MLP_RUN_ID", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

    with start_job("pipeline") as run_id:
        assert re.fullmatch(r"[0-9a-f]{32}", run_id)
