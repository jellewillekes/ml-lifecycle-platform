# CI and CD

## Contributor checks

Run these locally before opening a PR. You do not need a GCP account or any
hosted credentials.

Match the check to the scope of your change:

| Change scope | Run |
| --- | --- |
| logic in `src/` | `make check` |
| touched `docs/` | also `make docs-check` |
| pipeline, registry, serving, or infra | `make e2e-clean` |
| interface changes | `make test-integration` |

Available local commands:

- `make check`: format, lint, typecheck, fast tests
- `make docs-check`: handbook link and local doc path validation
- `make test-integration`: integration lane
- `make e2e`: full local golden path with teardown
- `make test-e2e`: same flow, keeps the stack up for debugging

That is the full contributor surface. The rest of this page is maintainer
reference for the hosted CD and Ops workflows. You can stop here for a normal
local PR.

---

## Maintainer reference (hosted workflows)

The remaining sections describe the hosted GCP workflows, the CI/CD cadence
contract, branch-protection expectations, and the trigger policy. They are not
required reading for normal contribution.

### Workflow classification

Every workflow in this repo belongs to exactly one of three lanes. The workflow
`name:` field carries the lane prefix so the Actions sidebar makes intent
obvious at a glance.

- `CI`: fast developer feedback plus the local nightly E2E lane. Runs on every
  pull request and every push to `master`. No GCP credentials required.
- `CD`: hosted image publication, staged deploy, and staged release validation.
  Maintainer only. Runs against staging when hosted-relevant paths change.
- `Ops`: manual staging validation, debugging, and recovery workflows.
  Maintainer only. Never auto-triggered on pull requests or pushes.

Security-scanning workflows (`CodeQL`, `Gitleaks`, `Zizmor`) and repo-hygiene
workflows (`PR Title`, `Release Please`) keep short standalone names because
they target the repository itself, not a runtime environment.

### Full workflow matrix

| Workflow | Trigger | Purpose |
| --- | --- | --- |
| `CI / Presubmit and Postsubmit` | pull requests, push to `master`, manual dispatch | presubmit hygiene, lint, docs validation, typecheck, unit tests, Docker build safety, plus postsubmit integration tests on `master` |
| `CI / Infra Validation` | path-filtered pull requests and push to `master`, manual dispatch | non-mutating Terraform fmt, backend-less init, and validate for the hosted staging foundation |
| `CI / Local E2E` | nightly and manual dispatch | dockerized local golden path |
| `CodeQL` | pull requests, push to `master`, weekly, manual dispatch | native GitHub code scanning for source vulnerabilities and coding errors |
| `Gitleaks` | pull requests, push to `master`, weekly, manual dispatch | secret scanning for committed credentials, keys, and tokens |
| `Zizmor` | pull requests, push to `master`, weekly, manual dispatch | GitHub Actions security lint and SARIF upload |
| `PR Title` | pull requests | Conventional Commits PR title check |
| `Release Please` | push to `master`, manual dispatch | release-please PR maintenance |
| `Ops / Verify GCP Auth` | path-filtered pull requests, path-filtered push to `master`, manual dispatch | GitHub OIDC to GCP WIF verification plus hosted-foundation prerequisite checks |
| `CD / Publish Hosted Images` | reusable workflow call and manual dispatch | builds, smoke-checks, and publishes hosted runtime images to Artifact Registry |
| `CD / Deploy MLflow / Staging` | manual dispatch and reusable workflow call | deploys hosted MLflow from a digest-pinned image and runs authenticated smoke checks |
| `CD / Deploy Serving / Staging` | manual dispatch and reusable workflow call | deploys hosted serving from a digest-pinned image and runs authenticated smoke checks |
| `CD / Deploy Platform Jobs / Staging` | manual dispatch and reusable workflow call | deploys hosted Cloud Run Jobs from a digest-pinned platform image and preserves the current MLflow/serving images |
| `CD / Release Validation / Staging` | path-filtered push to `master`, nightly, manual dispatch | canonical hosted publish-deploy-validate path with explicit staging fixture preparation |
| `Ops / Seed Staging Fixture` | manual dispatch and reusable workflow call | creates a deterministic hosted release fixture from a digest-pinned platform image: rollback-ready `prod` plus a fresh promotable `candidate` |
| `Ops / Run Platform Job / Staging` | manual dispatch and reusable workflow call | executes one deployed Cloud Run Job in staging with an optional args override |
| `Ops / Serving Baseline / Staging` | manual dispatch | runs an advisory k6 baseline against the direct hosted serving staging URL and uploads artifacts |

