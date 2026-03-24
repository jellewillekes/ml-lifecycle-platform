# CI and CD

The repo uses three workflow groups:

- `CI`: fast developer feedback plus the local nightly E2E lane
- `CD`: hosted image publication, staged deploy, and staged release validation
- `Ops`: manual staging validation, debugging, and recovery workflows

Current lanes:

| Lane | Trigger | Purpose |
| --- | --- | --- |
| `CI / Presubmit and Postsubmit` | pull requests, push to `master`, manual dispatch | presubmit hygiene, lint, typecheck, unit tests, Docker build safety, plus postsubmit integration tests on `master` |
| `CI / Local E2E` | nightly and manual dispatch | dockerized local golden path |
| `CodeQL` | pull requests, push to `master`, weekly, manual dispatch | native GitHub code scanning for source vulnerabilities and coding errors |
| `Gitleaks` | pull requests, push to `master`, weekly, manual dispatch | secret scanning for committed credentials, keys, and tokens |
| `Zizmor` | pull requests, push to `master`, weekly, manual dispatch | GitHub Actions security lint and SARIF upload |
| `Ops / Verify GCP Auth` | push to `master` when auth or staging-foundation paths change, manual dispatch, path-filtered pull requests | GitHub OIDC to GCP WIF verification plus hosted-foundation prerequisite checks |
| `CD / Publish Hosted Images` | reusable workflow call and manual dispatch | builds, smoke-checks, and publishes hosted runtime images to Artifact Registry |
| `CD / Deploy MLflow / Staging` | manual dispatch and reusable workflow call | deploys hosted MLflow from a digest-pinned image and runs authenticated smoke checks |
| `CD / Deploy Serving / Staging` | manual dispatch and reusable workflow call | deploys hosted serving from a digest-pinned image and runs authenticated smoke checks |
| `CD / Deploy Platform Jobs / Staging` | manual dispatch and reusable workflow call | deploys hosted Cloud Run Jobs from a digest-pinned platform image and preserves the current MLflow/serving images |
| `CD / Release Validation / Staging` | push to `master` when hosted-relevant paths change, nightly, manual dispatch | canonical hosted publish-deploy-validate path with explicit staging fixture preparation |
| `Ops / Seed Staging Fixture` | manual dispatch and reusable workflow call | creates a deterministic hosted release fixture from a digest-pinned platform image: rollback-ready `prod` plus a fresh promotable `candidate` |
| `Ops / Run Platform Job / Staging` | manual dispatch and reusable workflow call | executes one deployed Cloud Run Job in staging with an optional args override |
| `Ops / Serving Baseline / Staging` | manual dispatch | runs an advisory k6 baseline against the direct hosted serving staging URL and uploads artifacts |

## Local mapping

- `make check`: format, lint, typecheck, fast tests
- `make test-integration`: integration lane
- `make e2e`: full local golden path with teardown
- `make test-e2e`: same flow, keeps the stack up for debugging

## Default rule set

- pull requests get presubmit CI and security checks, not hosted staging deploys
- `CD / Release Validation / Staging` runs automatically after merges to `master` only when hosted-relevant paths changed
- `CD / Release Validation / Staging` also runs nightly on `master` for staging drift detection
- manual dispatch remains the operator path for release readiness checks, post-incident verification, auth debugging, and targeted staged deploys

## PR checks

Recommended required checks on `master`:

- `PR Title`
- `Hygiene`
- `Python Version`
- `Docker Build`
- `Lint`
- `Typecheck`
- `Unit Tests (pytest)`
- `CodeQL Analyze (Python)`
- `Secret Scan`

`Zizmor` is useful as an advisory security check, but it does not need to block every pull request on day one while older workflows are still being tightened.

Do not require `Postsubmit Integration`, `CI / Local E2E`, or `CD / Release Validation / Staging` on pull requests. They are slower and belong outside the fast review loop.

CodeQL, Gitleaks, and Zizmor also publish findings into GitHub code scanning when the token has permission to upload SARIF.

## Failure debugging

Useful outputs:

- `mypy-output`
- `pytest-output`
- `pytest-integration-output`
- `coverage-xml`
- `docker-logs-<run_id>` from the e2e workflow

## GCP auth verification

The `Ops / Verify GCP Auth` workflow exists to prove the GitHub Actions to GCP trust chain before adding image push or deploy logic.

Required repository variables:

- `GCP_PROJECT_ID`
- `GCP_WIF_PROVIDER`
- `GCP_CI_SERVICE_ACCOUNT`

Populate them from Terraform outputs in `deployments/gcp/terraform/`.

The workflow authenticates with `google-github-actions/auth`, impersonates the CI service account, then verifies the expected project, Artifact Registry repository, buckets, secrets, and WIF provider still exist.

Do not add static service account keys for this repo. The hosted path should stay on OIDC + Workload Identity Federation.

## Hosted image publishing

Hosted image publication lives in:

- `.github/workflows/publish-images.yml`

Trigger model:

- automatic through `CD / Release Validation / Staging`
- manual via `workflow_dispatch` for targeted branch verification
- not part of `CI / Presubmit and Postsubmit`

Published image refs:

- `europe-west1-docker.pkg.dev/fpl-project-jelle/mlp-images/mlflow:<git-sha>`
- `europe-west1-docker.pkg.dev/fpl-project-jelle/mlp-images/platform:<git-sha>`
- `europe-west1-docker.pkg.dev/fpl-project-jelle/mlp-images/serving:<git-sha>`

Contract:

