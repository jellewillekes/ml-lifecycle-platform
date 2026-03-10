from __future__ import annotations

from dataclasses import dataclass
import json
import subprocess
from typing import Any

DEFAULT_ARTIFACT_REPOSITORY = "mlp-images"
DEFAULT_REGION = "europe-west1"
DEFAULT_SECRET_IDS = (
    "mlp-mlflow-tracking-uri",
    "mlp-mlflow-tracking-username",
    "mlp-mlflow-tracking-password",
)


class VerificationError(RuntimeError):
    """Raised when CI auth verification fails."""


@dataclass(frozen=True)
class GcpAuthVerificationConfig:
    project_id: str
    service_account: str
    workload_identity_provider: str
    region: str = DEFAULT_REGION
    artifact_repository: str = DEFAULT_ARTIFACT_REPOSITORY
    artifacts_bucket: str | None = None
    data_bucket: str | None = None
    secret_ids: tuple[str, ...] = DEFAULT_SECRET_IDS

    @property
    def resolved_artifacts_bucket(self) -> str:
        return self.artifacts_bucket or f"{self.project_id}-mlp-artifacts"

    @property
    def resolved_data_bucket(self) -> str:
        return self.data_bucket or f"{self.project_id}-mlp-data"


def parse_workload_identity_provider(provider_name: str) -> tuple[str, str, str]:
    parts = provider_name.split("/")
    if len(parts) != 8:
        raise VerificationError(
            "workload identity provider must match "
            "'projects/<number>/locations/global/workloadIdentityPools/<pool>/providers/<provider>'."
        )
    if (
        parts[0] != "projects"
        or parts[2] != "locations"
        or parts[3] != "global"
        or parts[4] != "workloadIdentityPools"
        or parts[6] != "providers"
    ):
        raise VerificationError(
            "workload identity provider must match "
            "'projects/<number>/locations/global/workloadIdentityPools/<pool>/providers/<provider>'."
        )
    return parts[1], parts[5], parts[7]


def _run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=False, capture_output=True, text=True)


def _run_gcloud_json(args: list[str], *, expectation: str) -> Any:
    completed = _run_command(args)
    if completed.returncode != 0:
        stderr = (
            completed.stderr.strip()
            or completed.stdout.strip()
            or "unknown gcloud error"
        )
        raise VerificationError(f"{expectation}: {stderr}")

    stdout = completed.stdout.strip()
    if not stdout:
        raise VerificationError(f"{expectation}: gcloud returned no JSON output.")

    try:
        return json.loads(stdout)
    except json.JSONDecodeError as error:
        raise VerificationError(
            f"{expectation}: gcloud returned invalid JSON: {error.msg}."
        ) from error


def _run_gcloud_text(args: list[str], *, expectation: str) -> str:
    completed = _run_command(args)
    if completed.returncode != 0:
        stderr = (
            completed.stderr.strip()
            or completed.stdout.strip()
            or "unknown gcloud error"
        )
        raise VerificationError(f"{expectation}: {stderr}")
    stdout = completed.stdout.strip()
    if not stdout:
        raise VerificationError(f"{expectation}: gcloud returned no output.")
    return stdout


def verify_active_account(expected_service_account: str) -> None:
    accounts = _run_gcloud_json(
        ["gcloud", "auth", "list", "--filter=status:ACTIVE", "--format=json"],
        expectation="failed to list active gcloud accounts after OIDC auth",
    )
    active_accounts = [
        entry.get("account", "") for entry in accounts if isinstance(entry, dict)
    ]
    if expected_service_account not in active_accounts:
        raise VerificationError(
            "expected active gcloud account "
            f"'{expected_service_account}', got {active_accounts or ['<none>']}."
        )


def verify_access_token() -> None:
    _run_gcloud_text(
        ["gcloud", "auth", "print-access-token"],
        expectation="failed to mint an access token after service account impersonation",
    )


def verify_project(project_id: str) -> None:
    project = _run_gcloud_json(
        ["gcloud", "projects", "describe", project_id, "--format=json"],
        expectation=f"failed to describe project '{project_id}'",
    )
    if project.get("projectId") != project_id:
        raise VerificationError(
            f"expected project '{project_id}', got '{project.get('projectId', '<missing>')}'."
        )


