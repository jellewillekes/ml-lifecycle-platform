from __future__ import annotations

import io
import json
import logging

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from ml_lifecycle_platform.common.logging import (
    JsonFormatter,
    bind_log_context,
    clear_log_context,
    configure_logging,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _reset_log_context():
    clear_log_context()
    yield
    clear_log_context()


def _capture(formatter: JsonFormatter) -> tuple[logging.Logger, io.StringIO]:
    logger = logging.getLogger(f"test.{id(formatter)}")
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger, buf


def test_json_formatter_emits_cloud_logging_severity():
    logger, buf = _capture(JsonFormatter(service="test-svc"))
    logger.warning("boom")
    payload = json.loads(buf.getvalue().strip())
    assert payload["severity"] == "WARNING"
    assert payload["service"] == "test-svc"
    assert payload["message"] == "boom"


def test_json_formatter_includes_bound_context():
    logger, buf = _capture(JsonFormatter(service="svc"))
    bind_log_context(job_name="promote", run_id="abc123")
    logger.info("job.start")
    payload = json.loads(buf.getvalue().strip())
    assert payload["job_name"] == "promote"
    assert payload["run_id"] == "abc123"


def test_json_formatter_includes_extra_fields():
    logger, buf = _capture(JsonFormatter(service="svc"))
    logger.info("predict", extra={"mode": "prod", "latency_ms": 12})
    payload = json.loads(buf.getvalue().strip())
    assert payload["mode"] == "prod"
    assert payload["latency_ms"] == 12


def test_json_formatter_injects_trace_ids_when_span_is_active():
    # Use a local provider to avoid depending on or mutating the global one.
    provider = TracerProvider()
    tracer = provider.get_tracer("test")

    logger, buf = _capture(JsonFormatter(service="svc"))
    with trace.use_span(
        tracer.start_span("unit"), end_on_exit=True, set_status_on_exception=False
    ):
        logger.info("inside-span")

    payload = json.loads(buf.getvalue().strip())
    assert "logging.googleapis.com/trace" in payload
    assert "logging.googleapis.com/spanId" in payload
    assert payload["logging.googleapis.com/spanId"] != "0" * 16


def test_configure_logging_is_idempotent():
    configure_logging("svc-a")
    configure_logging("svc-a")
    handlers = [
        h for h in logging.getLogger().handlers if getattr(h, "_mlp_json", False)
    ]
    assert len(handlers) == 1
