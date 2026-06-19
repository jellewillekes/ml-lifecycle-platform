# Architecture

Last verified: 2026-04-18

The platform runs one logical contract across two environments. The local path is the contributor default. The hosted GCP staging path is an advanced maintainer-only path — you do not need it to contribute.

## System shape

```text
local path:
  ingest -> validate_data -> featurize -> train -> evaluate -> validate_model -> register -> promote -> serve

hosted path:
  GitHub Actions -> Artifact Registry
  Terraform -> GCP foundation + staging infra
  Cloud Run -> MLflow + serving + platform jobs
  Cloud Scheduler -> conservative maintenance cadence
```

MLflow is the control plane. It owns runs, model versions, aliases, and release evidence. Container deploys choose runtime bits; MLflow aliases choose model state.

## Local path

```text
developer shell
  -> Makefile / CLI
  -> Docker Compose
  -> PostgreSQL + MinIO + MLflow
  -> pipeline / promote / rollback / reproduce / serving
```

Runtime profile: `configs/env/local.yaml`. Model spec: `configs/models/breast_cancer_demo.yaml`.

Start here: [`docs/runbooks/local-bootstrap.md`](runbooks/local-bootstrap.md).

## Hosted staging path (advanced — maintainer only)

### What is live in staging

- Cloud Run MLflow staging
- Cloud Run serving staging
- Cloud Run jobs: `mlp-maintenance-staging`, `mlp-reproduce-staging`, `mlp-promote-staging`, `mlp-rollback-staging`, `mlp-pipeline-staging`
- Cloud Scheduler: `mlp-maintenance-staging-schedule` (enabled), `mlp-pipeline-staging-schedule` (paused)
- Self-hosted observability: OTel Collector + VictoriaMetrics + Tempo + Grafana OSS on a single GCE VM inside the staging VPC

### Fixed decisions

These decisions should not be reopened without a concrete blocker:

- MLflow remains the control plane.
- Deploy workloads by image digest, not mutable tag.
- Reuse `gs://fpl-project-jelle-mlp-artifacts` for hosted MLflow artifacts.
- Use Cloud SQL Postgres with private IP for hosted MLflow metadata.
- Use direct Cloud Run URLs plus IAM auth for staging before adding an external load balancer.
- Reuse `mlp-runtime@<project>.iam.gserviceaccount.com` for hosted workloads unless tighter separation is clearly needed.
- Fixed names: Cloud SQL `mlp-mlflow-staging`, MLflow service `mlp-mlflow-staging`, serving `mlp-serving-staging`.

### Manual bootstrap exceptions

Most deploy state is Terraform-managed, but a few permissions are intentionally manual bootstrap steps:

- Terraform state bucket IAM for `mlp-ci`
- `roles/cloudscheduler.admin` for `mlp-ci`

Documented in [`docs/reference/gcp-resources.md`](reference/gcp-resources.md).

Start here: [`docs/runbooks/hosted-golden-path.md`](runbooks/hosted-golden-path.md).

## Boundaries that matter

| Boundary | Source of truth | Why it exists |
| --- | --- | --- |
| Runtime wiring | `configs/env/<env>.yaml` plus env overrides | chooses endpoints, paths, compose wiring, model name, and model spec |
| Model behavior | `configs/models/*.yaml` | chooses data source, trainer, evaluation gate, and serving feature contract |
| Registry and release state | MLflow model versions and aliases | tracks `candidate`, `prod`, `champion` and release metadata |
| Hosted infra | `deployments/gcp/terraform/` | keeps resource names, IAM, network, SQL, and secret contracts committed |
| Hosted runtime images | CD / Publish Hosted Images workflow artifact | gives deploy workflows immutable container identity |

## Serving contract

Endpoints:

- `GET /livez`
- `GET /readyz`
- `GET /health`
- `GET /metrics`
- `GET /metadata/model`
- `GET /metadata/schema`
- `POST /predict?mode=prod|candidate|canary|shadow`

Release aliases:

- `candidate` — freshly trained model
- `prod` — promoted model
- `champion` — long-standing winner

Routing behavior:

- `prod`: always use `@prod`
- `candidate`: always use `@candidate`
- `canary`: deterministic bucket split between the two
- `shadow`: return `@prod`, run `@candidate` best-effort in parallel

## Release evidence

Promotion, rollback, and reproduce emit a shared evidence bundle:

- `promotion_decision.json`
- `release_manifest.json`
- `rollback_target.json`
- `model_card.md`

MLflow stores the bundle under:

- `reports/releases/<operation>/<model_name>/v<version>/`

The release manifest records source run ID, dataset fingerprint, config hash, git SHA, current prod version, previous prod version, and policy outcome.

## Code layout

Core OSS surface (local golden path):

- `src/ml_lifecycle_platform/pipeline/` — pipeline steps and orchestration
- `src/ml_lifecycle_platform/registry/` — register, promote, rollback, reproduce
- `src/ml_lifecycle_platform/policy/` — promotion policy
- `src/ml_lifecycle_platform/serving/` — API, router, metrics, smoke test
- `src/ml_lifecycle_platform/runtime/` — runtime profile and bootstrap
- `src/ml_lifecycle_platform/core/` — model specs and protocol definitions
- `src/ml_lifecycle_platform/contracts/` — lineage and reproducibility payloads
- `src/ml_lifecycle_platform/backends/local/` — local adapters
- `src/ml_lifecycle_platform/common/` — shared string constants

Advanced hosted surface (maintainer only):

- `src/ml_lifecycle_platform/hosted_ci/` — helpers for GitHub Actions workflows

## Known limitations

**Post-rollback candidate state** — after rollback, the previous `prod` is restored correctly, but the old promoted version may still sit behind `candidate` carrying `release_status=prod`. A later `promote --dry-run` correctly blocks even when a `candidate` alias exists. This is a model-state hygiene limitation, not a broken job path.

**Scheduler is intentionally conservative** — no scheduled promote, no scheduled rollback, no automatic promotion to `prod`.

## Non-goals

- no feature store
- no warehouse integration
- no distributed training
- no multi-model serving platform
- no hosted ALB or public edge yet
- no production rollout
- no scheduled release-control actions

## Further reading

- [`docs/reference/local-runtime.md`](reference/local-runtime.md) — runtime profiles, model spec shape, env var overrides
- [`docs/reference/configuration.md`](reference/configuration.md) — runtime env vars, serving settings, hosted secrets
- [`docs/adrs/ADR-0001-portability-surface.md`](adrs/ADR-0001-portability-surface.md) — portability boundary decisions
- [`docs/adrs/ADR-0002-mlflow-control-plane.md`](adrs/ADR-0002-mlflow-control-plane.md) — MLflow as control plane
- [`docs/diagrams/`](diagrams/) — architecture SVGs (context, container, deployment views)
