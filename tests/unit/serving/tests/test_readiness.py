from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from ml_lifecycle_platform.serving.settings import get_settings

pytestmark = pytest.mark.unit


def test_readyz_is_ok_in_unit_testing_mode(client: TestClient) -> None:
    # UNIT_TESTING mode should be ready immediately.
    r = client.get("/readyz")
    assert r.status_code == 200
    # This endpoint returns plain text.
    assert r.text.strip() == "ready"


def test_livez_does_not_require_mlflow_configuration_on_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UNIT_TESTING", "1")
    monkeypatch.setenv("MODEL_NAME", "local_csv_binary_clf")
    monkeypatch.setenv(
        "MLP_MODEL_SPEC_PATH", "configs/models/local_csv_binary_classifier.yaml"
    )
    get_settings.cache_clear()

    import ml_lifecycle_platform.serving.app as app_module

    app_module.model_prod = None
    app_module.model_candidate = None
    app_module.prod_version = None
    app_module.candidate_version = None
    app_module._last_refresh_ts = 0.0
    app_module._load_feature_contract.cache_clear()

    def fail_configure_mlflow() -> None:
        raise AssertionError("configure_mlflow should not run during FastAPI startup")

    monkeypatch.setattr(app_module, "configure_mlflow", fail_configure_mlflow)

    try:
        with TestClient(app_module.app) as test_client:
            response = test_client.get("/livez")
            assert response.status_code == 200
            assert response.json() == {"status": "alive"}
    finally:
        get_settings.cache_clear()
