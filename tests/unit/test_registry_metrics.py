from __future__ import annotations

from collections.abc import Iterator

import pytest
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

import ml_lifecycle_platform.registry.metrics as registry_metrics
from ml_lifecycle_platform.registry.metrics import record_release

pytestmark = pytest.mark.unit


@pytest.fixture
def reader(monkeypatch: pytest.MonkeyPatch) -> Iterator[InMemoryMetricReader]:
    instance = InMemoryMetricReader()
    provider = MeterProvider(metric_readers=[instance])
    registry_metrics._release_counter.cache_clear()
    monkeypatch.setattr(
        registry_metrics.otel_metrics,
        "get_meter",
        lambda name: provider.get_meter(name),
    )
    yield instance
    registry_metrics._release_counter.cache_clear()


def test_record_release_increments_counter(reader: InMemoryMetricReader) -> None:
    record_release("promote", "breast_cancer_clf")
    record_release("rollback", "breast_cancer_clf")
    record_release("promote", "breast_cancer_clf")

    data = reader.get_metrics_data()
    assert data is not None

    by_op: dict[str, float] = {}
    for rm in data.resource_metrics:
        for sm in rm.scope_metrics:
            for metric in sm.metrics:
                if metric.name != "releases_total":
                    continue
                for point in metric.data.data_points:
                    attrs = point.attributes or {}
                    if attrs.get("model") != "breast_cancer_clf":
                        continue
                    op = str(attrs.get("op", ""))
                    by_op[op] = by_op.get(op, 0) + float(point.value)  # type: ignore[union-attr]

    assert by_op == {"promote": 2, "rollback": 1}
