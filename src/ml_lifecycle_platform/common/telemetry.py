"""OpenTelemetry initialisation for serving and job entrypoints.

A single ``init_telemetry(service)`` installs OTLP exporters for traces and
metrics, reading the endpoint from ``OTEL_EXPORTER_OTLP_ENDPOINT``. All
exporter setup is best-effort: if the collector is unreachable or the
endpoint is unset, boot continues with a no-op tracer/meter.

Protocol selection follows the OTel SDK convention via
``OTEL_EXPORTER_OTLP_PROTOCOL``: ``grpc`` (default, used end-to-end by both
the local compose collector and the self-hosted staging collector) or
``http/protobuf`` (kept as a future option for any managed OTLP/HTTP
gateway).

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


def _otlp_protocol() -> str:
    return os.getenv("OTEL_EXPORTER_OTLP_PROTOCOL", "grpc").strip().lower()


def _build_span_exporter() -> Any:
    if _otlp_protocol() == "http/protobuf":
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter as HttpSpanExporter,
        )

        return HttpSpanExporter()

    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
        OTLPSpanExporter as GrpcSpanExporter,
    )

    return GrpcSpanExporter()


def _build_metric_exporter() -> Any:
    if _otlp_protocol() == "http/protobuf":
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
            OTLPMetricExporter as HttpMetricExporter,
        )

        return HttpMetricExporter()

    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
        OTLPMetricExporter as GrpcMetricExporter,
    )

    return GrpcMetricExporter()


def _install_trace_provider(service: str, resource: Resource) -> None:
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider(resource=resource)
    if _otlp_enabled():
        try:
            provider.add_span_processor(BatchSpanProcessor(_build_span_exporter()))
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
            readers.append(PeriodicExportingMetricReader(_build_metric_exporter()))
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


def force_flush(timeout_millis: int = 5000) -> None:
    """Flush pending traces and metrics before process exit.

    Best-effort: short-lived jobs (maintenance, promote, rollback, reproduce,
    pipeline) exit before the periodic metric reader's next interval, so
    without a flush the last observations are dropped.
    """

    tracer_provider = trace.get_tracer_provider()
    flush_traces = getattr(tracer_provider, "force_flush", None)
    if callable(flush_traces):
        try:
            flush_traces(timeout_millis)
        except Exception as exc:  # pragma: no cover - best effort
            logger.warning("otel trace flush failed: %s", exc)

    meter_provider = metrics.get_meter_provider()
    flush_metrics = getattr(meter_provider, "force_flush", None)
    if callable(flush_metrics):
        try:
            flush_metrics(timeout_millis)
        except Exception as exc:  # pragma: no cover - best effort
            logger.warning("otel metric flush failed: %s", exc)


def reset_for_tests() -> None:
    """Clear the init cache; for unit tests only."""

    _INITIALIZED.clear()
