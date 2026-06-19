"""Validate the freshly trained candidate against the model spec's quality
gates before ``register``.

Runs after ``evaluate`` and before ``register``. Re-scores the candidate on the
held-out test split, then checks the overall metric floor, per-segment minimums,
and (when a baseline exists) regression against the previous validation run.
Writes ``model_validation_report.json`` to the MLflow run and aborts the
pipeline (non-zero exit) on failure, so the registry only ever holds candidates
worth promoting.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import mlflow
import pandas as pd

from ml_lifecycle_platform.common.constants import (
    ART_MODEL_VALIDATION_REPORT_JSON,
    MLFLOW_ARTIFACT_PATH_REPORTS,
    STEP_VALIDATE_MODEL,
    TAG_MODEL_NAME,
    TAG_STEP,
)
from ml_lifecycle_platform.core.model_spec_types import (
    ModelSpec,
    ModelValidationSpec,
    SegmentSpec,
)
from ml_lifecycle_platform.core.model_specs import load_model_spec
from ml_lifecycle_platform.pipeline.metrics import compute_binary_metrics
from ml_lifecycle_platform.pipeline.scoring import (
    ScoredTestSplit,
    load_scored_test_split,
)
from ml_lifecycle_platform.runtime.bootstrap import get_runtime_context
from ml_lifecycle_platform.runtime.mlflow import ensure_experiment


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


@dataclass(frozen=True)
class SegmentMeasurement:
    """A segment's measured metric, or ``None`` when it cannot be computed."""

    name: str
    value: float | None
    detail: str


@dataclass(frozen=True)
class ModelValidationReport:
    model_name: str
    metric: str
    overall_value: float
    baseline_value: float | None
    passed: bool
    checks: tuple[CheckResult, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "metric": self.metric,
            "overall_value": self.overall_value,
            "baseline_value": self.baseline_value,
            "passed": self.passed,
            "checks": [check.to_dict() for check in self.checks],
        }

    def failure_reason(self) -> str:
        failed = [check for check in self.checks if not check.passed]
        return "; ".join(f"{check.name}: {check.detail}" for check in failed)


def _overall_check(mv: ModelValidationSpec, overall_value: float) -> CheckResult:
    return CheckResult(
        name="overall",
        passed=overall_value >= mv.min_overall,
        detail=f"{mv.metric}={overall_value:.4f} (minimum {mv.min_overall})",
    )


def _segment_check(
    segment: SegmentSpec, measurement: SegmentMeasurement | None
) -> CheckResult:
    name = f"segment:{segment.name}"
    if measurement is None or measurement.value is None:
        reason = measurement.detail if measurement else "no measurement"
        return CheckResult(name=name, passed=True, detail=f"skipped ({reason})")
    return CheckResult(
        name=name,
        passed=measurement.value >= segment.min_metric,
        detail=(
            f"{measurement.value:.4f} on {measurement.detail} "
            f"(minimum {segment.min_metric})"
        ),
    )


def _regression_check(
    mv: ModelValidationSpec, overall_value: float, baseline_value: float | None
) -> CheckResult:
    if mv.max_regression is None or baseline_value is None:
        reason = (
            "regression gate disabled" if baseline_value is not None else "no baseline"
        )
        return CheckResult(
            name="no_regression", passed=True, detail=f"skipped ({reason})"
        )
    floor = baseline_value - mv.max_regression
    return CheckResult(
        name="no_regression",
        passed=overall_value >= floor,
        detail=f"{overall_value:.4f} vs baseline {baseline_value:.4f} (floor {floor:.4f})",
    )


def run_model_validation(
    *,
    spec: ModelSpec,
    overall_value: float,
    segment_measurements: tuple[SegmentMeasurement, ...],
    baseline_value: float | None,
) -> ModelValidationReport:
    """Run every model-quality gate and collect the verdicts into a report.

    Pure: no MLflow or filesystem side effects, so it is exercised directly in
    unit tests. ``main`` handles scoring, baseline lookup, and run logging.
    """
    mv = spec.model_validation
    measurements_by_name = {m.name: m for m in segment_measurements}

    checks: list[CheckResult] = [_overall_check(mv, overall_value)]
    for segment in mv.segments:
        checks.append(_segment_check(segment, measurements_by_name.get(segment.name)))
    checks.append(_regression_check(mv, overall_value, baseline_value))

    return ModelValidationReport(
        model_name=spec.model_name,
        metric=mv.metric,
        overall_value=overall_value,
        baseline_value=baseline_value,
        passed=all(check.passed for check in checks),
        checks=tuple(checks),
    )


