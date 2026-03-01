from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from mlflow.tracking import MlflowClient

from ml_lifecycle_platform.common.config import get_model_name
from ml_lifecycle_platform.common.constants import (
    ART_REPRO_CONTRACT_JSON,
    ART_REPRO_REPORT_JSON,
    TAG_SOURCE_RUN_ID,
)
from ml_lifecycle_platform.common.mlflow_utils import client as mlflow_client
from ml_lifecycle_platform.common.repro import (
    get_uv_lock_hash,
    sha256_file,
    sha256_text,
)
from ml_lifecycle_platform.contracts.dataset_fingerprint import (
    compute_fingerprint,
    get_git_sha,
)
from ml_lifecycle_platform.contracts.repro_contract import ReproContract
from ml_lifecycle_platform.pipeline.train import (
    config_hash_for_params,
    load_training_inputs,
    train_from_inputs,
)

logger = logging.getLogger(__name__)


@dataclass
class ReproduceFailure(Exception):
    code: str
    message: str
    details: dict[str, Any]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild a registered model from the source training run."
    )
    parser.add_argument("--model-name", default=get_model_name())
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--model-version")
    group.add_argument("--alias")
    parser.add_argument("--report-path", default=ART_REPRO_REPORT_JSON)
    parser.add_argument("--format", choices=["json", "text"], default="json")
    return parser.parse_args(argv)


def _resolve_model_version(
    client: MlflowClient,
    model_name: str,
    model_version: str | None,
    alias: str | None,
) -> Any:
    if model_version:
        return client.get_model_version(model_name, model_version)
    assert alias is not None
    return client.get_model_version_by_alias(model_name, alias)


