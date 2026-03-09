# GCP Bootstrap

Last verified: 2026-03-09

This runbook adopts the existing Google Cloud project and the existing Terraform state bucket as the M1 bootstrap foundation.

Current adopted identifiers:

- project ID: `fpl-project-jelle`
- Terraform state bucket: `fpl-tf-state-jelle`
- Terraform state prefix: `ml-lifecycle-platform/gcp/bootstrap`

What this root does:

- targets the existing GCP project
- initializes remote Terraform state in the existing GCS bucket
- enables the required project APIs from Terraform

What this root does not do:

- create or rename the project
- create, rename, or manage the backend state bucket in the same state
- deploy Cloud Run, load balancing, or runtime resources yet

## Why the backend bucket is not a Terraform resource here

The remote state bucket is intentionally external to this Terraform root.

Managing the backend bucket from the same state that depends on that bucket creates a bootstrap loop and an easy foot-gun. The boring approach is to treat `fpl-tf-state-jelle` as pre-existing platform infrastructure and only consume it as the backend.

## Prerequisites

- Terraform `1.5.7`
- Google Cloud SDK with both user auth and ADC configured
- access to project `fpl-project-jelle`
- access to bucket `gs://fpl-tf-state-jelle`

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

These are the minimum boring APIs needed for project-level bootstrap and the next round of IAM work.

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
terraform -chdir=deployments/gcp/terraform apply
```

Expected result:

- Terraform state lives in `gs://fpl-tf-state-jelle/ml-lifecycle-platform/gcp/bootstrap`
- Terraform tracks required API enablement for project `fpl-project-jelle`

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
- confirm the bucket name is unchanged and globally unique
