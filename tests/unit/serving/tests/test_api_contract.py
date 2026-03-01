from __future__ import annotations


import pytest
from starlette.testclient import TestClient

from ml_lifecycle_platform.serving.constants import HEADER_REQUEST_ID

pytestmark = pytest.mark.unit


def test_livez_ok(client: TestClient) -> None:
    r = client.get("/livez")
    assert r.status_code == 200
    assert r.json() == {"status": "alive"}


@pytest.mark.parametrize("mode", ["prod", "candidate", "shadow"])
def test_predict_modes_ok(client: TestClient, mode: str) -> None:
    r = client.post(
        f"/predict?mode={mode}",
        json={"rows": [{"f1": 1.0, "f2": 2.0, "f3": 3.0}]},
    )
    assert r.status_code == 200, r.text

    body = r.json()
    assert body["mode"] == mode
    assert body["n"] == 1
    assert isinstance(body["proba"], list)
    assert len(body["proba"]) == 1
    assert isinstance(body["proba"][0], float)


def test_predict_invalid_payload_422(client: TestClient) -> None:
    # send invalid JSON for Pydantic model
    r = client.post(
        "/predict?mode=prod",
        content=b"not-json",
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 422


def test_request_id_header_is_echoed_if_provided(client: TestClient) -> None:
    rid = "abc-123"
    r = client.post(
        "/predict?mode=prod",
        headers={HEADER_REQUEST_ID: rid},
        json={"rows": [{"f1": 1.0, "f2": 2.0, "f3": 3.0}]},
    )
    assert r.status_code == 200, r.text
    assert r.headers.get(HEADER_REQUEST_ID) == rid


def test_request_id_header_is_generated_if_missing(client: TestClient) -> None:
    r = client.post(
        "/predict?mode=prod",
        json={"rows": [{"f1": 1.0, "f2": 2.0, "f3": 3.0}]},
    )
    assert r.status_code == 200, r.text
    # Middleware should add it
    rid = r.headers.get(HEADER_REQUEST_ID)
    assert isinstance(rid, str)
    assert rid != ""


def test_canary_bucket_is_stable_for_same_request_id(client: TestClient) -> None:
    rid = "stable-rid"

    r1 = client.post(
        "/predict?mode=canary",
        headers={HEADER_REQUEST_ID: rid},
        json={"rows": [{"f1": 1.0, "f2": 2.0, "f3": 3.0}]},
    )
    r2 = client.post(
        "/predict?mode=canary",
        headers={HEADER_REQUEST_ID: rid},
        json={"rows": [{"f1": 1.0, "f2": 2.0, "f3": 3.0}]},
    )

    assert r1.status_code == 200, r1.text
    assert r2.status_code == 200, r2.text

    b1 = r1.json().get("bucket")
    b2 = r2.json().get("bucket")
    assert b1 == b2


def test_candidate_mode_still_loads_after_health_primes_prod_cache(
    client: TestClient,
) -> None:
    health = client.get("/health")
    assert health.status_code == 200, health.text

    r = client.post(
        "/predict?mode=candidate",
        json={"rows": [{"f1": 1.0, "f2": 2.0, "f3": 3.0}]},
    )
    assert r.status_code == 200, r.text
    assert r.json()["chosen"] == "candidate"
