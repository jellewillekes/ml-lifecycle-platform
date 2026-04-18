from __future__ import annotations

from types import SimpleNamespace

import pytest

from ml_lifecycle_platform.hosted_ci.hosted_release_fixture_verifier import (
    HostedReleaseFixtureVerificationConfig,
    VerificationError,
    verify_release_fixture,
)
from ml_lifecycle_platform.policy.policy_engine import PolicyDecision, Violation

pytestmark = pytest.mark.unit


def test_verify_release_fixture_returns_versions_when_fixture_is_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, tuple[object, ...]]] = []

    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.hosted_release_fixture_verifier.mlflow.set_tracking_uri",
        lambda uri: calls.append(("set_tracking_uri", (uri,))),
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.hosted_release_fixture_verifier.MlflowClient",
        lambda: object(),
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.hosted_release_fixture_verifier.load_model_spec",
        lambda path: SimpleNamespace(policy="policy", spec_path=path),
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.hosted_release_fixture_verifier.evaluate_promotion_policy",
        lambda client, model_name, policy: PolicyDecision(
            allowed=True,
            errors=(),
            warnings=(),
            context={
                "candidate_version": "4",
                "current_prod_version": "3",
                "model_name": model_name,
            },
        ),
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.hosted_release_fixture_verifier._resolve_rollback_target",
        lambda client, model_name: (
            SimpleNamespace(version="3"),
            "2",
            None,
            None,
            "manifest",
        ),
    )

    fixture = verify_release_fixture(
        HostedReleaseFixtureVerificationConfig(
            tracking_uri="https://mlflow.example.run.app",
            tracking_token="token",
            model_name="breast_cancer_clf",
            model_spec_path="configs/models/breast_cancer_demo.yaml",
        )
    )

    assert fixture == {
        "candidate_version": "4",
        "current_prod_version": "3",
        "rollback_target_version": "2",
        "rollback_resolution_source": "manifest",
        "current_prod_alias_version": "3",
    }
    assert ("set_tracking_uri", ("https://mlflow.example.run.app",)) in calls


def test_verify_release_fixture_fails_when_promotion_would_be_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.hosted_release_fixture_verifier.mlflow.set_tracking_uri",
        lambda uri: None,
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.hosted_release_fixture_verifier.MlflowClient",
        lambda: object(),
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.hosted_release_fixture_verifier.load_model_spec",
        lambda path: SimpleNamespace(policy="policy", spec_path=path),
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.hosted_release_fixture_verifier.evaluate_promotion_policy",
        lambda client, model_name, policy: PolicyDecision(
            allowed=False,
            errors=(
                Violation(
                    code="NOOP_PROMOTION",
                    message="Promotion blocked: candidate is already the current prod version.",
                    details={"candidate_version": "3", "current_prod_version": "3"},
                ),
            ),
            warnings=(),
            context={"candidate_version": "3", "current_prod_version": "3"},
        ),
    )

    with pytest.raises(VerificationError, match="not promotable"):
        verify_release_fixture(
            HostedReleaseFixtureVerificationConfig(
                tracking_uri="https://mlflow.example.run.app",
                tracking_token="token",
                model_name="breast_cancer_clf",
                model_spec_path="configs/models/breast_cancer_demo.yaml",
            )
        )


def test_verify_release_fixture_fails_when_rollback_target_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.hosted_release_fixture_verifier.mlflow.set_tracking_uri",
        lambda uri: None,
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.hosted_release_fixture_verifier.MlflowClient",
        lambda: object(),
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.hosted_release_fixture_verifier.load_model_spec",
        lambda path: SimpleNamespace(policy="policy", spec_path=path),
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.hosted_release_fixture_verifier.evaluate_promotion_policy",
        lambda client, model_name, policy: PolicyDecision(
            allowed=True,
            errors=(),
            warnings=(),
            context={"candidate_version": "4", "current_prod_version": "3"},
        ),
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.hosted_release_fixture_verifier._resolve_rollback_target",
        lambda client, model_name: (_ for _ in ()).throw(
            RuntimeError(
                "Rollback blocked: current prod does not have a previous prod recorded."
            )
        ),
    )

    with pytest.raises(VerificationError, match="not rollback-ready"):
        verify_release_fixture(
            HostedReleaseFixtureVerificationConfig(
                tracking_uri="https://mlflow.example.run.app",
                tracking_token="token",
                model_name="breast_cancer_clf",
                model_spec_path="configs/models/breast_cancer_demo.yaml",
            )
        )
