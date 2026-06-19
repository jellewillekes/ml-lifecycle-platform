from __future__ import annotations

import pandas as pd
import pytest
from pydantic import ValidationError

from ml_lifecycle_platform.contracts.label_event import (
    LabelEvent,
    LabelsTableValidationError,
    validate_labels_table,
)

pytestmark = pytest.mark.unit


def _label_event() -> LabelEvent:
    return LabelEvent(
        corr_id="req-1",
        label_time_ns=1_700_000_000_000_000_000,
        label=1,
        source="binance_bar_close",
    )


def _labels_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "corr_id": ["req-1", "req-2"],
            "event_id": ["evt-1", "evt-2"],
            "label_time_ns": [
                1_700_000_000_000_000_000,
                1_700_000_000_000_000_001,
            ],
            "label": [1, 0],
            "source": ["binance_bar_close", "binance_bar_close"],
            "schema_version": ["1", "1"],
        }
    )


def test_label_event_round_trips() -> None:
    event = _label_event()
    assert LabelEvent.from_dict(event.to_dict()) == event


def test_label_event_rejects_empty_corr_id() -> None:
    with pytest.raises(ValidationError):
        LabelEvent(
            corr_id="   ",
            label_time_ns=1,
            label=1,
            source="binance_bar_close",
        )


def test_label_event_unknown_schema_version_refused() -> None:
    payload = _label_event().to_dict()
    payload["schema_version"] = "2"
    with pytest.raises(ValueError, match="schema_version"):
        LabelEvent.from_dict(payload)


def test_labels_table_accepts_valid_frame() -> None:
    assert len(validate_labels_table(_labels_df())) == 2


def test_labels_table_rejects_null_join_key() -> None:
    df = _labels_df()
    df.loc[0, "corr_id"] = None
    with pytest.raises(LabelsTableValidationError):
        validate_labels_table(df)


def test_labels_table_rejects_missing_column() -> None:
    df = _labels_df().drop(columns=["label_time_ns"])
    with pytest.raises(LabelsTableValidationError):
        validate_labels_table(df)
