# Local Runtime

This document covers the concrete local runtime path shipped in `M0`.

## Runtime profile resolution

The CLI loads one runtime profile from:

- `configs/env/<env>.yaml` when you run `mlp --env <env> ...`
- `MLP_PROFILE_PATH` when you want an explicit profile file

Default local path:

- [`configs/env/local.yaml`](../../configs/env/local.yaml)

Public starter files:

- [`.env.example`](../../.env.example)
- [`configs/models/breast_cancer_demo.yaml`](../../configs/models/breast_cancer_demo.yaml)
- [`configs/models/local_csv_binary_classifier.yaml`](../../configs/models/local_csv_binary_classifier.yaml)
- [`examples/csv/local_csv_binary_classifier.csv`](../../examples/csv/local_csv_binary_classifier.csv)

The selected profile becomes:

- process environment for local Python commands
- environment passed into Docker Compose services
- default model name and model spec path
- local artifact and event-log paths

## Runtime profile fields that matter

| Field | Used by | Why it matters |
| --- | --- | --- |
| `tracking_uri` | local Python commands | points MLflow tracking to the active backend |
| `registry_uri` | local Python commands | points model registry reads and writes |
| `experiment_name` | pipeline and register flow | decides where local runs land |
| `model_name` | register, promote, rollback, serve | default registered model name |
| `model_spec_path` | pipeline and serving | selects data source, training config, feature contract, and promotion policy |
| `data_dir` | pipeline steps | local working data path |
| `artifacts_dir` | pipeline and release evidence mirror | local runtime artifact root |
| `event_log_path` | local `EventStore` | append-only JSONL event path |
| `compose_file` | `mlp infra`, pipeline, serving, e2e | Docker Compose file used by operator commands |
| `compose_tracking_uri` | containers | MLflow endpoint inside Compose |
| `compose_registry_uri` | containers | registry endpoint inside Compose |
| `compose_serve_url` | smoke and local defaults | serving URL inside Compose |

## Supported env var overrides

Operators can override the shipped profile with environment variables.

Common overrides:

- `MLP_ENV`
- `MLP_PROFILE_PATH`
- `MLFLOW_TRACKING_URI`
- `MLFLOW_REGISTRY_URI`
- `EXPERIMENT_NAME`
- `MODEL_NAME`
- `MLP_MODEL_SPEC_PATH`
- `LOG_LEVEL`
- `MLP_DATA_DIR`
- `MLP_ARTIFACTS_DIR`
- `MLP_EVENT_LOG_PATH`

Less common local-runtime overrides:

- `MLP_COMPOSE_FILE`
- `MLP_COMPOSE_TRACKING_URI`
- `MLP_COMPOSE_REGISTRY_URI`
- `MLP_COMPOSE_SERVE_URL`
- `MLFLOW_S3_ENDPOINT_URL`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

## Model spec shape

The runtime profile chooses one model spec. The model spec is the behavior contract for one model.

Important sections:

| Section | Purpose |
| --- | --- |
| `source` | chooses `sklearn_demo` or `csv` input |
| `split` | test split and deterministic seed |
| `preprocessor` | preprocessing kind |
| `trainer` | trainer type and hyperparameters |
| `evaluation` | reported metrics and promotion gate threshold |
| `feature_contract` | serving request schema |
| `policy` | promotion policy requirements |

Concrete examples:

- [`configs/models/breast_cancer_demo.yaml`](../../configs/models/breast_cancer_demo.yaml)
- [`configs/models/local_csv_binary_classifier.yaml`](../../configs/models/local_csv_binary_classifier.yaml)
- [`examples/csv/local_csv_binary_classifier.csv`](../../examples/csv/local_csv_binary_classifier.csv)

## Serving contract in local runtime

Serving reads two things:

- the registered model selected by MLflow alias
- the feature contract from the active model spec

That means:

- changing `MODEL_NAME` without also changing `MLP_MODEL_SPEC_PATH` can break request validation
- the local serving path should keep model name and model spec aligned
- the runbooks use the same model name and model spec together when they override defaults

## Release reports in local runtime

Promotion, rollback, and reproduce emit release evidence to MLflow under:

- `reports/releases/<operation>/<model_name>/v<version>/`

When the local runtime is active, the platform also mirrors those files under:

- `<artifacts_dir>/reports/releases/...`

The same operations may append structured events to:

- `<event_log_path>`

## Local Docker path

Primary operator entrypoints:

- `make e2e`
- `make up`
- `make run-pipeline`
- `make policy-check`
- `make promote`
- `make rollback-prod`
- `make serve`
- `make smoke-test`
- `make reproduce ...`
- `make down`

The Makefile is the supported operator surface. It wraps the same CLI subcommands shipped in `mlp`.
