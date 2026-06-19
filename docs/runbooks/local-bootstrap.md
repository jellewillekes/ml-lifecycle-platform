# Local Bootstrap

Use this runbook for a fresh clone and the local golden path.

## Prerequisites

- Python `>=3.11.7`
- `uv`
- Docker with Compose
- a clean shell with Docker running

## Install dependencies

From the repo root:

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

Optional fast validation before starting infra:

```bash
make docs-check
make check
```

## Fastest end-to-end validation

For a clean confidence check, use the single command path first:

```bash
make e2e
```

Use the manual flow below when you want to inspect each step.

## Start local infrastructure

```bash
make up
```

Expected local endpoints:

- MLflow UI: `http://localhost:5050`
- MinIO Console: `http://localhost:9001`

If startup fails:

- run `make logs`
- verify Docker is running
- verify ports `5050`, `9000`, and `9001` are available

## Run the default golden path

Run these commands in order:

```bash
make run-pipeline
make policy-check
make promote
make serve
make smoke-test
make reproduce ALIAS=prod MODEL_NAME=breast_cancer_clf
```

What each command does:

- `make run-pipeline`: build images, run pipeline, register candidate
- `make policy-check`: run promotion dry-run and fail fast if policy blocks
- `make promote`: move candidate to `prod` and `champion`
- `make serve`: start the serving API
- `make smoke-test`: call the serving path against the promoted model
- `make reproduce ...`: rebuild the promoted model from its source training run

## Verify outputs

After the golden path:

- MLflow should contain a training run and a registered model version
- the registered model should resolve `@prod`
- serving should answer `GET /health`
- `reproduce_report.json` should exist in the repo root unless you override `REPORT=...`
- release evidence should exist in MLflow under `reports/releases/...`

Quick checks:

```bash
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/metadata/model
```

If `localhost:8000` is already in use on your machine:

```bash
MLP_HOST_SERVE_PORT=8001 make serve
curl -fsS http://localhost:8001/health
```

`make e2e` falls back to an ephemeral host port automatically when `8000` is busy because the smoke test talks to `http://serving:8000` inside Compose.

If you want a deterministic clean slate before the golden path:

```bash
make e2e-clean
```

That is better than making `make e2e` destructive by default.

## Run the CSV-backed spec

```bash
MODEL_SPEC=configs/models/local_csv_binary_classifier.yaml make run-pipeline
uv run mlp --env local registry promote --model-name local_csv_binary_clf
MODEL_NAME=local_csv_binary_clf MLP_MODEL_SPEC_PATH=configs/models/local_csv_binary_classifier.yaml make serve
MODEL_NAME=local_csv_binary_clf MLP_MODEL_SPEC_PATH=configs/models/local_csv_binary_classifier.yaml make smoke-test
make reproduce ALIAS=prod MODEL_NAME=local_csv_binary_clf REPORT=reproduce_csv.json
```

Keep model name and model spec aligned when you override one of them.

Starter CSV location:

- [`examples/csv/local_csv_binary_classifier.csv`](../../examples/csv/local_csv_binary_classifier.csv)

## Train multiple models

The pipeline is spec-driven, so one command trains every spec in `configs/models/`:

```bash
uv run mlp --env local pipeline run --all
uv run mlp --env local pipeline run --model binance_btc_1m
```

Each model is isolated in its own MLflow experiment (keyed on `model_name`), and
`--all` continues past a single model's failure, then exits non-zero listing the
models that failed. Serving stays one model per container; each instance exposes
`/predict/<model_name>` and rejects any other name with a 404.

## Tear down

```bash
make down
```

This removes local Compose state and volumes.
