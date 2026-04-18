"""Typed schemas for the promotion and rollback release-report bundles that
get written to MLflow artifacts (decision, manifest, rollback target, card)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ml_lifecycle_platform.common.constants import (
    ART_MODEL_CARD_MD,
    ART_PROMOTION_DECISION_JSON,
    ART_RELEASE_MANIFEST_JSON,
    ART_ROLLBACK_TARGET_JSON,
    RELEASE_REPORT_SCHEMA_VERSION,
)
from ml_lifecycle_platform.policy.policy_engine import PolicyDecision


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class PolicyOutcome:
    status: str
    allowed: bool | None
    errors: tuple[dict[str, Any], ...] = ()
    warnings: tuple[dict[str, Any], ...] = ()
    context: dict[str, Any] = field(default_factory=dict)
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "allowed": self.allowed,
            "errors": [dict(item) for item in self.errors],
            "warnings": [dict(item) for item in self.warnings],
            "context": dict(self.context),
            "reason": self.reason,
        }

    @classmethod
    def from_policy_decision(cls, decision: PolicyDecision) -> PolicyOutcome:
        return cls(
            status="evaluated",
            allowed=bool(decision.allowed),
            errors=tuple(v.__dict__ for v in decision.errors),
            warnings=tuple(v.__dict__ for v in decision.warnings),
            context=dict(decision.context),
        )

    @classmethod
    def not_evaluated(
        cls,
        *,
        reason: str,
        context: dict[str, Any] | None = None,
    ) -> PolicyOutcome:
        return cls(
            status="not_evaluated",
            allowed=None,
            context={} if context is None else dict(context),
            reason=reason,
        )


@dataclass(frozen=True)
class OperationResult:
    status: str
    code: str | None = None
    message: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "code": self.code,
            "message": self.message,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class PromotionDecisionReport:
    generated_at: str
    operation: str
    model_name: str
    model_version: str
    source_run_id: str
    policy_outcome: PolicyOutcome
    result: OperationResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": RELEASE_REPORT_SCHEMA_VERSION,
            "generated_at": self.generated_at,
            "operation": self.operation,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "source_run_id": self.source_run_id,
            "policy_outcome": self.policy_outcome.to_dict(),
            "result": self.result.to_dict(),
        }


@dataclass(frozen=True)
class ReleaseManifest:
    generated_at: str
    operation: str
    model_name: str
    model_version: str
    source_run_id: str
    dataset_fingerprint: str | None
    config_hash: str | None
    git_sha: str | None
    current_prod_version: str | None
    previous_prod_version: str | None
    policy_outcome: PolicyOutcome
    result: OperationResult
    metrics: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": RELEASE_REPORT_SCHEMA_VERSION,
            "generated_at": self.generated_at,
            "operation": self.operation,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "source_run_id": self.source_run_id,
            "dataset_fingerprint": self.dataset_fingerprint,
            "config_hash": self.config_hash,
            "git_sha": self.git_sha,
            "current_prod_version": self.current_prod_version,
            "previous_prod_version": self.previous_prod_version,
            "policy_outcome": self.policy_outcome.to_dict(),
            "result": self.result.to_dict(),
            "metrics": dict(self.metrics),
        }

    @classmethod
    def from_json(cls, payload: str) -> ReleaseManifest:
        raw = json.loads(payload)
        if not isinstance(raw, dict):
            raise ValueError("Release manifest payload must be a JSON object.")
        policy = raw.get("policy_outcome")
        result = raw.get("result")
        if not isinstance(policy, dict):
            raise ValueError("Release manifest is missing policy_outcome.")
        if not isinstance(result, dict):
            raise ValueError("Release manifest is missing result.")
        metrics = raw.get("metrics", {})
        if not isinstance(metrics, dict):
            raise ValueError("Release manifest metrics must be a JSON object.")
        return cls(
            generated_at=str(raw.get("generated_at", "")),
            operation=str(raw.get("operation", "")),
            model_name=str(raw.get("model_name", "")),
            model_version=str(raw.get("model_version", "")),
            source_run_id=str(raw.get("source_run_id", "")),
            dataset_fingerprint=_optional_str(raw.get("dataset_fingerprint")),
            config_hash=_optional_str(raw.get("config_hash")),
            git_sha=_optional_str(raw.get("git_sha")),
            current_prod_version=_optional_str(raw.get("current_prod_version")),
            previous_prod_version=_optional_str(raw.get("previous_prod_version")),
            policy_outcome=_parse_policy_outcome(policy),
            result=_parse_operation_result(result),
            metrics={str(key): float(value) for key, value in metrics.items()},
        )


@dataclass(frozen=True)
class RollbackTargetReport:
    generated_at: str
    operation: str
    model_name: str
    model_version: str
    source_run_id: str
    current_prod_version: str | None
    previous_prod_version: str | None
    target_version: str | None
    target_source_run_id: str | None
    result: OperationResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": RELEASE_REPORT_SCHEMA_VERSION,
            "generated_at": self.generated_at,
            "operation": self.operation,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "source_run_id": self.source_run_id,
            "current_prod_version": self.current_prod_version,
            "previous_prod_version": self.previous_prod_version,
            "target_version": self.target_version,
            "target_source_run_id": self.target_source_run_id,
            "result": self.result.to_dict(),
        }


@dataclass(frozen=True)
class ReleaseReportBundle:
    decision: PromotionDecisionReport
    manifest: ReleaseManifest
    rollback_target: RollbackTargetReport
    model_card: str

    def file_contents(self) -> dict[str, bytes]:
        return {
            ART_PROMOTION_DECISION_JSON: json.dumps(
                self.decision.to_dict(), indent=2, sort_keys=True
            ).encode("utf-8"),
            ART_RELEASE_MANIFEST_JSON: json.dumps(
                self.manifest.to_dict(), indent=2, sort_keys=True
            ).encode("utf-8"),
            ART_ROLLBACK_TARGET_JSON: json.dumps(
                self.rollback_target.to_dict(), indent=2, sort_keys=True
            ).encode("utf-8"),
            ART_MODEL_CARD_MD: self.model_card.encode("utf-8"),
        }


def render_model_card(bundle: ReleaseReportBundle) -> str:
    manifest = bundle.manifest
    lines = [
        f"# Model Card: {manifest.model_name} v{manifest.model_version}",
        "",
        f"- Operation: `{manifest.operation}`",
        f"- Result: `{manifest.result.status}`",
        f"- Source run: `{manifest.source_run_id}`",
        f"- Current prod: `{manifest.current_prod_version or 'n/a'}`",
        f"- Previous prod: `{manifest.previous_prod_version or 'n/a'}`",
        f"- Dataset fingerprint: `{manifest.dataset_fingerprint or 'n/a'}`",
        f"- Config hash: `{manifest.config_hash or 'n/a'}`",
        f"- Git SHA: `{manifest.git_sha or 'n/a'}`",
        "",
        "## Policy Outcome",
        "",
        f"- Status: `{bundle.decision.policy_outcome.status}`",
        f"- Allowed: `{bundle.decision.policy_outcome.allowed}`",
    ]
    if bundle.decision.policy_outcome.reason:
        lines.append(f"- Reason: `{bundle.decision.policy_outcome.reason}`")
    if manifest.metrics:
        lines.extend(["", "## Metrics", ""])
        for key, value in sorted(manifest.metrics.items()):
            lines.append(f"- {key}: `{value}`")
    return "\n".join(lines) + "\n"


def _parse_policy_outcome(policy: dict[str, Any]) -> PolicyOutcome:
    return PolicyOutcome(
        status=str(policy.get("status", "")),
        allowed=_optional_bool(policy.get("allowed")),
        errors=_tuple_of_dicts(policy.get("errors")),
        warnings=_tuple_of_dicts(policy.get("warnings")),
        context=_dict_or_empty(policy.get("context")),
        reason=_optional_str(policy.get("reason")),
    )


def _parse_operation_result(result: dict[str, Any]) -> OperationResult:
    return OperationResult(
        status=str(result.get("status", "")),
        code=_optional_str(result.get("code")),
        message=_optional_str(result.get("message")),
        details=_dict_or_empty(result.get("details")),
    )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)


def _dict_or_empty(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _tuple_of_dicts(value: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list):
        return ()
    items: list[dict[str, Any]] = []
    for entry in value:
        if isinstance(entry, dict):
            items.append(dict(entry))
    return tuple(items)
