# ML Lifecycle Platform

[![CI](https://github.com/jellewillekes/ml-lifecycle-platform/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/jellewillekes/ml-lifecycle-platform/actions/workflows/ci.yml)
[![E2E](https://github.com/jellewillekes/ml-lifecycle-platform/actions/workflows/e2e.yml/badge.svg?event=schedule)](https://github.com/jellewillekes/ml-lifecycle-platform/actions/workflows/e2e.yml)
[![Coverage](https://codecov.io/gh/jellewillekes/ml-lifecycle-platform/branch/master/graph/badge.svg)](https://codecov.io/gh/jellewillekes/ml-lifecycle-platform)

A production ML platform for safe, reproducible model promotion and serving, composed of modular, industry-standard infra services.

The platform supports:

- Training and evaluation
- Quality gating
- Registry-based releases
- Alias-based promotion
- Progressive delivery (canary / shadow)
- Deterministic rollback
- Online serving
- End-to-end verification

This repo is a reference implementation for ML platform engineering patterns, mainly for personal use.

See `docs/architecture/current-state.md` for the verified baseline.
See `docs/architecture/m0-portability-charter.md` for the frozen `M0` target.

---

## System Guarantees

The platform guarantees the following properties:

- Reproducible runs: every training run logs dataset fingerprint, config hash,
  and git SHA.
- Quality-gated promotion: `candidate -> prod` only happens after evaluation
  passes and required metadata is present.
- Alias-first registry model: deployment is driven by MLflow aliases
  (`candidate`, `prod`, `champion`), not stages.
- Deterministic rollback: each promotion records `previous_prod_version`.
  Rollback is alias mutation.
- Artifact lineage: every model version links back to its source training run.
- Control-plane / data-plane separation: training, registry policy, and serving
  are separate.
- End-to-end verifiability: CI and E2E validate training, policy checks,
  promotion, serving, and rollback.

---

## Release Model (Alias-Based)

MLflow stages are not used.

### Aliases

| Alias     | Description                    |
|-----------|--------------------------------|
| candidate | Most recent gated model         |
| prod      | Current production model        |
| champion  | Synonym for prod                |

### Promotion Guardrails

Required metadata:

- dataset_fingerprint
- git_sha
- config_hash
- training_run_id

Promotion is blocked if any tag is missing.

### Policy Check (Non-Mutating)

Promotion supports dry-run mode.

- checks required metadata
- checks evaluation gate status
- returns a structured JSON decision report
- performs no registry writes

Example:

```bash
make policy-check
```

The output contract:

```json
{
  "allowed": true|false,
  "context": {},
  "errors": [],
  "warnings": []
}
```

CI and E2E rely on this output.

### Rollback Metadata

```
previous_prod_version=<version>
```
---

## Architecture Overview

### Control Plane

- Make targets
- CI/CD workflows
- Promotion gates
- Metadata validation

### Data Plane

- Training artifacts (MinIO)
- Model registry (MLflow)
- Evaluation reports
- Prediction logs

### Serving Plane

- FastAPI inference service
- Alias resolver
- Canary router
- Shadow traffic duplicator

### Lifecycle

```
Ingest → Featurize → Train → Evaluate → Register → Promote → Serve
```

Serving path:

```
models:/<name>@prod → FastAPI → Clients
```

### Execution Flow

```
Train/Evaluate (`src/ml_lifecycle_platform.pipeline`)
        |
        v
MLflow Registry (PostgreSQL backend)
        |
        |-- aliases: candidate / prod / champion
        |
        v
Serving (FastAPI)
        |
        |-- prod (default)
        |-- candidate (optional)
        |-- canary (bucketed routing)
        |-- shadow (mirrored inference)
        |
        v
Clients
```

---

## Technology Stack

- MLflow
- PostgreSQL
- MinIO
- FastAPI
- Docker Compose
- Makefile

---

## Interface Contracts

### Registry Contract
- Deployment is alias-driven.
- Serving resolves `models:/<name>@prod` by default.

### Promotion Contract
- Required tags: `dataset_fingerprint`, `git_sha`, `config_hash`, `training_run_id`
- Dry-run mode outputs `{allowed, context, errors, warnings}`

### Rollback Contract
- Rollback mutates aliases only.
- No rebuild or retraining required.

---

## Repository Structure

```bash
.
├── src/ml_lifecycle_platform/
│   ├── common/        # Shared config, constants, MLflow helpers
│   ├── contracts/     # Metadata and lineage contracts
│   ├── pipeline/      # Ingest, featurize, train, evaluate, orchestrate
│   ├── policy/        # Promotion policy checks
│   ├── registry/      # Register, promote, rollback
│   └── serving/       # FastAPI inference service
├── tests/             # Unit and integration tests
├── scripts/           # Tooling and automation
├── docker/            # Container assets
├── mlflow_server/     # MLflow tracking server image
└── .github/           # CI governance
```

---

## Local Execution

```bash
make down && make clean && make up && make run-pipeline && make policy-check && make promote && make serve && make smoke-test && make e2e
```

Service endpoints:

- MLflow UI: http://localhost:5050
- MinIO Console: http://localhost:9001
- Serving API: http://localhost:8000

---

## End-to-End Validation

```bash
make e2e
make e2e-keep
```

---

## Rollback

```bash
make rollback-prod
```

---

## Serving Modes

### Endpoint

```bash
POST /predict?mode=prod|candidate|canary|shadow
```

### Routing Modes

| Mode      | Behavior                                                                 |
|-----------|--------------------------------------------------------------------------|
| prod      | Resolves `@prod` (default production alias)                              |
| candidate | Resolves `@candidate` if available; otherwise returns 503                |
| canary    | Deterministic traffic split between prod and candidate                   |
| shadow    | Executes candidate in parallel; response derived from prod               |

Canary routing is deterministic per request.

---

## Failure Handling

### Promotion Failures

- Missing required metadata → promotion blocked
- Evaluation gate failed → candidate rejected

### Serving Failures

- Alias resolution failure → HTTP 503
- Registry connectivity issues → HTTP 503

### Recovery

Rollback is explicit:

```bash
make rollback-prod
```

---

## Local Development

```bash
make check
make fix
make test-coverage
```

### Testing

- `unit`: fast tests, this is the default local pytest path
- `integration`: local multi-component tests using sqlite-backed MLflow or filesystem boundaries
- `e2e`: Docker-based golden-path verification via `make e2e`

Common commands:

```bash
make test
make test-unit
make test-integration
make e2e
```

---

## Reproducibility

Models are reproducible from:

- Dataset fingerprints
- Config hashes
- Git SHA
- Source run ID

---

## Releases & Versioning

This project follows Conventional Commits.

- Automated changelogs
- Semantic versioning
- Release Please automation

Release Please does not create a new release for every merged PR. For the
release model and failure-handling notes, see `docs/releases.md`.

---

## Security & Licensing

- Security issues: see `SECURITY.md`
- License: MIT in `LICENSE`
