# CI Guide

This repo uses three CI lanes with different scopes:

| Lane | Workflow | Trigger | Scope |
| --- | --- | --- | --- |
| Presubmit | `CI` | pull requests | repo hygiene, docker runtime version guard, docker build (platform + serving), lint, typecheck, unit tests |
| Postsubmit | `CI` | push to `master` | repo hygiene, docker runtime version guard, docker build (platform + serving), lint, typecheck, unit tests, integration tests |
| Nightly | `E2E` | schedule + manual dispatch | golden-path verification |

## Required PR Checks

Recommended required status checks for `master` branch protection:

- `PR Title` (conventional)
- `Repo Hygiene`
- `Docker Runtime Python Guard`
- `Docker Build (platform + serving)`
- `Lint (ruff)`
- `Typecheck (mypy)`
- `Unit Tests (pytest)`

Do not require `Integration Tests (pytest)` or nightly `E2E` on pull requests.
Those stay out of the fast presubmit loop, we keep them in merge loop.

## Local to CI Mapping

- `make test` or `make test-unit`
  Matches the PR unit-test path.
- `docker build --target platform .` and `docker build --target serving .`
  Match the PR docker-build safety checks.
- `make test-integration`
  Matches the push-to-`master` integration path.
- `make test-e2e`
  Matches the nightly workflow command path and leaves the stack up for logs.
- `make e2e`
  Local wrapper around the same golden-path steps, with automatic teardown.

## Branch Protection Recommendations

GitHub branch protection settings for `master`:

- Require a pull request before merging.
- Require the five presubmit checks listed above to pass.
- Require branches to be up to date before merging.
- Require conversation resolution before merging.
- Allow squash merge and prefer it as the default merge strategy.
- If possible, disable merge strategies that bypass the
  PR-title that do not follow Conventional Commits 
- Do not require nightly `E2E` or push-only integration checks for PR mergeability.

## Failure Artifacts

When CI fails, use these uploaded artifacts first:

- `mypy-output`
- `pytest-output`
- `pytest-integration-output`
- `coverage-xml`
- `docker-logs-<run_id>` from the nightly E2E workflow

## Design Notes

- Presubmit is for fast feedback. After repo hygiene passes, docker runtime
  guard, docker builds, lint, typecheck, and unit tests run in parallel where
  possible.
- Docker build checks are intentionally in presubmit so base-image and
  dependency-resolution breakage is detected before merge rather than waiting
  for nightly E2E.
- Integration tests are deterministic but non-blocking for commiting to a PR.
- Nightly E2E is separate because it validates the golden path (dockerized), not in the fast developer loop.
- Conventional Commit PR titles matter because squash merges make the PR title
  the canonical commit message on `master` and are added to `CHANGELOG.md`.
