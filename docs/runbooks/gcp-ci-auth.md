# GCP CI Auth

Last verified: 2026-03-10

This runbook verifies the GitHub Actions to GCP trust chain before any image push or deploy workflow is trusted.

Workflow:

- `.github/workflows/gcp-auth-verify.yml`

What it proves:

- GitHub Actions can mint an OIDC token
- Google Workload Identity Federation accepts that token
- the workflow can impersonate the intended CI service account
- the expected hosted-foundation resources exist in `fpl-project-jelle`

## Required GitHub Actions variables

Set these repository variables from Terraform outputs:

- `GCP_PROJECT_ID`
  - `terraform -chdir=deployments/gcp/terraform output -raw project_id`
- `GCP_WIF_PROVIDER`
  - `terraform -chdir=deployments/gcp/terraform output -raw workload_identity_provider_name`
- `GCP_CI_SERVICE_ACCOUNT`
  - `terraform -chdir=deployments/gcp/terraform output -raw ci_service_account_email`

No static service account key is used.

## How to run it

Run the workflow manually from the branch you want to verify:

1. Open `Actions`
2. Select `Ops / Verify GCP Auth`
3. Click `Run workflow`
4. Choose the branch
5. Run it

The workflow also runs automatically on `master` when auth or staging-foundation paths change.

## What it checks

After authentication, the workflow verifies:

- project access to `fpl-project-jelle`
- CI service account impersonation
- WIF provider existence
- Artifact Registry repository `mlp-images`
- buckets:
  - `fpl-project-jelle-mlp-artifacts`
  - `fpl-project-jelle-mlp-data`
- Secret Manager placeholders:
  - `mlp-mlflow-tracking-uri`
  - `mlp-mlflow-tracking-username`
  - `mlp-mlflow-tracking-password`

## Failure debugging

If the workflow fails before `gcloud` setup:

- confirm the job still has `permissions.id-token: write`
- confirm the GitHub Actions variables are set
- confirm `GCP_WIF_PROVIDER` matches the Terraform output exactly
- confirm `GCP_CI_SERVICE_ACCOUNT` matches the Terraform output exactly
- confirm the repo is still the trusted GitHub repository in the WIF provider condition

If the workflow authenticates but the verification step fails:

- check that the expected Terraform foundation resources still exist
- compare the failing resource name with the naming conventions in [`gcp-foundation.md`](./gcp-foundation.md)
