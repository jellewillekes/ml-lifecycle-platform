# Current State

Last verified: 2026-03-17

## Summary

This repo is a local-first ML platform with MLflow as the tracking, registry, and release-control system.
The local runtime is still the main operator path, but the first hosted GCP staging path now exists.
Hosted MLflow staging is live and verified on Cloud Run, and the serving deploy path is implemented against that hosted MLflow service.

Current lifecycle:

```text
ingest -> featurize -> train -> evaluate -> register -> promote -> serve
```

Serving resolves:

```text
models:/<model_name>@prod
```

## What is implemented

- model-spec driven pipeline with two supported sources:
  - `sklearn_demo`
  - `csv`
- reproducibility contract with:
  - model spec
  - dataset fingerprint
  - config hash
  - git SHA
  - env lock hash
- alias-based release flow:
  - `candidate`
  - `prod`
  - `champion`
- dry-run promotion policy
- explicit release evidence bundles for:
  - `promote`
  - `rollback`
  - `reproduce`
- rollback by alias mutation with manifest-recorded previous prod resolution
- FastAPI serving with:
  - `prod`
  - `candidate`
  - `canary`
  - `shadow`
- Docker Compose local environment
- unit, integration, and dockerized e2e coverage
- Terraform-managed GCP foundation for:
  - Artifact Registry
  - hosted buckets
  - placeholder secrets
  - runtime and CI service accounts
  - GitHub OIDC federation
- Terraform-managed scheduler identity for conservative staged job cadence
- Terraform-managed staging infra for:
  - staging VPC and subnet
  - private service access
  - Cloud SQL Postgres for hosted MLflow metadata
  - MLflow staging secrets and outputs for later deploy workflows
- CI workflows for:
  - GCP auth verification
  - hosted image publication with immutable SHA tags and digest capture
  - hosted MLflow staging deploy by digest with authenticated smoke verification
  - hosted serving staging deploy by digest with authenticated smoke verification
  - hosted platform jobs deploy by digest
- Cloud Scheduler for:
  - daily hosted maintenance cadence
  - paused hosted pipeline cadence placeholder

## Current hosted staging state

- hosted MLflow staging is live and verified
- hosted serving staging deploy path exists and is wired to hosted MLflow
- hosted Cloud Run Jobs for platform actions are live and manually validated
- Cloud Scheduler now triggers conservative maintenance cadence on top of those jobs
- bootstrap IAM for `mlp-ci` bucket access is still partially out-of-band and documented in the runbooks
- current operating target is:
  - local green
  - GCP staging green

## Code layout

- `src/ml_lifecycle_platform/pipeline/`: pipeline steps and orchestration
- `src/ml_lifecycle_platform/registry/`: register, promote, rollback, reproduce
- `src/ml_lifecycle_platform/policy/`: promotion policy
- `src/ml_lifecycle_platform/serving/`: API, router, metrics, smoke test
- `src/ml_lifecycle_platform/runtime/`: runtime profile and bootstrap
- `src/ml_lifecycle_platform/core/`: model specs and protocol definitions
- `src/ml_lifecycle_platform/contracts/`: lineage and repro payloads
- `src/ml_lifecycle_platform/backends/local/`: local adapters

## Defaults

- default runtime profile: [`configs/env/local.yaml`](../../configs/env/local.yaml)
- default model spec: [`configs/models/breast_cancer_demo.yaml`](../../configs/models/breast_cancer_demo.yaml)
- alternate CSV spec: [`configs/models/local_csv_binary_classifier.yaml`](../../configs/models/local_csv_binary_classifier.yaml)

## Release evidence

Registry operations emit a shared evidence bundle:

- `promotion_decision.json`
- `release_manifest.json`
- `rollback_target.json`
- `model_card.md`

MLflow stores the bundle under:

- `reports/releases/<operation>/<model_name>/v<version>/`

The release manifest records:

- source run ID
- dataset fingerprint
- config hash
- git SHA
- current prod version
- previous prod version
- policy outcome

Rollback resolves its target from the promoted version's recorded `release_manifest.json`
and only falls back to `previous_prod_version` for compatibility with older model
versions that do not yet have a manifest.

## Non-goals of the current repo

- no feature store
- no warehouse integration
- no distributed training
- no multi-model serving platform
- no hosted ALB or public edge yet
- no scheduled promotion or rollback path
