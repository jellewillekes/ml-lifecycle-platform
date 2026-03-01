from __future__ import annotations

import re

import pytest
from starlette.testclient import TestClient

pytestmark = pytest.mark.unit


def _parse_labels(label_blob: str) -> dict[str, str]:
    # a="b",c="d"
    out: dict[str, str] = {}
    if not label_blob.strip():
        return out
    for part in label_blob.split(","):
        k, v = part.split("=", 1)
        out[k.strip()] = v.strip().strip('"')
    return out


def _get_counter_value(text: str, metric_name: str, want: dict[str, str]) -> float:
    # accept any label order
    pat = re.compile(rf"^{re.escape(metric_name)}\{{([^}}]*)\}}\s+([0-9eE\.\+\-]+)$")
    for line in text.splitlines():
        m = pat.match(line)
        if not m:
            continue
        labels = _parse_labels(m.group(1))
        if all(labels.get(k) == v for k, v in want.items()):
            return float(m.group(2))
    raise AssertionError(f"Metric not found: {metric_name} labels={want}")


def test_predict_increments_metrics(client: TestClient) -> None:
    base = client.get("/metrics").text

    # middleware labels: endpoint, mode, status
    labels = {"endpoint": "/predict", "mode": "prod", "status": "200"}
    base_count = _get_counter_value(base, "requests_total", labels)

    r = client.post(
        "/predict?mode=prod",
        json={"rows": [{"f1": 1.0, "f2": 2.0, "f3": 3.0}]},
    )
    assert r.status_code == 200

    after = client.get("/metrics").text
    after_count = _get_counter_value(after, "requests_total", labels)

    assert after_count == base_count + 1.0
