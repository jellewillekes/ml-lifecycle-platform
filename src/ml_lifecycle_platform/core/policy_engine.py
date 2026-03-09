from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from mlflow.exceptions import MlflowException

from ml_lifecycle_platform.common.constants import (
    ALIAS_CANDIDATE,
    ALIAS_PROD,
    GATE_PASSED,
    TAG_CONFIG_HASH,
    TAG_DATASET_FINGERPRINT,
    TAG_DETERMINISTIC_SEED,
    TAG_ENV_LOCK_HASH,
    TAG_GATE,
    TAG_GIT_SHA,
    TAG_RELEASE_STATUS,
    TAG_REPRO_SCHEMA_VERSION,
    TAG_SOURCE_RUN_ID,
    TAG_TRAINING_RUN_ID,
)
from ml_lifecycle_platform.core.model_specs import PolicySpec, default_policy_spec

REPRODUCIBILITY_EVIDENCE_TAGS: tuple[str, ...] = (
    TAG_SOURCE_RUN_ID,
    TAG_ENV_LOCK_HASH,
    TAG_DETERMINISTIC_SEED,
    TAG_REPRO_SCHEMA_VERSION,
)


class PromotionPolicyClient(Protocol):
    def get_model_version_by_alias(self, model_name: str, alias: str) -> Any: ...

    def get_model_version(self, model_name: str, version: str) -> Any: ...

    def get_run(self, run_id: str) -> Any: ...


@dataclass(frozen=True)
class Violation:
    code: str
    message: str
    details: dict[str, Any]


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    errors: tuple[Violation, ...]
    warnings: tuple[Violation, ...]
    context: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "errors": [v.__dict__ for v in self.errors],
            "warnings": [v.__dict__ for v in self.warnings],
            "context": self.context,
        }


def missing_required_tags(
    tags: Mapping[str, str] | None, required_tags: tuple[str, ...]
) -> list[str]:
    safe_tags = tags or {}
    return [key for key in required_tags if not str(safe_tags.get(key, "")).strip()]


def evaluate_required_metadata_rule(
    candidate_tags: Mapping[str, str] | None, policy: PolicySpec
) -> Violation | None:
    missing = missing_required_tags(candidate_tags, policy.required_metadata_tags)
    if not missing:
        return None
    return Violation(
        code="MISSING_REQUIRED_TAGS",
        message="Promotion blocked: candidate model version is missing required metadata tags.",
        details={"missing": missing},
    )


def evaluate_gate_rule(candidate_tags: Mapping[str, str] | None) -> Violation | None:
    gate_val = str((candidate_tags or {}).get(TAG_GATE, "")).strip()
    if gate_val == GATE_PASSED:
        return None
    return Violation(
        code="GATE_NOT_PASSED",
        message="Promotion blocked: model gate status is not 'passed'.",
        details={"expected": GATE_PASSED, "actual": gate_val},
    )


def evaluate_release_status_rule(
    candidate_tags: Mapping[str, str] | None, policy: PolicySpec
) -> Violation | None:
    release_status = str((candidate_tags or {}).get(TAG_RELEASE_STATUS, "")).strip()
    if release_status == policy.required_release_status:
        return None
    return Violation(
        code="INVALID_RELEASE_STATUS",
        message="Promotion blocked: candidate release_status is not eligible for promotion.",
        details={
            "expected": policy.required_release_status,
            "actual": release_status,
        },
    )


def evaluate_noop_promotion_rule(
    *,
    candidate_version: str | None,
    current_prod_version: str | None,
    policy: PolicySpec,
) -> Violation | None:
    if not policy.block_noop_promotion:
        return None
    if candidate_version is None or current_prod_version is None:
        return None
    if str(candidate_version) != str(current_prod_version):
        return None
    return Violation(
        code="NOOP_PROMOTION",
        message="Promotion blocked: candidate is already the current prod version.",
        details={
            "candidate_version": candidate_version,
            "current_prod_version": current_prod_version,
        },
    )


def evaluate_reproducibility_rule(
    *,
    candidate_tags: Mapping[str, str] | None,
    policy: PolicySpec,
    source_run_lookup_ok: bool,
) -> tuple[Violation, ...]:
    if not policy.require_reproducibility_evidence:
        return ()

    missing = missing_required_tags(candidate_tags, REPRODUCIBILITY_EVIDENCE_TAGS)
    if missing:
        return (
            Violation(
                code="MISSING_REPRODUCIBILITY_EVIDENCE",
                message="Promotion blocked: candidate model version is missing required reproducibility evidence.",
                details={"missing": missing},
            ),
        )

    if source_run_lookup_ok:
        return ()

    run_id = str((candidate_tags or {}).get(TAG_SOURCE_RUN_ID, "")).strip()
    return (
        Violation(
            code="SOURCE_RUN_ID_NOT_FOUND",
            message="Promotion blocked: source_run_id tag is present but the MLflow run could not be fetched.",
            details={"run_id": run_id},
        ),
    )


