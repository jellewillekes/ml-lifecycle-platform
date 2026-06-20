"""Compute a ``DriftBaseline`` from a model's training split at promotion time
(UP-31). The split is the ``repro/inputs/train.csv`` artifact already logged by
the training run; a missing or unreadable split degrades to no baseline rather
than failing the promotion."""

from __future__ import annotations

import logging
import tempfile

import pandas as pd
from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient

from ml_lifecycle_platform.common.constants import (
    MLFLOW_ARTIFACT_PATH_REPRO,
    TRAIN_CSV,
)
from ml_lifecycle_platform.contracts.drift_baseline import (
    DEFAULT_QUANTILE_GRID,
    ColumnStats,
    DriftBaseline,
    quantile_keys,
    validate_drift_baseline,
)

logger = logging.getLogger(__name__)

TRAIN_SPLIT_ARTIFACT = f"{MLFLOW_ARTIFACT_PATH_REPRO}/inputs/{TRAIN_CSV}"


def compute_drift_baseline(
    df: pd.DataFrame,
    *,
    model_name: str,
    model_version: str,
    source_run_id: str,
    created_at: str,
    quantile_grid: tuple[float, ...] = DEFAULT_QUANTILE_GRID,
) -> DriftBaseline:
    """Per-column summary stats + quantile grid over the training split.

    Non-numeric or all-null columns are skipped (drift compares numeric
    feature distributions). The label column is included like any other column;
    the drift job only compares columns that also appear in live events.
    """
    keys = quantile_keys(quantile_grid)
    columns: dict[str, ColumnStats] = {}
    for name in df.columns:
        series = pd.to_numeric(df[name], errors="coerce")
        total = int(len(series))
        non_null = series.dropna()
        if total == 0 or non_null.empty:
            continue
        quantile_values = non_null.quantile(list(quantile_grid))
        columns[str(name)] = ColumnStats(
            count=total,
            null_rate=float(series.isna().mean()),
            mean=float(non_null.mean()),
            std=float(non_null.std(ddof=0)),
            min=float(non_null.min()),
            max=float(non_null.max()),
            quantiles={
                key: float(quantile_values.iloc[index])
                for index, key in enumerate(keys)
            },
        )
    baseline = DriftBaseline(
        model_name=model_name,
        model_version=model_version,
        source_run_id=source_run_id,
        created_at=created_at,
        columns=columns,
        quantile_grid=tuple(quantile_grid),
    )
    return validate_drift_baseline(baseline)


def baseline_from_source_run(
    client: MlflowClient,
    *,
    source_run_id: str,
    model_name: str,
    model_version: str,
    created_at: str,
) -> DriftBaseline | None:
    """Download the training split from the source run and compute a baseline.

    Returns ``None`` (with a warning) if the split is unavailable — a missing
    baseline must never break a promotion.
    """
    try:
        with tempfile.TemporaryDirectory(prefix="drift-baseline-") as tmpdir:
            local = client.download_artifacts(
                run_id=source_run_id,
                path=TRAIN_SPLIT_ARTIFACT,
                dst_path=tmpdir,
            )
            df = pd.read_csv(local)
        return compute_drift_baseline(
            df,
            model_name=model_name,
            model_version=model_version,
            source_run_id=source_run_id,
            created_at=created_at,
        )
    except (MlflowException, OSError, ValueError) as exc:
        logger.warning(
            "Could not compute drift baseline for %s v%s: %s",
            model_name,
            model_version,
            exc,
        )
        return None
