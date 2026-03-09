# CI

The repo has six lanes:

| Lane | Trigger | Purpose |
| --- | --- | --- |
| `CI` presubmit | pull requests | hygiene, lint, typecheck, unit tests, Docker build safety |
| `CI` postsubmit | push to `master` | same as presubmit plus integration tests |
| `CodeQL` | pull requests, push to `master`, weekly, manual dispatch | native GitHub code scanning for source vulnerabilities and coding errors |
| `Gitleaks` | pull requests, push to `master`, weekly, manual dispatch | secret scanning for committed credentials, keys, and tokens |
| `Zizmor` | pull requests, push to `master`, weekly, manual dispatch | GitHub Actions security lint and SARIF upload |
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
