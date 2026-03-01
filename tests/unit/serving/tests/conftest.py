from __future__ import annotations


import pytest
from fastapi.testclient import TestClient
from _pytest.monkeypatch import MonkeyPatch

from ml_lifecycle_platform.serving.settings import get_settings


@pytest.fixture()
def client(monkeypatch: MonkeyPatch) -> TestClient:
    """
    Serve the FastAPI app in UNIT_TESTING mode so:
    - no real MLflow is called
    - models are deterministic stub models
    """
    monkeypatch.setenv("UNIT_TESTING", "1")

    # Ensure settings cache is clean (Settings is cached via lru_cache)
    get_settings.cache_clear()

    # Import lazily after env is set, so settings pick it up.
    import ml_lifecycle_platform.serving.app as app_module

    # Ensure global model cache is clean between tests
    app_module.model_prod = None
    app_module.model_candidate = None
    app_module.prod_version = None
    app_module.candidate_version = None
    app_module._last_refresh_ts = 0.0

    return TestClient(app_module.app)
