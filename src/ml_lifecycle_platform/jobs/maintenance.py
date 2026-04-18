"""Periodic hosted-staging maintenance check that the configured model alias
still resolves to a registered version on the hosted MLflow tracking server."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Any

from opentelemetry import metrics as otel_metrics
from opentelemetry.metrics import CallbackOptions, Observation

from ml_lifecycle_platform.common.constants import ALIAS_PROD
from ml_lifecycle_platform.common.jobs import start_job
from ml_lifecycle_platform.hosted_ci.hosted_model_alias_verifier import (
    HostedModelAliasVerificationConfig,
    verify_model_alias,
)
from ml_lifecycle_platform.runtime.bootstrap import (
    configure_mlflow,
    get_runtime_context,
)

logger = logging.getLogger(__name__)

_last_success_epoch: float | None = None


def _observe_last_success(
    options: CallbackOptions,  # noqa: ARG001
) -> Iterable[Observation]:
    if _last_success_epoch is None:
        return ()
    return (Observation(_last_success_epoch, {"job": "maintenance"}),)


@lru_cache(maxsize=1)
def _register_last_success_gauge() -> Any:
    meter = otel_metrics.get_meter("ml_lifecycle_platform.jobs.maintenance")
    return meter.create_observable_gauge(
        "maintenance_job_last_success_seconds",
        callbacks=[_observe_last_success],
        description=(
            "Unix timestamp of the most recent successful maintenance check. "
            "Use `time() - maintenance_job_last_success_seconds` for staleness."
        ),
        unit="s",
    )


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
    parser.add_argument("--alias", default=ALIAS_PROD)
    parser.add_argument("--format", choices=["json", "text"], default="json")
    return parser.parse_args(argv)


def run_maintenance_check(*, alias: str = ALIAS_PROD) -> MaintenanceReport:
    global _last_success_epoch

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

    _register_last_success_gauge()
    _last_success_epoch = time.time()

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
    args = parse_args(sys.argv[1:] if argv is None else argv)
    with start_job("maintenance", level=get_runtime_context().log_level):
        report = run_maintenance_check(alias=args.alias)
        _print_report(report, args.format)


if __name__ == "__main__":
    main()
