from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

from ml_lifecycle_platform.common.constants import RUNTIME_EVENT_SCHEMA_VERSION


class RuntimeEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = RUNTIME_EVENT_SCHEMA_VERSION
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    event_type: str
    payload: dict[str, JsonValue]

    @field_validator("event_type")
    @classmethod
    def _validate_event_type(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must be a non-empty string")
        return stripped

    def to_dict(self) -> dict[str, JsonValue]:
        return self.model_dump(mode="json")
