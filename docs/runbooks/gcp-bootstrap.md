# GCP Bootstrap

Last verified: 2026-03-10

> Forking the repo? Start from [`oss-deploy.md`](./oss-deploy.md). It tells
> you which identifiers in this runbook to swap and links back here at the
> right step.

This runbook covers the shared Terraform root that adopts the existing GCP project and remote state bucket and now also manages the first hosted foundation resources.

Current adopted identifiers:

- project ID: `fpl-project-jelle`
- Terraform state bucket: `fpl-tf-state-jelle`
- Terraform state prefix: `ml-lifecycle-platform/gcp/bootstrap`

What this root does:

- targets the existing GCP project
- initializes remote Terraform state in the existing GCS bucket
- enables the required project APIs from Terraform
- manages the first hosted foundation resources:
  - Artifact Registry repository
  - hosted buckets
  - placeholder secrets
  - CI and runtime service accounts
  - GitHub Actions Workload Identity Federation

What this root does not do:

- create or rename the project
- create, rename, or manage the backend state bucket in the same state
- provision Cloud SQL yet
- deploy Cloud Run services or jobs yet
- deploy load balancing or scheduler resources yet

## Why the backend bucket is not a Terraform resource here

The remote state bucket is intentionally external to this Terraform root.

Managing the backend bucket from the same state that depends on that bucket creates a bootstrap loop and an easy foot-gun. The boring approach is to treat `fpl-tf-state-jelle` as pre-existing platform infrastructure and only consume it as the backend.

## Prerequisites

- Terraform `1.5.7`
- Google Cloud SDK with both user auth and ADC configured
- access to project `fpl-project-jelle`
- access to bucket `gs://fpl-tf-state-jelle`

## Manual bootstrap IAM for `mlp-ci`

The Terraform backend bucket is external to this root, and the hosted app buckets are already managed resources inside the root.

That creates one boring bootstrap rule:

- `mlp-ci` cannot use Terraform to grant itself the bucket IAM it needs to run Terraform

So these bindings must exist before GitHub Actions deploy workflows can apply this root:

- `roles/storage.objectAdmin` on `gs://fpl-tf-state-jelle`
- `roles/storage.admin` on `gs://fpl-project-jelle-mlp-artifacts`
- `roles/storage.admin` on `gs://fpl-project-jelle-mlp-data`

Member:

- `serviceAccount:mlp-ci@fpl-project-jelle.iam.gserviceaccount.com`

Apply them once with an operator identity:

```bash
gcloud storage buckets add-iam-policy-binding gs://fpl-tf-state-jelle \
  --member=serviceAccount:mlp-ci@fpl-project-jelle.iam.gserviceaccount.com \
  --role=roles/storage.objectAdmin

gcloud storage buckets add-iam-policy-binding gs://fpl-project-jelle-mlp-artifacts \
  --member=serviceAccount:mlp-ci@fpl-project-jelle.iam.gserviceaccount.com \
  --role=roles/storage.admin

gcloud storage buckets add-iam-policy-binding gs://fpl-project-jelle-mlp-data \
  --member=serviceAccount:mlp-ci@fpl-project-jelle.iam.gserviceaccount.com \
  --role=roles/storage.admin
```

This is intentionally documented as bootstrap state, not hidden as if the root were self-provisioning.

Authenticate once on a new machine:

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project fpl-project-jelle
gcloud auth application-default set-quota-project fpl-project-jelle
```

Quick access checks:

```bash
gcloud projects describe fpl-project-jelle
gcloud storage buckets describe gs://fpl-tf-state-jelle
```

## Clean checkout flow

From the repo root:

```bash
make terraform-gcp-fmt
make terraform-gcp-init
make terraform-gcp-validate
terraform -chdir=deployments/gcp/terraform plan
```

That flow uses committed defaults:

- `TF_STATE_BUCKET=fpl-tf-state-jelle`
- `TF_STATE_PREFIX=ml-lifecycle-platform/gcp/bootstrap`
- `TF_VAR_project_id=fpl-project-jelle`
- `TF_VAR_region=europe-west1`

Override them only when you intentionally need a different target:

```bash
TF_VAR_region=europe-west1 make terraform-gcp-init
TF_VAR_region=europe-west1 terraform -chdir=deployments/gcp/terraform plan
```

## Optional local overrides

If you do not want to use environment variables, create a local, untracked `deployments/gcp/terraform/terraform.tfvars` from the example:

```bash
cp deployments/gcp/terraform/terraform.tfvars.example deployments/gcp/terraform/terraform.tfvars
```

Then edit the file if you need a different region or service list.

## API management model

This root is intentionally narrow.

Managed APIs today:

- `serviceusage.googleapis.com`
- `cloudresourcemanager.googleapis.com`
- `iam.googleapis.com`
- `artifactregistry.googleapis.com`
- `iamcredentials.googleapis.com`
- `secretmanager.googleapis.com`
- `storage.googleapis.com`
- `sts.googleapis.com`

These are the minimum boring APIs needed for the adopted project, hosted foundation, and CI federation path.

We are not using the authoritative `google_project_services` resource yet because that would disable every API not listed here. That is a bad default while the project may still contain old manual experiments.

## Pre-adoption cleanup

If the project still contains old APIs or resources, inventory them before the first apply:

```bash
gcloud services list --enabled --project fpl-project-jelle
```

Delete stale resources manually before expanding this Terraform root. Do not try to make this first bootstrap root authoritative for the whole project on day one.

## First apply

After the plan looks correct:

```bash
make terraform-gcp-apply
```

Expected result:

- Terraform state lives in `gs://fpl-tf-state-jelle/ml-lifecycle-platform/gcp/bootstrap`
- Terraform tracks required API enablement for project `fpl-project-jelle`
- the hosted foundation resources from [`gcp-foundation.md`](./gcp-foundation.md) exist and match the committed naming contract

## What comes next

This root is the starting point for `M2`, not the end state.

The next staged additions are:

- Cloud SQL and MLflow storage wiring
- hosted MLflow on Cloud Run
- hosted serving on Cloud Run

See [`../architecture/m2-staging-platform.md`](../architecture/m2-staging-platform.md) for the fixed decisions and implementation order.
See [`./gcp-staging-infra.md`](./gcp-staging-infra.md) for the concrete `UP-16` stateful infra contract.

## Debugging

Common checks:

```bash
terraform -chdir=deployments/gcp/terraform state pull
terraform -chdir=deployments/gcp/terraform providers
gcloud services list --enabled --project fpl-project-jelle
```

If `terraform init` fails on the backend:

- confirm your ADC credentials are valid
- confirm you can read `gs://fpl-tf-state-jelle`
- confirm `mlp-ci` has `roles/storage.objectAdmin` on `gs://fpl-tf-state-jelle` before relying on GitHub Actions applies
- confirm the bucket name is unchanged and globally unique
