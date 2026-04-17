# How It Works Now

Last verified: 2026-04-17

This page is the shortest current explanation of how the repo works in practice.

Use it when you want the operator path and current boundaries without reading every runbook first.

## Two real paths

The repo has two operating paths. The local path is the contributor default. The hosted staging path is an advanced maintainer path — you do not need it to contribute.

### Local path

Used for:

- day-to-day development
- fast iteration
- most debugging
- local end-to-end validation

Shape:

```text
developer shell
  -> Makefile / CLI
  -> Docker Compose
  -> PostgreSQL + MinIO + MLflow
  -> pipeline / promote / rollback / reproduce / serving
```

Main entrypoint:

- [`../runbooks/local-bootstrap.md`](../runbooks/local-bootstrap.md)

## Hosted staging path (advanced — maintainer only)

Used for:

- published image deployment
- hosted MLflow validation
- hosted serving validation
- hosted platform job execution
- conservative scheduler-driven maintenance

Shape:

```text
GitHub Actions
  -> Workload Identity Federation
  -> Artifact Registry image publish
  -> Terraform apply

GCP staging
  -> Cloud Run MLflow
  -> Cloud Run serving
  -> Cloud Run platform jobs
  -> Cloud Scheduler
  -> Cloud SQL
  -> GCS artifacts/data
  -> Secret Manager
```

## What is live in staging

Hosted resources currently in use:

- Cloud Run MLflow staging
- Cloud Run serving staging
- Cloud Run jobs:
  - `mlp-maintenance-staging`
  - `mlp-reproduce-staging`
  - `mlp-promote-staging`
  - `mlp-rollback-staging`
  - `mlp-pipeline-staging`
- Cloud Scheduler jobs:
  - `mlp-maintenance-staging-schedule`
  - `mlp-pipeline-staging-schedule`

Current scheduler stance:

- `maintenance` is enabled
- `pipeline` exists but is paused
- `promote` is manual
- `rollback` is manual

## What remains the control plane

MLflow is still the control plane for model state.

It owns:

- runs
- model versions
- aliases
- release evidence

Container deploys choose runtime bits.

MLflow aliases choose model state.

That separation still matters:

- image identity answers "what code is deployed"
- alias and version identity answer "what model is active"

## Current operator flows

### 1. Publish images

Use:

- `CD / Publish Hosted Images`

Output:

- immutable `platform` and `serving` image refs tagged by Git SHA

### 2. Deploy hosted MLflow

Use:

- [`../runbooks/deploy-mlflow.md`](../runbooks/deploy-mlflow.md)

### 3. Deploy hosted serving

Use:

- [`../runbooks/deploy-serving.md`](../runbooks/deploy-serving.md)

### 4. Deploy hosted platform jobs and scheduler

Use:

- `CD / Deploy Platform Jobs / Staging`

This applies the shared Terraform root and preserves:

- current MLflow image
- current serving image
- selected `platform` image

Main runbook:

- [`../runbooks/deploy-platform-jobs.md`](../runbooks/deploy-platform-jobs.md)

### 5. Run hosted platform jobs manually

Use:

- `Ops / Run Platform Job / Staging`

Safe hosted proof order:

1. `maintenance`
2. `reproduce`
3. `promote` with `dry_run`
4. `rollback` with `dry_run`
5. `pipeline`

### 5a. Run the canonical hosted golden path

Use:

- [`../runbooks/hosted-golden-path.md`](../runbooks/hosted-golden-path.md)

This is the one-button hosted path that:

- publishes images once
- deploys MLflow, serving, and platform jobs by digest
- validates the staged hosted flow end to end

### 6. Inspect or operate scheduler

Use:

- [`../runbooks/schedule-platform-jobs.md`](../runbooks/schedule-platform-jobs.md)

Typical checks:

- list scheduler jobs
- describe scheduler jobs
- force-run `mlp-maintenance-staging-schedule`
- verify resulting Cloud Run Job execution

## Manual bootstrap exceptions

Most deploy state is Terraform-managed, but a few permissions are still intentionally manual bootstrap steps.

Current important exceptions:

- Terraform state bucket IAM for `mlp-ci`
- bucket IAM used during the original bootstrap flow
- `roles/cloudscheduler.admin` for `mlp-ci`

These are documented in:

- [`../reference/gcp-resources.md`](../reference/gcp-resources.md)

## Current known limitations

### Post-rollback candidate state can be confusing

After rollback:

- the previous `prod` can be restored correctly
- but the old promoted version may still sit behind `candidate`
- that version may still carry `release_status=prod`

Result:

- a later `promote --dry-run` can correctly block even when a `candidate` alias exists

This is a model-state hygiene limitation, not a broken Cloud Run Job or scheduler path.

### Scheduler is intentionally conservative

The repo does not currently support:

- scheduled `promote`
- scheduled `rollback`
- automatic promotion to `prod`

That is intentional.

## What is not in place yet

Still out of scope:

- public edge / ALB
- custom domain
- production rollout
- scheduled release-control actions
- additional orchestration beyond conservative maintenance cadence

## Where to read next

Local contributor path:

- [`../runbooks/local-bootstrap.md`](../runbooks/local-bootstrap.md)
- [`./current-state.md`](./current-state.md)
- [`./overview.md`](./overview.md)

Advanced hosted path (maintainer only):

- [`./m2-staging-platform.md`](./m2-staging-platform.md)
- [`../runbooks/deploy-platform-jobs.md`](../runbooks/deploy-platform-jobs.md)
- [`../runbooks/schedule-platform-jobs.md`](../runbooks/schedule-platform-jobs.md)
- [`../reference/gcp-resources.md`](../reference/gcp-resources.md)
