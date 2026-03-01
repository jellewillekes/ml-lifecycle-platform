from __future__ import annotations

from starlette.testclient import TestClient


def test_readyz_is_ok_in_unit_testing_mode(client: TestClient) -> None:
    # In UNIT_TESTING mode, app should be ready immediately.
    r = client.get("/readyz")
    assert r.status_code == 200
    # Endpoint returns plain text in this implementation
    assert r.text.strip() == "ready"
