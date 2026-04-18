from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass

from ml_lifecycle_platform.hosted_ci.hosted_model_alias_verifier import (
    HostedModelAliasVerificationConfig,
    verify_model_alias,
)
from ml_lifecycle_platform.runtime.bootstrap import (
    configure_mlflow,
    get_runtime_context,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MaintenanceReport:
    tracking_uri: str
    model_name: str
    alias: str
    resolved_version: str
    alias_reachable: bool


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

    tracking_uri = runtime.metadata.tracking_uri
    model_name = runtime.model_name

    resolved_version = verify_model_alias(
        HostedModelAliasVerificationConfig(
            tracking_uri=tracking_uri,
            tracking_token="",
            model_name=model_name,
            alias=alias,
        )
    )

    return MaintenanceReport(
        tracking_uri=tracking_uri,
        model_name=model_name,
        alias=alias,
        resolved_version=resolved_version,
        alias_reachable=True,
    )


def _print_report(report: MaintenanceReport, fmt: str) -> None:
    payload = asdict(report)
    if fmt == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    for key, value in payload.items():
        print(f"{key}={value}")


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=get_runtime_context().log_level)
    args = parse_args(sys.argv[1:] if argv is None else argv)
    report = run_maintenance_check(alias=args.alias)
    _print_report(report, args.format)


if __name__ == "__main__":
    main()
