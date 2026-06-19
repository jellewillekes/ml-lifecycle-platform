from __future__ import annotations

from typing import Any

import pytest

from ml_lifecycle_platform.core.model_specs import model_spec_from_dict
from ml_lifecycle_platform.pipeline.validate_model import (
    SegmentMeasurement,
    run_model_validation,
)

pytestmark = pytest.mark.unit


def _spec(model_validation: dict[str, Any] | None = None):
    payload: dict[str, Any] = {
        "schema_version": "model_spec/v1",
        "model_name": "validate_model_test",
        "task": "binary_classifier",
        "label_column": "target",
        "source": {"kind": "sklearn_demo", "dataset_name": "breast_cancer"},
        "split": {"test_size": 0.2, "random_state": 42, "stratify": True},
        "preprocessor": {"kind": "standard_scaler"},
        "trainer": {
            "kind": "logistic_regression",
            "max_iter": 2000,
            "solver": "lbfgs",
            "class_weight": "balanced",
            "random_state": 42,
        },
        "evaluation": {
            "metrics": ["accuracy", "f1", "roc_auc"],
            "gate": {"metric": "roc_auc", "threshold": 0.5},
        },
        "feature_contract": {
            "version": "validate_model_test.input/v1",
            "allow_unknown_fields": False,
            "features": [
                {"name": "f1", "dtype": "float"},
                {"name": "f2", "dtype": "float"},
            ],
        },
    }
    if model_validation is not None:
        payload["model_validation"] = model_validation
    return model_spec_from_dict(
        payload, spec_path="configs/models/breast_cancer_demo.yaml"
    )


_FULL_GATES = {
    "metric": "roc_auc",
    "min_overall": 0.80,
    "max_regression": 0.05,
    "segments": [{"name": "high_f1", "column": "f1", "min": 1.0, "min_metric": 0.80}],
}


def _failed_check_names(report) -> set[str]:
    return {check.name for check in report.checks if not check.passed}


def test_all_gates_pass() -> None:
    report = run_model_validation(
        spec=_spec(_FULL_GATES),
        overall_value=0.95,
        segment_measurements=(SegmentMeasurement("high_f1", 0.90, "10 rows"),),
        baseline_value=0.93,
    )

    assert report.passed is True
    assert report.failure_reason() == ""


def test_overall_below_floor_fails() -> None:
    report = run_model_validation(
        spec=_spec(_FULL_GATES),
        overall_value=0.50,
        segment_measurements=(SegmentMeasurement("high_f1", 0.90, "10 rows"),),
        baseline_value=None,
    )

    assert report.passed is False
    assert "overall" in _failed_check_names(report)


def test_segment_below_minimum_fails() -> None:
    report = run_model_validation(
        spec=_spec(_FULL_GATES),
        overall_value=0.95,
        segment_measurements=(SegmentMeasurement("high_f1", 0.70, "10 rows"),),
        baseline_value=None,
    )

    assert report.passed is False
    assert "segment:high_f1" in _failed_check_names(report)
    assert report.failure_reason()


def test_regression_beyond_tolerance_fails() -> None:
    # 0.80 clears the 0.80 overall floor but drops 0.15 below the 0.95 baseline.
    report = run_model_validation(
        spec=_spec(_FULL_GATES),
        overall_value=0.80,
        segment_measurements=(SegmentMeasurement("high_f1", 0.90, "10 rows"),),
        baseline_value=0.95,
    )

    assert report.passed is False
    assert _failed_check_names(report) == {"no_regression"}


def test_missing_baseline_skips_regression_gate() -> None:
    report = run_model_validation(
        spec=_spec(_FULL_GATES),
        overall_value=0.85,
        segment_measurements=(SegmentMeasurement("high_f1", 0.90, "10 rows"),),
        baseline_value=None,
    )

    assert report.passed is True


def test_uncomputable_segment_is_skipped_not_failed() -> None:
    report = run_model_validation(
        spec=_spec(_FULL_GATES),
        overall_value=0.95,
        segment_measurements=(
            SegmentMeasurement("high_f1", None, "3 rows, metric undefined"),
        ),
        baseline_value=None,
    )

    assert report.passed is True
    assert "segment:high_f1" not in _failed_check_names(report)
