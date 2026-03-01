# CI Guide

This repository uses three CI lanes with intentionally different scopes:

| Lane | Workflow | Trigger | Scope |
| --- | --- | --- | --- |
| Presubmit | `CI` | pull requests | repo hygiene, lint, typecheck, unit tests |
| Postsubmit | `CI` | push to `master` | repo hygiene, lint, typecheck, unit tests, integration tests |
| Nightly | `E2E` | schedule + manual dispatch | dockerized golden-path verification |

## Required PR Checks

Recommended required status checks for `master` branch protection:

- `PR Title`
- `Repo Hygiene`
- `Lint (ruff)`
- `Typecheck (mypy)`
- `Unit Tests (pytest)`

Do not require `Integration Tests (pytest)` or nightly `E2E` on pull requests. Those are intentionally kept out of the fast presubmit loop.

## Local To CI Mapping

- `make test` or `make test-unit`
  Matches the PR unit-test path.
- `make test-integration`
  Matches the push-to-`master` integration path.
- `make test-e2e`
  Matches the nightly workflow command path and leaves the stack up for log collection.
- `make e2e`
  Local wrapper around the same golden-path steps, with automatic teardown.

## Branch Protection Recommendations

GitHub branch protection settings for `master`:

- Require a pull request before merging.
- Require the five presubmit checks listed above to pass.
- Require branches to be up to date before merging.
- Require conversation resolution before merging.
- Allow squash merge and prefer it as the default merge strategy.
- If possible in repo settings, disable merge strategies that bypass the PR-title-as-canonical-signal model.
- Do not require nightly `E2E` or push-only integration checks for PR mergeability.

## Failure Artifacts

When CI fails, use these uploaded artifacts first:

- `mypy-output`
- `pytest-output`
- `pytest-integration-output`
- `coverage-xml`
- `docker-logs-<run_id>` from the nightly E2E workflow

## Design Notes

- Presubmit is optimized for fast feedback. After the cheap repo-hygiene gate, lint, typecheck, and unit tests run in parallel.
- Integration tests are deterministic but intentionally non-blocking for PR iteration.
- Nightly E2E stays separate because it validates the dockerized golden path rather than the fast developer loop.
- Conventional Commit PR titles are part of the presubmit contract because squash merges make the PR title the canonical commit message on `master`.
