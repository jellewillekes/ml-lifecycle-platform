from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any

from mlflow.tracking import MlflowClient

from ml_lifecycle_platform.common.mlflow_utils import client as mlflow_client
from ml_lifecycle_platform.runtime.bootstrap import get_runtime_context
from ml_lifecycle_platform.common.constants import (
    ALIAS_CANDIDATE,
    ALIAS_CHAMPION,
    ALIAS_PROD,
    RELEASE_STATUS_PREVIOUS_PROD,
    TAG_CONFIG_HASH,
    TAG_DATASET_FINGERPRINT,
    TAG_GIT_SHA,
    TAG_PREVIOUS_PROD_VERSION,
    TAG_PROMOTED_FROM_ALIAS,
    TAG_RELEASE_STATUS,
    TAG_SOURCE_RUN_ID,
)
from ml_lifecycle_platform.core.model_specs import (
    PolicySpec,
    default_policy_spec,
    load_model_spec,
)
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
from ml_lifecycle_platform.core.policy_engine import (
    PolicyDecision,
    evaluate_promotion_policy,
)
from ml_lifecycle_platform.registry.release_evidence import emit_release_evidence

logger = logging.getLogger(__name__)


def _resolve_policy_for_model(model_name: str) -> PolicySpec:
    spec = load_model_spec(get_runtime_context().model_spec_path)
    if spec.model_name != model_name:
        logger.warning(
            "Active model spec %s targets model %s; using default promotion policy for %s",
            spec.spec_path,
            spec.model_name,
            model_name,
        )
        return default_policy_spec()
    return spec.policy


def _print_decision(decision: PolicyDecision, fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(decision.to_dict(), indent=2, sort_keys=True))
        return

    print(f"allowed={decision.allowed}")
    for v in decision.errors:
        print(f"ERROR {v.code}: {v.message} {v.details}")
    for v in decision.warnings:
        print(f"WARN  {v.code}: {v.message} {v.details}")
    print(f"context={decision.context}")


def _try_get_prod_version(client: MlflowClient, model_name: str) -> str | None:
    try:
        prod = client.get_model_version_by_alias(model_name, ALIAS_PROD)
    except Exception:
        return None
    return str(prod.version)


def _model_version_source_run_id(model_version: Any) -> str:
    return str((model_version.tags or {}).get(TAG_SOURCE_RUN_ID, "")).strip()


def _source_run_metrics(client: MlflowClient, run_id: str) -> dict[str, float]:
    try:
        run = client.get_run(run_id)
    except Exception:
        return {}
    metrics = getattr(getattr(run, "data", None), "metrics", {}) or {}
    return {str(key): float(value) for key, value in metrics.items()}


def _build_promotion_bundle(
    *,
    client: MlflowClient,
    decision: PolicyDecision,
    model_name: str,
    candidate_version: str,
    current_prod_version: str | None,
    previous_prod_version: str | None,
) -> tuple[str, ReleaseReportBundle]:
    candidate = client.get_model_version(model_name, candidate_version)
    candidate_tags = candidate.tags or {}
    source_run_id = _model_version_source_run_id(candidate)
    if not source_run_id:
        raise RuntimeError(
            "Promotion evidence emission requires source_run_id on the candidate "
            f"model version. Expected tag '{TAG_SOURCE_RUN_ID}'."
        )

    target_source_run_id: str | None = None
    if previous_prod_version is not None:
        try:
            previous_prod = client.get_model_version(model_name, previous_prod_version)
            target_source_run_id = _model_version_source_run_id(previous_prod) or None
        except Exception:
            target_source_run_id = None

    generated_at = utc_now_iso()
    policy_outcome = PolicyOutcome.from_policy_decision(decision)
    result = OperationResult(
        status="succeeded",
        code="promotion_applied",
        message="Candidate alias promoted to prod and champion.",
        details={
            "from_alias": str(decision.context.get("from_alias", "")),
            "to_alias": str(decision.context.get("to_alias", "")),
        },
    )
    manifest = ReleaseManifest(
        generated_at=generated_at,
        operation="promote",
        model_name=model_name,
        model_version=candidate_version,
        source_run_id=source_run_id,
        dataset_fingerprint=str(candidate_tags.get(TAG_DATASET_FINGERPRINT, "")).strip()
        or None,
        config_hash=str(candidate_tags.get(TAG_CONFIG_HASH, "")).strip() or None,
        git_sha=str(candidate_tags.get(TAG_GIT_SHA, "")).strip() or None,
        current_prod_version=current_prod_version,
        previous_prod_version=previous_prod_version,
        policy_outcome=policy_outcome,
        result=result,
        metrics=_source_run_metrics(client, source_run_id),
    )
    bundle = ReleaseReportBundle(
        decision=PromotionDecisionReport(
            generated_at=generated_at,
            operation="promote",
            model_name=model_name,
            model_version=candidate_version,
            source_run_id=source_run_id,
            policy_outcome=policy_outcome,
            result=result,
        ),
        manifest=manifest,
        rollback_target=RollbackTargetReport(
            generated_at=generated_at,
            operation="promote",
            model_name=model_name,
            model_version=candidate_version,
            source_run_id=source_run_id,
            current_prod_version=current_prod_version,
            previous_prod_version=previous_prod_version,
            target_version=previous_prod_version,
            target_source_run_id=target_source_run_id,
            result=OperationResult(
                status="recorded",
                code="rollback_target_recorded",
                message="Rollback target recorded from the previous prod version.",
                details={},
            ),
        ),
        model_card="",
    )
    return source_run_id, ReleaseReportBundle(
        decision=bundle.decision,
        manifest=bundle.manifest,
        rollback_target=bundle.rollback_target,
        model_card=render_model_card(bundle),
    )


