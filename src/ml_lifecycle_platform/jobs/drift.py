"""Batch drift job (UP-32): for each model, read a rolling window of prediction
events through a ``BatchEventReader``, compare each feature against the prod
release baseline, write ``drift_report.json`` into release evidence, and expose
``mlp_drift_ks_statistic{model, feature}`` for Grafana alerting.

Reads on demand locally (``make drift``) and on a schedule in staging. No
baseline or no events for a model means it is skipped, not a failure.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import tempfile
import time
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path
from typing import Any

from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient
from opentelemetry import metrics as otel_metrics
from opentelemetry.metrics import CallbackOptions, Observation

from ml_lifecycle_platform.backends.gcp.bigquery_event_reader import BigQueryEventReader
from ml_lifecycle_platform.backends.local.event_reader import DuckDBEventReader
from ml_lifecycle_platform.common.constants import (
    ALIAS_PROD,
    ART_DRIFT_REPORT_JSON,
    MLFLOW_ARTIFACT_PATH_REPORTS,
)
from ml_lifecycle_platform.common.jobs import start_job
from ml_lifecycle_platform.contracts.drift_baseline import DriftBaseline
from ml_lifecycle_platform.contracts.drift_report import DriftReport
from ml_lifecycle_platform.contracts.release_reports import utc_now_iso
from ml_lifecycle_platform.core.drift import DEFAULT_KS_THRESHOLD, compute_drift
from ml_lifecycle_platform.core.model_specs import discover_model_specs
from ml_lifecycle_platform.core.ports import BatchEventReader
from ml_lifecycle_platform.registry.show_baseline import load_baseline
from ml_lifecycle_platform.runtime.bootstrap import (
    configure_mlflow,
    get_runtime_context,
)
from ml_lifecycle_platform.runtime.mlflow import client as mlflow_client

logger = logging.getLogger(__name__)

_DEFAULT_JSONL_PATH = "artifacts/prediction-events.jsonl"
_NS_PER_HOUR = 3_600 * 1_000_000_000

# Latest KS values, read by the observable gauge callback on metric flush.
_ks_values: dict[tuple[str, str], float] = {}


def _observe_ks(options: CallbackOptions) -> Iterable[Observation]:  # noqa: ARG001
    return tuple(
        Observation(value, {"model": model, "feature": feature})
        for (model, feature), value in _ks_values.items()
    )


@lru_cache(maxsize=1)
def _register_ks_gauge() -> Any:
    meter = otel_metrics.get_meter("ml_lifecycle_platform.jobs.drift")
    return meter.create_observable_gauge(
        "mlp_drift_ks_statistic",
        callbacks=[_observe_ks],
        description="KS statistic per model/feature versus the release baseline.",
    )


def build_event_reader() -> BatchEventReader:
    kind = os.getenv("MLP_EVENT_SINK", "none").strip().lower()
    if kind == "jsonl":
        path = os.getenv("MLP_EVENT_JSONL_PATH", _DEFAULT_JSONL_PATH)
        return DuckDBEventReader(Path(path))
    if kind == "bigquery":
        table = os.getenv("MLP_EVENT_BQ_TABLE", "").strip()
        if not table:
            raise RuntimeError("MLP_EVENT_BQ_TABLE is required for the bigquery reader")
        return BigQueryEventReader(table)
    raise RuntimeError(f"no batch event reader for MLP_EVENT_SINK={kind!r}")


def _load_prod_baseline(client: MlflowClient, model_name: str) -> DriftBaseline | None:
    try:
        model_version = client.get_model_version_by_alias(model_name, ALIAS_PROD)
    except MlflowException as exc:
        logger.warning("No prod alias for %s; skipping drift: %s", model_name, exc)
        return None
    try:
        return load_baseline(
            client, model_name=model_name, version=str(model_version.version)
        )
    except SystemExit as exc:
        logger.warning("No drift baseline for %s: %s", model_name, exc)
        return None


def _emit_drift_report(
    client: MlflowClient, *, report: DriftReport, source_run_id: str
) -> str:
    root = (
        f"{MLFLOW_ARTIFACT_PATH_REPORTS}/drift/"
        f"{report.model_name}/v{report.model_version}"
    )
    content = report.to_json().encode("utf-8")
    with tempfile.TemporaryDirectory(prefix="drift-report-") as tmpdir:
        local = Path(tmpdir) / ART_DRIFT_REPORT_JSON
        local.write_bytes(content)
        try:
            client.log_artifact(
                run_id=source_run_id, local_path=str(local), artifact_path=root
            )
        except MlflowException as exc:
            logger.warning("Could not log drift report to MLflow: %s", exc)
    try:
        get_runtime_context().artifact_store.write_bytes(
            f"{root}/{ART_DRIFT_REPORT_JSON}", content
        )
    except OSError as exc:
        logger.warning("Could not mirror drift report locally: %s", exc)
    return root


def run_drift_for_model(
    client: MlflowClient,
    model_name: str,
    *,
    reader: BatchEventReader,
    window_hours: float,
    threshold: float,
    now_ns: int,
) -> DriftReport | None:
    baseline = _load_prod_baseline(client, model_name)
    if baseline is None:
        return None
    start_ns = now_ns - int(window_hours * _NS_PER_HOUR)
    window = reader.read_window(model_name, start_ns, now_ns)
    report = compute_drift(
        window,
        baseline,
        window_start_ns=start_ns,
        window_end_ns=now_ns,
        created_at=utc_now_iso(),
        threshold=threshold,
    )
    _register_ks_gauge()
    for feature in report.features.values():
        _ks_values[(model_name, feature.feature)] = feature.ks_statistic
    _emit_drift_report(client, report=report, source_run_id=baseline.source_run_id)
    return report


def _resolve_models(args: argparse.Namespace, model_name: str) -> list[str]:
    if args.all:
        return [spec.model_name for spec in discover_model_specs()]
    if args.model:
        return [str(args.model)]
    return [model_name]


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="drift")
    selector = parser.add_mutually_exclusive_group()
    selector.add_argument("--model", help="Run drift for one model by name")
    selector.add_argument("--all", action="store_true", help="Run drift for every spec")
    parser.add_argument("--window-hours", type=float, default=24.0)
    parser.add_argument("--threshold", type=float, default=DEFAULT_KS_THRESHOLD)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    runtime = get_runtime_context()
    with start_job("drift", level=runtime.log_level):
        configure_mlflow(runtime)
        client = mlflow_client()
        reader = build_event_reader()
        now_ns = time.time_ns()
        reports = 0
        for model_name in _resolve_models(args, runtime.model_name):
            report = run_drift_for_model(
                client,
                model_name,
                reader=reader,
                window_hours=args.window_hours,
                threshold=args.threshold,
                now_ns=now_ns,
            )
            if report is not None:
                reports += 1
                print(
                    f"[drift] {model_name}: drifted={report.drifted} "
                    f"features={len(report.features)} n_events={report.n_events}"
                )
        if reports == 0:
            print("[drift] no model had a baseline and events to compare.")


if __name__ == "__main__":
    main()
