"""OTel counter emitted by registry release ops (promote, rollback, reproduce)
so dashboards can track release cadence without parsing MLflow audit events."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from opentelemetry import metrics as otel_metrics


@lru_cache(maxsize=1)
def _release_counter() -> Any:
    meter = otel_metrics.get_meter("ml_lifecycle_platform.registry")
    return meter.create_counter(
        "releases_total",
        description="Count of successful registry release operations.",
    )


def record_release(op: str, model: str) -> None:
    """Increment the release counter for ``op`` on ``model``.

    ``op`` is one of ``promote``, ``rollback``, ``reproduce``.
    """

    _release_counter().add(1, {"op": op, "model": model})
