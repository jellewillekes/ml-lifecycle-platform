# Current State

Last verified: 2026-03-02

## Purpose

This document is a verified snapshot of what is built in the repository today. It
describes the current product shape, package layout, operational model, release
history, and known gaps before the M0 portability refactor begins.

Use this page as the baseline for future architecture work. It describes the system
as it exists now, not the target shape proposed for M0 and beyond.

## Verification basis

This snapshot is based on:

- the live repository layout and source code under `src/ml_lifecycle_platform/`
- release history in [`CHANGELOG.md`](../../CHANGELOG.md)
- package metadata in [`pyproject.toml`](../../pyproject.toml)
- CI, release, and governance files under [`.github/`](../../.github/)
- current maintainer docs in [`docs/`](../)
- local validation during this review:
  - `make test-unit` passed with `27 passed, 3 deselected`
  - `git diff --check` passed
  - the repository already documents a separate dockerized E2E lane in
    [`docs/ci.md`](../ci.md) and [`.github/workflows/e2e.yml`](../../.github/workflows/e2e.yml)

## Executive summary

This repository is a real Python package, not a placeholder scaffold. The package is
published as `ml-lifecycle-platform` in [`pyproject.toml`](../../pyproject.toml),
with implementation code under [`src/ml_lifecycle_platform/`](../../src/ml_lifecycle_platform/)
and tests under [`tests/`](../../tests/).

Today the platform implements:

- alias-based MLflow model lifecycle using `candidate`, `prod`, and `champion`
- end-to-end pipeline orchestration from ingest to registration
- policy-gated promotion with a dry-run mode
- deterministic rollback using `previous_prod_version`
- online serving with `prod`, `candidate`, `canary`, and `shadow` modes
- deterministic request ID propagation and canary bucketing
- reproducibility metadata and reproduce-from-registry support
- Prometheus metrics, health/readiness endpoints, and structured logs
- professional repository governance with CI lanes, PR-title enforcement, release
  automation, and security/legal baselines

The repository is already a serious local-first reference implementation for safe ML
model release operations. It is not yet a hosted production platform, and it does
not yet have the M0 portability split, handbook/runbook set, drift pipeline, or
environment-aware deployment workflow.

## Product and system shape

### Product goal

The repository describes itself in [`README.md`](../../README.md) as a
"production-style model release platform" focused on safety, reproducibility, and
operational discipline.

### Current package layout

The current architecture is organized around these package areas:

- [`src/ml_lifecycle_platform/pipeline/`](../../src/ml_lifecycle_platform/pipeline/)
  for ingest, featurize, train, evaluate, and orchestration
- [`src/ml_lifecycle_platform/policy/`](../../src/ml_lifecycle_platform/policy/)
  for release-policy evaluation
- [`src/ml_lifecycle_platform/registry/`](../../src/ml_lifecycle_platform/registry/)
  for registration, promotion, rollback, and reproduction
- [`src/ml_lifecycle_platform/serving/`](../../src/ml_lifecycle_platform/serving/)
  for the FastAPI inference service, routing, metrics, and smoke testing
- [`src/ml_lifecycle_platform/contracts/`](../../src/ml_lifecycle_platform/contracts/)
  and [`src/ml_lifecycle_platform/common/`](../../src/ml_lifecycle_platform/common/)
  for shared contracts, constants, config helpers, and MLflow utilities

### Local operational model

The canonical local system today is a Docker Compose stack plus Makefile command
wrappers. The stack includes:

- MLflow
- PostgreSQL
- MinIO
- FastAPI
- Docker Compose
- `make` targets for operator workflows

The key local entrypoints are defined in [`Makefile`](../../Makefile) and backed by
[`docker-compose.yml`](../../docker-compose.yml).

### Runtime flow

The current lifecycle is:

```text
Ingest -> Featurize -> Train -> Evaluate -> Register -> Promote -> Serve
```

The current serving path resolves production models from MLflow aliases:

```text
models:/<name>@prod -> FastAPI -> clients
```

## Verified implementation history

### v0.1.0 foundation

The historical `0.1.0` section in [`CHANGELOG.md`](../../CHANGELOG.md) captures the
initial platform foundation:

- alias-based release flow
- progressive delivery
- reproducibility and lineage
- health/metrics/structured logging
- CI and repository governance

### v0.2.0 release policy

`0.2.0` added the release-policy module and dry-run promotion guardrails. That work
is reflected in the changelog and in the current implementation under
[`src/ml_lifecycle_platform/policy/release_policy.py`](../../src/ml_lifecycle_platform/policy/release_policy.py)
and [`src/ml_lifecycle_platform/registry/promote.py`](../../src/ml_lifecycle_platform/registry/promote.py).

### v0.2.1 release automation fix

`0.2.1` fixed Release Please root configuration and aligned release metadata.

### v0.3.0 reproducibility maturity

Current package metadata reports `0.3.0`, and the `0.3.0` release adds
reproduce-from-registry support in
[`src/ml_lifecycle_platform/registry/reproduce.py`](../../src/ml_lifecycle_platform/registry/reproduce.py).

## Verified capabilities today

### Alias-based release lifecycle

Implemented now:

- registration assigns `candidate`
- promotion sets `prod` and `champion`
- the platform does not rely on MLflow stages

Primary evidence:

- [`README.md`](../../README.md)
- [`src/ml_lifecycle_platform/common/constants.py`](../../src/ml_lifecycle_platform/common/constants.py)
- [`src/ml_lifecycle_platform/registry/register.py`](../../src/ml_lifecycle_platform/registry/register.py)
- [`src/ml_lifecycle_platform/registry/promote.py`](../../src/ml_lifecycle_platform/registry/promote.py)

