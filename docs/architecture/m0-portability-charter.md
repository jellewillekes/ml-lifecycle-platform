# M0 Portability Charter

Last verified: 2026-04-18

Status: accepted roadmap scope

## Intent

Keep the local platform stable while introducing only a narrow portability seam.

## In scope

The portability boundary is limited to:

- `ArtifactStore`
- `EventStore`
- `JobRunner`
- `Secrets`

Everything else stays concrete in `M0`.

## Explicitly concrete in M0

- MLflow registry and release control
- promotion policy
- register / promote / rollback / reproduce flows
- serving API and routing behavior
- local Docker Compose operator path

## Invariants

- MLflow remains the source of truth for model versions and aliases
- local Compose remains the default developer and operator path
- alias-based releases stay `candidate -> prod -> champion`
- promotion stays policy-gated
- release evidence stays MLflow-backed
- rollback stays alias mutation, not retraining

## What this avoids

- broad backend abstraction
- a second control plane
- speculative hosted-platform work
- new workflow engines or deployment stacks inside `M0`

Related:

- [`docs/architecture/current-state.md`](./current-state.md)
- [`docs/adrs/ADR-0001-portability-surface.md`](../adrs/ADR-0001-portability-surface.md)
- [`docs/adrs/ADR-0002-mlflow-control-plane.md`](../adrs/ADR-0002-mlflow-control-plane.md)