Local mirror of `CI / Infra Validation`:

- `make terraform-gcp-fmt` + `make terraform-gcp-validate`

### Trigger policy and cadence

The hosted golden path takes ~21 minutes end-to-end. That is acceptable for CD
and release validation, and too slow for default PR CI. The trigger policy
below keeps fast feedback fast and pushes hosted validation to the points
where it actually adds signal.

**On pull requests.** Run only fast, account-free checks:

- `CI / Presubmit and Postsubmit` (lint, typecheck, docs, unit tests, Docker
  build safety)
- `CI / Infra Validation` when Terraform paths change
- `CodeQL`, `Gitleaks`, `Zizmor` for security
- `PR Title` for Conventional Commits
- `Ops / Verify GCP Auth` when auth-relevant paths change

Do not require or auto-trigger any `CD / *` workflow on pull requests.

**On push to `master`.** `CD / Release Validation / Staging` auto-triggers
only when hosted-relevant paths change. The current path filter covers:

- `.github/workflows/hosted-golden-path-staging.yml` and the reusable hosted
  workflows it calls
- `Dockerfile`, `pyproject.toml`, `uv.lock`
- `configs/env/staging.yaml`, `configs/models/**`
- `deployments/gcp/**`
- hosted validation scripts (`scripts/resolve_cloud_run_service_contract.py`,
  `scripts/retry_terraform_gcp_init.sh`, `scripts/verify_*.py`)
- `src/ml_lifecycle_platform/**`

Docs-only changes, local-only workflow changes, and pure unit-test refactors
do not auto-trigger hosted validation.

**On a schedule.** `CD / Release Validation / Staging` runs nightly on
`master` at 02:00 UTC for drift detection. It catches staging drift, broken
workload identity or auth, expired or missing secrets, Artifact Registry or
deploy wiring regressions, and Cloud Run validation regressions before an
operator needs them.

`CI / Local E2E` runs nightly at 04:00 UTC as an independent local-path check
with no cloud dependency.

**On manual dispatch.** Keep manual triggers available for:

- release readiness checks before cutting a release
- post-incident verification after recovering staging
- IAM, WIF, or secret rotation validation
- targeted staged deploys (`CD / Deploy MLflow|Serving|Platform Jobs / Staging`)
- operator recovery (`Ops / Seed Staging Fixture`, `Ops / Run Platform Job`)
- performance baselining (`Ops / Serving Baseline / Staging`)

### Operator cadence expectations

- the nightly run is the primary drift-detection signal; a red nightly run is
  actionable before the next merge window
- merging a hosted-relevant change to `master` triggers one staging validation
  automatically; operators do not need to run it manually afterwards
- one manual `CD / Release Validation / Staging` run before a release is
  enough; the same workflow also runs nightly so a recent green run is
  usually already available
- `Ops / *` workflows are never required to be green on `master`; they are
  operator tools, not release gates

### PR checks

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

Branch protection matches on job names, not workflow names, so the lane
prefix added to workflow `name:` fields does not affect required-check
configuration.

`Zizmor` is useful as an advisory security check, but it does not need to
block every pull request on day one while older workflows are still being
tightened.

`CI / Infra Validation` should stay path-filtered. Do not make it a globally
required check unless branch protection is updated to support conditional
required checks for Terraform changes.

Do not require `Postsubmit Integration`, `CI / Local E2E`, or
`CD / Release Validation / Staging` on pull requests. They are slower and
belong outside the fast review loop.

CodeQL, Gitleaks, and Zizmor also publish findings into GitHub code scanning
when the token has permission to upload SARIF.

### Security hygiene contract

The contributor-facing rules for secrets, credentials, and workflow-log
exposure live in [`reference/security-hygiene.md`](./reference/security-hygiene.md).
That page is the minimum bar every PR should preserve; the security-scanning
workflows listed above are the enforcement layer.
