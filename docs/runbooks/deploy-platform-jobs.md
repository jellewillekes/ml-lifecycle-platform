# Deploy Platform Jobs Staging

Last verified: 2026-03-17

This runbook covers the hosted Cloud Run Jobs path added in `UP-21`.

Current scope:

- deploy Cloud Run jobs from the published `platform` image
- keep hosted execution separate from local Compose
- validate safe hosted execution paths before mutating ones

Out of scope here:

- scheduler or cadence wiring
- automatic promotion to `prod`
- edge or load balancer concerns

Scheduler note:

- `UP-22` adds scheduler resources in the same Terraform root
- scheduler-specific operator flow now lives in [`schedule-platform-jobs.md`](./schedule-platform-jobs.md)
- this runbook stays focused on job deployment and manual execution

## Job contract

Deployed jobs:

- `mlp-maintenance-staging`
- `mlp-reproduce-staging`
- `mlp-promote-staging`
- `mlp-rollback-staging`
- `mlp-pipeline-staging`

All jobs use:

- Artifact Registry image `platform`
- runtime service account `mlp-runtime@fpl-project-jelle.iam.gserviceaccount.com`
- `MLP_ENV=staging`
- hosted MLflow staging as both tracking and registry URI
- model name `breast_cancer_clf`
- model spec `configs/models/breast_cancer_demo.yaml`

Important boundary:

- `maintenance` and `reproduce` are read-mostly/debug paths
- `promote`, `rollback`, and `pipeline` can mutate hosted model state
- `pipeline` may create candidate state
- promotion to `prod` remains a separate release action

## Deploy path

Run the GitHub Actions workflow:

- `Deploy Platform Jobs Staging`

Input:

- required `platform_image`
  - digest-pinned Artifact Registry ref published by `Publish Images`

What it does:

1. authenticate to GCP with WIF
2. validate the provided digest-pinned `platform_image`
3. resolve the current hosted MLflow and serving images
4. apply Terraform with:
   - `TF_VAR_mlflow_image=<current-mlflow-ref@sha256:...>`
   - `TF_VAR_serving_image=<current-serving-ref@sha256:...>`
   - `TF_VAR_platform_image=<provided-platform-ref@sha256:...>`

The workflow preserves MLflow and serving because all three runtime paths still share one Terraform root.

## Manual execution

Run the GitHub Actions workflow:

- `Run Platform Job Staging`

Inputs:

- `job_name`
- `execution_mode`

`execution_mode` keeps the hosted job invocation safe and predictable:

- `default`
  - runs the deployed job defaults
  - valid for all jobs
- `dry_run`
  - only valid for `promote` and `rollback`
  - expands to the full module invocation needed by Cloud Run Jobs
  - avoids the earlier operator error where a partial `--args` override replaced the job's `-m ...` entrypoint

Recommended validation order:

If you want a deterministic hosted validation fixture first, run:

- `Seed Hosted Staging Model`

That workflow leaves staging with:

- a rollback-ready `prod`
- a fresh distinct `candidate`

Then run:

1. `maintenance`
2. `reproduce`
3. `promote` with `execution_mode=dry_run`
4. `rollback` with `execution_mode=dry_run`
5. `pipeline`

This keeps the first hosted proofs read-mostly or policy-only before running mutating paths.

## Failure modes

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| platform image digest cannot be resolved | `Publish Images` has not published `platform:<sha>` | run `Publish Images` first or use the correct SHA |
| jobs disappear after MLflow or serving deploy | shared Terraform root applied without preserving `platform_image` | keep preserving the current platform image in deploy workflows |
| `maintenance` fails on prod alias | hosted MLflow no longer has `breast_cancer_clf@prod` | reseed or repair hosted model state first |
| `reproduce` fails on artifact download | hosted MLflow artifacts or credentials are incomplete | inspect hosted MLflow artifact root and runtime permissions |
| `promote` with `execution_mode=dry_run` returns exit code `2` | policy blocked promotion | inspect the JSON policy decision before mutating |
| `rollback` with `execution_mode=dry_run` returns `blocked` | current `prod` has no recorded previous prod | rollback target was never recorded; inspect release evidence |

## Maintenance semantics

`maintenance` is intentionally conservative:

- the hard requirement is that hosted MLflow resolves `breast_cancer_clf@prod`
- the job no longer fails on a slow MLflow UI root `/` response
- if alias resolution succeeds, maintenance is considered healthy enough for hosted operations

This keeps the maintenance check focused on real model/control-plane state instead of a flaky UI-root probe.

## Current state limitations

The hosted jobs path is operational, but there is one state-management detail operators should expect today:

- after a successful `promote`, the promoted version is tagged with `release_status=prod`
- after a later `rollback`, the system can restore the previous `prod` version correctly
- however, the previously promoted version may still remain behind the `candidate` alias while still carrying `release_status=prod`

What this means in practice:

- `promote` with `execution_mode=dry_run` may return exit code `2` even when a `candidate` alias exists
- the JSON payload may show:
  - `candidate_version != current_prod_version`
  - but `candidate_tags_subset.release_status = "prod"`
- this is currently expected and should be read as a **policy-blocked state**, not a broken Cloud Run Job

Operator guidance:

- if you want a promotion path that can succeed again, run `pipeline` to register a fresh candidate version
- treat post-rollback `promote --dry-run` failures as a model-state hygiene issue, not an execution-path failure
- do not manually force promotion around this check; let the pipeline create a new candidate first

This is a known limitation in the current alias/state cleanup semantics after rollback. The execution path is working correctly; the remaining gap is making the post-rollback candidate state less confusing.
