# ML Lifecycle Platform

[![ci](https://img.shields.io/github/actions/workflow/status/jellewillekes/ml-lifecycle-platform/ci.yml?branch=master&label=ci)](https://github.com/jellewillekes/ml-lifecycle-platform/actions/workflows/ci.yml)
[![e2e](https://img.shields.io/github/actions/workflow/status/jellewillekes/ml-lifecycle-platform/e2e.yml?branch=master&label=e2e)](https://github.com/jellewillekes/ml-lifecycle-platform/actions/workflows/e2e.yml)
[![staging](https://img.shields.io/github/actions/workflow/status/jellewillekes/ml-lifecycle-platform/hosted-golden-path-staging.yml?branch=master&label=staging)](https://github.com/jellewillekes/ml-lifecycle-platform/actions/workflows/hosted-golden-path-staging.yml)
[![coverage](https://codecov.io/gh/jellewillekes/ml-lifecycle-platform/branch/master/graph/badge.svg)](https://codecov.io/gh/jellewillekes/ml-lifecycle-platform/branch/master/graph/badge.svg)
[![release](https://img.shields.io/github/v/release/jellewillekes/ml-lifecycle-platform?label=release)](https://github.com/jellewillekes/ml-lifecycle-platform/releases)
[![python](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fjellewillekes%2Fml-lifecycle-platform%2Fmaster%2Fpyproject.toml&label=python)](pyproject.toml)
[![license](https://img.shields.io/github/license/jellewillekes/ml-lifecycle-platform?label=license)](LICENSE)

_Spec-driven ML lifecycle platform with MLflow as the control plane — local-first, with hosted GCP staging._

An ML platform for training, evaluating, registering, promoting, serving, and reproducing models. MLflow is the control plane. The current implementation is local-first with Terraform-managed GCP foundation and staging infra plus GitHub Actions-produced runtime images ready for hosted rollout.

```text
local path:   train -> register -> promote -> serve
hosted path:  GitHub Actions -> Artifact Registry -> Cloud Run / Jobs -> staging validation
```

[Quick Start](#quick-start) · [Architecture](docs/architecture/overview.md) · [CI/CD](docs/ci.md) · [Hosted Staging Runbook](docs/runbooks/hosted-golden-path.md) · [Contributing](CONTRIBUTING.md)

## Current Status

- local runtime is the default developer and operator path
- hosted staging exists for image publication, staged deploy, and release validation
- the supported first validation path is local `make e2e`
- production rollout and multi-environment promotion remain out of scope

## Handbook Entry Points

- [`docs/README.md`](docs/README.md): handbook index
- [`docs/runbooks/local-bootstrap.md`](docs/runbooks/local-bootstrap.md): fresh-clone local setup and golden path
- [`docs/architecture/overview.md`](docs/architecture/overview.md): system boundaries and current topology
- [`docs/ci.md`](docs/ci.md): contributor checks and CI lane reference

Advanced (hosted — maintainer only):

- [`docs/runbooks/hosted-golden-path.md`](docs/runbooks/hosted-golden-path.md): canonical hosted staging validation path
- [`docs/runbooks/gcp-bootstrap.md`](docs/runbooks/gcp-bootstrap.md): bootstrap and hosted foundation setup

## Starter Files

- [`.env.example`](.env.example)
- [`configs/env/local.yaml`](configs/env/local.yaml)
- [`configs/models/breast_cancer_demo.yaml`](configs/models/breast_cancer_demo.yaml)
- [`configs/models/local_csv_binary_classifier.yaml`](configs/models/local_csv_binary_classifier.yaml)
- [`examples/csv/local_csv_binary_classifier.csv`](examples/csv/local_csv_binary_classifier.csv)

## What it does

- Runs the training pipeline: `ingest -> featurize -> train -> evaluate -> register`
- Registers gated models into MLflow
- Promotes by alias: `candidate -> prod -> champion`
- Writes release evidence for promote, rollback, and reproduce flows
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

Install dependencies:

```bash
uv sync --dev
```

Optional local override file:

```bash
cp .env.example .env
```

Docker Compose reads `.env` automatically. For local Python commands in your current shell, source it explicitly if you want the same overrides:

```bash
set -a; source .env; set +a
```

Fast local checks:

```bash
make check &&
make docs-check &&
make test-all
```

Golden validation path:

```bash
make e2e
```

If you want a clean reset first:

```bash
make e2e-clean
```

Manual local operator flow:

```bash
make up &&
make run-pipeline &&
make policy-check &&
make promote &&
make serve &&
make smoke-test &&
make reproduce ALIAS=prod MODEL_NAME=breast_cancer_clf &&
make down
```

Run the CSV-backed model spec:

```bash
MODEL_SPEC=configs/models/local_csv_binary_classifier.yaml make run-pipeline
uv run mlp --env local registry promote --model-name local_csv_binary_clf
MODEL_NAME=local_csv_binary_clf MLP_MODEL_SPEC_PATH=configs/models/local_csv_binary_classifier.yaml make serve
MODEL_NAME=local_csv_binary_clf MLP_MODEL_SPEC_PATH=configs/models/local_csv_binary_classifier.yaml make smoke-test
make reproduce ALIAS=prod MODEL_NAME=local_csv_binary_clf REPORT=reproduce_csv.json
```

If local host ports are already occupied, override them explicitly:

```bash
MLP_HOST_MLFLOW_PORT=5051 MLP_HOST_MINIO_PORT=9002 MLP_HOST_MINIO_CONSOLE_PORT=9003 MLP_HOST_SERVE_PORT=8001 make up
```

Tear down:

```bash
make down
```

## Common Commands

Quality:

- `make check`
- `make docs-check`
- `make test-unit`
- `make test-integration`
- `make test-all`

Local infra:

- `make up`
- `make down`
- `make logs`
- `make build`

Advanced (hosted infra — maintainer only):

- `make terraform-gcp-fmt`
- `make terraform-gcp-init`
- `make terraform-gcp-plan`
- `make terraform-gcp-apply`
- `make terraform-gcp-validate`

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

## Release Evidence

Promotion, rollback, and reproduce write a machine-readable evidence bundle.

Each bundle includes:

- `promotion_decision.json`
- `release_manifest.json`
- `rollback_target.json`
- `model_card.md`

The bundle records:

- source run ID
- dataset fingerprint
- config hash
- git SHA
- current prod version
- previous prod version
- policy outcome

MLflow stores those artifacts under:

- `reports/releases/<operation>/<model_name>/v<version>/`

The active model version also records stable artifact-path tags:

- `release_reports_path`
- `promotion_decision_path`
- `release_manifest_path`
- `rollback_target_path`
- `model_card_path`

Operational behavior:

- `promote` writes the release evidence bundle to the promoted version's source run
- `rollback` resolves the rollback target from the recorded `release_manifest.json` and falls back to `previous_prod_version` only for compatibility
- `reproduce` still writes `reproduce_report.json` and also writes the same release evidence pattern

When the local runtime profile is active, the same bundle is mirrored under the configured local artifacts directory and a release event is appended to the local file-backed event log when available.

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

The command writes:

- the requested local `reproduce_report.json`
- a release evidence bundle in MLflow under `reports/releases/reproduce/...`

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

examples/
  csv/          public sample CSV data
```

## More Docs

- [`docs/README.md`](docs/README.md)
- [`docs/architecture/overview.md`](docs/architecture/overview.md)
- [`docs/architecture/local-runtime.md`](docs/architecture/local-runtime.md)
- [`docs/runbooks/local-bootstrap.md`](docs/runbooks/local-bootstrap.md)
- [`docs/architecture/current-state.md`](docs/architecture/current-state.md)
- [`docs/ci.md`](docs/ci.md)
- [`docs/releases.md`](docs/releases.md)
- [`CONTRIBUTING.md`](CONTRIBUTING.md)
