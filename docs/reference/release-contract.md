# Release Contract

This repo has three different release identities.

Do not collapse them into one thing.

## 1. GitHub/package release

Source of truth:

- squash-merged commit history on `master`
- Release Please

Purpose:

- version the Python package and changelog

Current mechanism:

- PR title carries the Conventional Commit signal
- Release Please opens or updates the release PR
- merge of the release PR creates the Git tag and GitHub release

## 2. Model release

Source of truth:

- MLflow model versions and aliases
- release evidence stored in MLflow artifacts

Purpose:

- decide which model version is `candidate`, `prod`, or `champion`

Current aliases:

- `candidate`
- `prod`
- `champion`

Current evidence bundle:

- `promotion_decision.json`
- `release_manifest.json`
- `rollback_target.json`
- `model_card.md`

Artifact path:

- `reports/releases/<operation>/<model_name>/v<version>/`

## 3. Runtime image release

Source of truth:

- `Publish Images` workflow
- `image-digests.json` artifact

Purpose:

- identify the exact container bits used for hosted deploys

Current published image names:

- `platform`
- `serving`

Current registry:

- `europe-west1-docker.pkg.dev/fpl-project-jelle/mlp-images`

Current publish rule:

- publish immutable Git SHA tags only
- capture remote digests after push
- downstream deploys should use digests, not tags

## Current contract

These identities are separate on purpose:

| Identity | Chooses | Current source of truth |
| --- | --- | --- |
| package release | versioned repo/package state | Release Please |
| image release | container filesystem and runtime bits | Artifact Registry digest |
| model release | served model version and alias state | MLflow alias and version |

This is the key rule for M2:

- image deploy chooses the runtime container
- MLflow alias chooses the served model

Do not encode model rollout into image tagging.

## Rollback rules

### Package rollback

- handled at the Git/tag/release level
- unrelated to model alias rollback

### Model rollback

- `rollback` resolves the target from the current prod version's `release_manifest.json`
- `previous_prod_version` remains a compatibility and one-step-undo field

### Hosted runtime rollback

Not deployed yet, but the contract is already fixed:

- rollback by image digest, not tag
- model rollback remains an MLflow alias operation

If a hosted deploy fails because of container behavior, roll back the image digest.
If a hosted deploy fails because of a bad promoted model, roll back the MLflow alias.

Those are different incidents.

## Reproducibility contract

Each training run records:

- model spec
- dataset fingerprint
- config hash
- git SHA
- `uv.lock` hash
- probe inputs and expected probabilities

That data answers a different question again:

- "can we rebuild this model version?"

It is not the same as:

- "which image is deployed?"
- "which model alias is live?"

## What deploy workflows should consume

Today and going forward:

- consume `image-digests.json` for container identity
- consume MLflow aliases and model versions for model identity
- do not deploy from mutable tags
- do not infer model rollout from package release versions

Companion docs:

- [`../ci.md`](../ci.md)
- [`../releases.md`](../releases.md)
- [`../adrs/ADR-0002-mlflow-control-plane.md`](../adrs/ADR-0002-mlflow-control-plane.md)