def evaluate_metric_thresholds_rule(
    *,
    source_run: Any | None,
    source_run_id: str,
    policy: PolicySpec,
) -> tuple[Violation, ...]:
    if not policy.minimum_metric_thresholds:
        return ()

    if source_run is None:
        return (
            Violation(
                code="METRIC_SOURCE_RUN_NOT_AVAILABLE",
                message="Promotion blocked: source run metrics are unavailable for policy evaluation.",
                details={"run_id": source_run_id},
            ),
        )

    run_metrics = getattr(getattr(source_run, "data", None), "metrics", {}) or {}
    violations: list[Violation] = []
    for threshold in policy.minimum_metric_thresholds:
        metric_key = f"test_{threshold.metric}"
        actual = run_metrics.get(metric_key)
        if actual is None:
            violations.append(
                Violation(
                    code="MISSING_METRIC",
                    message="Promotion blocked: source run is missing a required metric for policy evaluation.",
                    details={
                        "metric": threshold.metric,
                        "metric_key": metric_key,
                        "run_id": source_run_id,
                    },
                )
            )
            continue

        actual_value = float(actual)
        if actual_value < threshold.threshold:
            violations.append(
                Violation(
                    code="METRIC_BELOW_THRESHOLD",
                    message="Promotion blocked: source run metric is below the configured threshold.",
                    details={
                        "metric": threshold.metric,
                        "metric_key": metric_key,
                        "expected_min": threshold.threshold,
                        "actual": actual_value,
                        "run_id": source_run_id,
                    },
                )
            )
    return tuple(violations)


def _try_get_alias_version(
    client: PromotionPolicyClient, model_name: str, alias: str
) -> str | None:
    try:
        mv = client.get_model_version_by_alias(model_name, alias)
    except (MlflowException, KeyError, ValueError):
        return None
    return str(mv.version)


def evaluate_promotion_policy(
    client: PromotionPolicyClient,
    model_name: str,
    *,
    policy: PolicySpec | None = None,
    from_alias: str = ALIAS_CANDIDATE,
    to_alias: str = ALIAS_PROD,
) -> PolicyDecision:
    active_policy = default_policy_spec() if policy is None else policy
    errors: list[Violation] = []
    warnings: list[Violation] = []

    candidate_version = _try_get_alias_version(client, model_name, from_alias)
    current_prod_version = _try_get_alias_version(client, model_name, to_alias)

    context: dict[str, Any] = {
        "model_name": model_name,
        "from_alias": from_alias,
        "to_alias": to_alias,
        "candidate_version": candidate_version,
        "current_prod_version": current_prod_version,
    }

    if candidate_version is None:
        errors.append(
            Violation(
                code="MISSING_ALIAS",
                message=f"Promotion blocked: alias '{from_alias}' does not exist.",
                details={"alias": from_alias},
            )
        )
        return PolicyDecision(
            allowed=False,
            errors=tuple(errors),
            warnings=tuple(warnings),
            context=context,
        )

    candidate = client.get_model_version(model_name, candidate_version)
    candidate_tags = candidate.tags or {}
    context["candidate_tags_subset"] = {
        TAG_GATE: candidate_tags.get(TAG_GATE, ""),
        TAG_RELEASE_STATUS: candidate_tags.get(TAG_RELEASE_STATUS, ""),
        TAG_SOURCE_RUN_ID: candidate_tags.get(TAG_SOURCE_RUN_ID, ""),
        TAG_DATASET_FINGERPRINT: candidate_tags.get(TAG_DATASET_FINGERPRINT, ""),
        TAG_GIT_SHA: candidate_tags.get(TAG_GIT_SHA, ""),
        TAG_CONFIG_HASH: candidate_tags.get(TAG_CONFIG_HASH, ""),
        TAG_TRAINING_RUN_ID: candidate_tags.get(TAG_TRAINING_RUN_ID, ""),
        TAG_ENV_LOCK_HASH: candidate_tags.get(TAG_ENV_LOCK_HASH, ""),
        TAG_DETERMINISTIC_SEED: candidate_tags.get(TAG_DETERMINISTIC_SEED, ""),
        TAG_REPRO_SCHEMA_VERSION: candidate_tags.get(TAG_REPRO_SCHEMA_VERSION, ""),
    }

    for violation in (
        evaluate_required_metadata_rule(candidate_tags, active_policy),
        evaluate_gate_rule(candidate_tags),
        evaluate_release_status_rule(candidate_tags, active_policy),
        evaluate_noop_promotion_rule(
            candidate_version=candidate_version,
            current_prod_version=current_prod_version,
            policy=active_policy,
        ),
    ):
        if violation is not None:
            errors.append(violation)

    source_run = None
    source_run_lookup_ok = False
    source_run_id = str(candidate_tags.get(TAG_SOURCE_RUN_ID, "")).strip()
    if not source_run_id:
        warnings.append(
            Violation(
                code="MISSING_SOURCE_RUN_ID",
                message="Missing source_run_id tag; promotion will be less auditable.",
                details={"tag": TAG_SOURCE_RUN_ID},
            )
        )
    else:
        try:
            source_run = client.get_run(source_run_id)
            source_run_lookup_ok = True
        except Exception:
            warnings.append(
                Violation(
                    code="SOURCE_RUN_ID_NOT_FOUND",
                    message="source_run_id tag is present but the MLflow run could not be fetched.",
                    details={"run_id": source_run_id},
                )
            )

    errors.extend(
        evaluate_reproducibility_rule(
            candidate_tags=candidate_tags,
            policy=active_policy,
            source_run_lookup_ok=source_run_lookup_ok,
        )
    )
    errors.extend(
        evaluate_metric_thresholds_rule(
            source_run=source_run,
            source_run_id=source_run_id,
            policy=active_policy,
        )
    )

    return PolicyDecision(
        allowed=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
        context=context,
    )
