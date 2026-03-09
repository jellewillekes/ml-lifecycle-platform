# ADR-0001: M0 Portability Surface

Status: Accepted

Date: 2026-03-03

## Context

The repo is entering `M0: Stable portable local platform`.

Today the system is still local-first:

- local Docker Compose is the main runtime path
- MLflow is the registry and release-control source of truth
- release policy, promotion, rollback, and serving behavior already live in
  concrete Python modules and tests

Without a hard boundary, `M0` becomes a broad abstraction exercise.

## Decision

`M0` portability is limited to four backend-facing interfaces:

- `ArtifactStore`
- `EventStore`
- `JobRunner`
- `Secrets`

Only these four interfaces are allowed as implementation boundaries (seams) in
`M0`.

Everything else stays concrete in `M0`, including:

- MLflow registry and release-control behavior
- runtime profile loading from YAML plus env overrides
- model spec parsing and validation
- release policy evaluation
- registry workflows such as register, promote, rollback, and reproduce
- lineage and reproducibility contracts
- serving routing semantics and API behavior

## Interface intent

### `ArtifactStore`

Handles runtime artifacts used by training, evaluation, registration, serving,
and reproducibility.

Examples:

- model artifacts
- evaluation reports
- reproducibility payloads
- mirrored release evidence bundles under the local artifacts directory

Current local implementation:

- file-backed store rooted at `artifacts_dir`

### `EventStore`

Handles structured platform events.

This does not mean adding a workflow engine or a message bus in `M0`.

Current local implementation:

- append-only JSONL file at `event_log_path`

### `JobRunner`

Runs bounded jobs and runtime steps.

This does not mean turning the platform into a full workflow orchestrator in
`M0`.

Current local implementation:

- Python module execution through the configured `python_executable`

### `Secrets`

Provides runtime secrets needed by local or hosted backends.

This is not a full redesign of config handling.

Current local implementation:

- environment variable reads

## Explicit non-interfaces for M0

The following are outside the `M0` portability surface:

- `ModelRegistry`
- `ReleaseControlPlane`
- `ReleasePolicy`
- `ServingRouter`
- `FeatureStore`
- `ExperimentTracker`
- `DeploymentManager`

MLflow and the existing release-control behavior stay concrete by design.

## Consequences

- limits refactor scope
- keeps `M0` reviewable
- preserves the current local golden path while backend boundaries are added
- prevents speculative abstractions from spreading through the repo

Trade-offs:

- some concrete dependencies remain in place in `M0`
- alternate backends outside these four interfaces must wait for a later phase
  or a new ADR

## Related documents

- [`m0-portability-charter.md`](../architecture/m0-portability-charter.md)
- [`ADR-0002-mlflow-control-plane.md`](./ADR-0002-mlflow-control-plane.md)
