from __future__ import annotations

import pandas as pd
import pytest
import requests

from ml_lifecycle_platform.backends.common.data_sources import binance_rest
from ml_lifecycle_platform.backends.common.data_sources.binance_rest import (
    BinanceKlinesSource,
    OHLCV_COLUMNS,
    fetch_klines,
)
from ml_lifecycle_platform.backends.common.data_sources.ohlcv_features import (
    FEATURE_COLUMNS,
)

pytestmark = pytest.mark.unit


class _FakeResponse:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        return self._payload


def _kline_row(open_time: int, close: float) -> list[object]:
    # Binance returns 12-element arrays; only the first six matter here.
    return [
        open_time,
        "1.0",
        "2.0",
        "0.5",
        str(close),
        "10.0",
        0,
        "0",
        0,
        "0",
        "0",
        "0",
    ]


def test_fetch_klines_parses_payload_into_ohlcv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = [_kline_row(i * 60_000, 100.0 + i) for i in range(5)]

    def fake_get(
        url: str, params: object = None, timeout: object = None
    ) -> _FakeResponse:
        return _FakeResponse(payload)

    monkeypatch.setattr(binance_rest.requests, "get", fake_get)

    frame = fetch_klines("BTCUSDT", "1m", 5)

    assert list(frame.columns) == list(OHLCV_COLUMNS)
    assert frame["close"].tolist() == [100.0, 101.0, 102.0, 103.0, 104.0]
    assert frame["open_time"].is_monotonic_increasing


def test_fetch_klines_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def flaky_get(
        url: str, params: object = None, timeout: object = None
    ) -> _FakeResponse:
        calls["n"] += 1
        if calls["n"] < 3:
            raise requests.RequestException("transient")
        return _FakeResponse([_kline_row(0, 100.0)])

    monkeypatch.setattr(binance_rest.requests, "get", flaky_get)
    monkeypatch.setattr(binance_rest.time, "sleep", lambda _seconds: None)

    frame = fetch_klines("BTCUSDT", "1m", 1)

    assert calls["n"] == 3
    assert len(frame) == 1


def test_fetch_klines_raises_after_exhausting_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def always_fails(
        url: str, params: object = None, timeout: object = None
    ) -> _FakeResponse:
        raise requests.RequestException("down")

    monkeypatch.setattr(binance_rest.requests, "get", always_fails)
    monkeypatch.setattr(binance_rest.time, "sleep", lambda _seconds: None)

    with pytest.raises(RuntimeError, match="Failed to fetch Binance klines"):
        fetch_klines("BTCUSDT", "1m", 1)


def test_source_fetch_returns_model_ready_frame(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = [_kline_row(i * 60_000, 100.0 + (i % 7)) for i in range(60)]

    def fake_get(
        url: str, params: object = None, timeout: object = None
    ) -> _FakeResponse:
        return _FakeResponse(payload)

    monkeypatch.setattr(binance_rest.requests, "get", fake_get)

    source = BinanceKlinesSource(
        symbol="BTCUSDT", interval="1m", limit=60, label_column="target"
    )
    frame = source.fetch()

    assert isinstance(frame, pd.DataFrame)
    assert list(frame.columns) == [*FEATURE_COLUMNS, "target"]
    assert not frame.empty
