from __future__ import annotations

import base64
import json
import os
import threading
import time

from google.auth.transport.requests import Request
from google.oauth2 import id_token
from mlflow.tracking._tracking_service import utils as tracking_utils

ENV_MLFLOW_CLOUD_RUN_AUDIENCE = "MLFLOW_CLOUD_RUN_AUDIENCE"
ENV_MLFLOW_TRACKING_TOKEN = "MLFLOW_TRACKING_TOKEN"
_REFRESH_WINDOW_SEC = 300.0
_DEFAULT_TOKEN_TTL_SEC = 3600.0

_cached_audience: str | None = None
_cached_token: str | None = None
_cached_expiry: float = 0.0
_lock = threading.Lock()


def configure_mlflow_cloud_run_auth() -> None:
    audience = _audience()
    if audience is None:
        return

    token = _token_for_audience(audience)
    if os.environ.get(ENV_MLFLOW_TRACKING_TOKEN) == token:
        return

    os.environ[ENV_MLFLOW_TRACKING_TOKEN] = token
    _clear_tracking_store_cache()


def _audience() -> str | None:
    audience = os.getenv(ENV_MLFLOW_CLOUD_RUN_AUDIENCE, "").strip()
    return audience or None


def _token_for_audience(audience: str) -> str:
    global _cached_audience, _cached_token, _cached_expiry

    now = time.time()
    with _lock:
        if (
            _cached_token is not None
            and _cached_audience == audience
            and now < (_cached_expiry - _REFRESH_WINDOW_SEC)
        ):
            return _cached_token

        token = id_token.fetch_id_token(Request(), audience)
        expiry = _decode_token_expiry(token) or (now + _DEFAULT_TOKEN_TTL_SEC)

        _cached_audience = audience
        _cached_token = token
        _cached_expiry = expiry
        return token


def _clear_tracking_store_cache() -> None:
    cache_clear = getattr(
        tracking_utils._tracking_store_registry._get_store_with_resolved_uri,
        "cache_clear",
        None,
    )
    if cache_clear is not None:
        cache_clear()


def _decode_token_expiry(token: str) -> float | None:
    parts = token.split(".")
    if len(parts) != 3:
        return None

    payload = parts[1]
    padded = payload + "=" * (-len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
        claims = json.loads(decoded.decode("utf-8"))
    except ValueError:
        return None

    exp = claims.get("exp")
    if isinstance(exp, (int, float)):
        return float(exp)
    return None
