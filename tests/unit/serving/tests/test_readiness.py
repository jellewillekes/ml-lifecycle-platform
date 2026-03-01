from __future__ import annotations

import pytest
from starlette.testclient import TestClient

pytestmark = pytest.mark.unit


def test_readyz_is_ok_in_unit_testing_mode(client: TestClient) -> None:
    # In UNIT_TESTING mode, app should be ready immediately.
    r = client.get("/readyz")
    assert r.status_code == 200
    # Endpoint returns plain text in this implementation
    assert r.text.strip() == "ready"
