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
    TAG_GATE,
    TAG_GIT_SHA,
    TAG_RELEASE_STATUS,
    TAG_SOURCE_RUN_ID,
    TAG_TRAINING_RUN_ID,
)

_REQUIRED_TAGS: tuple[str, ...] = (
    TAG_DATASET_FINGERPRINT,
    TAG_GIT_SHA,
    TAG_CONFIG_HASH,
    TAG_TRAINING_RUN_ID,
)


class PromotionPolicyClient(Protocol):
    def get_model_version_by_alias(self, model_name: str, alias: str) -> Any: ...

    def get_model_version(self, model_name: str, version: str) -> Any: ...

    def get_run(self, run_id: str) -> Any: ...


@dataclass(frozen=True)
class Violation:
    """Policy violation or warning."""

    code: str
    message: str
    details: dict[str, Any]


@dataclass(frozen=True)
class PolicyDecision:
    """Result of promotion policy evaluation."""

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


def _missing_required_tags(tags: Mapping[str, str] | None) -> list[str]:
    safe_tags = tags or {}
    return [k for k in _REQUIRED_TAGS if not str(safe_tags.get(k, "")).strip()]


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
    from_alias: str = ALIAS_CANDIDATE,
    to_alias: str = ALIAS_PROD,
) -> PolicyDecision:
    """Evaluate promotion eligibility without mutating the registry."""

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

    # Keep dry-run output small and predictable.
    context["candidate_tags_subset"] = {
        TAG_GATE: candidate_tags.get(TAG_GATE, ""),
        TAG_RELEASE_STATUS: candidate_tags.get(TAG_RELEASE_STATUS, ""),
        TAG_SOURCE_RUN_ID: candidate_tags.get(TAG_SOURCE_RUN_ID, ""),
        TAG_DATASET_FINGERPRINT: candidate_tags.get(TAG_DATASET_FINGERPRINT, ""),
        TAG_GIT_SHA: candidate_tags.get(TAG_GIT_SHA, ""),
        TAG_CONFIG_HASH: candidate_tags.get(TAG_CONFIG_HASH, ""),
        TAG_TRAINING_RUN_ID: candidate_tags.get(TAG_TRAINING_RUN_ID, ""),
    }

    missing = _missing_required_tags(candidate_tags)
    if missing:
        errors.append(
            Violation(
                code="MISSING_REQUIRED_TAGS",
                message="Promotion blocked: candidate model version is missing required metadata tags.",
                details={"missing": missing},
            )
        )

    gate_val = str(candidate_tags.get(TAG_GATE, "")).strip()
    if gate_val != GATE_PASSED:
        errors.append(
            Violation(
                code="GATE_NOT_PASSED",
                message="Promotion blocked: model gate status is not 'passed'.",
                details={"expected": GATE_PASSED, "actual": gate_val},
            )
        )

    rs_val = str(candidate_tags.get(TAG_RELEASE_STATUS, "")).strip()
    if rs_val != from_alias:
        errors.append(
            Violation(
                code="INVALID_RELEASE_STATUS",
                message="Promotion blocked: candidate release_status is not eligible for promotion.",
                details={"expected": from_alias, "actual": rs_val},
            )
        )

    if current_prod_version is not None and str(current_prod_version) == str(
        candidate_version
    ):
        errors.append(
            Violation(
                code="NOOP_PROMOTION",
                message="Promotion blocked: candidate is already the current prod version.",
                details={
                    "candidate_version": candidate_version,
                    "current_prod_version": current_prod_version,
                },
            )
        )

    run_id = str(candidate_tags.get(TAG_SOURCE_RUN_ID, "")).strip()
    if not run_id:
        warnings.append(
            Violation(
                code="MISSING_SOURCE_RUN_ID",
                message="Missing source_run_id tag; promotion will be less auditable.",
                details={"tag": TAG_SOURCE_RUN_ID},
            )
        )
    else:
        try:
            client.get_run(run_id)
        except Exception:
            warnings.append(
                Violation(
                    code="SOURCE_RUN_ID_NOT_FOUND",
                    message="source_run_id tag is present but the MLflow run could not be fetched.",
                    details={"run_id": run_id},
                )
            )

    return PolicyDecision(
        allowed=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
        context=context,
    )
