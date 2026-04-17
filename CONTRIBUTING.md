# Contributing

Keep changes small, test-backed, and easy to review.

You do not need a GCP account to contribute. The normal contribution path is local-only: clone, `uv sync --dev`, `make check`, `make e2e`. The hosted GCP staging path is a maintainer-only advanced path and is not required for any normal PR.

## Before opening a PR

Match verification to the scope of the change:

- logic in `src/` → `make check`
- touched `docs/` → also `make docs-check`
- touched pipeline, registry, serving, or infra → `make e2e-clean`
- interface changes → `make test-integration`

Do not claim a check was run if it was not run.

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

## Guardrails

- Don't modify files under paths blocked by [`scripts/precommit_block_forbidden_tracked_paths.sh`](scripts/precommit_block_forbidden_tracked_paths.sh).
- Don't bypass precommit with `--no-verify` — fix the underlying issue.
- Don't `git push --force` to `master`.
- Generated or ignored paths (`mlruns/`, `mlartifacts/`, `.env`, `coverage.xml`, `reproduce_*.json`) are not committed.

## Agent tooling

Coding-agent config (`CLAUDE.md`, `Agents.md`, `AGENTS.md`, `.claude/`) is per-developer and gitignored. Do not commit these.

Start with the handbook in [`docs/README.md`](docs/README.md).

Useful references:

- [`docs/runbooks/local-bootstrap.md`](docs/runbooks/local-bootstrap.md)
- [`docs/architecture/overview.md`](docs/architecture/overview.md)
- [`docs/ci.md`](docs/ci.md)
- [`docs/releases.md`](docs/releases.md)
