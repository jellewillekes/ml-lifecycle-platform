# GitHub Environments

Last verified: 2026-05-08

This runbook documents the purpose, configuration, and operational procedures for the `staging` and `production` GitHub Environments used in this repository.

## Environments

### staging

- **Protection rule:** none (auto-approve)
- **Purpose:** gates every hosted-deploy workflow so that GCP Workload Identity Federation can enforce environment-scoped SA impersonation
- **Who triggers it:** GitHub Actions automatically when a job declares `environment: staging`

### production

- **Protection rule:** 5-minute wait timer (no required reviewer)
- **Purpose:** skeleton gate for future production deploys (UP-47); no production infrastructure is provisioned yet
- **Who triggers it:** `workflow_dispatch` only, from `master`

## Variables by scope

| Variable | Scope | Set from |
|---|---|---|
| `GCP_PROJECT_ID` | `staging` environment | `terraform output -raw project_id` |
| `GCP_WIF_PROVIDER` | `staging` environment | `terraform output -raw workload_identity_provider_name` |
| `GCP_CI_SERVICE_ACCOUNT` | `staging` environment | `terraform output -raw ci_service_account_email` |

These variables were moved from repository scope to `staging` environment scope so the WIF subject-claim binding can enforce that only environment-scoped jobs can resolve them.

## Service accounts and WIF binding

| SA | Account ID | WIF binding |
|---|---|---|
| `mlp-ci-staging` | `mlp-ci-staging@<project>.iam.gserviceaccount.com` | `principalSet://.../attribute.environment/staging` |
| `mlp-ci-prod` | `mlp-ci-prod@<project>.iam.gserviceaccount.com` | none — reserved, UP-47 |

The WIF provider maps `assertion.environment` → `attribute.environment`. A workflow job must declare `environment: staging` for its OIDC token to carry `environment=staging`; without that claim the `mlp-ci-staging` impersonation is denied.

## Adding or rotating variables

To add a variable to the `staging` environment:

```bash
gh api --method POST \
  /repos/jellewillekes/ml-lifecycle-platform/environments/staging/variables \
  -f name=MY_VAR -f value=my_value
```

To update an existing variable:

```bash
gh api --method PATCH \
  /repos/jellewillekes/ml-lifecycle-platform/environments/staging/variables/MY_VAR \
  -f value=new_value
```

To list current variables:

```bash
gh api /repos/jellewillekes/ml-lifecycle-platform/environments/staging/variables \
  --jq '.variables[].name'
```

## SA or WIF cutover sequence

If you need to rotate the SA key or rebind the WIF provider:

1. Run `terraform apply` to create the new SA / update the WIF binding.
2. Immediately update the GitHub environment variable that changed (step above) — do NOT merge any workflow trigger between these two steps or auth will fail.
3. Run `gh workflow run gcp-auth-verify.yml --ref <branch>` to confirm the new chain.
4. Merge only after the verify workflow passes.

## Which workflows use `environment: staging`

- `publish-images.yml` — `build-and-push` job
- `gcp-auth-verify.yml` — `verify` job
- `deploy-mlflow-staging.yml` — `deploy` job
- `deploy-platform-jobs-staging.yml` — `deploy` job
- `deploy-serving-staging.yml` — `deploy` job
- `run-platform-job-staging.yml` — `run` job
- `seed-staging-model.yml` — `seed` job
- `hosted-golden-path-staging.yml` — all deploy jobs

## Which workflows use `environment: production`

- `deploy-serving-production.yml` — `deploy` job (skeleton, UP-47)
- `deploy-mlflow-production.yml` — `deploy` job (skeleton, UP-47)
- `deploy-platform-jobs-production.yml` — `deploy` job (skeleton, UP-47)
