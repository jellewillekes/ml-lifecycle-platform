from __future__ import annotations

import argparse
from pathlib import Path

from ml_lifecycle_platform.ci.serving_staging_baseline import write_baseline_context


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write context for a hosted serving staging baseline run."
    )
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--service-url", required=True)
    parser.add_argument("--service-name", required=True)
    parser.add_argument("--service-image", required=True)
    parser.add_argument("--duration", default="5m")
    parser.add_argument("--rate", type=int, default=1)
    parser.add_argument("--realistic-iterations", type=int, default=25)
    parser.add_argument("--git-sha", default="")
    parser.add_argument("--notes", default="")
    parser.add_argument("--workflow-run-id", default="")
    parser.add_argument("--workflow-run-attempt", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    write_baseline_context(
        Path(args.output_path),
        service_url=args.service_url,
        service_name=args.service_name,
        service_image=args.service_image,
        duration=args.duration,
        rate=args.rate,
        realistic_iterations=args.realistic_iterations,
        git_sha=args.git_sha or None,
        notes=args.notes or None,
        workflow_run_id=args.workflow_run_id or None,
        workflow_run_attempt=args.workflow_run_attempt or None,
    )


if __name__ == "__main__":
    main()
