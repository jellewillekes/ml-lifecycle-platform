"""Pydantic contract for a single prediction emitted onto the event plane.

The envelope carries ns-precision timestamps and latency attribution so the
cold event sink (UP-29a), drift (UP-32), replay (UP-30), and feedback (UP-34)
all read one stable schema. Contract-only: nothing emits this yet.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

from ml_lifecycle_platform.common.constants import PREDICTION_EVENT_SCHEMA_VERSION
from ml_lifecycle_platform.contracts.model_ref import ModelRef

# ns-since-epoch must fit a signed 64-bit column (BigQuery INT64, Parquet).
_INT64_MAX = 2**63 - 1


class EventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    service: str
    env: Literal["local", "staging", "prod"]
    run_id: str | None = None
    git_sha: str | None = None


class PredictionEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1"] = "1"
    event_id: UUID = Field(default_factory=uuid4)
    corr_id: str
    event_time_ns: int
    ingest_time_ns: int
    model_ref: ModelRef
    features: dict[str, JsonValue]
    prediction: JsonValue
    latency_ns: int
    envelope: EventEnvelope

    @field_validator("corr_id")
    @classmethod
    def _validate_corr_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must be a non-empty string")
        return stripped

    @field_validator("event_time_ns", "ingest_time_ns", "latency_ns")
    @classmethod
    def _validate_ns(cls, value: int) -> int:
        if value < 0 or value > _INT64_MAX:
            raise ValueError(f"ns value out of signed 64-bit range: {value}")
        return value

    @property
    def idempotency_key(self) -> str:
        """Stable dedup key for the sink; survives serialisation round-trips."""
        return str(self.event_id)

    def to_dict(self) -> dict[str, JsonValue]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PredictionEvent:
        schema_version = str(payload.get("schema_version", ""))
        if schema_version != PREDICTION_EVENT_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported PredictionEvent schema_version={schema_version!r} "
                f"(expected {PREDICTION_EVENT_SCHEMA_VERSION!r})"
            )
        data = dict(payload)
        if "model_ref" in data:
            data["model_ref"] = ModelRef.from_dict(data["model_ref"])
        return cls.model_validate(data)
