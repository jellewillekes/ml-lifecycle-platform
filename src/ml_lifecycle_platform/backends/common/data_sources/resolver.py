"""Resolve a model spec's declared source into a concrete `DataSource`
adapter. This is the single dispatch point: adding a new source kind touches
only this function (plus its adapter, spec type, and parser arm)."""

from __future__ import annotations

from ml_lifecycle_platform.core.model_spec_types import (
    BinanceSourceSpec,
    CsvSourceSpec,
    ModelSpec,
    SklearnDemoSourceSpec,
)
from ml_lifecycle_platform.core.ports import DataSource

from .binance_rest import BinanceKlinesSource
from .csv_source import CsvSource
from .sklearn_demo import SklearnDemoSource


def build_data_source(spec: ModelSpec) -> DataSource:
    """Return the `DataSource` adapter for the spec's declared source."""
    source = spec.source

    if isinstance(source, BinanceSourceSpec):
        return BinanceKlinesSource(
            symbol=source.symbol,
            interval=source.interval,
            limit=source.limit,
            label_column=spec.label_column,
        )
    if isinstance(source, CsvSourceSpec):
        return CsvSource(source.resolved_path(spec_path=spec.spec_path))
    if isinstance(source, SklearnDemoSourceSpec):
        return SklearnDemoSource(source.dataset_name)

    raise ValueError(f"Unsupported source kind: {source.kind!r}")
