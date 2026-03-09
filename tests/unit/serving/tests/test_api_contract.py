from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from ml_lifecycle_platform.serving.constants import (
    HEADER_FEATURE_CONTRACT_VERSION,
    HEADER_REQUEST_ID,
)

pytestmark = pytest.mark.unit


def _valid_row() -> dict[str, float]:
    return {
        "mean_radius": 17.99,
        "mean_texture": 10.38,
        "mean_perimeter": 122.8,
        "mean_area": 1001.0,
        "mean_smoothness": 0.1184,
    }


@pytest.mark.parametrize("mode", ["prod", "candidate", "shadow"])
def test_predict_modes_ok(client: TestClient, mode: str) -> None:
    r = client.post(f"/predict?mode={mode}", json={"rows": [_valid_row()]})
    assert r.status_code == 200, r.text

    body = r.json()
    assert body["mode"] == mode
    assert body["n"] == 1
    assert isinstance(body["proba"], list)
    assert len(body["proba"]) == 1
    assert isinstance(body["proba"][0], float)
    assert body["metadata"]["contract_version"] == "local_csv_binary_clf.input/v1"
    assert r.headers[HEADER_FEATURE_CONTRACT_VERSION] == "local_csv_binary_clf.input/v1"


def test_metadata_model_exposes_contract_version(client: TestClient) -> None:
    r = client.get("/metadata/model")

    assert r.status_code == 200, r.text
    assert r.json() == {
        "model_name": "local_csv_binary_clf",
        "prod_alias": "prod",
        "candidate_alias": "candidate",
        "prod_version": None,
        "candidate_version": None,
        "contract_version": "local_csv_binary_clf.input/v1",
        "allow_unknown_fields": False,
    }


def test_metadata_schema_exposes_feature_contract(client: TestClient) -> None:
    r = client.get("/metadata/schema")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["model_name"] == "local_csv_binary_clf"
    assert body["contract_version"] == "local_csv_binary_clf.input/v1"
    assert body["allow_unknown_fields"] is False
    assert body["features"] == [
        {"name": "mean_radius", "dtype": "float", "required": True},
        {"name": "mean_texture", "dtype": "float", "required": True},
        {"name": "mean_perimeter", "dtype": "float", "required": True},
        {"name": "mean_area", "dtype": "float", "required": True},
        {"name": "mean_smoothness", "dtype": "float", "required": True},
    ]


def test_predict_invalid_json_payload_422(client: TestClient) -> None:
    r = client.post(
        "/predict?mode=prod",
        content=b"not-json",
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 422


def test_predict_rejects_missing_fields(client: TestClient) -> None:
    row = _valid_row()
    del row["mean_texture"]

    r = client.post("/predict?mode=prod", json={"rows": [row]})

    assert r.status_code == 422, r.text
    assert r.json() == {
        "detail": {
            "code": "INVALID_FEATURE_CONTRACT",
            "message": "Prediction request does not match feature contract.",
            "contract_version": "local_csv_binary_clf.input/v1",
            "issues": [
                {
                    "row": 0,
                    "field": "mean_texture",
                    "code": "missing_field",
                    "message": "Required feature is missing from request row.",
                    "expected_type": "float",
                }
            ],
        }
    }


def test_predict_rejects_unknown_fields(client: TestClient) -> None:
    row = _valid_row()
    row["unexpected"] = 1.0

    r = client.post("/predict?mode=prod", json={"rows": [row]})

    assert r.status_code == 422, r.text
    assert r.json()["detail"] == {
        "code": "INVALID_FEATURE_CONTRACT",
        "message": "Prediction request does not match feature contract.",
        "contract_version": "local_csv_binary_clf.input/v1",
        "issues": [
            {
                "row": 0,
                "field": "unexpected",
                "code": "unknown_field",
                "message": "Request row contains a field that is not declared in the feature contract.",
            }
        ],
    }


def test_predict_rejects_type_mismatches(client: TestClient) -> None:
    row = _valid_row()
    row["mean_area"] = "not-a-number"  # type: ignore[assignment]

    r = client.post("/predict?mode=prod", json={"rows": [row]})

    assert r.status_code == 422, r.text
    assert r.json()["detail"] == {
        "code": "INVALID_FEATURE_CONTRACT",
        "message": "Prediction request does not match feature contract.",
        "contract_version": "local_csv_binary_clf.input/v1",
        "issues": [
            {
                "row": 0,
                "field": "mean_area",
                "code": "type_mismatch",
                "message": "Feature value does not match the declared contract type.",
                "expected_type": "float",
                "actual_type": "string",
            }
        ],
    }


def test_request_id_header_is_echoed_if_provided(client: TestClient) -> None:
    rid = "abc-123"
    r = client.post(
        "/predict?mode=prod",
        headers={HEADER_REQUEST_ID: rid},
        json={"rows": [_valid_row()]},
    )
    assert r.status_code == 200, r.text
    assert r.headers.get(HEADER_REQUEST_ID) == rid


def test_request_id_header_is_generated_if_missing(client: TestClient) -> None:
    r = client.post("/predict?mode=prod", json={"rows": [_valid_row()]})
    assert r.status_code == 200, r.text
    rid = r.headers.get(HEADER_REQUEST_ID)
    assert isinstance(rid, str)
    assert rid != ""


def test_canary_bucket_is_stable_for_same_request_id(client: TestClient) -> None:
    rid = "stable-rid"

    r1 = client.post(
        "/predict?mode=canary",
        headers={HEADER_REQUEST_ID: rid},
        json={"rows": [_valid_row()]},
    )
    r2 = client.post(
        "/predict?mode=canary",
        headers={HEADER_REQUEST_ID: rid},
        json={"rows": [_valid_row()]},
    )

    assert r1.status_code == 200, r1.text
    assert r2.status_code == 200, r2.text
    assert r1.json()["bucket"] == r2.json()["bucket"]


def test_candidate_mode_still_loads_after_health_primes_prod_cache(
    client: TestClient,
) -> None:
    health = client.get("/health")
    assert health.status_code == 200, health.text

    r = client.post("/predict?mode=candidate", json={"rows": [_valid_row()]})
    assert r.status_code == 200, r.text
    assert r.json()["chosen"] == "candidate"