### End-to-end orchestration

Implemented now:

- orchestrated execution of `ingest -> featurize -> train -> evaluate -> register`
- propagation of training-run identity into evaluation and registration

Primary evidence:

- [`src/ml_lifecycle_platform/pipeline/orchestrate.py`](../../src/ml_lifecycle_platform/pipeline/orchestrate.py)
- [`Makefile`](../../Makefile)

### Progressive delivery in serving

Implemented now:

- `prod`, `candidate`, `canary`, and `shadow` routing modes
- deterministic canary routing
- shadow execution plus divergence metrics

Primary evidence:

- [`src/ml_lifecycle_platform/serving/router.py`](../../src/ml_lifecycle_platform/serving/router.py)
- [`src/ml_lifecycle_platform/serving/app.py`](../../src/ml_lifecycle_platform/serving/app.py)
- [`src/ml_lifecycle_platform/serving/metrics.py`](../../src/ml_lifecycle_platform/serving/metrics.py)

### Reproducibility and lineage

Implemented now:

- dataset fingerprint capture
- config hash, git SHA, training run ID, deterministic seed, and repro contract
- registration-time propagation of lineage metadata onto model versions
- reproduction of a registered model from its source run with parity checks

Primary evidence:

- [`src/ml_lifecycle_platform/contracts/dataset_fingerprint.py`](../../src/ml_lifecycle_platform/contracts/dataset_fingerprint.py)
- [`src/ml_lifecycle_platform/contracts/repro_contract.py`](../../src/ml_lifecycle_platform/contracts/repro_contract.py)
- [`src/ml_lifecycle_platform/pipeline/train.py`](../../src/ml_lifecycle_platform/pipeline/train.py)
- [`src/ml_lifecycle_platform/registry/reproduce.py`](../../src/ml_lifecycle_platform/registry/reproduce.py)

### Promotion policy and rollback safety

Implemented now:

- pure, non-mutating dry-run policy evaluation
- blocking on missing metadata, invalid release status, missing gate pass, and no-op
  promotion
- rollback to the previous production version through alias mutation

Primary evidence:

- [`src/ml_lifecycle_platform/policy/release_policy.py`](../../src/ml_lifecycle_platform/policy/release_policy.py)
- [`src/ml_lifecycle_platform/registry/promote.py`](../../src/ml_lifecycle_platform/registry/promote.py)
- [`src/ml_lifecycle_platform/registry/rollback.py`](../../src/ml_lifecycle_platform/registry/rollback.py)

### Serving operability

Implemented now:

- `/livez`, `/readyz`, `/health`, and `/metrics`
- request ID propagation
- structured logs
- Prometheus counters and latency histograms

Primary evidence:

- [`src/ml_lifecycle_platform/serving/app.py`](../../src/ml_lifecycle_platform/serving/app.py)
- [`src/ml_lifecycle_platform/serving/metrics.py`](../../src/ml_lifecycle_platform/serving/metrics.py)
- [`tests/unit/serving/tests/`](../../tests/unit/serving/tests/)

### Governance and release workflow

Implemented now:

- pull-request template
- CODEOWNERS
- contributing and security guides
- PR-title enforcement using Conventional Commits
- Release Please automation
- separated CI lanes for presubmit, postsubmit, and nightly E2E

Primary evidence:

- [`.github/PULL_REQUEST_TEMPLATE.md`](../../.github/PULL_REQUEST_TEMPLATE.md)
- [`.github/CODEOWNERS`](../../.github/CODEOWNERS)
- [`CONTRIBUTING.md`](../../CONTRIBUTING.md)
- [`SECURITY.md`](../../SECURITY.md)
- [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)
- [`.github/workflows/pr-title.yml`](../../.github/workflows/pr-title.yml)
- [`.github/workflows/release-please.yml`](../../.github/workflows/release-please.yml)
- [`docs/ci.md`](../ci.md)
- [`docs/releases.md`](../releases.md)

## Current CI and release model

The repository uses an intentionally split CI model:

- pull requests run repo hygiene, lint, typecheck, and unit tests
- pushes to `master` add integration tests
- nightly or manual execution runs the dockerized E2E lane

Release management is Conventional-Commit-driven and handled through Release Please.
The release source of truth is the squash-merged PR history on `master`, not an
ad hoc manual changelog process.

## What is not done yet

The biggest missing areas today are:

- the M0 portability structure: `core/`, `backends/`, `runtime/`, `cli/`,
  checked-in runtime profiles, and a central composition root
- current-state architecture/runbook documentation beyond CI and release process
- versioned serving input contracts and schema discovery endpoints
- config-driven model specs and config-driven policy thresholds
- explicit release-report bundles for promote, rollback, and reproduce
- drift detection, replay loops, and delayed-feedback capture
- hosted GCP deployment, Workload Identity Federation, and GitHub Environment
  approval gates
- multi-model platformization beyond the current example pipeline

## Known cleanup items

These are not platform gaps, but they are real repository follow-ups:

- [`.github/dependabot.yml`](../../.github/dependabot.yml) still contains stale
  directories such as `/project` and `/serving`
- repository health files are not complete for a public OSS workflow yet; there is
  no `CODE_OF_CONDUCT.md`, issue-template set, or maintainer/governance doc
- some comments still reflect older layout assumptions and should be scrubbed during
  the OSS workflow cleanup

## Relationship to the roadmap

This page documents the baseline that future M0 work must preserve while changing
structure. The next architecture documents should answer a different question:

- this page: what exists today
- M0 charter and ADRs: what shape the repository is allowed to move toward

Contributors should use this page to understand the current system before reading
future portability or cloud-roadmap documents.
