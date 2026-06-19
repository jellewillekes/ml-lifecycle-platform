"""Pydantic + Pandera contracts for delayed realized labels.

The row-level ``LabelEvent`` mirrors ``PredictionEvent``'s envelope
conventions; ``labels_table_schema`` validates the batch ``labels`` table that
feedback capture (UP-34) joins against prediction events on ``corr_id``.
Contract-only: no ingestion job here.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal
from uuid import UUID, uuid4

import pandas as pd
import pandera.pandas as pa
from pandera.errors import SchemaError, SchemaErrors
from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

from ml_lifecycle_platform.common.constants import LABEL_EVENT_SCHEMA_VERSION

# ns-since-epoch must fit a signed 64-bit column (BigQuery INT64, Parquet).
_INT64_MAX = 2**63 - 1


class LabelEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1"] = "1"
    event_id: UUID = Field(default_factory=uuid4)
    corr_id: str
    label_time_ns: int
    label: JsonValue
    source: str

    @field_validator("corr_id", "source")
    @classmethod
    def _validate_non_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must be a non-empty string")
        return stripped

    @field_validator("label_time_ns")
    @classmethod
    def _validate_ns(cls, value: int) -> int:
        if value < 0 or value > _INT64_MAX:
            raise ValueError(f"ns value out of signed 64-bit range: {value}")
        return value

    def to_dict(self) -> dict[str, JsonValue]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> LabelEvent:
        schema_version = str(payload.get("schema_version", ""))
        if schema_version != LABEL_EVENT_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported LabelEvent schema_version={schema_version!r} "
                f"(expected {LABEL_EVENT_SCHEMA_VERSION!r})"
            )
        return cls.model_validate(dict(payload))


class LabelsTableValidationError(ValueError):
    pass


def labels_table_schema() -> pa.DataFrameSchema:
    """Pandera schema for the batch ``labels`` table.

    ``corr_id`` is the join key against prediction events. Every key column is
    required and non-null, so a missing column or a bad join key fails loudly
    before the feedback join (UP-34) runs.
    """
    return pa.DataFrameSchema(
        columns={
            "corr_id": pa.Column(str, required=True, nullable=False),
            "event_id": pa.Column(str, required=True, nullable=False),
            "label_time_ns": pa.Column(int, required=True, nullable=False),
            "label": pa.Column(required=True, nullable=False),
            "source": pa.Column(str, required=True, nullable=False),
            "schema_version": pa.Column(str, required=True, nullable=False),
        },
        strict=False,
        coerce=False,
    )


def validate_labels_table(df: pd.DataFrame) -> pd.DataFrame:
    try:
        return labels_table_schema().validate(df, lazy=True)
    except (SchemaError, SchemaErrors) as error:
        raise LabelsTableValidationError(
            f"labels table failed contract validation: {error}"
        ) from error
