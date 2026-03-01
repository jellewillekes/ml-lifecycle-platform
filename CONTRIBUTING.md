# Contributing

## Development setup

This repo uses `uv` for deterministic dependency management.

Common workflows:

- `make check` — format + lint + type + fast unit tests
- `make test` — default fast unit suite
- `make test-coverage` — unit suite with coverage output
- `make test-integration` — local sqlite/filesystem integration tests
- `make e2e` — docker compose end-to-end flow

Pytest test tiers:

- `unit` — hermetic, fast, default on PRs
- `integration` — local component boundaries without secrets
- `e2e` — dockerized golden path; kept separate from pytest by design

## Branching & PRs

- Branch off `master`.
- Keep PRs small and reviewable (prefer <300 LOC).
- Include a rollback plan when behavior changes.

## Commit / PR title conventions

PR titles follow Conventional Commits:

- `feat: ...`
- `fix: ...`
- `docs: ...`
- `chore: ...`
- `refactor: ...`
- `test: ...`
- `ci: ...`

## Presubmit expectations

Before opening a PR:

- `make check`
- If you add integration coverage: `make test-integration`
- If your change touches docker/services: `make e2e` (or explain why not)

## Dependency updates

Dependabot opens weekly PRs for:

- GitHub Actions versions
- Python dependencies at repo root

## Pre-commit hooks (optional)

Install hooks:

```bash
python -m pip install pre-commit
pre-commit install
pre-commit install --hook-type pre-push
```
