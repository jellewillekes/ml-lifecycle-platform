from __future__ import annotations

import pandas as pd
import pytest

from ml_lifecycle_platform.backends.common.data_sources.binance_rest import (
    BinanceKlinesSource,
)
from ml_lifecycle_platform.backends.common.data_sources.csv_source import CsvSource
from ml_lifecycle_platform.backends.common.data_sources.resolver import (
    build_data_source,
)
from ml_lifecycle_platform.backends.common.data_sources.sklearn_demo import (
    SklearnDemoSource,
)
from ml_lifecycle_platform.core.model_specs import load_model_spec

pytestmark = pytest.mark.unit


def test_resolver_dispatches_binance() -> None:
    spec = load_model_spec("configs/models/binance_btc_1m.yaml")
    assert isinstance(build_data_source(spec), BinanceKlinesSource)


def test_resolver_dispatches_csv() -> None:
    spec = load_model_spec("configs/models/local_csv_binary_classifier.yaml")
    assert isinstance(build_data_source(spec), CsvSource)


def test_resolver_dispatches_sklearn_demo() -> None:
    spec = load_model_spec("configs/models/breast_cancer_demo.yaml")
    assert isinstance(build_data_source(spec), SklearnDemoSource)


def test_csv_source_reads_committed_example_offline() -> None:
    spec = load_model_spec("configs/models/local_csv_binary_classifier.yaml")
    frame = build_data_source(spec).fetch()

    assert isinstance(frame, pd.DataFrame)
    assert spec.label_column in frame.columns
    assert not frame.empty


def test_sklearn_demo_source_returns_breast_cancer_frame() -> None:
    frame = SklearnDemoSource("breast_cancer").fetch()

    assert isinstance(frame, pd.DataFrame)
    assert "target" in frame.columns


def test_sklearn_demo_source_rejects_unknown_dataset() -> None:
    with pytest.raises(ValueError, match="Unsupported sklearn demo dataset"):
        SklearnDemoSource("iris")
