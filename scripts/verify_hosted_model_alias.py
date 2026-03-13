#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify that hosted MLflow exposes a required model alias."
    )
    parser.add_argument("--tracking-uri", required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--alias", default="prod")
    return parser


def main() -> int:
    from ml_lifecycle_platform.ci.hosted_model_alias_verifier import (
        HostedModelAliasVerificationConfig,
        VerificationError,
        verify_model_alias,
    )

    tracking_token = os.getenv("MLFLOW_TRACKING_TOKEN", "").strip()
    if not tracking_token:
        print(
            "MLFLOW_TRACKING_TOKEN must be set for hosted model alias verification.",
            file=sys.stderr,
        )
        return 2

    args = build_parser().parse_args()
    config = HostedModelAliasVerificationConfig(
        tracking_uri=args.tracking_uri,
        tracking_token=tracking_token,
        model_name=args.model_name,
        alias=args.alias,
    )
    try:
        version = verify_model_alias(config)
    except VerificationError as error:
        print(f"Hosted model alias verification failed: {error}", file=sys.stderr)
        return 2

    print(
        f"Verified hosted MLflow alias {args.model_name}@{args.alias} -> version={version}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