def _read_contract(client: MlflowClient, run_id: str, work_dir: Path) -> ReproContract:
    try:
        contract_path = Path(
            client.download_artifacts(
                run_id=run_id,
                path=f"repro/{ART_REPRO_CONTRACT_JSON}",
                dst_path=str(work_dir),
            )
        )
    except Exception as exc:
        error_text = str(exc)
        code = (
            "artifact_credentials_missing"
            if "Unable to locate credentials" in error_text
            else "missing_repro_contract"
        )
        raise ReproduceFailure(
            code=code,
            message="Could not download repro contract from source training run.",
            details={"run_id": run_id, "error": error_text},
        ) from exc

    try:
        return ReproContract.from_json(contract_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ReproduceFailure(
            code="invalid_repro_contract",
            message="Repro contract exists but is invalid.",
            details={"run_id": run_id, "error": str(exc)},
        ) from exc


def _download_required_artifact(
    client: MlflowClient,
    run_id: str,
    artifact_path: str,
    work_dir: Path,
) -> Path:
    try:
        return Path(
            client.download_artifacts(
                run_id=run_id,
                path=artifact_path,
                dst_path=str(work_dir),
            )
        )
    except Exception as exc:
        error_text = str(exc)
        code = (
            "artifact_credentials_missing"
            if "Unable to locate credentials" in error_text
            else "artifact_missing"
        )
        raise ReproduceFailure(
            code=code,
            message="Required training-run artifact is missing.",
            details={
                "run_id": run_id,
                "artifact_path": artifact_path,
                "error": error_text,
            },
        ) from exc


def _read_expected_predictions(path: Path) -> list[float]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    values = payload.get("probabilities")
    if not isinstance(values, list) or not values:
        raise ReproduceFailure(
            code="invalid_expected_predictions",
            message="Expected prediction artifact is invalid.",
            details={"path": str(path)},
        )
    return [float(v) for v in values]


def _initial_report(
    model_name: str,
    model_version: str,
    source_run_id: str,
) -> dict[str, Any]:
    return {
        "status": "failed",
        "reason": None,
        "model_name": model_name,
        "model_version": model_version,
        "source_run_id": source_run_id,
        "checks": {},
    }


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _print_report(report: dict[str, Any], fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
        return

    print(f"status={report['status']}")
    if report.get("reason"):
        print(f"reason={report['reason']}")
    for name, value in report.get("checks", {}).items():
        print(f"{name}={value}")


def reproduce_model(
    client: MlflowClient,
    *,
    model_name: str,
    model_version: str | None,
    alias: str | None,
) -> dict[str, Any]:
    model_version_info = _resolve_model_version(
        client,
        model_name,
        model_version=model_version,
        alias=alias,
    )
    source_run_id = str(
        (model_version_info.tags or {}).get(TAG_SOURCE_RUN_ID, "")
    ).strip()
    if not source_run_id:
        raise ReproduceFailure(
            code="missing_source_run_id",
            message="Model version is missing the source training run reference.",
            details={
                "model_name": model_name,
                "model_version": str(model_version_info.version),
                "required_tag": TAG_SOURCE_RUN_ID,
            },
        )

    report = _initial_report(
        model_name=model_name,
        model_version=str(model_version_info.version),
        source_run_id=source_run_id,
    )

    with tempfile.TemporaryDirectory(prefix="reproduce-") as tmpdir:
        work_dir = Path(tmpdir)
        contract = _read_contract(client, source_run_id, work_dir)
        if contract.training_run_id != source_run_id:
            raise ReproduceFailure(
                code="training_run_id_mismatch",
                message="Repro contract training run does not match model source run.",
                details={
                    "source_run_id": source_run_id,
                    "contract_training_run_id": contract.training_run_id,
                },
            )

        current_git_sha = get_git_sha()
        report["checks"]["git_sha"] = {
            "expected": contract.git_sha,
            "actual": current_git_sha,
            "matched": current_git_sha == contract.git_sha,
        }
        if current_git_sha != contract.git_sha:
            raise ReproduceFailure(
                code="git_sha_mismatch",
                message="Current checkout does not match the training run git SHA.",
                details=report["checks"]["git_sha"],
            )

        current_env_lock_hash = get_uv_lock_hash()
        report["checks"]["env_lock_hash"] = {
            "expected": contract.env_lock_hash,
            "actual": current_env_lock_hash,
            "matched": current_env_lock_hash == contract.env_lock_hash,
        }
        if current_env_lock_hash != contract.env_lock_hash:
            raise ReproduceFailure(
                code="env_lock_mismatch",
                message="Current uv.lock hash does not match the source training run.",
                details=report["checks"]["env_lock_hash"],
            )

        recomputed_config_hash = config_hash_for_params(contract.params)
        report["checks"]["config_hash"] = {
            "expected": contract.config_hash,
            "actual": recomputed_config_hash,
            "matched": recomputed_config_hash == contract.config_hash,
        }
        if recomputed_config_hash != contract.config_hash:
            raise ReproduceFailure(
                code="config_hash_mismatch",
                message="Repro contract params do not reproduce the logged config hash.",
                details=report["checks"]["config_hash"],
            )

        if contract.deterministic_seed is None:
            raise ReproduceFailure(
                code="missing_seed",
                message="Repro contract is missing the deterministic seed.",
                details={"training_run_id": source_run_id},
            )

        train_path = _download_required_artifact(
            client, source_run_id, contract.train_dataset_artifact, work_dir
        )
        _ = _download_required_artifact(
            client, source_run_id, contract.test_dataset_artifact, work_dir
        )
        preprocessor_path = _download_required_artifact(
            client, source_run_id, contract.preprocessor_artifact, work_dir
        )
        probe_inputs_path = _download_required_artifact(
            client, source_run_id, contract.probe_inputs_artifact, work_dir
        )
        expected_predictions_path = _download_required_artifact(
            client, source_run_id, contract.expected_predictions_artifact, work_dir
        )
        uv_lock_path = _download_required_artifact(
            client, source_run_id, contract.uv_lock_artifact, work_dir
        )

        logged_env_lock_hash = sha256_file(uv_lock_path)
        report["checks"]["logged_env_lock_hash"] = {
            "expected": contract.env_lock_hash,
            "actual": logged_env_lock_hash,
            "matched": logged_env_lock_hash == contract.env_lock_hash,
        }
        if logged_env_lock_hash != contract.env_lock_hash:
            raise ReproduceFailure(
                code="logged_env_lock_mismatch",
                message="Logged uv.lock artifact does not match the contract hash.",
                details=report["checks"]["logged_env_lock_hash"],
            )

        inputs_dir = train_path.parent
        downloaded_inputs = load_training_inputs(
            data_dir=inputs_dir,
            artifacts_dir=preprocessor_path.parent,
        )
        recomputed_fp = compute_fingerprint(
            train_df=downloaded_inputs.train_df,
            test_df=downloaded_inputs.test_df,
            data_source_uri=contract.data_source_uri,
            git_sha=contract.git_sha,
        )
        recomputed_dataset_fingerprint = sha256_text(recomputed_fp.to_json())
        report["checks"]["dataset_fingerprint"] = {
            "expected": contract.dataset_fingerprint,
            "actual": recomputed_dataset_fingerprint,
            "matched": recomputed_dataset_fingerprint == contract.dataset_fingerprint,
        }
        if recomputed_dataset_fingerprint != contract.dataset_fingerprint:
            raise ReproduceFailure(
                code="dataset_fingerprint_mismatch",
                message="Downloaded training inputs do not match the logged dataset fingerprint.",
                details=report["checks"]["dataset_fingerprint"],
            )

        result = train_from_inputs(downloaded_inputs, contract.params)
        probe_inputs = pd.read_csv(probe_inputs_path)
        expected_probabilities = _read_expected_predictions(expected_predictions_path)
        actual_probabilities = [
            float(v) for v in result.pipeline.predict_proba(probe_inputs)[:, 1]
        ]
        max_abs_diff = max(
            (
                abs(expected - actual)
                for expected, actual in zip(
                    expected_probabilities, actual_probabilities
                )
            ),
            default=0.0,
        )
        prediction_match = np.allclose(
            expected_probabilities,
            actual_probabilities,
            rtol=1e-12,
            atol=1e-12,
        )
        report["checks"]["prediction_parity"] = {
            "matched": bool(prediction_match),
            "count": len(expected_probabilities),
            "max_abs_diff": float(max_abs_diff),
        }
        if not prediction_match:
            raise ReproduceFailure(
                code="prediction_parity_failed",
                message="Reproduced model predictions differ from the logged probe outputs.",
                details=report["checks"]["prediction_parity"],
            )

        report["checks"]["metrics"] = result.metrics
        report["status"] = "matched"
        report["reason"] = None
        return report


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    args = parse_args(sys.argv[1:] if argv is None else argv)
    report_path = Path(args.report_path)

    try:
        report = reproduce_model(
            mlflow_client(),
            model_name=args.model_name,
            model_version=args.model_version,
            alias=args.alias,
        )
        _write_report(report_path, report)
        _print_report(report, args.format)
        raise SystemExit(0)
    except ReproduceFailure as exc:
        report = {
            "status": "failed",
            "reason": exc.code,
            "message": exc.message,
            "details": exc.details,
        }
        _write_report(report_path, report)
        _print_report(report, args.format)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
