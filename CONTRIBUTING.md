# Contributing

## Development setup

This repo uses `uv` for dependency management.

For CI lanes, required checks, and branch-protection guidance, see `docs/ci.md`.
For release behavior and Release Please expectations, see `docs/releases.md`.

Common workflows:

- `make check` — format + lint + type + fast unit tests
- `make test` — default fast unit suite
- `make test-coverage` — unit suite with coverage output
- `make test-integration` — local sqlite/filesystem integration tests
- `make e2e` — docker compose end-to-end flow

Pytest test tiers:

- `unit` — fast, default on PRs
- `integration` — local component boundaries without secrets
- `e2e` — dockerized golden path, kept separate from pytest by design

## Branching & PRs

- Branch off `master`.
- Keep PRs small and reviewable (prefer <300 LOC).
- Include a rollback plan when behavior changes.
- Use squash merges for pull requests.
- Treat the PR title as the canonical release-note and changelog signal.

## Commit / PR title conventions

This repository enforces Conventional Commit PR titles. With squash merges, the PR
title becomes the canonical commit message on `master`, which is what Release
Please uses to build release notes.

Allowed PR title types:

- `feat: ...`
- `fix: ...`
- `docs: ...`
- `chore: ...`
- `refactor: ...`
- `test: ...`
- `ci: ...`
- `deps: ...`

Commit messages inside the PR do not need separate enforcement as long as the
repository uses squash merge consistently.

Not every valid PR title type produces a release PR. In normal operation, expect
release PRs for releasable changes such as `feat` and `fix`, while `docs`,
`chore`, `refactor`, `test`, and `ci` may merge without any new release.

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
