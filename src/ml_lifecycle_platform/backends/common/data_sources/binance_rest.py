"""Binance public-market-data adapter: fetch OHLCV klines over REST and turn
them into a model-ready feature table via the shared OHLCV transform.

The default base URL is the public market-data mirror, which needs no API key
(satisfying the no-token cost rule) and avoids the geo-blocking that affects
``api.binance.com`` from some regions and clouds."""

from __future__ import annotations

import time
from typing import Any

import pandas as pd
import requests

from .ohlcv_features import build_ohlcv_features

DEFAULT_BASE_URL = "https://data-api.binance.vision"
KLINES_PATH = "/api/v3/klines"
REQUEST_TIMEOUT_S = 10.0
MAX_RETRIES = 3
RETRY_BACKOFF_S = 1.0

OHLCV_COLUMNS = ("open_time", "open", "high", "low", "close", "volume")


def fetch_klines(
    symbol: str,
    interval: str,
    limit: int,
    *,
    base_url: str = DEFAULT_BASE_URL,
) -> pd.DataFrame:
    """Fetch up to ``limit`` OHLCV bars for ``symbol`` at ``interval``."""
    payload = _request_klines(symbol, interval, limit, base_url=base_url)
    return _to_ohlcv_frame(payload)


def _request_klines(
    symbol: str,
    interval: str,
    limit: int,
    *,
    base_url: str,
) -> list[Any]:
    url = f"{base_url.rstrip('/')}{KLINES_PATH}"
    params: dict[str, str | int] = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
    }
    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_S)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise ValueError(f"Unexpected klines payload type: {type(payload)}")
            return payload
        except (requests.RequestException, ValueError) as error:
            last_error = error
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF_S * (attempt + 1))

    raise RuntimeError(
        f"Failed to fetch Binance klines for {symbol} {interval} after "
        f"{MAX_RETRIES} attempts: {last_error}"
    )


def _to_ohlcv_frame(payload: list[Any]) -> pd.DataFrame:
    rows = [
        {
            "open_time": int(row[0]),
            "open": float(row[1]),
            "high": float(row[2]),
            "low": float(row[3]),
            "close": float(row[4]),
            "volume": float(row[5]),
        }
        for row in payload
    ]
    frame = pd.DataFrame(rows, columns=list(OHLCV_COLUMNS))
    return frame.sort_values("open_time").reset_index(drop=True)


class BinanceKlinesSource:
    """`DataSource` adapter: Binance OHLCV klines -> labeled feature table."""

    def __init__(
        self,
        *,
        symbol: str,
        interval: str,
        limit: int,
        label_column: str,
        base_url: str = DEFAULT_BASE_URL,
    ) -> None:
        self._symbol = symbol
        self._interval = interval
        self._limit = limit
        self._label_column = label_column
        self._base_url = base_url

    def fetch(self) -> pd.DataFrame:
        ohlcv = fetch_klines(
            self._symbol,
            self._interval,
            self._limit,
            base_url=self._base_url,
        )
        return build_ohlcv_features(ohlcv, label_column=self._label_column)
