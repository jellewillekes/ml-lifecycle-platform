from __future__ import annotations

from types import SimpleNamespace

import pytest

from ml_lifecycle_platform.hosted_ci.hosted_model_alias_verifier import (
    HostedModelAliasVerificationConfig,
    VerificationError,
    verify_model_alias,
)

pytestmark = pytest.mark.unit


def test_verify_model_alias_returns_resolved_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, tuple[object, ...]]] = []

    class _FakeClient:
        def get_model_version_by_alias(
            self, model_name: str, alias: str
        ) -> SimpleNamespace:
            calls.append(("get_model_version_by_alias", (model_name, alias)))
            return SimpleNamespace(version="7")

    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.hosted_model_alias_verifier.mlflow.set_tracking_uri",
        lambda uri: calls.append(("set_tracking_uri", (uri,))),
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.hosted_model_alias_verifier.MlflowClient",
        lambda: _FakeClient(),
    )

    version = verify_model_alias(
        HostedModelAliasVerificationConfig(
            tracking_uri="https://mlflow.example.run.app",
            tracking_token="token",
            model_name="breast_cancer_clf",
        )
    )

    assert version == "7"
    assert ("set_tracking_uri", ("https://mlflow.example.run.app",)) in calls
    assert ("get_model_version_by_alias", ("breast_cancer_clf", "prod")) in calls


def test_verify_model_alias_fails_with_actionable_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeClient:
        def get_model_version_by_alias(
            self, model_name: str, alias: str
        ) -> SimpleNamespace:
            del model_name, alias
            raise RuntimeError(
                "INVALID_PARAMETER_VALUE: Registered model alias prod not found."
            )

    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.hosted_model_alias_verifier.mlflow.set_tracking_uri",
        lambda uri: None,
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.hosted_model_alias_verifier.MlflowClient",
        lambda: _FakeClient(),
    )

    with pytest.raises(VerificationError, match="breast_cancer_clf@prod"):
        verify_model_alias(
            HostedModelAliasVerificationConfig(
                tracking_uri="https://mlflow.example.run.app",
                tracking_token="token",
                model_name="breast_cancer_clf",
            )
        )
