from __future__ import annotations

import pytest

from ml_lifecycle_platform.serving.router import (
    BucketContext,
    SeedSource,
    choose_canary_bucket,
    decide_routing,
)

pytestmark = pytest.mark.unit


def test_choose_canary_bucket_is_deterministic_for_request_id() -> None:
    ctx = BucketContext(
        request_id="my-request-id",
        client_provided_request_id=True,
        rows=[{"f1": 1.0, "f2": 2.0}],
    )

    d1 = choose_canary_bucket(ctx)
    d2 = choose_canary_bucket(ctx)

    assert d1.bucket == d2.bucket
    assert d1.seed_source == d2.seed_source
    assert d1.seed_source == SeedSource.REQUEST_ID


def test_choose_canary_bucket_falls_back_to_payload_hash_when_no_request_id() -> None:
    ctx = BucketContext(
        request_id=None,
        client_provided_request_id=False,
        rows=[{"f1": 1.0, "f2": 2.0}],
    )

    d1 = choose_canary_bucket(ctx)
    d2 = choose_canary_bucket(ctx)

    assert d1.bucket == d2.bucket
    assert d1.seed_source == d2.seed_source
    assert d1.seed_source == SeedSource.PAYLOAD_HASH


def test_decide_routing_is_deterministic_given_bucket() -> None:
    # Routing is a pure function of (mode, canary_pct, bucket).
    bucket = 10
    r1 = decide_routing(mode="canary", canary_pct=20, bucket=bucket)
    r2 = decide_routing(mode="canary", canary_pct=20, bucket=bucket)

    assert r1 == r2
