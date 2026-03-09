# Contributing

Keep changes small, test-backed, and easy to review.

## Before opening a PR

Run what applies:

- `make check`
- `make docs-check` if you changed docs
- `make test-integration`
- `make e2e` if you changed Docker, serving, promotion flow, or the local operator path

## PR expectations

- Branch from `master`
- Keep the PR focused
- Link the issue when there is one
- Include rollback notes for behavior changes
- Use squash merge

## PR title

PR titles must use Conventional Commits:

- `feat: ...`
- `fix: ...`
- `docs: ...`
- `refactor: ...`
- `test: ...`
- `ci: ...`
- `chore: ...`
- `deps: ...`

The PR title becomes the squash commit message and feeds Release Please.

## Local workflows

- `make check`
- `make docs-check`
- `make test-unit`
- `make test-integration`
- `make e2e`

## Notes

- Prefer deleting code over adding new layers.
- Preserve current behavior unless there is a clear bug.
- If you touch the model lifecycle, validate the demo spec path at minimum.

Start with the handbook in [`docs/README.md`](docs/README.md).

Useful references:

- [`docs/runbooks/local-bootstrap.md`](docs/runbooks/local-bootstrap.md)
- [`docs/architecture/overview.md`](docs/architecture/overview.md)
- [`docs/ci.md`](docs/ci.md)
- [`docs/releases.md`](docs/releases.md)
