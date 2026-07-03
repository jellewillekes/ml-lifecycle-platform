"""Batch drift computation (UP-32): compare a live event window against a
release ``DriftBaseline``.

The KS statistic is computed directly from the baseline's quantile grid (a
step-CDF) versus the live window's empirical CDF — no resampling, deterministic.
``mean_delta`` / ``std_delta`` come from the stored summary stats. A feature is
flagged when its KS statistic exceeds the threshold.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from ml_lifecycle_platform.contracts.drift_baseline import ColumnStats, DriftBaseline
from ml_lifecycle_platform.contracts.drift_report import DriftReport, FeatureDrift

DEFAULT_KS_THRESHOLD = 0.3


def _ks_from_quantiles(
    stats: ColumnStats, grid: Sequence[float], live_sorted: np.ndarray
) -> float:
    """KS = sup_x |F_live(x) - F_base(x)|, F_base from the baseline quantiles."""
    n = int(live_sorted.size)
    if n == 0:
        return 0.0
    xs = np.array([stats.quantiles[f"{q:.2f}"] for q in grid], dtype=float)
    ps = np.array(list(grid), dtype=float)
    # Degenerate (constant) baseline column: full distance unless live matches.
    if float(xs.max() - xs.min()) == 0.0:
        return 0.0 if bool(np.all(live_sorted == xs[0])) else 1.0
    eval_points = np.union1d(live_sorted, xs)
    f_live = np.searchsorted(live_sorted, eval_points, side="right") / n
    f_base = np.clip(np.interp(eval_points, xs, ps), 0.0, 1.0)
    return float(np.max(np.abs(f_live - f_base)))


def compute_drift(
    window: pd.DataFrame,
    baseline: DriftBaseline,
    *,
    window_start_ns: int,
    window_end_ns: int,
    created_at: str,
    threshold: float = DEFAULT_KS_THRESHOLD,
) -> DriftReport:
    """Compare every baseline feature also present in ``window``."""
    grid = baseline.quantile_grid
    features: dict[str, FeatureDrift] = {}
    for name, stats in baseline.columns.items():
        if name not in window.columns:
            continue
        live = pd.to_numeric(window[name], errors="coerce").dropna()
        if live.empty:
            continue
        live_sorted = np.sort(live.to_numpy(dtype=float))
        ks = _ks_from_quantiles(stats, grid, live_sorted)
        features[name] = FeatureDrift(
            feature=name,
            ks_statistic=ks,
            mean_delta=abs(float(live.mean()) - stats.mean),
            std_delta=abs(float(live.std(ddof=0)) - stats.std),
            n_events=int(live.size),
            flagged=ks > threshold,
        )
    return DriftReport(
        model_name=baseline.model_name,
        model_version=baseline.model_version,
        window_start_ns=window_start_ns,
        window_end_ns=window_end_ns,
        n_events=int(len(window)),
        threshold=threshold,
        created_at=created_at,
        features=features,
        drifted=any(feature.flagged for feature in features.values()),
    )
