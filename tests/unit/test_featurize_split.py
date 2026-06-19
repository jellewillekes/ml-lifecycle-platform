from __future__ import annotations

import pandas as pd
import pytest

from ml_lifecycle_platform.core.model_spec_types import SplitSpec
from ml_lifecycle_platform.pipeline.featurize import split_train_test

pytestmark = pytest.mark.unit


def _xy(n: int) -> tuple[pd.DataFrame, pd.Series]:
    X = pd.DataFrame({"f": range(n)})
    y = pd.Series([0, 1] * (n // 2))
    return X, y


def test_chronological_split_holds_out_the_most_recent_rows() -> None:
    X, y = _xy(100)
    split = SplitSpec(
        test_size=0.2, random_state=42, stratify=False, method="chronological"
    )

    X_train, X_test, _y_train, _y_test = split_train_test(X, y, split)

    # No shuffle: train is the earliest 80 rows, test is the latest 20, in order.
    assert list(X_test.index) == list(range(80, 100))
    assert list(X_train.index) == list(range(0, 80))


def test_random_split_shuffles_rows() -> None:
    X, y = _xy(100)
    split = SplitSpec(test_size=0.2, random_state=42, stratify=True, method="random")

    _X_train, X_test, _y_train, _y_test = split_train_test(X, y, split)

    # A stratified random split does not hand back a contiguous tail.
    assert list(X_test.index) != list(range(80, 100))
    assert len(X_test) == 20
