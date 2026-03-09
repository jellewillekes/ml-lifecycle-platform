# Releases

This repo uses Release Please.

## Source of truth

- PRs are squash-merged into `master`
- the PR title is the canonical Conventional Commit signal
- Release Please reads merged commits on `master`
- while the project is still on `0.x`, `feat` and `fix` both bump the patch version

## What usually creates a release

- `feat`
- `fix`

These may merge without a release:

- `docs`
- `chore`
- `refactor`
- `test`
- `ci`

That is expected.

## Versioning rule in `0.x`

This repo is configured to increment `0.0.1` style while it stays pre-`1.0`.

Examples:

- `0.5.0` + `fix:` -> `0.5.1`
- `0.5.0` + `feat:` -> `0.5.1`

This is set in [`.release-please-config.json`](../.release-please-config.json) with:

- `"bump-patch-for-minor-pre-major": true`

## Normal flow

1. Open a PR with a valid Conventional Commit title.
2. Merge with squash merge.
3. Release Please updates or opens the release PR.
4. Merging the release PR updates:
   - `pyproject.toml`
   - `CHANGELOG.md`
   - `.release-please-manifest.json`
5. Release Please creates the Git tag and GitHub release.

## If tags drift

If Release Please says a tag already exists, check:

- `pyproject.toml`
- `CHANGELOG.md`
- `.release-please-manifest.json`

Those three files should agree with the published release.
