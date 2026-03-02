# Contributing

## Development setup

This repo uses `uv` for dependency management.

For CI lanes, required checks, and branch-protection guidance, see `docs/ci.md`.
For release behavior and Release Please expectations, see `docs/releases.md`.
For the verified baseline system shape before the M0 refactor, see
`docs/architecture/current-state.md`.

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

## Issues, milestones, and roadmap work

- Use GitHub Issues for planned work, bugs, feature requests, and documentation
  follow-ups.
- Link implementation PRs to issues when possible using `Closes #<issue>` or
  `Related to #<issue>`.
- Group roadmap work with milestones such as `M0`, `M1`, and later phases instead
  of encoding long-term status only in docs.
- Keep issue scope crisp. One issue should usually map to one reviewable PR or one
  small sequence of tightly related PRs.
- Prefer public issue discussion for design clarification unless the topic is
  security-sensitive.

## Contribution expectations

- Start with a GitHub issue for non-trivial changes before opening a large PR.
- Keep changes single-purpose. Avoid mixing refactor, infra, and behavior changes in
  one PR unless there is no safe separation.
- If you change user-visible behavior, include tests and a clear rollback note.
- If you touch docker/services or the local golden path, explain how you validated
  `make e2e` or why it was not run.
- If your change is part of a roadmap work package, reference the issue and preserve
  the documented scope and non-goals.

## Maintainer response model

- This project is currently maintained on a best-effort basis by a small maintainer
  set.
- Issues and PRs may not receive an immediate response.
- Small, well-scoped, well-tested contributions are significantly easier to review
  and merge than large speculative changes.

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
- Dockerfiles in supported repository paths

## Pre-commit hooks (optional)

Install hooks:

```bash
python -m pip install pre-commit
pre-commit install
pre-commit install --hook-type pre-push
