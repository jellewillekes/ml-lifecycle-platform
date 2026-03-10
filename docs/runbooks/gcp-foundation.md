# GCP Foundation

Last verified: 2026-03-10

This runbook creates the first hosted GCP foundation layer on top of the adopted project and Terraform backend from [`gcp-bootstrap.md`](./gcp-bootstrap.md).

Current scope:

- Artifact Registry repository for platform images
- GCS buckets for hosted artifacts and data
- Secret Manager placeholders for hosted MLflow connectivity
- service accounts for CI and runtime workloads
- GitHub Actions workload identity federation for the repo CI path
- base IAM bindings for image push, bucket access, and secret access

Out of scope here:

- Cloud Run services or jobs
- ingress or load balancing
- hosted MLflow
- alerting, schedulers, or dashboards

## Naming conventions

Foundation resources use the `mlp` prefix.

Resources created by this root:

- Artifact Registry repository: `mlp-images`
- buckets:
  - `${project_id}-mlp-artifacts`
  - `${project_id}-mlp-data`
- service accounts:
  - `mlp-ci@<project>.iam.gserviceaccount.com`
  - `mlp-runtime@<project>.iam.gserviceaccount.com`
- Secret Manager placeholders:
  - `mlp-mlflow-tracking-uri`
  - `mlp-mlflow-tracking-username`
  - `mlp-mlflow-tracking-password`
- workload identity:
  - pool: `github-actions`
  - provider: `github-oidc`

## Managed APIs

This ticket extends the bootstrap API set with the hosted-foundation minimum:

- `artifactregistry.googleapis.com`
- `iamcredentials.googleapis.com`
- `secretmanager.googleapis.com`
- `storage.googleapis.com`
- `sts.googleapis.com`

The bootstrap APIs remain managed too:

- `serviceusage.googleapis.com`
- `cloudresourcemanager.googleapis.com`
- `iam.googleapis.com`

## GitHub Actions federation model

CI authentication uses GitHub OIDC through Workload Identity Federation.

This root creates:

- one workload identity pool and provider
- one CI service account
- one `roles/iam.workloadIdentityUser` binding from the GitHub repo principal set to that CI service account

The provider condition restricts trust to the current repository by numeric GitHub owner and repository IDs, not just names. That avoids name-reuse issues if the repo or owner name ever changes hands.

Current bound repository:

- `jellewillekes/ml-lifecycle-platform`

## Runtime IAM model

The runtime service account gets only the base permissions needed for later hosted workloads to read secrets and write objects:

- `roles/storage.objectAdmin` on the hosted artifacts and data buckets
- `roles/secretmanager.secretAccessor` on the hosted MLflow secrets

The CI service account gets:

- `roles/artifactregistry.writer` on the image repository

Nothing in this root grants deploy-time permissions for Cloud Run or broader project admin actions yet.

## Handoff to M2

This foundation layer is intentionally enough for:

- GitHub Actions auth through WIF
- image publication into Artifact Registry
- reserving stable bucket and secret names for hosted follow-up work

`M2` should build on this root by adding:

- Cloud SQL
- hosted MLflow
- hosted serving
- edge and orchestration later

Use the fixed decisions in [`../architecture/m2-staging-platform.md`](../architecture/m2-staging-platform.md) as the default shape unless a later ADR changes them.
The concrete stateful infra added in `UP-16` is documented in [`./gcp-staging-infra.md`](./gcp-staging-infra.md).

## Operator flow

From the repo root:

```bash
make terraform-gcp-fmt
make terraform-gcp-init
make terraform-gcp-validate
make terraform-gcp-plan
```

Apply when the plan looks correct:

```bash
terraform -chdir=deployments/gcp/terraform apply
```

## Outputs for later tickets

After apply, inspect the outputs:

```bash
terraform -chdir=deployments/gcp/terraform output
```

Most important outputs for CI and deploy follow-up work:

- `artifact_registry_docker_repository`
- `foundation_service_accounts`
- `foundation_bucket_names`
- `foundation_secret_ids`
- `workload_identity_provider_name`

Those outputs are enough for:

- GitHub Actions auth through `google-github-actions/auth`
- pushing Docker images into Artifact Registry
- wiring later runtime configs to the reserved bucket and secret names

## Manual verification

Check the concrete resources after apply:

```bash
gcloud artifacts repositories list --location=europe-west1 --project fpl-project-jelle
gcloud storage buckets list --project fpl-project-jelle
gcloud secrets list --project fpl-project-jelle
gcloud iam service-accounts list --project fpl-project-jelle
gcloud iam workload-identity-pools list --location=global --project fpl-project-jelle
terraform -chdir=deployments/gcp/terraform output
```

## Debugging

If Workload Identity Federation fails later in CI:

- wait a few minutes after first apply because pool/provider IAM propagation is not instant
- confirm the GitHub repository owner ID and repository ID still match reality
- confirm the workflow uses the full `workload_identity_provider_name` output
- confirm the workflow impersonates the CI service account email from `foundation_service_accounts`
