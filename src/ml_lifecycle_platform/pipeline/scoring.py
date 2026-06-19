"""Load the candidate model from the captured train run and score it on the
held-out test split. Shared by the ``evaluate`` and ``validate_model`` steps so
both read the same model and predictions."""

from __future__ import annotations

from dataclasses import dataclass

import mlflow
import numpy as np
import pandas as pd

from ml_lifecycle_platform.common.constants import (
    ART_TRAIN_RUN_ID,
    MLFLOW_ARTIFACT_PATH_MODEL,
    TEST_CSV,
)
from ml_lifecycle_platform.core.batch_contracts import validate_labeled_dataset
from ml_lifecycle_platform.core.model_spec_types import ModelSpec
from ml_lifecycle_platform.runtime.context import RuntimeContext


@dataclass(frozen=True)
class ScoredTestSplit:
    test_df: pd.DataFrame
    y_true: pd.Series
    pred: np.ndarray
    proba: np.ndarray


def load_scored_test_split(ctx: RuntimeContext, spec: ModelSpec) -> ScoredTestSplit:
    """Read the test split, load the trained model, and return its scores.

    ``test_df`` keeps the feature columns so callers can slice it into segments.
    """
    test_df = pd.read_csv(ctx.data_dir / TEST_CSV)
    test_df = validate_labeled_dataset(
        test_df, spec=spec, stage="evaluate", dataset_name="test"
    )
    X_test = test_df.drop(columns=[spec.label_column])
    y_true = test_df[spec.label_column].astype(int)

    train_run_id = (
        (ctx.artifacts_dir / ART_TRAIN_RUN_ID).read_text(encoding="utf-8").strip()
    )
    model = mlflow.pyfunc.load_model(
        f"runs:/{train_run_id}/{MLFLOW_ARTIFACT_PATH_MODEL}"
    )

    proba = np.array(model.predict(X_test))
    pred = (proba >= 0.5).astype(int)
    return ScoredTestSplit(test_df=test_df, y_true=y_true, pred=pred, proba=proba)
