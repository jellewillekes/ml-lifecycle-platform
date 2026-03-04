# ADR-0002: MLflow Remains The M0 Control Plane

Status: Accepted

Date: 2026-03-03

## Context

The repo already uses MLflow as the release-control system:

- model versions are registered in MLflow
- aliases `candidate`, `prod`, and `champion` define release state
- promotion policy reads MLflow model-version metadata
- promotion mutates MLflow aliases and tags
- rollback uses MLflow alias metadata such as `previous_prod_version`
- serving resolves `models:/<name>@prod`

That is already reflected in the Makefile workflows, Docker Compose runtime,
integration tests, and current docs.

If `M0` also tried to abstract the release-control plane, the refactor would
get larger and riskier.

## Decision

MLflow remains the registry and release-control source of truth for all of
`M0`.

In `M0`:

- MLflow registered model versions remain the authoritative release records
- MLflow aliases remain the authoritative release pointers
- MLflow model-version tags remain the authoritative promotion and rollback
  metadata
- serving continues to resolve models from MLflow aliases
- policy evaluation continues to read its decision inputs from MLflow metadata

Do not add an alternate registry, release database, or second control plane in
`M0`.

## What stays concrete in M0

These behaviors stay concrete and MLflow-backed in `M0`:

- `candidate -> prod -> champion` alias flow
- promotion dry-run and allow-or-block decisions
- rollback via `previous_prod_version`
- source training run linkage
- dataset fingerprint, config hash, git SHA, and training run metadata checks

This is intentional even while other backend boundaries are narrowed.

## Consequences

- preserves the current local Compose workflow
- keeps release semantics stable during package movement
- avoids splitting source of truth across multiple systems
- lets later `M0` PRs refactor structure without redefining release behavior

Trade-offs:
- registry portability is deferred beyond `M0`
- hosted environments in `M1` and later must still integrate around MLflow
  unless a later ADR changes that direction

## Rejected alternatives

### Introduce a generic registry interface in M0

Rejected because it would widen the refactor and force early abstraction
decisions the repo does not need yet.

### Add a separate release-control database or service in M0

Rejected because it would create two sources of truth during the phase meant to
stabilize local portability.

## Related documents

- [`m0-portability-charter.md`](../architecture/m0-portability-charter.md)
- [`ADR-0001-portability-surface.md`](./ADR-0001-portability-surface.md)
