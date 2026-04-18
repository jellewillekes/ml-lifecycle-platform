"""Prometheus counters and histograms exposed by the serving API (request
counts, prediction latency, shadow-diff magnitude), dual-emitted to OTel
meters under the same names and labels. Labels stay bounded to avoid
cardinality explosions."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from opentelemetry import metrics as otel_metrics
from prometheus_client import Counter, Histogram

# Labels stay bounded. Do not label by request_id, model_name, or similar.
REQUESTS_TOTAL = Counter(
    "requests_total",
    "Total HTTP requests handled by the serving API.",
    labelnames=("endpoint", "mode", "status"),
)

PREDICT_LATENCY_SECONDS = Histogram(
    "predict_latency_seconds",
    "Latency of /predict requests in seconds.",
    labelnames=("mode", "status", "chosen"),
    # Prometheus defaults are fine for now.
)

SHADOW_DIFF_MAE = Histogram(
    "shadow_diff_mae",
    "Mean absolute difference between primary and shadow predictions (when shadow runs).",
    labelnames=("mode",),
)


@lru_cache(maxsize=1)
def _otel_instruments() -> tuple[Any, Any, Any]:  # type: ignore[valid-type]
    meter = otel_metrics.get_meter("ml_lifecycle_platform.serving")
    return (
        meter.create_counter(
            "requests_total",
            description="Total HTTP requests handled by the serving API.",
        ),
        meter.create_histogram(
            "predict_latency_seconds",
            description="Latency of /predict requests in seconds.",
            unit="s",
        ),
        meter.create_histogram(
            "shadow_diff_mae",
            description="Mean absolute difference between primary and shadow predictions.",
        ),
    )


@lru_cache(maxsize=1)
def _startup_histogram() -> Any:
    meter = otel_metrics.get_meter("ml_lifecycle_platform.serving")
    return meter.create_histogram(
        "serving_startup_seconds",
        description="Wall time from lifespan start to serving ready, in seconds.",
        unit="s",
    )


def record_request(endpoint: str, mode: str, status: str) -> None:
    REQUESTS_TOTAL.labels(endpoint=endpoint, mode=mode, status=status).inc()
    counter, _, _ = _otel_instruments()
    counter.add(1, {"endpoint": endpoint, "mode": mode, "status": status})


def record_predict_latency(
    mode: str, status: str, chosen: str, latency_s: float
) -> None:
    PREDICT_LATENCY_SECONDS.labels(mode=mode, status=status, chosen=chosen).observe(
        latency_s
    )
    _, latency, _ = _otel_instruments()
    latency.record(latency_s, {"mode": mode, "status": status, "chosen": chosen})


def record_shadow_diff(mode: str, mae: float) -> None:
    SHADOW_DIFF_MAE.labels(mode=mode).observe(mae)
    _, _, shadow = _otel_instruments()
    shadow.record(mae, {"mode": mode})


def record_startup_latency(latency_s: float) -> None:
    _startup_histogram().record(latency_s)
