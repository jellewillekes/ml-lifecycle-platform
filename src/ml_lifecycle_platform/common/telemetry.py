"""OpenTelemetry initialisation for serving and job entrypoints.

A single ``init_telemetry(service)`` installs OTLP exporters for traces and
metrics, reading the endpoint from ``OTEL_EXPORTER_OTLP_ENDPOINT``. All
exporter setup is best-effort: if the collector is unreachable or the
endpoint is unset, boot continues with a no-op tracer/meter.

The Prometheus ``/metrics`` endpoint remains the local scrape surface
(metrics are dual-emitted to Prometheus and to OTel), so compose stays
unchanged.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from opentelemetry import metrics, trace
from opentelemetry.sdk.resources import Resource

logger = logging.getLogger(__name__)

_INITIALIZED: dict[str, bool] = {}


def _otlp_enabled() -> bool:
    return bool(os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip())


def _install_trace_provider(service: str, resource: Resource) -> None:
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider(resource=resource)
    if _otlp_enabled():
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )

            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        except Exception as exc:  # pragma: no cover - best effort
            logger.warning(
                "otel trace exporter init failed; traces will be dropped: %s",
                exc,
            )
    trace.set_tracer_provider(provider)


def _install_meter_provider(service: str, resource: Resource) -> None:
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

    readers: list[Any] = []
    if _otlp_enabled():
        try:
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
                OTLPMetricExporter,
            )

            readers.append(PeriodicExportingMetricReader(OTLPMetricExporter()))
        except Exception as exc:  # pragma: no cover - best effort
            logger.warning(
                "otel metric exporter init failed; metrics will be dropped: %s",
                exc,
            )

    provider = MeterProvider(resource=resource, metric_readers=readers)
    metrics.set_meter_provider(provider)


def init_telemetry(service: str) -> None:
    """Initialise OTel trace + meter providers for ``service``.

    Idempotent per service name. Never raises: exporter errors are logged
    and providers remain installed so in-process spans still resolve.
    """

    if _INITIALIZED.get(service):
        return

    try:
        resource = Resource.create(
            {
                "service.name": service,
                "service.namespace": "ml-lifecycle-platform",
            }
        )
        _install_trace_provider(service, resource)
        _install_meter_provider(service, resource)
        _INITIALIZED[service] = True
    except Exception as exc:  # pragma: no cover - best effort
        logger.warning("init_telemetry(%s) failed: %s", service, exc)


def reset_for_tests() -> None:
    """Clear the init cache; for unit tests only."""

    _INITIALIZED.clear()