def verify_artifact_repository(project_id: str, region: str, repository: str) -> None:
    payload = _run_gcloud_json(
        [
            "gcloud",
            "artifacts",
            "repositories",
            "describe",
            repository,
            "--location",
            region,
            "--project",
            project_id,
            "--format=json",
        ],
        expectation=f"failed to describe Artifact Registry repository '{repository}'",
    )
    if payload.get("name", "").split("/")[-1] != repository:
        raise VerificationError(
            f"Artifact Registry repository lookup returned unexpected name '{payload.get('name', '<missing>')}'."
        )


def verify_bucket(bucket_name: str) -> None:
    payload = _run_gcloud_json(
        [
            "gcloud",
            "storage",
            "buckets",
            "describe",
            f"gs://{bucket_name}",
            "--format=json",
        ],
        expectation=f"failed to describe bucket '{bucket_name}'",
    )
    if payload.get("name") != bucket_name:
        raise VerificationError(
            f"bucket lookup returned unexpected name '{payload.get('name', '<missing>')}'."
        )


def verify_secret(project_id: str, secret_id: str) -> None:
    payload = _run_gcloud_json(
        [
            "gcloud",
            "secrets",
            "describe",
            secret_id,
            "--project",
            project_id,
            "--format=json",
        ],
        expectation=f"failed to describe secret '{secret_id}'",
    )
    if payload.get("name", "").split("/")[-1] != secret_id:
        raise VerificationError(
            f"secret lookup returned unexpected name '{payload.get('name', '<missing>')}'."
        )


def verify_service_account(project_id: str, service_account: str) -> None:
    payload = _run_gcloud_json(
        [
            "gcloud",
            "iam",
            "service-accounts",
            "describe",
            service_account,
            "--project",
            project_id,
            "--format=json",
        ],
        expectation=f"failed to describe service account '{service_account}'",
    )
    if payload.get("email") != service_account:
        raise VerificationError(
            "service account lookup returned unexpected email "
            f"'{payload.get('email', '<missing>')}'."
        )


def verify_workload_identity_provider(project_id: str, provider_name: str) -> None:
    _, pool_id, provider_id = parse_workload_identity_provider(provider_name)
    payload = _run_gcloud_json(
        [
            "gcloud",
            "iam",
            "workload-identity-pools",
            "providers",
            "describe",
            provider_id,
            "--project",
            project_id,
            "--location",
            "global",
            "--workload-identity-pool",
            pool_id,
            "--format=json",
        ],
        expectation=f"failed to describe workload identity provider '{provider_name}'",
    )
    if payload.get("name") != provider_name:
        raise VerificationError(
            "workload identity provider lookup returned unexpected name "
            f"'{payload.get('name', '<missing>')}'."
        )


def verify_resources(config: GcpAuthVerificationConfig) -> None:
    verify_active_account(config.service_account)
    verify_access_token()
    verify_project(config.project_id)
    verify_service_account(config.project_id, config.service_account)
    verify_workload_identity_provider(
        config.project_id, config.workload_identity_provider
    )
    verify_artifact_repository(
        config.project_id,
        config.region,
        config.artifact_repository,
    )
    verify_bucket(config.resolved_artifacts_bucket)
    verify_bucket(config.resolved_data_bucket)
    for secret_id in config.secret_ids:
        verify_secret(config.project_id, secret_id)


def format_success_summary(config: GcpAuthVerificationConfig) -> str:
    return "\n".join(
        [
            f"Verified OIDC auth for project: {config.project_id}",
            f"Verified impersonated service account: {config.service_account}",
            f"Verified workload identity provider: {config.workload_identity_provider}",
            f"Verified Artifact Registry repository: {config.artifact_repository}",
            f"Verified buckets: {config.resolved_artifacts_bucket}, {config.resolved_data_bucket}",
            "Verified secrets: " + ", ".join(config.secret_ids),
        ]
    )
