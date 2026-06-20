from __future__ import annotations

import pandas as pd
import pytest

from ml_lifecycle_platform.contracts.drift_baseline import (
    ColumnStats,
    DriftBaseline,
    DriftBaselineValidationError,
    validate_drift_baseline,
)
from ml_lifecycle_platform.registry.drift_baseline import compute_drift_baseline

pytestmark = pytest.mark.unit


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "f1": [0.0, 1.0, 2.0, 3.0, 4.0],
            "f2": [10.0, 10.0, 10.0, 10.0, 10.0],
            "label": [0, 1, 0, 1, 1],
        }
    )


def _baseline() -> DriftBaseline:
    return compute_drift_baseline(
        _frame(),
        model_name="m",
        model_version="1",
        source_run_id="run-1",
        created_at="2026-01-01T00:00:00+00:00",
    )


def test_compute_baseline_stats() -> None:
    baseline = _baseline()
    assert set(baseline.columns) == {"f1", "f2", "label"}
    f1 = baseline.columns["f1"]
    assert f1.count == 5
    assert f1.null_rate == 0.0
    assert f1.mean == pytest.approx(2.0)
    assert f1.min == 0.0
    assert f1.max == 4.0
    assert f1.quantiles["0.50"] == pytest.approx(2.0)
    # constant column has zero population std
    assert baseline.columns["f2"].std == 0.0


def test_baseline_round_trips() -> None:
    baseline = _baseline()
    assert DriftBaseline.from_dict(baseline.to_dict()) == baseline


def test_unknown_schema_version_rejected() -> None:
    payload = _baseline().to_dict()
    payload["schema_version"] = "drift_baseline/v2"
    with pytest.raises(ValueError, match="schema_version"):
        DriftBaseline.from_dict(payload)


def test_skips_non_numeric_columns() -> None:
    df = pd.DataFrame({"f1": [1.0, 2.0], "name": ["a", "b"]})
    baseline = compute_drift_baseline(
        df, model_name="m", model_version="1", source_run_id="r", created_at="t"
    )
    assert "name" not in baseline.columns
    assert "f1" in baseline.columns


def test_validation_rejects_bad_null_rate() -> None:
    bad = DriftBaseline(
        model_name="m",
        model_version="1",
        source_run_id="r",
        created_at="t",
        columns={
            "f1": ColumnStats(
                count=5,
                null_rate=1.5,
                mean=0.0,
                std=0.0,
                min=0.0,
                max=0.0,
                quantiles={},
            )
        },
    )
    with pytest.raises(DriftBaselineValidationError):
        validate_drift_baseline(bad)
