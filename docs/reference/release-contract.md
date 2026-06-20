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

- Artifact Registry digests produced by `CD / Publish Hosted Images`

Purpose:

- identify the exact container bits used for hosted deploys

Current published image names:

- `mlflow`
- `platform`
- `serving`

Current registry:

- `europe-west1-docker.pkg.dev/fpl-project-jelle/mlp-images`

Current publish rule:

- publish immutable Git SHA tags only
- capture remote digests after push
- downstream deploys should use digest-pinned image refs, not tags
- reusable workflow outputs are the normal transport path
- `image-digests.json` is the human/debug artifact, not the primary deploy contract

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

The deploy contract is already fixed:

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

## Drift baseline

Every promotion computes a `DriftBaseline` from the model's training split
(`repro/inputs/train.csv` on the source run) and attaches it to release
evidence. The `release_manifest.json` carries a `baseline_ref` pointing at the
`drift_baseline.json` artifact under the same release-evidence root.

The baseline is the statistical fingerprint of the data the model was trained
on, so a production release can be compared against live traffic later:

- per column: `count`, `null_rate`, `mean`, `std`, `min`, `max`, plus a quantile
  grid (p0…p100 by 5)
- the quantile grid lets batch drift (UP-32) reconstruct a step-CDF for a KS
  test; `mean`/`std` drive a cheaper mean/std delta
- **stat-test choice for v1: KS + mean/std delta** per feature
- a missing or unreadable training split degrades to no baseline rather than
  failing the promotion

Inspect it with `mlp registry show-baseline --model-version <v>` (or `--alias`).
A Pandera schema validates the per-column summary table before it is written.

## Event-plane contracts

The event plane is the durable record of what the platform predicted and what
actually happened. Drift, replay, and feedback all read from it. Two row-level
Pydantic contracts define it; both carry ns-precision timestamps.

These use a **bare-major envelope version** (`schema_version: "1"`), not the
`name/vN` scheme the artifact contracts above use. The event plane is consumed
by streaming and batch readers (BigQuery, DuckDB) where registry-style
versioning does not apply.

### Schema evolution

- additive, optional fields → no version bump
- any breaking change (rename, type change, new required field) → bump the
  major (`"1"` → `"2"`)
- a reader refuses an unknown major rather than guessing

### PredictionEvent

`contracts/prediction_event.py` — one prediction, with latency attribution.

| Field | Type | Stability |
| --- | --- | --- |
| `schema_version` | `Literal["1"]` | stable; bumped only on a breaking change |
| `event_id` | `UUID` | stable; the sink idempotency key |
| `corr_id` | `str` | stable; join key to the labels table |
| `event_time_ns` | `int` (ns, INT64) | stable |
| `ingest_time_ns` | `int` (ns, INT64) | stable |
| `model_ref` | `ModelRef` | stable; carries its own `model_ref/v1` version |
| `features` | `dict[str, JsonValue]` | may columnar-break at tick volume (UP-29a) |
| `prediction` | `JsonValue` | stable |
| `latency_ns` | `int` (ns, INT64) | stable |
| `envelope` | `EventEnvelope` | stable: `service`, `env`, `run_id`, `git_sha` |

### LabelEvent and the labels table

`contracts/label_event.py` — a delayed realized label plus the Pandera schema
for the batch `labels` table that feedback capture (UP-34) joins against
prediction events.

- **join key**: `corr_id` (prediction events ⋈ labels); required and non-null
  on both sides
- **freshness SLO**: a label is expected within its source's natural lag; a
  join is considered complete once that window has elapsed
- **late-arrival policy**: labels arriving after the window are still ingested
  and recompute the affected realized-performance rows; they never mutate the
  original prediction event

Realized-label sources for the three M4c models:

| Model | Realized label | Lag |
| --- | --- | --- |
| Binance BTC 1m | next-bar return sign at bar close | ~1 bar |
| Coinbase BTC 1m | next-bar return sign at bar close | ~1 bar |
| Open-Meteo temp 1h | ERA5 realized temperature | ~2 days |

## What deploy workflows should consume

Today and going forward:

- consume Artifact Registry image refs pinned by digest for container identity
- use reusable workflow outputs as the normal transport path between publish and deploy workflows
- keep `image-digests.json` as the operator/debug artifact
- consume MLflow aliases and model versions for model identity
- do not deploy from mutable tags
- do not infer model rollout from package release versions

Companion docs:

- [`../ci.md`](../ci.md)
- [`../releases.md`](../releases.md)
- [`../adrs/ADR-0002-mlflow-control-plane.md`](../adrs/ADR-0002-mlflow-control-plane.md)
