from __future__ import annotations

import base64
import json
import os

import pytest

from ml_lifecycle_platform.hosted_ci import mlflow_cloud_run_auth

pytestmark = pytest.mark.unit


def _jwt(*, exp: int) -> str:
    header = (
        base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}')
        .decode("ascii")
        .rstrip("=")
    )
    payload = (
        base64.urlsafe_b64encode(json.dumps({"exp": exp}).encode("utf-8"))
        .decode("ascii")
        .rstrip("=")
    )
    return f"{header}.{payload}."


def test_configure_mlflow_cloud_run_auth_is_noop_without_audience(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        mlflow_cloud_run_auth.ENV_MLFLOW_CLOUD_RUN_AUDIENCE, raising=False
    )
    monkeypatch.delenv(mlflow_cloud_run_auth.ENV_MLFLOW_TRACKING_TOKEN, raising=False)

    mlflow_cloud_run_auth.configure_mlflow_cloud_run_auth()

    assert os.getenv(mlflow_cloud_run_auth.ENV_MLFLOW_TRACKING_TOKEN) is None


def test_configure_mlflow_cloud_run_auth_sets_token_and_caches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        mlflow_cloud_run_auth.ENV_MLFLOW_CLOUD_RUN_AUDIENCE,
        "https://mlp-mlflow-staging.run.app",
    )
    monkeypatch.delenv(mlflow_cloud_run_auth.ENV_MLFLOW_TRACKING_TOKEN, raising=False)
    monkeypatch.setattr(mlflow_cloud_run_auth, "_cached_audience", None)
    monkeypatch.setattr(mlflow_cloud_run_auth, "_cached_token", None)
    monkeypatch.setattr(mlflow_cloud_run_auth, "_cached_expiry", 0.0)

    calls: list[str] = []
    clears: list[str] = []
    token = _jwt(exp=1_800_000_000)

    def _fetch_id_token(_request: object, audience: str) -> str:
        calls.append(audience)
        return token

    monkeypatch.setattr(
        mlflow_cloud_run_auth.id_token,
        "fetch_id_token",
        _fetch_id_token,
    )
    monkeypatch.setattr(
        mlflow_cloud_run_auth,
        "_clear_tracking_store_cache",
        lambda: clears.append("clear"),
    )

    mlflow_cloud_run_auth.configure_mlflow_cloud_run_auth()
    mlflow_cloud_run_auth.configure_mlflow_cloud_run_auth()

    assert os.environ[mlflow_cloud_run_auth.ENV_MLFLOW_TRACKING_TOKEN] == token
    assert calls == ["https://mlp-mlflow-staging.run.app"]
    assert clears == ["clear"]


def test_configure_mlflow_cloud_run_auth_refreshes_expiring_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        mlflow_cloud_run_auth.ENV_MLFLOW_CLOUD_RUN_AUDIENCE,
        "https://mlp-mlflow-staging.run.app",
    )
    monkeypatch.delenv(mlflow_cloud_run_auth.ENV_MLFLOW_TRACKING_TOKEN, raising=False)
    monkeypatch.setattr(mlflow_cloud_run_auth, "_cached_audience", None)
    monkeypatch.setattr(mlflow_cloud_run_auth, "_cached_token", None)
    monkeypatch.setattr(mlflow_cloud_run_auth, "_cached_expiry", 0.0)

    issued = iter([_jwt(exp=1_000), _jwt(exp=4_000)])
    now = iter([100.0, 800.0])
    clears: list[str] = []

    monkeypatch.setattr(mlflow_cloud_run_auth.time, "time", lambda: next(now))
    monkeypatch.setattr(
        mlflow_cloud_run_auth.id_token,
        "fetch_id_token",
        lambda _request, _audience: next(issued),
    )
    monkeypatch.setattr(
        mlflow_cloud_run_auth,
        "_clear_tracking_store_cache",
        lambda: clears.append("clear"),
    )

    mlflow_cloud_run_auth.configure_mlflow_cloud_run_auth()
    first = os.environ[mlflow_cloud_run_auth.ENV_MLFLOW_TRACKING_TOKEN]
    mlflow_cloud_run_auth.configure_mlflow_cloud_run_auth()
    second = os.environ[mlflow_cloud_run_auth.ENV_MLFLOW_TRACKING_TOKEN]

    assert first != second
    assert clears == ["clear", "clear"]


def test_decode_token_expiry_returns_none_for_invalid_token() -> None:
    assert mlflow_cloud_run_auth._decode_token_expiry("not-a-jwt") is None
