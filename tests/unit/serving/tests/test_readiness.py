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
    import ml_lifecycle_platform.serving.model_store as model_store_module

    from ml_lifecycle_platform.serving.model_store import get_model_store

    get_model_store().reset()
    app_module._load_feature_contract.cache_clear()

    def fail_configure_mlflow() -> None:
        raise AssertionError("configure_mlflow should not run during FastAPI startup")

    monkeypatch.setattr(model_store_module, "configure_mlflow", fail_configure_mlflow)

    try:
        with TestClient(app_module.app) as test_client:
            response = test_client.get("/livez")
            assert response.status_code == 200
            assert response.json() == {"status": "alive"}
    finally:
        get_settings.cache_clear()


def test_health_reports_not_ready_without_raising_when_prod_model_load_fails(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import ml_lifecycle_platform.serving.app as app_module

    monkeypatch.setattr(
        app_module,
        "_registry_resolves_prod_alias",
        lambda settings: (True, None),
    )
    monkeypatch.setattr(
        app_module,
        "_prod_model_loadable",
        lambda settings: (False, "prod model not loadable: registry timeout"),
    )

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["ready"] is False
    assert response.json()["prod_model_ok"] is False
    assert response.json()["prod_model_detail"] == (
        "prod model not loadable: registry timeout"
    )
