# Release Process

This repo uses Release Please for versioning, changelog updates, release PRs,
and Git tags.

## Source Of Truth

- Pull requests are squash-merged into `master`.
- The PR title is the canonical Conventional Commit signal.
- Release Please reads merged commits on `master` and opens a release PR when it
  sees releasable changes since the last tag.

## Valid vs Releasable PR Titles

All PR titles must follow Conventional Commits and pass the `PR Title` check.

Valid title types in this repository include:

- `feat`
- `fix`
- `docs`
- `chore`
- `refactor`
- `test`
- `ci`
- `deps`

Not every valid type is expected to produce a release PR.

In practice:

- `feat` should be expected to create a release PR.
- `fix` should be expected to create a release PR.
- `deps` may create a release PR when the dependency update is modeled as a
  releasable change.
- `docs`, `chore`, `refactor`, `test`, and `ci` may merge cleanly without
  generating any release PR.

That behavior is correct. Release Please is release automation, not
"every-merge automation."

## Normal Flow

1. Open a PR with a valid Conventional Commit title.
2. Merge it with squash merge.
3. On push to `master`, the `Release Please` workflow evaluates merged commits.
4. If releasable changes exist, Release Please opens or updates a release PR.
5. Merging the release PR updates:
   - `pyproject.toml`
   - `CHANGELOG.md`
   - `.release-please-manifest.json`
6. Release Please creates the Git tag and GitHub release.

## Failure Mode: Duplicate Tag

If Release Please reports that a tag already exists:

- do not recreate or delete the tag first
- verify that these three files agree with the published release:
  - `pyproject.toml`
  - `CHANGELOG.md`
  - `.release-please-manifest.json`

If the tag exists and the manifest is stale, update the manifest to the
published version and rerun the workflow.

## Operator Rules

- Keep `pyproject.toml`, `CHANGELOG.md`, and
  `.release-please-manifest.json` aligned.
- Use squash merge consistently.
- Do not assume every merged PR will result in a release PR.
