from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import asdict, dataclass

from ml_lifecycle_platform.ci.hosted_model_alias_verifier import (
    HostedModelAliasVerificationConfig,
    verify_model_alias,
)
from ml_lifecycle_platform.ci.mlflow_staging_verifier import (
    MlflowStagingVerificationConfig,
    verify_http_reachable,
)
from ml_lifecycle_platform.common.config import (
    get_log_level,
    get_model_name,
    get_tracking_uri,
)
from ml_lifecycle_platform.runtime.bootstrap import (
    configure_mlflow,
    get_runtime_context,
)


@dataclass(frozen=True)
class MaintenanceReport:
    tracking_uri: str
    model_name: str
    alias: str
    resolved_version: str
    http_reachable: bool


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run safe hosted staging maintenance checks."
    )
    parser.add_argument("--alias", default="prod")
    parser.add_argument("--format", choices=["json", "text"], default="json")
    return parser.parse_args(argv)


def run_maintenance_check(*, alias: str = "prod") -> MaintenanceReport:
    runtime = get_runtime_context()
    configure_mlflow(runtime)

    tracking_uri = get_tracking_uri()
    model_name = get_model_name()
    tracking_token = os.getenv("MLFLOW_TRACKING_TOKEN", "").strip()
    http_reachable = False

    if tracking_token:
        verify_http_reachable(
            MlflowStagingVerificationConfig(
                tracking_uri=tracking_uri,
                tracking_token=tracking_token,
                experiment_name="maintenance-unused",
            )
        )
        http_reachable = True

    resolved_version = verify_model_alias(
        HostedModelAliasVerificationConfig(
            tracking_uri=tracking_uri,
            tracking_token=tracking_token,
            model_name=model_name,
            alias=alias,
        )
    )

    return MaintenanceReport(
        tracking_uri=tracking_uri,
        model_name=model_name,
        alias=alias,
        resolved_version=resolved_version,
        http_reachable=http_reachable,
    )


def _print_report(report: MaintenanceReport, fmt: str) -> None:
    payload = asdict(report)
    if fmt == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    for key, value in payload.items():
        print(f"{key}={value}")


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=get_log_level())
    args = parse_args(sys.argv[1:] if argv is None else argv)
    report = run_maintenance_check(alias=args.alias)
    _print_report(report, args.format)


if __name__ == "__main__":
    main()
