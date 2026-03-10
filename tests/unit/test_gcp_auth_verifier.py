from __future__ import annotations

import subprocess

import pytest

from ml_lifecycle_platform.ci.gcp_auth_verifier import (
    GcpAuthVerificationConfig,
    VerificationError,
    format_success_summary,
    parse_workload_identity_provider,
    verify_resources,
)

pytestmark = pytest.mark.unit


def _completed(
    stdout: str, *, returncode: int = 0, stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["gcloud"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def test_parse_workload_identity_provider_rejects_invalid_name() -> None:
    with pytest.raises(
        VerificationError, match="workload identity provider must match"
    ):
        parse_workload_identity_provider("github-actions")


def test_verify_resources_checks_expected_gcloud_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    provider_name = (
        "projects/125515025877/locations/global/workloadIdentityPools/"
        "github-actions/providers/github-oidc"
    )

    responses = {
        (
            "gcloud",
            "auth",
            "list",
            "--filter=status:ACTIVE",
            "--format=json",
        ): _completed(
            '[{"account": "mlp-ci@fpl-project-jelle.iam.gserviceaccount.com"}]'
        ),
        ("gcloud", "auth", "print-access-token"): _completed("token"),
        (
            "gcloud",
            "projects",
            "describe",
            "fpl-project-jelle",
            "--format=json",
        ): _completed('{"projectId": "fpl-project-jelle"}'),
        (
            "gcloud",
            "iam",
            "service-accounts",
            "describe",
            "mlp-ci@fpl-project-jelle.iam.gserviceaccount.com",
            "--project",
            "fpl-project-jelle",
            "--format=json",
        ): _completed('{"email": "mlp-ci@fpl-project-jelle.iam.gserviceaccount.com"}'),
        (
            "gcloud",
            "iam",
            "workload-identity-pools",
            "providers",
            "describe",
            "github-oidc",
            "--project",
            "fpl-project-jelle",
            "--location",
            "global",
            "--workload-identity-pool",
            "github-actions",
            "--format=json",
        ): _completed(f'{{"name": "{provider_name}"}}'),
        (
            "gcloud",
            "artifacts",
            "repositories",
            "describe",
            "mlp-images",
            "--location",
            "europe-west1",
            "--project",
            "fpl-project-jelle",
            "--format=json",
        ): _completed(
            '{"name": "projects/fpl-project-jelle/locations/europe-west1/repositories/mlp-images"}'
        ),
        (
            "gcloud",
            "storage",
            "buckets",
            "describe",
            "gs://fpl-project-jelle-mlp-artifacts",
            "--format=json",
        ): _completed('{"name": "fpl-project-jelle-mlp-artifacts"}'),
        (
            "gcloud",
            "storage",
            "buckets",
            "describe",
            "gs://fpl-project-jelle-mlp-data",
            "--format=json",
        ): _completed('{"name": "fpl-project-jelle-mlp-data"}'),
        (
            "gcloud",
            "secrets",
            "describe",
            "mlp-mlflow-tracking-uri",
            "--project",
            "fpl-project-jelle",
            "--format=json",
        ): _completed(
            '{"name": "projects/fpl-project-jelle/secrets/mlp-mlflow-tracking-uri"}'
        ),
        (
            "gcloud",
            "secrets",
            "describe",
            "mlp-mlflow-tracking-username",
            "--project",
            "fpl-project-jelle",
            "--format=json",
        ): _completed(
            '{"name": "projects/fpl-project-jelle/secrets/mlp-mlflow-tracking-username"}'
        ),
        (
            "gcloud",
            "secrets",
            "describe",
            "mlp-mlflow-tracking-password",
            "--project",
            "fpl-project-jelle",
            "--format=json",
        ): _completed(
            '{"name": "projects/fpl-project-jelle/secrets/mlp-mlflow-tracking-password"}'
        ),
    }

    def fake_run(
        args: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        del check, capture_output, text
        calls.append(args)
        return responses[tuple(args)]

    monkeypatch.setattr(
        "ml_lifecycle_platform.ci.gcp_auth_verifier.subprocess.run", fake_run
    )

    config = GcpAuthVerificationConfig(
        project_id="fpl-project-jelle",
        service_account="mlp-ci@fpl-project-jelle.iam.gserviceaccount.com",
        workload_identity_provider=provider_name,
    )

    verify_resources(config)

    assert [tuple(call) for call in calls] == list(responses.keys())


def test_verify_resources_fails_with_actionable_message_on_account_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(
        args: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        del args, check, capture_output, text
        return _completed('[{"account": "someone@example.com"}]')

    monkeypatch.setattr(
        "ml_lifecycle_platform.ci.gcp_auth_verifier.subprocess.run", fake_run
    )

    config = GcpAuthVerificationConfig(
        project_id="fpl-project-jelle",
        service_account="mlp-ci@fpl-project-jelle.iam.gserviceaccount.com",
        workload_identity_provider=(
            "projects/125515025877/locations/global/workloadIdentityPools/"
            "github-actions/providers/github-oidc"
        ),
    )

    with pytest.raises(VerificationError, match="expected active gcloud account"):
        verify_resources(config)


def test_format_success_summary_includes_core_resources() -> None:
    config = GcpAuthVerificationConfig(
        project_id="fpl-project-jelle",
        service_account="mlp-ci@fpl-project-jelle.iam.gserviceaccount.com",
        workload_identity_provider=(
            "projects/125515025877/locations/global/workloadIdentityPools/"
            "github-actions/providers/github-oidc"
        ),
    )

    summary = format_success_summary(config)

    assert "fpl-project-jelle-mlp-artifacts" in summary
    assert "mlp-mlflow-tracking-uri" in summary
    assert "mlp-images" in summary
