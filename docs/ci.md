# CI

The repo has ten lanes:

| Lane | Trigger | Purpose |
| --- | --- | --- |
| `CI` presubmit | pull requests | hygiene, lint, typecheck, unit tests, Docker build safety |
| `CI` postsubmit | push to `master` | same as presubmit plus integration tests |
| `CodeQL` | pull requests, push to `master`, weekly, manual dispatch | native GitHub code scanning for source vulnerabilities and coding errors |
| `Gitleaks` | pull requests, push to `master`, weekly, manual dispatch | secret scanning for committed credentials, keys, and tokens |
| `Zizmor` | pull requests, push to `master`, weekly, manual dispatch | GitHub Actions security lint and SARIF upload |
| `GCP Auth Verify` | push to `master`, manual dispatch | GitHub OIDC to GCP WIF verification plus hosted-foundation prerequisite checks |
| `Publish Images` | called from `CI` on push to `master`, manual dispatch | builds, smoke-checks, and publishes hosted runtime images to Artifact Registry |
| `Deploy MLflow Staging` | manual dispatch | builds the hosted MLflow image, deploys Cloud Run staging by digest, and runs authenticated smoke checks |
| `Deploy Serving Staging` | manual dispatch | resolves a published serving image by SHA, deploys Cloud Run staging by digest, and runs authenticated smoke checks |
| `E2E` | nightly and manual dispatch | dockerized golden path |

## Local mapping

- `make check`: format, lint, typecheck, fast tests
- `make test-integration`: integration lane
- `make e2e`: full local golden path with teardown
- `make test-e2e`: same flow, keeps the stack up for debugging

## PR checks

Recommended required checks on `master`:

- `PR Title`
- `Repo Hygiene`
- `Docker Python Version Check`
- `Docker Build (platform + serving)`
- `Lint (ruff)`
- `Typecheck (mypy)`
- `Unit Tests (pytest)`
- `CodeQL Analyze (Python)`
- `Secret Scan`

`Zizmor` is useful as an advisory security check, but it does not need to block every pull request on day one while older workflows are still being tightened.

Do not require integration or nightly e2e on pull requests. They are slower and belong outside the fast review loop.

CodeQL, Gitleaks, and Zizmor also publish findings into GitHub code scanning when the token has permission to upload SARIF.

## Failure debugging

Useful outputs:

- `mypy-output`
- `pytest-output`
- `pytest-integration-output`
- `coverage-xml`
- `docker-logs-<run_id>` from the e2e workflow

## GCP auth verification

The `GCP Auth Verify` workflow exists to prove the GitHub Actions to GCP trust chain before adding image push or deploy logic.

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

- automatic as the final reusable workflow job in `CI` on push to `master`
- manual via `workflow_dispatch` for branch verification

Published image refs:

- `europe-west1-docker.pkg.dev/fpl-project-jelle/mlp-images/platform:<git-sha>`
- `europe-west1-docker.pkg.dev/fpl-project-jelle/mlp-images/serving:<git-sha>`

Contract:

- only immutable Git SHA tags are published
- each image is built once, smoke-tested locally in CI, then that same image is pushed
- digests are captured after push and recorded in both the workflow summary and `image-digests.json`

Downstream deploy workflows should consume digests, not tags. Treat tags as discovery aids and digests as the deploy contract.

Expected artifact shape:

```json
{
  "project_id": "fpl-project-jelle",
  "repository": "europe-west1-docker.pkg.dev/fpl-project-jelle/mlp-images",
  "git_sha": "<sha>",
  "images": {
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
- builds the hosted MLflow image from `deployments/gcp/mlflow/`
- pushes `mlflow:<git-sha>` to Artifact Registry
- applies Terraform with the resolved image digest
- verifies the deployed service with an authenticated MLflow smoke script

Bootstrap caveat:

- the first apply for this capability is still manual
- that initial apply grants the CI service account the Cloud Run deploy permissions it needs later

After that bootstrap apply, the workflow is the normal staging deploy path for MLflow.

## Hosted serving staging deploy

Hosted serving staging deploy lives in:

- `.github/workflows/deploy-serving-staging.yml`

Current shape:

- manual `workflow_dispatch`
- takes a required `git_sha` input
- resolves the published `serving:<git-sha>` image from Artifact Registry
- preserves the current hosted MLflow image input when applying the shared Terraform root
- applies Terraform with the resolved serving image digest
- verifies the deployed service with authenticated smoke checks

Serving smoke covers:

- `/health`
- `/metadata/model`
- `/metadata/schema`
- `/predict`

Important precondition:

- hosted MLflow staging must already contain the active model with a `prod` alias
- image deploy and model release stay separate
