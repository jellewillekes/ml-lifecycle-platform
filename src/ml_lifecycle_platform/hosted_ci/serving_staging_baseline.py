"""Assemble the k6 baseline-context JSON that drives the serving staging
load test — pins service URL, image, git SHA, and traffic scenarios for
the next load run."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


def build_baseline_context(
    *,
    service_url: str,
    service_name: str,
    service_image: str,
    duration: str,
    rate: int,
    realistic_iterations: int,
    git_sha: str | None = None,
    notes: str | None = None,
    workflow_run_id: str | None = None,
    workflow_run_attempt: str | None = None,
) -> dict[str, Any]:
    return {
        "service_url": service_url,
        "service_name": service_name,
        "service_image": service_image,
        "git_sha": git_sha,
        "notes": notes,
        "workflow_run_id": workflow_run_id,
        "workflow_run_attempt": workflow_run_attempt,
        "scenarios": {
            "realistic_predict": {
                "executor": "per-vu-iterations",
                "vus": 1,
                "iterations": realistic_iterations,
            },
            "light_sustained_predict": {
                "executor": "constant-arrival-rate",
                "rate_per_second": rate,
                "duration": duration,
                "pre_allocated_vus": 2,
                "max_vus": 4,
            },
        },
    }


def write_baseline_context(
    path: Path,
    *,
    service_url: str,
    service_name: str,
    service_image: str,
    duration: str,
    rate: int,
    realistic_iterations: int,
    git_sha: str | None = None,
    notes: str | None = None,
    workflow_run_id: str | None = None,
    workflow_run_attempt: str | None = None,
) -> dict[str, Any]:
    context = build_baseline_context(
        service_url=service_url,
        service_name=service_name,
        service_image=service_image,
        duration=duration,
        rate=rate,
        realistic_iterations=realistic_iterations,
        git_sha=git_sha,
        notes=notes,
        workflow_run_id=workflow_run_id,
        workflow_run_attempt=workflow_run_attempt,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(context, indent=2, sort_keys=True), encoding="utf-8")
    return context


def _metrics(summary: Mapping[str, Any]) -> Mapping[str, Any]:
    metrics = summary.get("metrics", {})
    if not isinstance(metrics, Mapping):
        return {}
    return metrics


def _metric_values(summary: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    metric = _metrics(summary).get(key, {})
    if not isinstance(metric, Mapping):
        return {}
    values = metric.get("values", {})
    if not isinstance(values, Mapping):
        return {}
    return values


def _threshold_rows(summary: Mapping[str, Any]) -> list[tuple[str, str, bool]]:
    rows: list[tuple[str, str, bool]] = []
    for metric_name, metric in sorted(_metrics(summary).items()):
        if not isinstance(metric, Mapping):
            continue
        thresholds = metric.get("thresholds", {})
        if not isinstance(thresholds, Mapping):
            continue
        for threshold_name, passed in sorted(thresholds.items()):
            rows.append((str(metric_name), str(threshold_name), bool(passed)))
    return rows


def _format_float(value: Any, digits: int = 1) -> str:
    if not isinstance(value, (int, float)):
        return "n/a"
    return f"{float(value):.{digits}f}"


def _format_int(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return "n/a"
    return str(int(value))


def render_baseline_markdown(
    summary: Mapping[str, Any],
    context: Mapping[str, Any],
) -> str:
    threshold_rows = _threshold_rows(summary)
    failed_thresholds = [row for row in threshold_rows if not row[2]]
    checks = _metric_values(summary, "checks")
    failed_rate = _metric_values(summary, "http_req_failed")
    request_count = _metric_values(summary, "http_reqs")

    lines = [
        "# Hosted Serving Staging Baseline",
        "",
        f"- Service: `{context.get('service_name', 'unknown')}`",
        f"- Service URL: `{context.get('service_url', 'unknown')}`",
        f"- Service image: `{context.get('service_image', 'unknown')}`",
        f"- Git SHA: `{context.get('git_sha') or 'unknown'}`",
        f"- Notes: `{context.get('notes') or 'n/a'}`",
        "",
        "## Outcome",
        "",
        f"- Requests: `{_format_int(request_count.get('count'))}`",
        f"- Check pass rate: `{_format_float(checks.get('rate'), digits=3)}`",
        f"- Error rate: `{_format_float(failed_rate.get('rate'), digits=3)}`",
        f"- Thresholds passed: `{len(threshold_rows) - len(failed_thresholds)}/{len(threshold_rows)}`",
        "",
        "## Scenario Metrics",
        "",
        "| Scenario | Avg ms | P95 ms | P99 ms | Max ms |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]

    for metric_name, scenario_name in (
        ("http_req_duration{scenario:realistic_predict}", "realistic_predict"),
        (
            "http_req_duration{scenario:light_sustained_predict}",
            "light_sustained_predict",
        ),
    ):
        values = _metric_values(summary, metric_name)
        lines.append(
            "| "
            f"{scenario_name} | "
            f"{_format_float(values.get('avg'))} | "
            f"{_format_float(values.get('p(95)'))} | "
            f"{_format_float(values.get('p(99)'))} | "
            f"{_format_float(values.get('max'))} |"
        )

    lines.extend(
        [
            "",
            "## Thresholds",
            "",
            "| Metric | Threshold | Status |",
            "| --- | --- | --- |",
        ]
    )

    if not threshold_rows:
        lines.append("| n/a | n/a | n/a |")
    else:
        for metric_name, threshold_name, passed in threshold_rows:
            lines.append(
                f"| `{metric_name}` | `{threshold_name}` | `{'PASS' if passed else 'FAIL'}` |"
            )

    if failed_thresholds:
        lines.extend(
            [
                "",
                "## Advisory Note",
                "",
                "Threshold failures are advisory in `UP-19`. Investigate before using the run as a reference baseline.",
            ]
        )

    return "\n".join(lines) + "\n"


def render_baseline_markdown_from_paths(
    *,
    summary_json_path: Path,
    context_json_path: Path,
) -> str:
    summary = json.loads(summary_json_path.read_text(encoding="utf-8"))
    context = json.loads(context_json_path.read_text(encoding="utf-8"))
    if not isinstance(summary, dict):
        raise ValueError("k6 summary payload must be a JSON object.")
    if not isinstance(context, dict):
        raise ValueError("Baseline context payload must be a JSON object.")
    return render_baseline_markdown(summary, context)