def apply_promotion(
    client: MlflowClient,
    *,
    model_name: str,
    candidate_version: str,
    from_alias: str,
    decision: PolicyDecision,
) -> None:
    """Promote one candidate version and record rollback metadata."""

    prev_prod_version = _try_get_prod_version(client, model_name)

    client.set_registered_model_alias(model_name, ALIAS_PROD, candidate_version)
    client.set_registered_model_alias(model_name, ALIAS_CHAMPION, candidate_version)

    client.set_model_version_tag(
        name=model_name,
        version=candidate_version,
        key=TAG_RELEASE_STATUS,
        value=ALIAS_PROD,
    )
    client.set_model_version_tag(
        name=model_name,
        version=candidate_version,
        key=TAG_PROMOTED_FROM_ALIAS,
        value=from_alias,
    )

    if prev_prod_version is not None:
        # Rollback reads this tag instead of inferring state from history.
        client.set_model_version_tag(
            name=model_name,
            version=candidate_version,
            key=TAG_PREVIOUS_PROD_VERSION,
            value=prev_prod_version,
        )

        try:
            client.set_model_version_tag(
                name=model_name,
                version=prev_prod_version,
                key=TAG_RELEASE_STATUS,
                value=RELEASE_STATUS_PREVIOUS_PROD,
            )
        except Exception:
            logger.info(
                "Could not mark old prod version %s as %s",
                prev_prod_version,
                RELEASE_STATUS_PREVIOUS_PROD,
            )

    logger.info(
        "Promoted %s v%s -> alias '%s' and '%s'",
        model_name,
        candidate_version,
        ALIAS_PROD,
        ALIAS_CHAMPION,
    )

    source_run_id, bundle = _build_promotion_bundle(
        client=client,
        decision=decision,
        model_name=model_name,
        candidate_version=candidate_version,
        current_prod_version=candidate_version,
        previous_prod_version=prev_prod_version,
    )
    emit_release_evidence(
        client,
        source_run_id=source_run_id,
        operation="promote",
        model_name=model_name,
        model_version=candidate_version,
        bundle=bundle,
        tag_target_version=candidate_version,
        event_type="release.promoted",
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Promote candidate model to prod with policy gating."
    )
    p.add_argument("--model-name", default=get_runtime_context().model_name)
    p.add_argument("--from-alias", default=ALIAS_CANDIDATE)
    p.add_argument("--to-alias", default=ALIAS_PROD)
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Evaluate policy only; do not mutate registry.",
    )
    p.add_argument("--format", choices=["json", "text"], default="json")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=get_runtime_context().log_level)

    args = parse_args(sys.argv[1:] if argv is None else argv)

    client = mlflow_client()
    decision = evaluate_promotion_policy(
        client=client,
        model_name=args.model_name,
        policy=_resolve_policy_for_model(args.model_name),
        from_alias=args.from_alias,
        to_alias=args.to_alias,
    )

    _print_decision(decision, args.format)

    if args.dry_run:
        raise SystemExit(0 if decision.allowed else 2)

    if not decision.allowed:
        raise SystemExit(2)

    candidate_version = str(decision.context["candidate_version"])
    apply_promotion(
        client=client,
        model_name=args.model_name,
        candidate_version=candidate_version,
        from_alias=args.from_alias,
        decision=decision,
    )


if __name__ == "__main__":
    main()
