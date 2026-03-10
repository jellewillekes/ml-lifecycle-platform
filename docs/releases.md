# Releases

This repo uses Release Please.

This document covers two separate release concepts:

- GitHub/package releases managed by Release Please
- model release evidence emitted by the registry workflows
- hosted runtime image publication for deploy workflows

For the full identity contract across package releases, image digests, and MLflow aliases, see [`reference/release-contract.md`](./reference/release-contract.md).

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

## Model release evidence

Registry operations also emit ML release evidence into MLflow.

Covered operations:

- `promote`
- `rollback`
- `reproduce`

Each operation writes the same bundle shape:

- `promotion_decision.json`
- `release_manifest.json`
- `rollback_target.json`
- `model_card.md`

Artifact path:

- `reports/releases/<operation>/<model_name>/v<version>/`

The manifest is the operator-facing release record and includes:

- source run ID
- dataset fingerprint
- config hash
- git SHA
- current prod version
- previous prod version
- policy outcome

Rollback behavior:

- rollback resolves the target from the current prod version's recorded `release_manifest.json`
- `previous_prod_version` remains as a compatibility and one-step-undo tag

Local runtime behavior:

- the same bundle is mirrored under the configured local artifacts directory
- a release event may also be appended to the local file-backed `EventStore`

## Hosted runtime images

Hosted runtime images are published by the `Publish Images` workflow described in [`ci.md`](./ci.md).

Current published image contracts:

- `platform`
- `serving`

Deploy workflows should consume image digests from the `image-digests.json` artifact, not mutable tags.

This is separate from model release state:

- image digest selects the runtime container
- MLflow model version and alias select the served model
