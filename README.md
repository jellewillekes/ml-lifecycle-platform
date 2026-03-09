# ML Lifecycle Platform

[![CI](https://github.com/jellewillekes/ml-lifecycle-platform/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/jellewillekes/ml-lifecycle-platform/actions/workflows/ci.yml)
[![E2E](https://github.com/jellewillekes/ml-lifecycle-platform/actions/workflows/e2e.yml/badge.svg?event=schedule)](https://github.com/jellewillekes/ml-lifecycle-platform/actions/workflows/e2e.yml)
[![Coverage](https://codecov.io/gh/jellewillekes/ml-lifecycle-platform/branch/master/graph/badge.svg)](https://codecov.io/gh/jellewillekes/ml-lifecycle-platform/branch/master/graph/badge.svg)

A production ML platform for training, evaluating, registering, promoting, serving, and reproducing models with MLflow as the control plane. The first implementation is local-first, afterwards connectors to `GCP` and `AWS` will be integraded.

## What it does

- Runs a simple pipeline: `ingest -> featurize -> train -> evaluate -> register`
- Registers gated models into MLflow
- Promotes by alias: `candidate -> prod -> champion`
- Serves `prod`, `candidate`, `canary`, and `shadow`
- Captures reproducibility metadata: dataset fingerprint, config hash, git SHA, env lock hash
- Rebuilds a registered model from its source training run

## Model Specs

The pipeline is model-spec driven.

Included specs:

- [`configs/models/breast_cancer_demo.yaml`](configs/models/breast_cancer_demo.yaml)
- [`configs/models/local_csv_binary_classifier.yaml`](configs/models/local_csv_binary_classifier.yaml)

Supported sources today:

- `source.kind = sklearn_demo`
- `source.kind = csv`

Default local spec:

- [`configs/env/local.yaml`](configs/env/local.yaml) points to the demo spec

## Quick Start

Requirements:

- Python `>=3.11.7`
- `uv`
- Docker with Compose

Fast local checks:

```bash
make check
```

Bring up local infra:

```bash
make up
```

Run the default demo flow:

```bash
make run-pipeline &&
make policy-check &&
make promote &&
make serve &&
make smoke-test &&
make reproduce ALIAS=prod MODEL_NAME=breast_cancer_clf
```

Run the CSV-backed model spec:

```bash
MODEL_SPEC=configs/models/local_csv_binary_classifier.yaml make run-pipeline
uv run mlp --env local registry promote --model-name local_csv_binary_clf
MODEL_NAME=local_csv_binary_clf make serve
MODEL_NAME=local_csv_binary_clf make smoke-test
make reproduce ALIAS=prod MODEL_NAME=local_csv_binary_clf REPORT=reproduce_csv.json
```

Tear down:

```bash
make down
```

## Common Commands

Quality:

- `make check`
- `make test-unit`
- `make test-integration`
- `make test-all`

Infra:

- `make up`
- `make down`
- `make logs`
- `make build`

Registry and serving:

- `make policy-check`
- `make promote`
- `make rollback-prod`
- `make serve`
- `make smoke-test`
- `make reproduce ALIAS=prod MODEL_NAME=<name>`

Golden path:

- `make e2e`
- `make e2e-keep`

## Serving

Serving API:

- `GET /livez`
- `GET /readyz`
- `GET /health`
- `GET /metrics`
- `POST /predict?mode=prod|candidate|canary|shadow`

Release aliases:

- `candidate`
- `prod`
- `champion`

Routing behavior:

- `prod`: always serves `@prod`
- `candidate`: serves `@candidate`
- `canary`: deterministic split between `prod` and `candidate`
- `shadow`: returns `prod`, runs the other alias best-effort in parallel

## Reproducibility

Every training run records enough state to verify a rebuild:

- model spec
- dataset fingerprint
- config hash
- git SHA
- `uv.lock` hash
- probe inputs and expected probabilities

Reproduce from the registry:

```bash
uv run mlp --env local registry reproduce --model-name breast_cancer_clf --alias prod --report-path reproduce_report.json --format json
```

## Repository Layout

```text
src/ml_lifecycle_platform/
  backends/     local runtime adapters
  cli/          operator CLI
  common/       config, constants, MLflow helpers
  contracts/    reproducibility and lineage payloads
  core/         model specs and protocol definitions
  pipeline/     ingest, featurize, train, evaluate, orchestrate
  policy/       promotion gate logic
  registry/     register, promote, rollback, reproduce
  runtime/      runtime context/bootstrap
  serving/      FastAPI app, router, metrics, smoke test

configs/
  env/          runtime profiles
  models/       model specs
  model_data/   local sample CSV data
```

## More Docs

- [`docs/architecture/current-state.md`](docs/architecture/current-state.md)
- [`docs/ci.md`](docs/ci.md)
- [`docs/releases.md`](docs/releases.md)
- [`CONTRIBUTING.md`](CONTRIBUTING.md)
