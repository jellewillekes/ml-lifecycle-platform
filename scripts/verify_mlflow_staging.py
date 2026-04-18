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
        description="Verify that hosted MLflow staging is reachable and can write metadata and artifacts."
    )
    parser.add_argument("--tracking-uri", required=True)
    parser.add_argument("--experiment-name", required=True)
    parser.add_argument("--run-name", default="staging-smoke")
    parser.add_argument("--artifact-name", default="smoke.txt")
    return parser


def main() -> int:
    from ml_lifecycle_platform.hosted_ci.mlflow_staging_verifier import (
        MlflowStagingVerificationConfig,
        VerificationError,
        verify_staging,
    )

    tracking_token = os.getenv("MLFLOW_TRACKING_TOKEN", "").strip()
    if not tracking_token:
        print(
            "MLFLOW_TRACKING_TOKEN must be set for hosted MLflow verification.",
            file=sys.stderr,
        )
        return 2

    args = build_parser().parse_args()
    config = MlflowStagingVerificationConfig(
        tracking_uri=args.tracking_uri,
        tracking_token=tracking_token,
        experiment_name=args.experiment_name,
        run_name=args.run_name,
        artifact_name=args.artifact_name,
    )
    try:
        run_id = verify_staging(config)
    except VerificationError as error:
        print(f"Hosted MLflow staging verification failed: {error}", file=sys.stderr)
        return 2

    print(f"Verified hosted MLflow staging at {args.tracking_uri} with run_id={run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
