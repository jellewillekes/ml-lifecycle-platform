from __future__ import annotations

from collections.abc import Iterator

import pytest
from _pytest.monkeypatch import MonkeyPatch
from fastapi.testclient import TestClient

from ml_lifecycle_platform.serving.settings import get_settings


@pytest.fixture()
def client(monkeypatch: MonkeyPatch) -> Iterator[TestClient]:
    """Serve the app in UNIT_TESTING mode with deterministic stub models."""
    monkeypatch.setenv("UNIT_TESTING", "1")

    # Clear the cached settings.
    get_settings.cache_clear()

    # Import after env vars are set.
    import ml_lifecycle_platform.serving.app as app_module

    # Clear the global model cache between tests.
    app_module.model_prod = None
    app_module.model_candidate = None
    app_module.prod_version = None
    app_module.candidate_version = None
    app_module._last_refresh_ts = 0.0

    try:
        with TestClient(app_module.app) as test_client:
            yield test_client
    finally:
        get_settings.cache_clear()
