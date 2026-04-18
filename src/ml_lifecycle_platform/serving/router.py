"""Deterministic request routing between model variants (prod, candidate,
canary, shadow) using stable bucketing from the request id or payload hash."""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Final, Literal, cast

from .constants import ALIAS_CANDIDATE, ALIAS_PROD

MODE_PROD: Final[str] = "prod"
MODE_CANDIDATE: Final[str] = "candidate"
MODE_CANARY: Final[str] = "canary"
MODE_SHADOW: Final[str] = "shadow"

Mode = Literal["prod", "candidate", "canary", "shadow"]
Alias = Literal["prod", "candidate"]


class SeedSource(StrEnum):
    """Entropy source for deterministic bucketing."""

    REQUEST_ID = "request_id"
    PAYLOAD_HASH = "payload_hash"
    RANDOM = "random"


@dataclass(frozen=True)
class RoutingDecision:
    """Routing result for one request."""

    chosen: Alias
    run_shadow: bool


@dataclass(frozen=True)
class BucketContext:
    """Inputs for deterministic bucketing."""

    request_id: str | None
    client_provided_request_id: bool
    rows: list[dict[str, Any]]


@dataclass(frozen=True)
class BucketDecision:
    bucket: int
    seed_source: SeedSource


def stable_bucket_from_bytes(payload: bytes) -> int:
    """Return a stable bucket in [0, 99] for arbitrary bytes."""
    h = hashlib.sha256(payload).hexdigest()
    return int(h, 16) % 100


def stable_bucket_from_str(seed: str) -> int:
    """Return a stable bucket in [0, 99] for a text seed."""
    return stable_bucket_from_bytes(seed.encode("utf-8"))


def stable_bucket_from_rows(rows: list[dict[str, Any]]) -> int:
    """Return a stable bucket in [0, 99] from request content."""
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return stable_bucket_from_bytes(payload)


def choose_canary_bucket(ctx: BucketContext) -> BucketDecision:
    """Choose a bucket from request id, then payload, then random fallback."""
    if ctx.client_provided_request_id and ctx.request_id:
        return BucketDecision(
            bucket=stable_bucket_from_str(ctx.request_id),
            seed_source=SeedSource.REQUEST_ID,
        )

    try:
        return BucketDecision(
            bucket=stable_bucket_from_rows(ctx.rows),
            seed_source=SeedSource.PAYLOAD_HASH,
        )
    except (TypeError, ValueError):
        # Fallback if the payload is not JSON-serializable.
        seed = secrets.token_hex(16)
        return BucketDecision(
            bucket=stable_bucket_from_str(seed),
            seed_source=SeedSource.RANDOM,
        )


def decide_routing(mode: Mode, canary_pct: int, bucket: int) -> RoutingDecision:
    """Compute routing for one request."""
    if not (0 <= bucket <= 99):
        raise ValueError(f"bucket must be in [0, 99], got {bucket}")

    canary_pct = max(0, min(100, int(canary_pct)))

    # Use serving.constants as the single source of truth.
    prod: Alias = cast(Alias, ALIAS_PROD)
    candidate: Alias = cast(Alias, ALIAS_CANDIDATE)

    if mode == MODE_PROD:
        return RoutingDecision(chosen=prod, run_shadow=False)

    if mode == MODE_CANDIDATE:
        return RoutingDecision(chosen=candidate, run_shadow=False)

    if mode == MODE_SHADOW:
        return RoutingDecision(chosen=prod, run_shadow=True)

    if mode == MODE_CANARY:
        if bucket < canary_pct:
            return RoutingDecision(chosen=candidate, run_shadow=True)
        return RoutingDecision(chosen=prod, run_shadow=True)

    raise ValueError(f"Unknown mode: {mode}")
