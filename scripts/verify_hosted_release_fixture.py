#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that hosted MLflow exposes a rollback-ready prod and a distinct "
            "promotable candidate."
        )
    )
    parser.add_argument("--tracking-uri", required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--model-spec-path", required=True)
    return parser


def main() -> int:
    from ml_lifecycle_platform.hosted_ci.hosted_release_fixture_verifier import (
        HostedReleaseFixtureVerificationConfig,
        VerificationError,
        verify_release_fixture,
    )

    tracking_token = os.getenv("MLFLOW_TRACKING_TOKEN", "").strip()
    if not tracking_token:
        print(
            "MLFLOW_TRACKING_TOKEN must be set for hosted release fixture verification.",
            file=sys.stderr,
        )
        return 2

    args = build_parser().parse_args()
    config = HostedReleaseFixtureVerificationConfig(
        tracking_uri=args.tracking_uri,
        tracking_token=tracking_token,
        model_name=args.model_name,
        model_spec_path=args.model_spec_path,
    )
    try:
        fixture = verify_release_fixture(config)
    except VerificationError as error:
        print(f"Hosted release fixture verification failed: {error}", file=sys.stderr)
        return 2

    print(json.dumps(fixture, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
