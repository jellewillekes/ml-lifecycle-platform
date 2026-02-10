# Model Release Platform

[![CI](https://github.com/jellewillekes/model-release-platform/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/jellewillekes/model-release-platform/actions/workflows/ci.yml)
[![E2E](https://github.com/jellewillekes/model-release-platform/actions/workflows/e2e.yml/badge.svg?branch=master)](https://github.com/jellewillekes/model-release-platform/actions/workflows/e2e.yml)

A production-style model release platform that manages the full lifecycle of machine learning models with an emphasis on safety, reproducibility, and operational discipline.

The platform supports:

- Training and evaluation
- Quality gating
- Registry-based releases
- Alias-based promotion
- Progressive delivery (canary / shadow)
- Deterministic rollback
- Online serving
- End-to-end verification

This repository serves as a reference implementation for ML platform engineering patterns.

---

## System Guarantees

The platform enforces the following guarantees by construction:

- Reproducible training
  Every training run is tracked, versioned, and immutable.

- Quality-gated releases
  Models are only registered and promoted when evaluation criteria are met.

- Alias-based release workflow
  Models move through aliases rather than deprecated MLflow stages.

- Deterministic rollback
  Each promotion records the previous production version.

- Artifact lineage
  Every model version links back to its source run and metadata.

- Separation of concerns
  Training and serving are decoupled.

- End-to-end automation
  The full lifecycle is executable via Make targets.

- Verifiable production
  Smoke and E2E tests validate deployments.

---

## Release Model (Alias-Based, No Stages)

MLflow stages are intentionally not used.

### Aliases

candidate — Most recently gated version
prod — Currently served version
champion — Synonym for prod

### Promotion Guardrails

Required tags:

- dataset_fingerprint
- git_sha
- config_hash
- training_run_id

Promotion is blocked if metadata is missing.

### Rollback Metadata

previous_prod_version=<version>

---

## Architecture Overview

Ingest → Featurize → Train → Evaluate → Register → Promote → Serve

Serving:
models:/<name>@prod → FastAPI → Clients

---

## Technology Stack

- MLflow
- PostgreSQL
- MinIO
- FastAPI
- Docker Compose
- Makefile

---

## Repository Structure

.
docker-compose.yml
Makefile
project/
serving/
docs/

---

## Quickstart (Local)

### Prerequisites

- Docker
- Docker Compose
- GNU Make
- Python 3.11+

### Start Infrastructure

make up

MLflow UI: http://localhost:5050
MinIO: http://localhost:9001

### Run Training Pipeline

make run-pipeline

### Promote

make promote

### Serve

make serve

### Verify

make smoke-test

---

## End-to-End Validation

make e2e
make e2e-keep

---

## Rollback

make rollback-prod

---

## Serving Modes

POST /predict?mode=prod|candidate|canary|shadow

CANARY_PCT=10

---

## Local Development

make check
make fix

---

## Governance & Contribution

This repository follows a lightweight governance model:

- Code ownership is defined in `.github/CODEOWNERS`
- All changes go through pull requests
- PRs follow a standard template (What / Why / How / Testing / Risk / Rollback)
- CI checks are required before merge

See:

- CONTRIBUTING.md for development and review guidelines
- CODEOWNERS for ownership and review routing

---

## Reproducibility

Models are reproducible from:

- Dataset fingerprints
- Config hashes
- Git SHA
- Source run ID

---

## Releases & Versioning

This project follows Conventional Commits and automated releases.

- Pull request titles follow `type: description`
- Changelog entries are generated automatically
- Releases are managed via Release Please

See:

- CHANGELOG.md for release history
- .release-please-config.json for release configuration

---

## Operational Workflow

make up
make run-pipeline
make promote
make rollback-prod
make serve
make smoke-test
make e2e

---

## Status

Reference implementation for ML platform engineering patterns.

---

## Security & Licensing

- Security issues: see SECURITY.md
- License: MIT (see LICENSE)
