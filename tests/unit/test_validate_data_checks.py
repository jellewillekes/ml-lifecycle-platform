from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from ml_lifecycle_platform.core.model_specs import model_spec_from_dict
from ml_lifecycle_platform.pipeline.validate_data import run_data_validation

pytestmark = pytest.mark.unit


def _spec(validation: dict[str, Any] | None = None):
    payload: dict[str, Any] = {
        "schema_version": "model_spec/v1",
        "model_name": "validate_data_test",
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
            "version": "validate_data_test.input/v1",
            "allow_unknown_fields": False,
            "features": [
                {"name": "f1", "dtype": "float"},
                {"name": "f2", "dtype": "float"},
            ],
        },
    }
    if validation is not None:
        payload["validation"] = validation
    return model_spec_from_dict(
        payload, spec_path="configs/models/breast_cancer_demo.yaml"
    )


def _good_df(rows: int = 4) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "f1": [float(i) for i in range(rows)],
            "f2": [float(i) * 0.5 for i in range(rows)],
            "target": [i % 2 for i in range(rows)],
        }
    )


def _failed_check_names(report) -> set[str]:
    return {check.name for check in report.checks if not check.passed}


def test_well_formed_data_passes_every_check() -> None:
    report = run_data_validation(_good_df(), _spec())

    assert report.passed is True
    assert all(check.passed for check in report.checks)
    assert report.row_count == 4
    assert report.failure_reason() == ""


def test_too_few_rows_fails_min_rows_check() -> None:
    report = run_data_validation(_good_df(4), _spec({"min_rows": 100}))

    assert report.passed is False
    assert "min_rows" in _failed_check_names(report)


def test_fully_null_column_is_caught() -> None:
    df = _good_df()
    df["f2"] = pd.NA

    report = run_data_validation(df, _spec())

    assert report.passed is False
    assert "no_fully_null_columns" in _failed_check_names(report)


def test_value_above_declared_maximum_fails_range_check() -> None:
    report = run_data_validation(
        _good_df(5),  # f1 spans 0..4, exceeding the 2.0 ceiling
        _spec({"feature_ranges": [{"name": "f1", "max": 2.0}]}),
    )

    assert report.passed is False
    assert "feature_ranges" in _failed_check_names(report)


def test_value_below_declared_minimum_fails_range_check() -> None:
    report = run_data_validation(
        _good_df(3),  # f1 spans 0..2, below the 1.0 floor
        _spec({"feature_ranges": [{"name": "f1", "min": 1.0}]}),
    )

    assert report.passed is False
    assert "feature_ranges" in _failed_check_names(report)


def test_schema_violation_is_a_failed_check_not_a_crash() -> None:
    df = _good_df()
    df["target"] = [2, 3, 4, 5]  # outside the {0, 1} label domain

    report = run_data_validation(df, _spec())

    assert report.passed is False
    assert "schema" in _failed_check_names(report)
    assert report.failure_reason()