- only immutable Git SHA tags are published
- each image is built once, smoke-tested in the publication workflow, then that same image is pushed
- if the Git SHA images already exist, the workflow reuses the published digests instead of rebuilding
- digests are captured after push and recorded in both the workflow summary and `image-digests.json`
- reusable workflow outputs expose digest-pinned image refs for downstream deploy workflows

Downstream deploy workflows should consume digest-pinned image refs, not tags. Treat tags as discovery aids, Artifact Registry digests as the source of truth, and `image-digests.json` as the operator/debug artifact.

Hosted-relevant auto-trigger paths for `CD / Release Validation / Staging` currently include:

- root runtime build inputs: `Dockerfile`, `pyproject.toml`, `uv.lock`
- staged config: `configs/env/staging.yaml`, `configs/models/**`
- hosted infra and deploy wiring: `deployments/gcp/**`
- hosted workflow definitions
- hosted verification scripts
- application package code under `src/ml_lifecycle_platform/**`

This is intentionally broader than only `serving/`, `pipeline/`, or `registry/`. The hosted images are built from the shared root package and Dockerfile, so a wider trigger is the safer default.

Expected artifact shape:

```json
{
  "project_id": "fpl-project-jelle",
  "repository": "europe-west1-docker.pkg.dev/fpl-project-jelle/mlp-images",
  "git_sha": "<sha>",
  "images": {
    "mlflow": {
      "tag": "<sha>",
      "ref": ".../mlflow:<sha>",
      "digest": "sha256:..."
    },
    "platform": {
      "tag": "<sha>",
      "ref": ".../platform:<sha>",
      "digest": "sha256:..."
    },
    "serving": {
      "tag": "<sha>",
      "ref": ".../serving:<sha>",
      "digest": "sha256:..."
    }
  }
}
```

## Hosted MLflow staging deploy

Hosted MLflow staging deploy lives in:

- `.github/workflows/deploy-mlflow-staging.yml`

Current shape:

- manual `workflow_dispatch`
- consumes a digest-pinned `mlflow_image` from `CD / Publish Hosted Images`
- applies Terraform with that image and preserves the current serving/platform images
- verifies the deployed service with an authenticated MLflow smoke script
- mints the Cloud Run verification token with `google-github-actions/auth`

Bootstrap caveat:

- the first apply for this capability is still manual
- that initial apply grants the CI service account the Cloud Run deploy permissions it needs later

After that bootstrap apply, the workflow is the normal staging deploy path for MLflow through `CD / Deploy MLflow / Staging`.

Operational notes:

- `terraform output -json <name>` returns the raw output value for a named output
- the workflow parses that raw JSON directly
- keep the shell parsing simple; the earlier heredoc-based version was fragile under GitHub Actions

## Hosted serving staging deploy

Hosted serving staging deploy lives in:

- `.github/workflows/deploy-serving-staging.yml`

Current shape:

- manual `workflow_dispatch`
- takes a required digest-pinned `serving_image` input
- preserves the current hosted MLflow image input when applying the shared Terraform root
- applies Terraform with the provided serving image
- verifies the deployed service with authenticated smoke checks
- mints the Cloud Run verification token with `google-github-actions/auth`

Serving smoke covers:

- `/health`
- `/metadata/model`
- `/metadata/schema`
- `/predict`

Important precondition:

- hosted MLflow staging must already contain the active model with a `prod` alias
- image deploy and model release stay separate

If hosted MLflow is live but the alias is missing, run:

- `.github/workflows/seed-staging-model.yml`

## Hosted serving staging baseline

Hosted serving staging baseline lives in:

- `.github/workflows/serving-staging-baseline.yml`

Current shape:

- manual `workflow_dispatch`
- resolves the current `serving_service` Terraform output
- mints an ID token for the direct Cloud Run staging URL
- runs the existing authenticated smoke test as a preflight
- runs a small advisory k6 baseline against `POST /predict?mode=prod`
- uploads machine-readable and markdown artifacts

The baseline is intentionally small in `UP-19`:

- one warmed realistic request scenario
- one light sustained-load scenario
- direct Cloud Run URL only, before `UP-20` adds an edge

## Hosted platform jobs staging

Hosted platform jobs live in:

- `.github/workflows/deploy-platform-jobs-staging.yml`
- `.github/workflows/run-platform-job-staging.yml`

Current shape:

- deploy workflow is manual `workflow_dispatch`
- deploy takes a required digest-pinned `platform_image` input
- deploy preserves the current hosted MLflow and serving image inputs when applying the shared Terraform root
- run executes one named Cloud Run Job in staging

Deployed jobs:

- `maintenance`
- `reproduce`
- `promote`
- `rollback`
- `pipeline`

Recommended first hosted proofs:

- `maintenance`
- `reproduce`
- `promote --dry-run`
- `rollback --dry-run`

Only after those are boring should operators move on to the mutating paths such as `pipeline` or an actual rollback.

For a deterministic full hosted check, use `CD / Release Validation / Staging`. That workflow seeds a rollback-ready `prod` plus a distinct promotable `candidate` before it runs the dry-run checks.

## Deploy workflow troubleshooting

Common staged deploy failures:

- Terraform lock failure on `gs://fpl-tf-state-jelle`
  - cause: missing state bucket bootstrap IAM for `mlp-ci`
- bucket IAM policy read failure on app buckets
  - cause: missing `roles/storage.admin` for `mlp-ci` on the artifacts or data bucket
- `KeyError: 'value'` while reading Terraform output
  - cause: wrong assumption about the shape of `terraform output -json <name>`
- `Invalid account type for --audiences`
  - cause: trying to use `gcloud auth print-identity-token --audiences` under WIF
  - fix: use `google-github-actions/auth` with `token_format: id_token`
