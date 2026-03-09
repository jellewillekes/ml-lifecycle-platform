from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ml_lifecycle_platform.core.batch_contracts import (
    BatchContractValidationError,
    validate_labeled_dataset,
)
from ml_lifecycle_platform.core.model_specs import load_model_spec

pytestmark = pytest.mark.unit


def test_validate_labeled_dataset_accepts_committed_csv_example() -> None:
    spec = load_model_spec("configs/models/local_csv_binary_classifier.yaml")
    csv_path = Path("examples/csv/local_csv_binary_classifier.csv")
    df = pd.read_csv(csv_path)

    validated = validate_labeled_dataset(
        df,
        spec=spec,
        stage="ingest",
        dataset_name="source",
    )

    assert list(validated.columns) == list(df.columns)


def test_validate_labeled_dataset_rejects_missing_label_column() -> None:
    spec = load_model_spec("configs/models/local_csv_binary_classifier.yaml")
    df = pd.read_csv(Path("examples/csv/local_csv_binary_classifier.csv")).drop(
        columns=[spec.label_column]
    )

    with pytest.raises(
        BatchContractValidationError,
        match="featurize dataset 'raw' failed contract validation",
    ) as error:
        validate_labeled_dataset(
            df,
            spec=spec,
            stage="featurize",
            dataset_name="raw",
        )

    assert spec.label_column in str(error.value)


def test_validate_labeled_dataset_rejects_unknown_columns() -> None:
    spec = load_model_spec("configs/models/local_csv_binary_classifier.yaml")
    df = pd.read_csv(Path("examples/csv/local_csv_binary_classifier.csv"))
    df["unexpected"] = 1.0

    with pytest.raises(BatchContractValidationError, match="unexpected"):
        validate_labeled_dataset(
            df,
            spec=spec,
            stage="train",
            dataset_name="train",
        )
