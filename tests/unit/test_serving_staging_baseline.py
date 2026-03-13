from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from ml_lifecycle_platform.ci.serving_staging_baseline import (
    build_baseline_context,
    render_baseline_markdown,
    render_baseline_markdown_from_paths,
    write_baseline_context,
)

pytestmark = pytest.mark.unit


def _summary_payload() -> dict[str, object]:
    return {
        "metrics": {
            "checks": {
                "values": {"rate": 1.0, "passes": 325, "fails": 0},
                "thresholds": {"rate>0.99": True},
            },
            "http_req_failed": {
                "values": {"rate": 0.0},
                "thresholds": {"rate<0.01": True},
            },
            "http_reqs": {
                "values": {"count": 325},
            },
            "http_req_duration{scenario:realistic_predict}": {
                "values": {"avg": 212.4, "p(95)": 350.1, "p(99)": 490.5, "max": 510.0},
                "thresholds": {"p(95)<1000": True, "p(99)<1500": True},
            },
            "http_req_duration{scenario:light_sustained_predict}": {
                "values": {
                    "avg": 280.4,
                    "p(95)": 700.1,
                    "p(99)": 930.2,
                    "max": 960.0,
                },
                "thresholds": {"p(95)<1500": True, "p(99)<2500": True},
            },
        }
    }


def test_build_baseline_context_returns_expected_shape() -> None:
    context = build_baseline_context(
        service_url="https://mlp-serving-staging.run.app",
        service_name="mlp-serving-staging",
        service_image="serving@sha256:abc",
        duration="5m",
        rate=1,
        realistic_iterations=25,
        git_sha="deadbeef",
        notes="first baseline",
        workflow_run_id="123",
        workflow_run_attempt="1",
    )

    assert context["service_name"] == "mlp-serving-staging"
    assert context["service_url"] == "https://mlp-serving-staging.run.app"
    assert context["git_sha"] == "deadbeef"
    assert context["scenarios"]["realistic_predict"]["iterations"] == 25
    assert context["scenarios"]["light_sustained_predict"]["rate_per_second"] == 1


def test_write_baseline_context_persists_json(tmp_path: Path) -> None:
    output_path = tmp_path / "baseline-context.json"

    write_baseline_context(
        output_path,
        service_url="https://mlp-serving-staging.run.app",
        service_name="mlp-serving-staging",
        service_image="serving@sha256:abc",
        duration="5m",
        rate=1,
        realistic_iterations=25,
    )

    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["service_name"] == "mlp-serving-staging"
    assert written["scenarios"]["light_sustained_predict"]["duration"] == "5m"


def test_render_baseline_markdown_includes_thresholds_and_metrics() -> None:
    report = render_baseline_markdown(
        _summary_payload(),
        build_baseline_context(
            service_url="https://mlp-serving-staging.run.app",
            service_name="mlp-serving-staging",
            service_image="serving@sha256:abc",
            duration="5m",
            rate=1,
            realistic_iterations=25,
            git_sha="deadbeef",
        ),
    )

    assert "# Hosted Serving Staging Baseline" in report
    assert "realistic_predict" in report
    assert "light_sustained_predict" in report
    assert "`6/6`" in report
    assert "`PASS`" in report


def test_render_baseline_markdown_from_paths_handles_failed_thresholds(
    tmp_path: Path,
) -> None:
    summary_path = tmp_path / "k6-summary.json"
    context_path = tmp_path / "baseline-context.json"

    summary = _summary_payload()
    metrics = cast(dict[str, Any], summary["metrics"])
    sustained_metric = cast(
        dict[str, Any], metrics["http_req_duration{scenario:light_sustained_predict}"]
    )
    thresholds = cast(dict[str, bool], sustained_metric["thresholds"])
    thresholds["p(95)<1500"] = False

    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    context_path.write_text(
        json.dumps(
            build_baseline_context(
                service_url="https://mlp-serving-staging.run.app",
                service_name="mlp-serving-staging",
                service_image="serving@sha256:abc",
                duration="5m",
                rate=1,
                realistic_iterations=25,
            )
        ),
        encoding="utf-8",
    )

    report = render_baseline_markdown_from_paths(
        summary_json_path=summary_path,
        context_json_path=context_path,
    )

    assert "`FAIL`" in report
    assert "Threshold failures are advisory" in report
