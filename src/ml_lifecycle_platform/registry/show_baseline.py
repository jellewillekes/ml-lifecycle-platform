"""CLI: print the ``DriftBaseline`` attached to a model version's release
evidence (UP-31). Resolves the version (or alias), finds the release-evidence
root tagged on the version, and downloads ``drift_baseline.json``."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient

from ml_lifecycle_platform.common.constants import (
    ART_DRIFT_BASELINE_JSON,
    TAG_RELEASE_REPORTS_PATH,
    TAG_SOURCE_RUN_ID,
)
from ml_lifecycle_platform.contracts.drift_baseline import DriftBaseline
from ml_lifecycle_platform.runtime.bootstrap import (
    configure_mlflow,
    get_runtime_context,
)
from ml_lifecycle_platform.runtime.mlflow import client as mlflow_client

_SUMMARY_HEADER = (
    f"{'column':<24} {'count':>8} {'null_rate':>10} {'mean':>12} {'std':>12}"
)


def _resolve_version(
    client: MlflowClient,
    model_name: str,
    *,
    version: str | None,
    alias: str | None,
) -> str:
    if version:
        return version
    model_version = client.get_model_version_by_alias(model_name, str(alias))
    return str(model_version.version)


def load_baseline(
    client: MlflowClient, *, model_name: str, version: str
) -> DriftBaseline:
    model_version = client.get_model_version(model_name, version)
    tags = model_version.tags or {}
    root = str(tags.get(TAG_RELEASE_REPORTS_PATH, "")).strip()
    source_run_id = str(tags.get(TAG_SOURCE_RUN_ID, "")).strip()
    if not root or not source_run_id:
        raise SystemExit(f"No release evidence found for {model_name} v{version}.")
    baseline_path = f"{root}/{ART_DRIFT_BASELINE_JSON}"
    with tempfile.TemporaryDirectory(prefix="show-baseline-") as tmpdir:
        try:
            local = client.download_artifacts(
                run_id=source_run_id, path=baseline_path, dst_path=tmpdir
            )
        except MlflowException as exc:
            raise SystemExit(
                f"No drift baseline at {baseline_path} for {model_name} v{version}: {exc}"
            ) from exc
        return DriftBaseline.from_json(Path(local).read_text(encoding="utf-8"))


def render_text(baseline: DriftBaseline) -> str:
    lines = [
        f"DriftBaseline {baseline.model_name} v{baseline.model_version}",
        f"  source_run_id: {baseline.source_run_id}",
        f"  created_at:    {baseline.created_at}",
        f"  columns:       {len(baseline.columns)}",
        "",
        _SUMMARY_HEADER,
    ]
    for name, stats in sorted(baseline.columns.items()):
        lines.append(
            f"{name:<24} {stats.count:>8} {stats.null_rate:>10.4f} "
            f"{stats.mean:>12.4f} {stats.std:>12.4f}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="show-baseline")
    parser.add_argument("--model-name")
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--model-version")
    selector.add_argument("--alias")
    parser.add_argument("--format", choices=["json", "text"], default="json")
    args = parser.parse_args(argv)

    runtime = get_runtime_context()
    configure_mlflow(runtime)
    client = mlflow_client()
    model_name = args.model_name or runtime.model_name
    version = _resolve_version(
        client, model_name, version=args.model_version, alias=args.alias
    )
    baseline = load_baseline(client, model_name=model_name, version=version)
    print(baseline.to_json() if args.format == "json" else render_text(baseline))


if __name__ == "__main__":
    main()
