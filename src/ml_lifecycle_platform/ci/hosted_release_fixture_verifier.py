from __future__ import annotations

import json
from dataclasses import dataclass

import mlflow
from mlflow import MlflowClient

from ml_lifecycle_platform.core.model_specs import load_model_spec
from ml_lifecycle_platform.policy.release_policy import evaluate_promotion_policy
from ml_lifecycle_platform.registry.rollback import _resolve_rollback_target


class VerificationError(RuntimeError):
    """Raised when hosted MLflow is missing the expected release fixture."""


@dataclass(frozen=True)
class HostedReleaseFixtureVerificationConfig:
    tracking_uri: str
    tracking_token: str
    model_name: str
    model_spec_path: str


def verify_release_fixture(
    config: HostedReleaseFixtureVerificationConfig,
) -> dict[str, str]:
    if not config.tracking_token.strip():
        raise VerificationError("hosted MLflow verification requires a tracking token.")

    mlflow.set_tracking_uri(config.tracking_uri)
    client = MlflowClient()
    model_spec = load_model_spec(config.model_spec_path)

    decision = evaluate_promotion_policy(
        client,
        config.model_name,
        policy=model_spec.policy,
    )
    if not decision.allowed:
        raise VerificationError(
            "hosted release fixture is not promotable: "
            f"{json.dumps(decision.to_dict(), sort_keys=True)}"
        )

    try:
        current_prod, rollback_target_version, _, _, resolution_source = (
            _resolve_rollback_target(client, model_name=config.model_name)
        )
    except RuntimeError as error:
        raise VerificationError(
            f"hosted release fixture is not rollback-ready: {error}"
        ) from error

    candidate_version = str(decision.context.get("candidate_version", "")).strip()
    current_prod_version = str(decision.context.get("current_prod_version", "")).strip()
    if not candidate_version or not current_prod_version:
        raise VerificationError(
            "hosted release fixture returned empty candidate/prod versions."
        )

    return {
        "candidate_version": candidate_version,
        "current_prod_version": current_prod_version,
        "rollback_target_version": rollback_target_version,
        "rollback_resolution_source": resolution_source,
        "current_prod_alias_version": str(current_prod.version),
    }
