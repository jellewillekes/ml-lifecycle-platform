from __future__ import annotations

import argparse
from pathlib import Path

from ml_lifecycle_platform.ci.cloud_run_service import (
    resolve_cloud_run_service_contract,
    write_github_output,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve a Cloud Run service contract for GitHub Actions workflows."
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--service-name", required=True)
    parser.add_argument("--github-output", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    contract = resolve_cloud_run_service_contract(
        project_id=args.project_id,
        region=args.region,
        service_name=args.service_name,
    )
    write_github_output(Path(args.github_output), contract)


if __name__ == "__main__":
    main()
