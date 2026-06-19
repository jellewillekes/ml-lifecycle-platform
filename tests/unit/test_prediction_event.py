from __future__ import annotations

import pytest
from pydantic import JsonValue, ValidationError

from ml_lifecycle_platform.contracts.model_ref import ModelRef
from ml_lifecycle_platform.contracts.prediction_event import (
    EventEnvelope,
    PredictionEvent,
)

pytestmark = pytest.mark.unit


def _event(
    *,
    corr_id: str = "req-1",
    event_time_ns: int = 1_700_000_000_000_000_000,
    ingest_time_ns: int = 1_700_000_000_000_000_100,
    prediction: JsonValue = 1,
    latency_ns: int = 4_200,
) -> PredictionEvent:
    return PredictionEvent(
        corr_id=corr_id,
        event_time_ns=event_time_ns,
        ingest_time_ns=ingest_time_ns,
        model_ref=ModelRef(model_name="binance_btc_1m", alias="prod"),
        features={"ret_1": 0.5, "vol": 12.0},
        prediction=prediction,
        latency_ns=latency_ns,
        envelope=EventEnvelope(service="serving", env="local"),
    )


def test_round_trips_through_dict() -> None:
    event = _event()
    restored = PredictionEvent.from_dict(event.to_dict())
    assert restored == event
    assert restored.model_ref == event.model_ref


def test_forbids_unknown_fields() -> None:
    payload = _event().to_dict()
    payload["unexpected"] = "nope"
    with pytest.raises(ValidationError):
        PredictionEvent.from_dict(payload)


def test_missing_required_field_rejected() -> None:
    payload = _event().to_dict()
    del payload["model_ref"]
    with pytest.raises(ValidationError):
        PredictionEvent.from_dict(payload)


def test_empty_corr_id_rejected() -> None:
    with pytest.raises(ValidationError):
        _event(corr_id="   ")


def test_unknown_schema_version_refused() -> None:
    payload = _event().to_dict()
    payload["schema_version"] = "2"
    with pytest.raises(ValueError, match="schema_version"):
        PredictionEvent.from_dict(payload)


def test_ns_overflow_rejected() -> None:
    with pytest.raises(ValidationError):
        _event(event_time_ns=2**63)


def test_idempotency_key_survives_round_trip() -> None:
    event = _event()
    restored = PredictionEvent.from_dict(event.to_dict())
    assert restored.idempotency_key == event.idempotency_key
    assert restored.event_id == event.event_id
