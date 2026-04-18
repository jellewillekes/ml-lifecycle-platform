# Overview

Last verified: 2026-04-18

The local path is the contributor default. The hosted GCP staging path is an advanced maintainer-only path — you do not need it to contribute. See [`how-it-works.md`](./how-it-works.md) for the contributor-oriented explanation.

This repo currently has one real local path and one real hosted staging path:

```text
local path:
  ingest -> featurize -> train -> evaluate -> register -> promote -> serve

hosted path today:
  GitHub Actions -> Artifact Registry
  Terraform -> GCP foundation + staging infra
  Cloud Run -> MLflow + serving + platform jobs
  Cloud Scheduler -> conservative maintenance cadence
```

The local path is fully operational. The hosted staging path is operational for M2 staging work:

- GitHub Actions can authenticate to GCP with WIF.
- GitHub Actions can publish immutable runtime images to Artifact Registry.
- Terraform has created the shared staging network, Cloud SQL, and MLflow staging secrets.
- Hosted MLflow and serving are live on Cloud Run.
- Hosted platform jobs are deployed on Cloud Run.
- Cloud Scheduler drives the conservative maintenance cadence.

## Current topology

The `developer shell` section below is the local contributor path. The `GitHub Actions` and `GCP staging infra` sections are the advanced hosted path.

```text
developer shell
  -> mlp CLI / Makefile
  -> runtime profile + model spec
  -> Docker Compose
     -> PostgreSQL
     -> MinIO
     -> MLflow server
     -> pipeline / promote / rollback / serving containers

GitHub Actions
  -> OIDC + Workload Identity Federation
  -> Artifact Registry image publish

GCP staging infra
  -> Artifact Registry (runtime images)
  -> GCS buckets (artifacts, data)
  -> Secret Manager
  -> Cloud SQL Postgres
  -> staging VPC + subnet + private service access
  -> Cloud Run MLflow
  -> Cloud Run serving
  -> Cloud Run platform jobs
  -> Cloud Scheduler
```

## Boundaries that matter

| Boundary | Source of truth | Why it exists |
| --- | --- | --- |
| Runtime wiring | `configs/env/<env>.yaml` plus env overrides | chooses endpoints, paths, compose wiring, model name, and model spec |
| Model behavior | `configs/models/*.yaml` | chooses data source, trainer, evaluation gate, and serving feature contract |
| Registry and release state | MLflow model versions and aliases | tracks `candidate`, `prod`, `champion` and release metadata |
| Hosted infra | `deployments/gcp/terraform/` | keeps resource names, IAM, network, SQL, and secret contracts committed |
| Hosted runtime images | `CD / Publish Hosted Images` workflow artifact and digests | gives deploy workflows immutable container identity |

## End-to-end flow

1. The operator selects a runtime profile with `mlp --env <name>` or the Makefile wrappers.
2. The runtime profile selects MLflow endpoints, model name, model spec, local paths, and Compose settings.
3. The pipeline reads the model spec and produces a training run plus reproducibility artifacts.
4. Registration creates a candidate model version and copies minimum lineage tags from the source run.
5. Promotion evaluates policy from the model spec, mutates MLflow aliases, and writes release evidence.
6. Serving resolves `models:/<model_name>@prod` or `@candidate` from MLflow and validates requests against the active feature contract from the model spec.
7. Hosted rollout deploys the `serving` and `platform` images by digest while still using MLflow aliases for model selection.

## Serving contract

Current endpoints:

- `GET /livez`
- `GET /readyz`
- `GET /health`
- `GET /metrics`
- `GET /metadata/model`
- `GET /metadata/schema`
- `POST /predict?mode=prod|candidate|canary|shadow`

Routing behavior:

- `prod`: always use `@prod`
- `candidate`: always use `@candidate`
- `canary`: deterministic bucket chooses the primary alias and runs the other alias as shadow
- `shadow`: return `@prod` and run `@candidate` best effort

## Release evidence

Registry workflows emit one shared evidence bundle:

- `promotion_decision.json`
- `release_manifest.json`
- `rollback_target.json`
- `model_card.md`

MLflow stores those artifacts under:

- `reports/releases/<operation>/<model_name>/v<version>/`

The release manifest is the operator-facing release record. It captures source run ID, dataset fingerprint, config hash, git SHA, current prod version, previous prod version, and policy outcome.

## What is intentionally not true yet

- no public hosted MLflow or serving edge
- no ALB or custom domain
- no scheduled promotion or rollback
