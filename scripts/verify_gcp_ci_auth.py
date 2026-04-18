#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def build_parser(
    *,
    default_region: str,
    default_artifact_repository: str,
    default_secret_ids: tuple[str, ...],
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify GitHub Actions -> GCP OIDC auth and required hosted foundation resources."
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--service-account", required=True)
    parser.add_argument("--workload-identity-provider", required=True)
    parser.add_argument("--region", default=default_region)
    parser.add_argument("--artifact-repository", default=default_artifact_repository)
    parser.add_argument("--artifacts-bucket")
    parser.add_argument("--data-bucket")
    parser.add_argument(
        "--secret-id",
        action="append",
        default=list(default_secret_ids),
        dest="secret_ids",
    )
    return parser


def main() -> int:
    from ml_lifecycle_platform.hosted_ci.gcp_auth_verifier import (
        DEFAULT_ARTIFACT_REPOSITORY,
        DEFAULT_REGION,
        DEFAULT_SECRET_IDS,
        GcpAuthVerificationConfig,
        VerificationError,
        format_success_summary,
        verify_resources,
    )

    args = build_parser(
        default_region=DEFAULT_REGION,
        default_artifact_repository=DEFAULT_ARTIFACT_REPOSITORY,
        default_secret_ids=DEFAULT_SECRET_IDS,
    ).parse_args()
    config = GcpAuthVerificationConfig(
        project_id=args.project_id,
        service_account=args.service_account,
        workload_identity_provider=args.workload_identity_provider,
        region=args.region,
        artifact_repository=args.artifact_repository,
        artifacts_bucket=args.artifacts_bucket,
        data_bucket=args.data_bucket,
        secret_ids=tuple(args.secret_ids),
    )
    try:
        verify_resources(config)
    except VerificationError as error:
        print(f"GCP auth verification failed: {error}", file=sys.stderr)
        return 2

    print(format_success_summary(config))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
