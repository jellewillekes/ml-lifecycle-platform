# CI

The repo has three lanes:

| Lane | Trigger | Purpose |
| --- | --- | --- |
| `CI` presubmit | pull requests | hygiene, lint, typecheck, unit tests, Docker build safety |
| `CI` postsubmit | push to `master` | same as presubmit plus integration tests |
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

Do not require integration or nightly e2e on pull requests. They are slower and belong outside the fast review loop.

## Failure debugging

Useful outputs:

- `mypy-output`
- `pytest-output`
- `pytest-integration-output`
- `coverage-xml`
- `docker-logs-<run_id>` from the e2e workflow
