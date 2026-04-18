"""Replay a training run from its reproducibility contract and verify that
the produced model matches the registered one."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient

from ml_lifecycle_platform.common.constants import (
    ALIAS_PROD,
    ART_REPRO_CONTRACT_JSON,
    ART_REPRO_REPORT_JSON,
    TAG_CONFIG_HASH,
    TAG_DATASET_FINGERPRINT,
    TAG_GIT_SHA,
    TAG_PREVIOUS_PROD_VERSION,
    TAG_SOURCE_RUN_ID,
)
from ml_lifecycle_platform.runtime.mlflow import client as mlflow_client
from ml_lifecycle_platform.runtime.bootstrap import get_runtime_context
from ml_lifecycle_platform.contracts.dataset_fingerprint import (
    compute_fingerprint,
    get_git_sha,
)
from ml_lifecycle_platform.contracts.repro_contract import ReproContract
from ml_lifecycle_platform.contracts.release_reports import (
    OperationResult,
    PolicyOutcome,
    PromotionDecisionReport,
    ReleaseManifest,
    ReleaseReportBundle,
    RollbackTargetReport,
    render_model_card,
    utc_now_iso,
)
from ml_lifecycle_platform.core.model_specs import model_spec_from_dict
from ml_lifecycle_platform.pipeline.train import (
    config_hash_for_spec,
    load_training_inputs,
    train_from_inputs,
)
from ml_lifecycle_platform.registry.release_evidence import emit_release_evidence

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_text(payload: str) -> str:
    return sha256_bytes(payload.encode("utf-8"))


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def get_uv_lock_path() -> Path:
    path = REPO_ROOT / "uv.lock"
    if not path.exists():
        raise RuntimeError(f"uv.lock not found at expected repo root path: {path}")
    return path


def get_uv_lock_hash() -> str:
    return sha256_file(get_uv_lock_path())


def _classify_download_error(exc: Exception, *, fallback_code: str) -> str:
    if "Unable to locate credentials" in str(exc):
        return "artifact_credentials_missing"
    return fallback_code


@dataclass
class ReproduceFailure(Exception):
    code: str
    message: str
    details: dict[str, Any]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild a registered model from the source training run."
    )
    parser.add_argument("--model-name", default=get_runtime_context().model_name)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--model-version")
    group.add_argument("--alias")
    parser.add_argument("--report-path", default=ART_REPRO_REPORT_JSON)
    parser.add_argument("--format", choices=["json", "text"], default="json")
    return parser.parse_args(argv)


# Returns Any because MLflow's get_model_version* return a mlflow.ModelVersion
# at runtime, but unit tests substitute a SimpleNamespace with the same surface.
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
    except (MlflowException, OSError) as exc:
        raise ReproduceFailure(
            code=_classify_download_error(exc, fallback_code="missing_repro_contract"),
            message="Could not download repro contract from source training run.",
            details={"run_id": run_id, "error": str(exc)},
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
    except (MlflowException, OSError) as exc:
        raise ReproduceFailure(
            code=_classify_download_error(exc, fallback_code="artifact_missing"),
            message="Required training-run artifact is missing.",
            details={
                "run_id": run_id,
                "artifact_path": artifact_path,
                "error": str(exc),
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


def _resolve_current_prod_version(client: MlflowClient, model_name: str) -> str | None:
    try:
        prod = client.get_model_version_by_alias(model_name, ALIAS_PROD)
    except MlflowException:
        return None
    return str(prod.version)


def _emit_reproduce_evidence(
    client: MlflowClient,
    *,
    model_name: str,
    model_version: str | None,
    alias: str | None,
    report: dict[str, Any],
) -> None:
    try:
        model_version_info = _resolve_model_version(
            client,
            model_name,
            model_version=model_version,
            alias=alias,
        )
    except MlflowException:
        logger.warning(
            "Could not resolve model version for reproduce evidence emission."
        )
        return

    tags = model_version_info.tags or {}
    source_run_id = str(tags.get(TAG_SOURCE_RUN_ID, "")).strip()
    if not source_run_id:
        logger.warning(
            "Skipping reproduce evidence emission: source_run_id is missing."
        )
        return

    metrics = report.get("checks", {}).get("metrics", {})
    if not isinstance(metrics, dict):
        metrics = {}

    generated_at = utc_now_iso()
    policy_outcome = PolicyOutcome.not_evaluated(
        reason="reproduce does not run promotion policy evaluation",
        context={"selector_alias": alias, "selector_model_version": model_version},
    )
    result = OperationResult(
        status=str(report.get("status", "failed")),
        code=_optional_text(report.get("reason")),
        message=_optional_text(report.get("message")),
        details=_report_details(report),
    )
    rollback_target = str(tags.get(TAG_PREVIOUS_PROD_VERSION, "")).strip() or None
    manifest = ReleaseManifest(
        generated_at=generated_at,
        operation="reproduce",
        model_name=model_name,
        model_version=str(model_version_info.version),
        source_run_id=source_run_id,
        dataset_fingerprint=str(tags.get(TAG_DATASET_FINGERPRINT, "")).strip() or None,
        config_hash=str(tags.get(TAG_CONFIG_HASH, "")).strip() or None,
        git_sha=str(tags.get(TAG_GIT_SHA, "")).strip() or None,
        current_prod_version=_resolve_current_prod_version(client, model_name),
        previous_prod_version=rollback_target,
        policy_outcome=policy_outcome,
        result=result,
        metrics={str(key): float(value) for key, value in metrics.items()},
    )
    bundle = ReleaseReportBundle(
        decision=PromotionDecisionReport(
            generated_at=generated_at,
            operation="reproduce",
            model_name=model_name,
            model_version=str(model_version_info.version),
            source_run_id=source_run_id,
            policy_outcome=policy_outcome,
            result=result,
        ),
        manifest=manifest,
        rollback_target=RollbackTargetReport(
            generated_at=generated_at,
            operation="reproduce",
            model_name=model_name,
            model_version=str(model_version_info.version),
            source_run_id=source_run_id,
            current_prod_version=manifest.current_prod_version,
            previous_prod_version=manifest.previous_prod_version,
            target_version=rollback_target,
            target_source_run_id=None,
            result=OperationResult(
                status="recorded",
                code="reproduce_context_recorded",
                message="Rollback context mirrored into reproduce evidence.",
                details={},
            ),
        ),
        model_card="",
    )
    emit_release_evidence(
        client,
        source_run_id=source_run_id,
        operation="reproduce",
        model_name=model_name,
        model_version=str(model_version_info.version),
        bundle=ReleaseReportBundle(
            decision=bundle.decision,
            manifest=bundle.manifest,
            rollback_target=bundle.rollback_target,
            model_card=render_model_card(bundle),
        ),
        tag_target_version=str(model_version_info.version),
        event_type="release.reproduced",
    )


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _report_details(report: dict[str, Any]) -> dict[str, Any]:
    details = report.get("details")
    if isinstance(details, dict):
        return dict(details)
    checks = report.get("checks")
    if isinstance(checks, dict):
        return {"checks": dict(checks)}
    return {}


def _verify_environment_hashes(contract: ReproContract, report: dict[str, Any]) -> None:
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


def _verify_config_hash(
    contract: ReproContract, spec: Any, report: dict[str, Any]
) -> None:
    recomputed_config_hash = config_hash_for_spec(spec)
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


@dataclass
class _DownloadedArtifacts:
    train_path: Path
    preprocessor_path: Path
    probe_inputs_path: Path
    expected_predictions_path: Path
    uv_lock_path: Path


def _download_contract_artifacts(
    client: MlflowClient,
    source_run_id: str,
    contract: ReproContract,
    work_dir: Path,
) -> _DownloadedArtifacts:
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
    return _DownloadedArtifacts(
        train_path=train_path,
        preprocessor_path=preprocessor_path,
        probe_inputs_path=probe_inputs_path,
        expected_predictions_path=expected_predictions_path,
        uv_lock_path=uv_lock_path,
    )


def _verify_dataset_fingerprint(
    contract: ReproContract,
    artifacts: _DownloadedArtifacts,
    report: dict[str, Any],
) -> Any:
    logged_env_lock_hash = sha256_file(artifacts.uv_lock_path)
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

    downloaded_inputs = load_training_inputs(
        data_dir=artifacts.train_path.parent,
        artifacts_dir=artifacts.preprocessor_path.parent,
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
    return downloaded_inputs


def _verify_prediction_parity(
    pipeline: Any,
    artifacts: _DownloadedArtifacts,
    report: dict[str, Any],
) -> None:
    probe_inputs = pd.read_csv(artifacts.probe_inputs_path)
    expected_probabilities = _read_expected_predictions(
        artifacts.expected_predictions_path
    )
    actual_probabilities = [
        float(v) for v in pipeline.predict_proba(probe_inputs)[:, 1]
    ]
    max_abs_diff = max(
        (
            abs(expected - actual)
            for expected, actual in zip(expected_probabilities, actual_probabilities)
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

        _verify_environment_hashes(contract, report)

        spec = model_spec_from_dict(
            contract.model_spec, spec_path="contract://model-spec"
        )
        _verify_config_hash(contract, spec, report)

        if contract.deterministic_seed is None:
            raise ReproduceFailure(
                code="missing_seed",
                message="Repro contract is missing the deterministic seed.",
                details={"training_run_id": source_run_id},
            )

        artifacts = _download_contract_artifacts(
            client, source_run_id, contract, work_dir
        )
        downloaded_inputs = _verify_dataset_fingerprint(contract, artifacts, report)

        result = train_from_inputs(downloaded_inputs, spec)
        _verify_prediction_parity(result.pipeline, artifacts, report)

        report["checks"]["metrics"] = result.metrics
        report["status"] = "matched"
        report["reason"] = None
        return report


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=get_runtime_context().log_level)
    args = parse_args(sys.argv[1:] if argv is None else argv)
    report_path = Path(args.report_path)
    client = mlflow_client()

    try:
        report = reproduce_model(
            client,
            model_name=args.model_name,
            model_version=args.model_version,
            alias=args.alias,
        )
        _write_report(report_path, report)
        _emit_reproduce_evidence(
            client,
            model_name=args.model_name,
            model_version=args.model_version,
            alias=args.alias,
            report=report,
        )
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
        _emit_reproduce_evidence(
            client,
            model_name=args.model_name,
            model_version=args.model_version,
            alias=args.alias,
            report=report,
        )
        _print_report(report, args.format)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
