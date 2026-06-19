"""Validate the raw dataset against the model spec's feature contract and
distribution assumptions before featurize/train.

Runs after ``ingest`` and before ``featurize``. Writes ``validation_report.json``
to the MLflow run and aborts the pipeline (non-zero exit) when any check fails,
so a malformed ingest never reaches train and the registry never fills with
candidates built on bad data.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import mlflow
import pandas as pd

from ml_lifecycle_platform.common.constants import (
    ART_VALIDATION_REPORT_JSON,
    MLFLOW_ARTIFACT_PATH_REPORTS,
    RAW_CSV,
    STEP_VALIDATE_DATA,
    TAG_MODEL_NAME,
    TAG_STEP,
)
from ml_lifecycle_platform.core.batch_contracts import (
    BatchContractValidationError,
    validate_labeled_dataset,
)
from ml_lifecycle_platform.core.model_spec_types import ModelSpec
from ml_lifecycle_platform.core.model_specs import load_model_spec
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
class ValidationReport:
    model_name: str
    dataset: str
    schema_version: str
    row_count: int
    passed: bool
    checks: tuple[CheckResult, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "dataset": self.dataset,
            "schema_version": self.schema_version,
            "row_count": self.row_count,
            "passed": self.passed,
            "checks": [check.to_dict() for check in self.checks],
        }

    def failure_reason(self) -> str:
        failed = [check for check in self.checks if not check.passed]
        return "; ".join(f"{check.name}: {check.detail}" for check in failed)


def _check_schema(df: pd.DataFrame, spec: ModelSpec) -> CheckResult:
    try:
        validate_labeled_dataset(
            df, spec=spec, stage="validate_data", dataset_name="raw"
        )
    except BatchContractValidationError as error:
        return CheckResult(name="schema", passed=False, detail=str(error))
    return CheckResult(name="schema", passed=True, detail="matches feature contract")


def _check_min_rows(df: pd.DataFrame, spec: ModelSpec) -> CheckResult:
    min_rows = spec.validation.min_rows
    row_count = len(df)
    return CheckResult(
        name="min_rows",
        passed=row_count >= min_rows,
        detail=f"{row_count} rows (minimum {min_rows})",
    )


def _check_no_fully_null_columns(df: pd.DataFrame) -> CheckResult:
    fully_null = [str(column) for column in df.columns if df[column].isna().all()]
    if fully_null:
        return CheckResult(
            name="no_fully_null_columns",
            passed=False,
            detail=f"fully-null columns: {', '.join(fully_null)}",
        )
    return CheckResult(
        name="no_fully_null_columns", passed=True, detail="no fully-null columns"
    )


def _check_feature_ranges(df: pd.DataFrame, spec: ModelSpec) -> CheckResult:
    violations: list[str] = []
    skipped: list[str] = []
    for feature_range in spec.validation.feature_ranges:
        if feature_range.name not in df.columns:
            skipped.append(feature_range.name)
            continue
        # NaN comparisons are False, so nulls never trip a bound here; the
        # no_fully_null_columns check owns null detection.
        column = pd.to_numeric(df[feature_range.name], errors="coerce")
        if feature_range.minimum is not None and (column < feature_range.minimum).any():
            violations.append(f"{feature_range.name} < {feature_range.minimum}")
        if feature_range.maximum is not None and (column > feature_range.maximum).any():
            violations.append(f"{feature_range.name} > {feature_range.maximum}")

    if violations:
        return CheckResult(
            name="feature_ranges",
            passed=False,
            detail=f"out of range: {'; '.join(violations)}",
        )
    detail = "within declared bounds"
    if skipped:
        detail += f" (skipped absent columns: {', '.join(skipped)})"
    return CheckResult(name="feature_ranges", passed=True, detail=detail)


def run_data_validation(df: pd.DataFrame, spec: ModelSpec) -> ValidationReport:
    """Run every data check and collect the verdicts into a report.

    Pure: no MLflow or filesystem side effects, so it is exercised directly in
    unit tests. ``main`` handles run logging and aborting the pipeline.
    """
    checks = (
        _check_schema(df, spec),
        _check_min_rows(df, spec),
        _check_no_fully_null_columns(df),
        _check_feature_ranges(df, spec),
    )
    return ValidationReport(
        model_name=spec.model_name,
        dataset="raw",
        schema_version=spec.schema_version,
        row_count=int(len(df)),
        passed=all(check.passed for check in checks),
        checks=checks,
    )


def main() -> None:
    ctx = get_runtime_context()
    ensure_experiment(ctx.experiment_name)
    mlflow.set_experiment(ctx.experiment_name)
    spec = load_model_spec(ctx.model_spec_path)

    raw_path = ctx.data_dir / RAW_CSV
    if not raw_path.exists():
        raise RuntimeError(f"Missing raw dataset: {raw_path}. Run ingest first.")

    df = pd.read_csv(raw_path)
    report = run_data_validation(df, spec)

    ctx.artifacts_dir.mkdir(parents=True, exist_ok=True)
    report_path = ctx.artifacts_dir / ART_VALIDATION_REPORT_JSON
    report_path.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True), encoding="utf-8"
    )

    with mlflow.start_run(run_name="validate_data") as run:
        mlflow.set_tag(TAG_STEP, STEP_VALIDATE_DATA)
        mlflow.set_tag(TAG_MODEL_NAME, spec.model_name)
        mlflow.log_params({"rows": report.row_count, "passed": report.passed})
        mlflow.log_artifact(
            str(report_path), artifact_path=MLFLOW_ARTIFACT_PATH_REPORTS
        )
        print(f"[validate_data] run_id={run.info.run_id} passed={report.passed}")

    if not report.passed:
        raise RuntimeError(f"Data validation failed: {report.failure_reason()}")


if __name__ == "__main__":
    main()