def _metric_value(metric: str, y_true: Any, pred: Any, proba: Any) -> float:
    result = compute_binary_metrics(
        metric_names=(metric,), y_true=y_true, pred=pred, proba=proba, prefix="m"
    )
    return result[f"m_{metric}"]


def _measure_segment(
    segment: SegmentSpec, scored: ScoredTestSplit, metric: str
) -> SegmentMeasurement:
    column = pd.to_numeric(scored.test_df[segment.column], errors="coerce")
    mask = pd.Series(True, index=scored.test_df.index)
    if segment.minimum is not None:
        mask &= column >= segment.minimum
    if segment.maximum is not None:
        mask &= column <= segment.maximum

    mask_np = mask.to_numpy()
    row_count = int(mask_np.sum())
    if row_count == 0:
        return SegmentMeasurement(name=segment.name, value=None, detail="0 rows match")

    try:
        value = _metric_value(
            metric,
            scored.y_true.to_numpy()[mask_np],
            scored.pred[mask_np],
            scored.proba[mask_np],
        )
    except ValueError:
        # roc_auc is undefined when a segment holds a single class.
        return SegmentMeasurement(
            name=segment.name, value=None, detail=f"{row_count} rows, metric undefined"
        )
    return SegmentMeasurement(
        name=segment.name, value=value, detail=f"{row_count} rows"
    )


def _previous_overall_metric(
    experiment_name: str, model_name: str, metric: str
) -> float | None:
    """The most recent prior ``validate_model`` run's overall metric, or None.

    Placeholder baseline until UP-31 lands a real previous-prod comparison.
    """
    experiment = mlflow.get_experiment_by_name(experiment_name)
    if experiment is None:
        return None
    runs = mlflow.search_runs(
        experiment_ids=[experiment.experiment_id],
        filter_string=(
            f"tags.{TAG_STEP} = '{STEP_VALIDATE_MODEL}' "
            f"and tags.{TAG_MODEL_NAME} = '{model_name}'"
        ),
        order_by=["attributes.start_time DESC"],
        max_results=1,
    )
    if not isinstance(runs, pd.DataFrame) or runs.empty:
        return None
    column = f"metrics.{metric}"
    if column not in runs.columns:
        return None
    value = runs.iloc[0][column]
    if pd.isna(value):
        return None
    return float(value)


def main() -> None:
    ctx = get_runtime_context()
    ensure_experiment(ctx.experiment_name)
    mlflow.set_experiment(ctx.experiment_name)
    spec = load_model_spec(ctx.model_spec_path)
    mv = spec.model_validation

    scored = load_scored_test_split(ctx, spec)
    overall_value = _metric_value(mv.metric, scored.y_true, scored.pred, scored.proba)
    measurements = tuple(
        _measure_segment(segment, scored, mv.metric) for segment in mv.segments
    )
    # Look up the baseline before opening this run, so it never matches itself.
    baseline_value = _previous_overall_metric(
        ctx.experiment_name, spec.model_name, mv.metric
    )

    report = run_model_validation(
        spec=spec,
        overall_value=overall_value,
        segment_measurements=measurements,
        baseline_value=baseline_value,
    )

    ctx.artifacts_dir.mkdir(parents=True, exist_ok=True)
    report_path = ctx.artifacts_dir / ART_MODEL_VALIDATION_REPORT_JSON
    report_path.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True), encoding="utf-8"
    )

    with mlflow.start_run(run_name="validate_model") as run:
        mlflow.set_tag(TAG_STEP, STEP_VALIDATE_MODEL)
        mlflow.set_tag(TAG_MODEL_NAME, spec.model_name)
        mlflow.log_metric(mv.metric, overall_value)
        mlflow.log_artifact(
            str(report_path), artifact_path=MLFLOW_ARTIFACT_PATH_REPORTS
        )
        print(f"[validate_model] run_id={run.info.run_id} passed={report.passed}")

    if not report.passed:
        raise RuntimeError(f"Model validation failed: {report.failure_reason()}")


if __name__ == "__main__":
    main()
