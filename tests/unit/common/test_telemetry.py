from __future__ import annotations

import pytest
from opentelemetry import metrics, trace

from ml_lifecycle_platform.common.telemetry import init_telemetry, reset_for_tests

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _reset():
    reset_for_tests()
    yield
    reset_for_tests()


def test_init_telemetry_without_otlp_endpoint_does_not_raise(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    init_telemetry("svc-no-otlp")

    tracer = trace.get_tracer("svc-no-otlp")
    meter = metrics.get_meter("svc-no-otlp")
    # Creating a span and an instrument must not raise.
    with tracer.start_as_current_span("smoke") as span:
        assert span is not None
    counter = meter.create_counter("smoke_counter")
    counter.add(1, {"k": "v"})


def test_init_telemetry_is_idempotent(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    init_telemetry("svc-idem")
    init_telemetry("svc-idem")


def test_init_telemetry_with_unreachable_endpoint_does_not_raise(monkeypatch):
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:59999")
    init_telemetry("svc-bad-otlp")

    tracer = trace.get_tracer("svc-bad-otlp")
    with tracer.start_as_current_span("smoke"):
        pass
