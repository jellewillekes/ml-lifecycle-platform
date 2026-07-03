# Schedule Platform Jobs Staging

Last verified: 2026-03-17

This runbook covers the conservative Cloud Scheduler layer added in `UP-22`.

Current scope:

- schedule only already-proven hosted Cloud Run Jobs
- keep maintenance cadence enabled first
- keep candidate-generation cadence present but paused by default
- document how to pause, inspect, and debug scheduled runs

Out of scope here:

- scheduled `promote`
- scheduled `rollback`
- automatic promotion to `prod`
- workflow engine behavior

## Resource contract

Scheduler caller identity:

- `mlp-runtime@fpl-project-jelle.iam.gserviceaccount.com`

Managed scheduler jobs:

- `mlp-maintenance-staging-schedule`
- `mlp-pipeline-staging-schedule`
- `mlp-drift-staging-schedule`

Target Cloud Run jobs:

- `mlp-maintenance-staging`
- `mlp-pipeline-staging`
- `mlp-drift-staging`

Current committed cadence:

| Scheduler job | Target job | Schedule | Time zone | Paused | Purpose |
| --- | --- | --- | --- | --- | --- |
| `mlp-maintenance-staging-schedule` | `mlp-maintenance-staging` | `17 3 * * *` | `UTC` | `false` | daily hosted control-plane verification |
| `mlp-pipeline-staging-schedule` | `mlp-pipeline-staging` | `17 4 * * 1` | `UTC` | `true` | optional weekly candidate-generation path |
| `mlp-drift-staging-schedule` | `mlp-drift-staging` | `17 5 * * *` | `UTC` | `false` | daily batch drift over the last 24h of prediction events |

Intentional boundary:

- only `maintenance` is enabled first
- `pipeline` exists as an operator-controlled next step
- `drift` is enabled: it is read-only (reads the event plane, writes a
  `drift_report.json` and a Prometheus gauge, mutates no model state)
- `promote` and `rollback` remain manual release actions

Drift operations (re-run on demand, local parity, alerting) live in the
dedicated [`drift.md`](drift.md) runbook.

## Deploy path

There is no separate scheduler deploy workflow.

Scheduler resources are applied through the same Terraform root as the hosted jobs:

- `CD / Deploy Platform Jobs / Staging`

That workflow already preserves:

- current hosted MLflow image
- current hosted serving image
- selected published `platform` image

So the same apply now owns:

- Cloud Run platform jobs
- scheduler invoker IAM
- Cloud Scheduler resources

One-time bootstrap requirement:

- `mlp-ci@fpl-project-jelle.iam.gserviceaccount.com` needs project role `roles/cloudscheduler.admin`
- that project-level IAM grant is intentionally still manual, like the existing Terraform-state and bucket-IAM bootstrap grants

## Operator flow

Recommended rollout:

1. deploy the Terraform root through `CD / Deploy Platform Jobs / Staging`
2. verify scheduler resources exist
3. force-run the maintenance schedule once
4. verify it creates a successful `mlp-maintenance-staging` execution
5. leave pipeline paused until maintenance cadence is boring

Useful checks:

```bash
terraform -chdir=deployments/gcp/terraform output platform_schedules
gcloud scheduler jobs list --location=europe-west1 --project fpl-project-jelle
gcloud scheduler jobs describe mlp-maintenance-staging-schedule --location=europe-west1 --project fpl-project-jelle
gcloud scheduler jobs describe mlp-pipeline-staging-schedule --location=europe-west1 --project fpl-project-jelle
```

Force-run maintenance once:

```bash
gcloud scheduler jobs run mlp-maintenance-staging-schedule \
  --location europe-west1 \
  --project fpl-project-jelle
```

Then inspect the resulting Cloud Run Job execution:

```bash
gcloud run jobs executions list \
  --job mlp-maintenance-staging \
  --region europe-west1 \
  --project fpl-project-jelle
```

## Pause and resume

Temporary incident-response controls:

```bash
gcloud scheduler jobs pause mlp-maintenance-staging-schedule \
  --location europe-west1 \
  --project fpl-project-jelle

gcloud scheduler jobs resume mlp-maintenance-staging-schedule \
  --location europe-west1 \
  --project fpl-project-jelle
```

Important:

- Terraform owns the committed paused state
- manual pause or resume is valid for incident response
- a later Terraform apply will restore the state committed in code

Permanent cadence changes should be made in:

- [`scheduler_platform.tf`](../../deployments/gcp/terraform/scheduler_platform.tf)

## Failure model

Treat these failure classes differently:

### Scheduler invoke failure

Examples:

- Cloud Scheduler job could not mint a token
- Cloud Scheduler job could not call the Run API
- no Cloud Run Job execution was created

Likely causes:

- scheduler service account missing
- runtime service account missing required job invoker binding
- scheduler invoker IAM missing
- wrong execute URI
- Cloud Scheduler API not enabled

### Runtime failure

Examples:

- scheduler created an execution
- the Cloud Run Job started
- the workload itself exited non-zero

This means the scheduler path worked and the workload failed.

### Policy-blocked dry-run

Examples:

- `promote --dry-run` returns exit code `2`
- `rollback --dry-run` returns a structured blocked result

These are not scheduler failures and not Cloud Run Job wiring failures.

They are expected state or policy outcomes.

## Current state limitation inherited from UP-21

After rollback, a previously promoted version can still remain behind the `candidate` alias while carrying `release_status=prod`.

What this means:

- a later `promote --dry-run` may correctly block even when `candidate` exists
- this is a model-state hygiene limitation
- it is not a broken scheduler path

Operator response:

- run `pipeline` to create a fresh candidate version
- do not bypass the policy check

## Why pipeline stays paused first

`pipeline` is not a pure read-only check.

It can:

- train
- evaluate
- register candidate state

That is useful, but it is still a model-state-changing path.

So the first committed scheduler stance is:

- maintenance enabled
- pipeline paused
- promote manual
- rollback manual
