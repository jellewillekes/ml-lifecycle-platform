# Contributing

## Development setup

This repo uses `uv` for deterministic dependency management.

From the repo root:

- `make check` – format + lint + type + tests
- `make e2e` – end-to-end flow (docker compose)

## Branching & PRs

- Create feature branches off `master`.
- Keep PRs small and reviewable (prefer <300 LOC change).
- Use the PR template and include a rollback plan when behavior changes.

## Commit / PR title conventions

We use Conventional Commits for PR titles:

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
- If your change touches docker/services: `make e2e` (or explain why not)

## Dependency updates

Dependabot opens weekly PRs for:
- GitHub Actions versions
- Python dependencies under `/project`

### Pre-commit hooks

Install hooks locally:

```bash
pip install pre-commit
pre-commit install
pre-commit install --hook-type pre-push
```
