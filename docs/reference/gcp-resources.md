# GCP Resources

This page is the committed GCP resource inventory for the current repo state.

It is not a full Google Cloud project inventory. It is the subset this repo owns through Terraform today.

Source of truth:

- [`deployments/gcp/terraform/`](../../deployments/gcp/terraform/)

## Scope today

Managed now:

- Artifact Registry
- hosted GCS buckets
- Secret Manager foundation placeholders
- CI and runtime service accounts
- GitHub Actions Workload Identity Federation
- staging VPC and subnet
- private service access for Cloud SQL
- Cloud SQL for hosted MLflow metadata
- active MLflow staging secrets
- Cloud Run MLflow service and CI deploy IAM bindings
- Cloud Run serving service and runtime-to-MLflow invoke IAM
- Cloud Run jobs for hosted platform actions
- Cloud Scheduler for conservative staged platform cadence

Not managed yet:

- ALB or custom domain

## Shared identifiers

| Item | Value |
| --- | --- |
| project ID | `fpl-project-jelle` |
| region | `europe-west1` |
| Terraform root | `deployments/gcp/terraform/` |
| Terraform backend bucket | `gs://fpl-tf-state-jelle` |

## Foundation resources

| Resource | Name | Purpose |
| --- | --- | --- |
| Artifact Registry repository | `mlp-images` | hosted runtime images |
| artifacts bucket | `fpl-project-jelle-mlp-artifacts` | hosted artifacts |
| data bucket | `fpl-project-jelle-mlp-data` | hosted data files |
| CI service account | `mlp-ci@fpl-project-jelle.iam.gserviceaccount.com` | GitHub Actions impersonation |
| runtime service account | `mlp-runtime@fpl-project-jelle.iam.gserviceaccount.com` | hosted workload identity |
| WIF pool | `github-actions` | GitHub OIDC trust root |
| WIF provider | `github-oidc` | GitHub repository trust binding |

Reserved foundation secrets:

- `mlp-mlflow-tracking-uri`
- `mlp-mlflow-tracking-username`
- `mlp-mlflow-tracking-password`

## Staging infra from UP-16

| Resource | Name | Purpose |
| --- | --- | --- |
| VPC | `mlp-staging-vpc` | shared network for hosted staging |
| subnet | `mlp-staging-subnet` | regional subnet in `europe-west1` |
| private service range | `mlp-staging-private-services` | private service access |
| Cloud SQL instance | `mlp-mlflow-staging` | hosted MLflow metadata backend |
| database | `mlflow` | MLflow metadata DB |
| DB user | `mlflow` | MLflow DB user |
| MLflow artifact root | `gs://fpl-project-jelle-mlp-artifacts/mlflow/` | hosted MLflow artifacts |

Active staging secrets:

- `mlp-mlflow-db-user`
- `mlp-mlflow-db-password`
- `mlp-mlflow-db-name`
- `mlp-mlflow-instance-connection-name`
- `mlp-mlflow-artifact-root`

## IAM contract

Current important bindings:

- `mlp-ci` can push images to Artifact Registry
- `mlp-ci` can deploy Cloud Run services after the one-time bootstrap apply
- `mlp-runtime` can read the hosted MLflow secrets
- `mlp-runtime` can write objects to the hosted artifacts and data buckets
- `mlp-runtime` has `roles/cloudsql.client`

Current deploy-specific CI bindings:

- `roles/run.admin`
- `roles/serviceusage.serviceUsageAdmin`
- `roles/iam.serviceAccountUser` on `mlp-runtime`

Manual bootstrap IAM outside this Terraform root:

- `roles/storage.objectAdmin` on `gs://fpl-tf-state-jelle`
- `roles/storage.admin` on:
  - `gs://fpl-project-jelle-mlp-artifacts`
  - `gs://fpl-project-jelle-mlp-data`
- `roles/cloudscheduler.admin` on project `fpl-project-jelle`

These bindings are required so `mlp-ci` can:

- create the Terraform remote-state lock object
- read and edit bucket IAM for the already-managed app buckets
- create and update Cloud Scheduler jobs from the deploy workflow

Current service-specific binding once deployed:

