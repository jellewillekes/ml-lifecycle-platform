from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

from mlflow.tracking import MlflowClient

from ml_lifecycle_platform.common.config import get_log_level, get_model_name
from ml_lifecycle_platform.common.constants import (
    ALIAS_PROD,
    TAG_CONFIG_HASH,
    TAG_DATASET_FINGERPRINT,
    TAG_GIT_SHA,
    TAG_PREVIOUS_PROD_VERSION,
    TAG_RELEASE_MANIFEST_PATH,
    TAG_SOURCE_RUN_ID,
)
from ml_lifecycle_platform.common.mlflow_utils import client as mlflow_client
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
from ml_lifecycle_platform.registry.release_evidence import (
    emit_release_evidence,
    load_release_manifest,
)

logger = logging.getLogger(__name__)


def _source_run_id(model_version: Any) -> str:
    return str((model_version.tags or {}).get(TAG_SOURCE_RUN_ID, "")).strip()


def _run_metrics(client: MlflowClient, run_id: str) -> dict[str, float]:
    try:
        run = client.get_run(run_id)
    except Exception:
        return {}
    metrics = getattr(getattr(run, "data", None), "metrics", {}) or {}
    return {str(key): float(value) for key, value in metrics.items()}


def _previous_prod_from_manifest(
    client: MlflowClient,
    *,
    current_prod: Any,
) -> tuple[str | None, str]:
    tags = current_prod.tags or {}
    manifest_path = str(tags.get(TAG_RELEASE_MANIFEST_PATH, "")).strip()
    source_run_id = _source_run_id(current_prod)
    if not manifest_path or not source_run_id:
        return None, "tag_fallback"
    with tempfile.TemporaryDirectory(prefix="rollback-manifest-") as tmpdir:
        try:
            manifest = load_release_manifest(
                client,
                source_run_id=source_run_id,
                manifest_path=manifest_path,
                work_dir=Path(tmpdir),
            )
        except Exception as exc:
            logger.warning("Could not read release manifest for rollback: %s", exc)
            return None, "tag_fallback"
    return manifest.previous_prod_version, "manifest"


def rollback_prod(client: MlflowClient, model_name: str) -> None:
    """Roll back prod to the recorded previous prod version."""
    current_prod = client.get_model_version_by_alias(model_name, ALIAS_PROD)
    current_tags = current_prod.tags or {}
    current_source_run_id = _source_run_id(current_prod)

    previous_prod, resolution_source = _previous_prod_from_manifest(
        client,
        current_prod=current_prod,
    )
    if not previous_prod:
        previous_prod = str(current_tags.get(TAG_PREVIOUS_PROD_VERSION, "")).strip()

    if not previous_prod:
        raise RuntimeError(
            "Rollback blocked: current prod does not have a previous prod recorded. "
            "Expected release_manifest.json or "
            f"tag '{TAG_PREVIOUS_PROD_VERSION}' on current prod model version."
        )

    target = client.get_model_version(model_name, previous_prod)
    target_source_run_id = _source_run_id(target) or None

    client.set_registered_model_alias(model_name, ALIAS_PROD, previous_prod)

    # Allow a one-step undo.
    client.set_model_version_tag(
        name=model_name,
        version=previous_prod,
        key=TAG_PREVIOUS_PROD_VERSION,
        value=str(current_prod.version),
    )

    logger.info(
        "Rolled back %s prod -> v%s (from v%s)",
        model_name,
        previous_prod,
        current_prod.version,
    )

    if not current_source_run_id:
        raise RuntimeError(
            "Rollback evidence emission requires source_run_id on the current prod "
            f"model version. Expected tag '{TAG_SOURCE_RUN_ID}'."
        )

    generated_at = utc_now_iso()
    policy_outcome = PolicyOutcome.not_evaluated(
        reason="rollback does not run promotion policy evaluation",
        context={"resolution_source": resolution_source},
    )
    result = OperationResult(
        status="succeeded",
        code="rollback_applied",
        message="Prod alias moved to the recorded previous prod version.",
        details={"resolution_source": resolution_source},
    )
    manifest = ReleaseManifest(
        generated_at=generated_at,
        operation="rollback",
        model_name=model_name,
        model_version=str(current_prod.version),
        source_run_id=current_source_run_id,
        dataset_fingerprint=str(current_tags.get(TAG_DATASET_FINGERPRINT, "")).strip()
        or None,
        config_hash=str(current_tags.get(TAG_CONFIG_HASH, "")).strip() or None,
        git_sha=str(current_tags.get(TAG_GIT_SHA, "")).strip() or None,
        current_prod_version=str(previous_prod),
        previous_prod_version=str(current_prod.version),
        policy_outcome=policy_outcome,
        result=result,
        metrics=_run_metrics(client, current_source_run_id),
    )
    bundle = ReleaseReportBundle(
        decision=PromotionDecisionReport(
            generated_at=generated_at,
            operation="rollback",
            model_name=model_name,
            model_version=str(current_prod.version),
            source_run_id=current_source_run_id,
            policy_outcome=policy_outcome,
            result=result,
        ),
        manifest=manifest,
        rollback_target=RollbackTargetReport(
            generated_at=generated_at,
            operation="rollback",
            model_name=model_name,
            model_version=str(current_prod.version),
            source_run_id=current_source_run_id,
            current_prod_version=str(current_prod.version),
            previous_prod_version=str(previous_prod),
            target_version=str(previous_prod),
            target_source_run_id=target_source_run_id,
            result=OperationResult(
                status="resolved",
                code="rollback_target_resolved",
                message="Rollback target resolved before alias mutation.",
                details={"resolution_source": resolution_source},
            ),
        ),
        model_card="",
    )
    emit_release_evidence(
        client,
        source_run_id=current_source_run_id,
        operation="rollback",
        model_name=model_name,
        model_version=str(current_prod.version),
        bundle=ReleaseReportBundle(
            decision=bundle.decision,
            manifest=bundle.manifest,
            rollback_target=bundle.rollback_target,
            model_card=render_model_card(bundle),
        ),
        tag_target_version=str(current_prod.version),
        event_type="release.rolled_back",
    )


def main() -> None:
    logging.basicConfig(level=get_log_level())
    rollback_prod(mlflow_client(), get_model_name())


if __name__ == "__main__":
    main()
