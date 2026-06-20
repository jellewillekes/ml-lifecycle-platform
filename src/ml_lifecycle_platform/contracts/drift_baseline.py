"""Schema-versioned ``DriftBaseline`` artifact — the statistical fingerprint of
the data a model was trained on, computed at promotion and attached to release
evidence (UP-31). Batch drift (UP-32) compares live event windows against it.

Per column it stores summary stats (count, null-rate, mean, std, min, max) and
a quantile grid. The quantiles let the drift job reconstruct a step-CDF for a
KS comparison; mean/std drive a cheaper mean/std delta. A Pandera schema
validates the summary table.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import pandas as pd
import pandera.pandas as pa
from pandera.errors import SchemaError, SchemaErrors

from ml_lifecycle_platform.common.constants import DRIFT_BASELINE_SCHEMA_VERSION

# p0, p5, ..., p100 — enough to reconstruct a step-CDF for a KS comparison.
DEFAULT_QUANTILE_GRID: tuple[float, ...] = tuple(round(i / 20, 2) for i in range(21))

_SUMMARY_KEYS = ("count", "null_rate", "mean", "std", "min", "max")


@dataclass(frozen=True)
class ColumnStats:
    count: int
    null_rate: float
    mean: float
    std: float
    min: float
    max: float
    quantiles: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "null_rate": self.null_rate,
            "mean": self.mean,
            "std": self.std,
            "min": self.min,
            "max": self.max,
            "quantiles": dict(self.quantiles),
        }

    @staticmethod
    def from_dict(payload: Mapping[str, Any]) -> ColumnStats:
        return ColumnStats(
            count=int(payload["count"]),
            null_rate=float(payload["null_rate"]),
            mean=float(payload["mean"]),
            std=float(payload["std"]),
            min=float(payload["min"]),
            max=float(payload["max"]),
            quantiles={str(k): float(v) for k, v in payload["quantiles"].items()},
        )


@dataclass(frozen=True)
class DriftBaseline:
    model_name: str
    model_version: str
    source_run_id: str
    created_at: str
    columns: dict[str, ColumnStats]
    quantile_grid: tuple[float, ...] = DEFAULT_QUANTILE_GRID
    schema_version: str = DRIFT_BASELINE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "source_run_id": self.source_run_id,
            "created_at": self.created_at,
            "quantile_grid": list(self.quantile_grid),
            "columns": {name: stats.to_dict() for name, stats in self.columns.items()},
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    def to_table(self) -> pd.DataFrame:
        """Flatten the per-column summary stats into a validatable table."""
        rows = [
            {"column": name, **{key: getattr(stats, key) for key in _SUMMARY_KEYS}}
            for name, stats in self.columns.items()
        ]
        return pd.DataFrame(rows, columns=["column", *_SUMMARY_KEYS])

    @staticmethod
    def from_dict(payload: Mapping[str, Any]) -> DriftBaseline:
        schema_version = str(payload.get("schema_version", ""))
        if schema_version != DRIFT_BASELINE_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported DriftBaseline schema_version={schema_version!r} "
                f"(expected {DRIFT_BASELINE_SCHEMA_VERSION!r})"
            )
        raw_columns = payload.get("columns")
        if not isinstance(raw_columns, dict):
            raise TypeError("DriftBaseline.columns must be a dict")
        grid = payload.get("quantile_grid", list(DEFAULT_QUANTILE_GRID))
        return DriftBaseline(
            model_name=str(payload["model_name"]),
            model_version=str(payload["model_version"]),
            source_run_id=str(payload["source_run_id"]),
            created_at=str(payload["created_at"]),
            columns={
                str(name): ColumnStats.from_dict(stats)
                for name, stats in raw_columns.items()
            },
            quantile_grid=tuple(float(q) for q in grid),
        )

    @staticmethod
    def from_json(payload: str) -> DriftBaseline:
        return DriftBaseline.from_dict(json.loads(payload))


class DriftBaselineValidationError(ValueError):
    pass


def drift_baseline_table_schema() -> pa.DataFrameSchema:
    """Pandera schema for the per-column summary table."""
    return pa.DataFrameSchema(
        columns={
            "column": pa.Column(str, required=True, nullable=False, unique=True),
            "count": pa.Column(int, pa.Check.ge(0), required=True, nullable=False),
            "null_rate": pa.Column(
                float, pa.Check.in_range(0.0, 1.0), required=True, nullable=False
            ),
            "mean": pa.Column(float, required=True, nullable=False),
            "std": pa.Column(float, pa.Check.ge(0.0), required=True, nullable=False),
            "min": pa.Column(float, required=True, nullable=False),
            "max": pa.Column(float, required=True, nullable=False),
        },
        strict=False,
        coerce=False,
    )


def validate_drift_baseline(baseline: DriftBaseline) -> DriftBaseline:
    """Validate the baseline's summary table; raise on a schema violation."""
    try:
        drift_baseline_table_schema().validate(baseline.to_table(), lazy=True)
    except (SchemaError, SchemaErrors) as error:
        raise DriftBaselineValidationError(
            f"drift baseline failed contract validation: {error}"
        ) from error
    return baseline


def quantile_keys(grid: Sequence[float]) -> list[str]:
    """Stable string keys for a quantile grid (matches ``ColumnStats.quantiles``)."""
    return [f"{q:.2f}" for q in grid]
