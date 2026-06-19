from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ml_lifecycle_platform.backends.common.data_sources.ohlcv_features import (
    FEATURE_COLUMNS,
    build_ohlcv_features,
)

pytestmark = pytest.mark.unit


def _synthetic_ohlcv(n: int) -> pd.DataFrame:
    # A smooth, strictly varying close series so rolling windows are well-defined.
    close = 100.0 + np.cumsum(np.sin(np.linspace(0, 6, n)) + 0.01)
    return pd.DataFrame(
        {
            "open_time": np.arange(n) * 60_000,
            "open": close,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": np.full(n, 10.0),
        }
    )


def test_build_features_returns_exactly_features_plus_label() -> None:
    out = build_ohlcv_features(_synthetic_ohlcv(60), label_column="target")

    assert list(out.columns) == [*FEATURE_COLUMNS, "target"]


def test_label_is_int_zero_or_one_with_no_nans() -> None:
    out = build_ohlcv_features(_synthetic_ohlcv(60), label_column="target")

    assert out["target"].dtype.kind == "i"
    assert set(out["target"].unique()).issubset({0, 1})
    assert not out.isna().any().any()


def test_warmup_and_final_unlabeled_bar_are_dropped() -> None:
    n = 60
    out = build_ohlcv_features(_synthetic_ohlcv(n), label_column="target")

    # vol_20 needs 20 ret_1 values (which itself consumes one row); the final
    # bar has no known next close. So output is strictly shorter than input.
    assert 0 < len(out) < n - 20


def test_label_matches_next_bar_direction_without_lookahead() -> None:
    # Monotonically rising close -> every labeled bar is an "up" (1).
    rising = pd.DataFrame(
        {
            "open_time": np.arange(40) * 60_000,
            "open": np.arange(40, dtype=float),
            "high": np.arange(40, dtype=float) + 1.0,
            "low": np.arange(40, dtype=float) - 1.0,
            "close": np.arange(100.0, 140.0),
            "volume": np.full(40, 10.0),
        }
    )

    out = build_ohlcv_features(rising, label_column="target")

    assert (out["target"] == 1).all()


def test_missing_close_column_raises() -> None:
    with pytest.raises(ValueError, match="close"):
        build_ohlcv_features(
            pd.DataFrame({"open_time": [1, 2, 3]}), label_column="target"
        )
