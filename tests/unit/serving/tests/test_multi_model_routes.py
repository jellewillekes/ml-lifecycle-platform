from __future__ import annotations

import pytest
from starlette.testclient import TestClient

pytestmark = pytest.mark.unit


def _valid_row() -> dict[str, float]:
    return {
        "mean_radius": 17.99,
        "mean_texture": 10.38,
        "mean_perimeter": 122.8,
        "mean_area": 1001.0,
        "mean_smoothness": 0.1184,
    }


def test_predict_path_param_matches_served_model(client: TestClient) -> None:
    r = client.post("/predict/local_csv_binary_clf", json={"rows": [_valid_row()]})
    assert r.status_code == 200, r.text
    assert r.json()["n"] == 1


def test_predict_path_param_unknown_model_404(client: TestClient) -> None:
    r = client.post("/predict/not_this_model", json={"rows": [_valid_row()]})
    assert r.status_code == 404, r.text


def test_predict_alias_route_still_works(client: TestClient) -> None:
    r = client.post("/predict", json={"rows": [_valid_row()]})
    assert r.status_code == 200, r.text


def test_metadata_model_path_param_ok(client: TestClient) -> None:
    r = client.get("/metadata/model/local_csv_binary_clf")
    assert r.status_code == 200, r.text
    assert r.json()["model_name"] == "local_csv_binary_clf"


def test_metadata_model_path_param_unknown_404(client: TestClient) -> None:
    r = client.get("/metadata/model/nope")
    assert r.status_code == 404, r.text


def test_metadata_schema_path_param_ok(client: TestClient) -> None:
    r = client.get("/metadata/schema/local_csv_binary_clf")
    assert r.status_code == 200, r.text
    assert r.json()["model_name"] == "local_csv_binary_clf"
