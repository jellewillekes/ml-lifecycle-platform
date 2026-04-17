# CI and CD

## Contributor checks

These are the commands you run locally before opening a PR:

- `make check`: format, lint, typecheck, fast tests
- `make docs-check`: handbook link and local doc path validation
- `make test-integration`: integration lane
- `make e2e`: full local golden path with teardown
- `make test-e2e`: same flow, keeps the stack up for debugging

You do not need a GCP account or any hosted credentials for these checks.

## Full workflow matrix

The repo uses three workflow groups:

- `CI`: fast developer feedback plus the local nightly E2E lane
- `CD`: hosted image publication, staged deploy, and staged release validation (maintainer only)
- `Ops`: manual staging validation, debugging, and recovery workflows (maintainer only)

Current lanes:

| Lane | Trigger | Purpose |
| --- | --- | --- |
| `CI / Presubmit and Postsubmit` | pull requests, push to `master`, manual dispatch | presubmit hygiene, lint, docs validation, typecheck, unit tests, Docker build safety, plus postsubmit integration tests on `master` |
| `CI / Infra Validation` | pull requests and push to `master` when GCP Terraform paths change, manual dispatch | non-mutating Terraform fmt, backend-less init, and validate for the hosted staging foundation |
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

Local mirror of `CI / Infra Validation`:

- `make terraform-gcp-fmt` + `make terraform-gcp-validate`

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
- `Docs Validation`
- `Lint`
- `Typecheck`
- `Unit Tests (pytest)`
- `CodeQL Analyze (Python)`
- `Secret Scan`

`Zizmor` is useful as an advisory security check, but it does not need to block every pull request on day one while older workflows are still being tightened.

`CI / Infra Validation` should stay path-filtered. Do not make it a globally required check unless branch protection is updated to support conditional required checks for Terraform changes.

Do not require `Postsubmit Integration`, `CI / Local E2E`, or `CD / Release Validation / Staging` on pull requests. They are slower and belong outside the fast review loop.

CodeQL, Gitleaks, and Zizmor also publish findings into GitHub code scanning when the token has permission to upload SARIF.
