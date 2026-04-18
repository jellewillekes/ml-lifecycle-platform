"""Binary classification metric helpers shared by the train and evaluate
pipeline steps."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score


def compute_binary_metrics(
    *,
    metric_names: tuple[str, ...],
    y_true: pd.Series,
    pred: np.ndarray,
    proba: np.ndarray,
    prefix: str,
) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for metric_name in metric_names:
        if metric_name == "accuracy":
            value = accuracy_score(y_true, pred)
        elif metric_name == "f1":
            value = f1_score(y_true, pred)
        elif metric_name == "roc_auc":
            value = roc_auc_score(y_true, proba)
        else:  # pragma: no cover
            raise ValueError(f"Unsupported metric: {metric_name}")
        metrics[f"{prefix}_{metric_name}"] = float(value)
    return metrics
