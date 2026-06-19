"""Derive a small alpha-feature table with a next-bar direction label from
OHLCV bars. Pure transform shared by every OHLCV data-source adapter, so a new
exchange adapter reuses it instead of reimplementing feature logic."""

from __future__ import annotations

import pandas as pd

EMA_FAST_SPAN = 12
RSI_WINDOW = 14
VOL_WINDOW = 20
MOMENTUM_WINDOW = 10

FEATURE_COLUMNS = (
    "ret_1",
    "ret_5",
    "momentum_10",
    "ema_ratio_fast",
    "rsi_14",
    "vol_20",
)


def build_ohlcv_features(ohlcv: pd.DataFrame, *, label_column: str) -> pd.DataFrame:
    """Return ``[*FEATURE_COLUMNS, label_column]`` sorted ascending by time.

    Every feature uses only information available at or before its own bar. The
    label is the sign of the next bar's close-to-close return (1 = up, 0 =
    down/flat). Warmup rows (incomplete rolling windows) and the final bar
    (whose next-bar label is unknown) are dropped, and the label is cast to the
    int {0, 1} that the dataset contract requires.
    """
    if "close" not in ohlcv.columns:
        raise ValueError("OHLCV frame must contain a 'close' column.")

    frame = ohlcv.reset_index(drop=True)
    close = frame["close"].astype(float)

    features = pd.DataFrame(index=frame.index)
    features["ret_1"] = close.pct_change(1)
    features["ret_5"] = close.pct_change(5)
    features["momentum_10"] = close / close.shift(MOMENTUM_WINDOW) - 1.0
    ema_fast = close.ewm(span=EMA_FAST_SPAN, adjust=False).mean()
    features["ema_ratio_fast"] = close / ema_fast - 1.0
    features["rsi_14"] = _rsi(close, RSI_WINDOW)
    features["vol_20"] = features["ret_1"].rolling(VOL_WINDOW).std()

    features[label_column] = _next_bar_direction(close)

    ordered = features[[*FEATURE_COLUMNS, label_column]].dropna().reset_index(drop=True)
    ordered[label_column] = ordered[label_column].astype(int)
    return ordered


def _next_bar_direction(close: pd.Series) -> pd.Series:
    """1 where the next close is higher than this close, 0 otherwise, NaN for
    the final bar whose next close is unknown (so it gets dropped)."""
    next_close = close.shift(-1)
    direction = (next_close > close).astype("float64")
    direction[next_close.isna()] = float("nan")
    return direction


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)
