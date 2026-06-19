"""`DataSource` adapter for the bundled scikit-learn demo dataset."""

from __future__ import annotations

import pandas as pd
from sklearn.datasets import load_breast_cancer


class SklearnDemoSource:
    """Load a scikit-learn bundled dataset as a labeled dataframe."""

    def __init__(self, dataset_name: str) -> None:
        if dataset_name != "breast_cancer":
            raise ValueError(f"Unsupported sklearn demo dataset: {dataset_name!r}")
        self._dataset_name = dataset_name

    def fetch(self) -> pd.DataFrame:
        dataset = load_breast_cancer(as_frame=True)
        return dataset.frame.copy()
