from __future__ import annotations

import pytest
from starlette.testclient import TestClient

pytestmark = pytest.mark.unit


def test_readyz_is_ok_in_unit_testing_mode(client: TestClient) -> None:
    # UNIT_TESTING mode should be ready immediately.
    r = client.get("/readyz")
    assert r.status_code == 200
    # This endpoint returns plain text.
    assert r.text.strip() == "ready"