- `roles/run.invoker` on `mlp-mlflow-staging`
- `roles/run.invoker` on `mlp-serving-staging`
- `roles/run.invoker` on `mlp-mlflow-staging` for `mlp-runtime`
- `roles/run.invoker` on `mlp-maintenance-staging` for `mlp-runtime`
- `roles/run.invoker` on `mlp-pipeline-staging` for `mlp-runtime`

## Current staging runtime inventory

| Resource | Name | Notes |
| --- | --- | --- |
| Cloud Run MLflow service | `mlp-mlflow-staging` | live, IAM-protected |
| Cloud Run serving service | `mlp-serving-staging` | deploy contract in repo, staging deploy workflow present |
| Cloud Run job | `mlp-maintenance-staging` | deployed by `UP-21`; safe hosted control-plane verification |
| Cloud Run job | `mlp-reproduce-staging` | deployed by `UP-21`; read-heavy reproduce path for `prod` |
| Cloud Run job | `mlp-promote-staging` | deployed by `UP-21`; release action, first validation should use `--dry-run` |
| Cloud Run job | `mlp-rollback-staging` | deployed by `UP-21`; release action, first validation should use `--dry-run` |
| Cloud Run job | `mlp-pipeline-staging` | deployed by `UP-21`; hosted pipeline path, may create candidate state |
| Cloud Scheduler job | `mlp-maintenance-staging-schedule` | added by `UP-22`; enabled conservative maintenance cadence |
| Cloud Scheduler job | `mlp-pipeline-staging-schedule` | added by `UP-22`; paused candidate-generation cadence |
| Cloud SQL instance | `mlp-mlflow-staging` | Postgres metadata backend for MLflow |
| artifact bucket prefix | `gs://fpl-project-jelle-mlp-artifacts/mlflow/` | MLflow artifact root |
| runtime service account | `mlp-runtime@fpl-project-jelle.iam.gserviceaccount.com` | used by hosted MLflow and serving |
| CI service account | `mlp-ci@fpl-project-jelle.iam.gserviceaccount.com` | used by GitHub Actions via WIF |

Bootstrap note:

- the Cloud Run services are Terraform-managed here
- some `mlp-ci` bucket IAM is intentionally still manual and out-of-band
- that is a bootstrap limitation, not hidden behavior

Still not granted:

- public ingress configuration

## Useful Terraform outputs

Current outputs operators and later PRs should use:

- `artifact_registry_docker_repository`
- `foundation_bucket_names`
- `foundation_secret_ids`
- `foundation_service_accounts`
- `staging_network`
- `mlflow_sql`
- `mlflow_secret_ids`
- `platform_schedules`
- `workload_identity_provider_name`

Most important current deploy-facing outputs:

### `mlflow_sql`

- `instance_name`
- `connection_name`
- `private_ip`
- `database_name`
- `database_user`
- `artifact_root`

### `staging_network`

- `network_name`
- `network_id`
- `subnetwork_name`
- `subnetwork_id`
- `subnetwork_cidr`
- `peering_range`
- `peering_cidr`

### `mlflow_service`

- `name`
- `uri`
- `image`
- `invoker_sa`

### `serving_service`

- `name`
- `uri`
- `image`
- `invoker_sa`

### `platform_jobs`

Per-job contract fields:

- `name`
- `image`
- `command`
- `args`
- `mutates_model_state`
- `safe_validation_args`

### `platform_schedules`

Per-schedule contract fields:

- `name`
- `region`
- `schedule`
- `time_zone`
- `paused`
- `target_job`

## Operator checks

After any Terraform apply, these are the fastest sanity checks:

```bash
terraform -chdir=deployments/gcp/terraform output
gcloud artifacts repositories list --location=europe-west1 --project fpl-project-jelle
gcloud sql instances describe mlp-mlflow-staging --project fpl-project-jelle
gcloud secrets list --project fpl-project-jelle
```

Companion runbooks:

- [`../runbooks/gcp-bootstrap.md`](../runbooks/gcp-bootstrap.md)
- [`../runbooks/gcp-foundation.md`](../runbooks/gcp-foundation.md)
- [`../runbooks/gcp-staging-infra.md`](../runbooks/gcp-staging-infra.md)
- [`../runbooks/deploy-platform-jobs.md`](../runbooks/deploy-platform-jobs.md)
- [`../runbooks/schedule-platform-jobs.md`](../runbooks/schedule-platform-jobs.md)
