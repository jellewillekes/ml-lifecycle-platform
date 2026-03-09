# Overview

This repo is a local-first ML platform for one main path:

```text
ingest -> featurize -> train -> evaluate -> register -> promote -> serve
```

It is intentionally narrow in `M0`:

- MLflow is the experiment tracker, model registry, and release-control system.
- Docker Compose is the local operator path.
- Runtime profiles select environment-specific endpoints and local paths.
- Model specs define the data source, trainer, evaluation gate, feature contract, and promotion policy for one model.

## Main pieces

| Area | Source of truth | Purpose |
| --- | --- | --- |
| Runtime wiring | `configs/env/<env>.yaml` | tracking URIs, model name, model spec path, local artifact paths, Compose settings |
| Model behavior | `configs/models/*.yaml` | data source, split, preprocessing, trainer, evaluation gate, feature contract, promotion policy |
| Release state | MLflow registered model versions and aliases | `candidate`, `prod`, `champion` pointers and model-version metadata |
| Release evidence | MLflow artifacts under `reports/releases/...` | promotion decision, release manifest, rollback target, model card |
| Serving contract | model spec feature contract plus serving API | request validation and routing behavior for `prod`, `candidate`, `canary`, `shadow` |

## How it fits together

1. The operator selects a runtime profile with `mlp --env <name>` or the Makefile wrappers.
2. The runtime profile selects the default model name, model spec, tracking URIs, local artifact paths, and Compose file.
3. The pipeline reads the model spec and produces a training run in MLflow plus local artifacts.
4. Registration creates a candidate model version and copies minimum lineage tags from the source training run.
5. Promotion evaluates policy from the model spec, mutates aliases in MLflow, and emits release evidence.
6. Serving resolves `models:/<model_name>@prod` or `@candidate` from MLflow and validates requests against the active feature contract from the model spec.
7. Rollback and reproduce reuse the same release metadata and evidence pattern.

## Serving contract

Current serving endpoints:

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
- `canary`: deterministic bucket chooses primary alias and runs the other alias as shadow
- `shadow`: serve `@prod` and run `@candidate` best effort

## Release evidence

Registry workflows emit the same evidence bundle shape:

- `promotion_decision.json`
- `release_manifest.json`
- `rollback_target.json`
- `model_card.md`

MLflow stores those artifacts under:

- `reports/releases/<operation>/<model_name>/v<version>/`

The release manifest is the operator-facing release record. It captures source run ID, dataset fingerprint, config hash, git SHA, current prod version, previous prod version, and policy outcome.

## What this doc does not cover

- hosted runtime topologies
- multi-environment deployment flows outside local Compose
- workflow orchestration beyond the current Makefile and CLI path
