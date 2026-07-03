from __future__ import annotations

import pandas as pd
import pytest

from ml_lifecycle_platform.contracts.drift_baseline import DriftBaseline
from ml_lifecycle_platform.contracts.drift_report import DriftReport
from ml_lifecycle_platform.core.drift import compute_drift
from ml_lifecycle_platform.registry.drift_baseline import compute_drift_baseline

pytestmark = pytest.mark.unit


def _baseline() -> DriftBaseline:
    ref = pd.DataFrame({"f1": list(range(100)), "f2": [5.0] * 100})
    return compute_drift_baseline(
        ref, model_name="m", model_version="1", source_run_id="r", created_at="t"
    )


def _report(window: pd.DataFrame) -> DriftReport:
    return compute_drift(
        window, _baseline(), window_start_ns=0, window_end_ns=1, created_at="t"
    )


def test_stable_window_not_flagged() -> None:
    report = _report(pd.DataFrame({"f1": list(range(100))}))
    assert report.features["f1"].ks_statistic <= 0.3
    assert not report.features["f1"].flagged
    assert not report.drifted


def test_shifted_window_flagged() -> None:
    report = _report(pd.DataFrame({"f1": list(range(1000, 1100))}))
    assert report.features["f1"].ks_statistic > 0.3
    assert report.features["f1"].flagged
    assert report.drifted


def test_only_compares_shared_features() -> None:
    report = _report(pd.DataFrame({"f1": list(range(100)), "unknown": [1] * 100}))
    # f2 is in the baseline but absent from the window; unknown is not in the baseline
    assert set(report.features) == {"f1"}


def test_report_round_trips() -> None:
    report = _report(pd.DataFrame({"f1": list(range(100))}))
    assert DriftReport.from_dict(report.to_dict()) == report


def test_unknown_report_schema_rejected() -> None:
    payload = _report(pd.DataFrame({"f1": list(range(100))})).to_dict()
    payload["schema_version"] = "drift_report/v2"
    with pytest.raises(ValueError, match="schema_version"):
        DriftReport.from_dict(payload)
