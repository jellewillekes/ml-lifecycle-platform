# Configuration

This page is the current config contract for the repo.

It covers what exists today:

- local runtime profiles
- env var overrides
- serving-only env vars
- hosted staging secrets created by Terraform (advanced — maintainer only)
- hosted MLflow and serving runtime env contracts (advanced — maintainer only)

## Source of truth order

Local runtime config resolves in this order:

1. explicit profile path via `MLP_PROFILE_PATH`
2. named profile via `MLP_ENV` or `mlp --env <name>`
3. env var overrides applied on top of the selected profile

Today the default profile is:

- [`configs/env/local.yaml`](../../configs/env/local.yaml)

The main implementation is:

- [`runtime/profile.py`](../../src/ml_lifecycle_platform/runtime/profile.py)
- [`cli/main.py`](../../src/ml_lifecycle_platform/cli/main.py)
- [`serving/settings.py`](../../src/ml_lifecycle_platform/serving/settings.py)

## Runtime profile fields

These fields come from `configs/env/<env>.yaml`.

| Field | Used by | Notes |
| --- | --- | --- |
| `environment` | CLI, logs | operator-facing environment name |
| `tracking_uri` | pipeline, registry, serving bootstrap | MLflow tracking backend |
| `registry_uri` | pipeline, registry, serving bootstrap | MLflow registry backend |
| `experiment_name` | pipeline | default experiment destination |
| `model_name` | register, promote, rollback, serve | default registered model |
| `model_spec_path` | pipeline, serving | must stay aligned with `model_name` |
| `log_level` | CLI, serving | current default logging level |
| `data_dir` | pipeline | local working data path |
| `artifacts_dir` | pipeline, release evidence mirror | local artifact root |
| `event_log_path` | local event store | JSONL event log path |
| `python_executable` | local command execution | Python interpreter passed through runtime |
| `canary_pct` | serving | `0-100` deterministic canary split |
| `s3_endpoint_url` | MLflow artifact access | local MinIO / S3-compatible endpoint |
| `aws_access_key_id` | MLflow artifact access | local object store credential |
| `aws_secret_access_key` | MLflow artifact access | local object store credential |
| `compose_file` | Makefile, CLI infra commands | local Docker Compose file |
| `compose_tracking_uri` | Compose containers | in-network MLflow URL |
| `compose_registry_uri` | Compose containers | in-network registry URL |
| `compose_s3_endpoint_url` | Compose containers | in-network MinIO URL |
| `compose_serve_url` | smoke path | in-network serving URL |
| `mlflow_host` | local MLflow server | bind host |
| `mlflow_port` | local MLflow server | bind port |
| `backend_store_uri` | local MLflow server | metadata backend |
| `artifact_root` | local MLflow server | artifact store root |

## Env var overrides

These env vars override the selected runtime profile today.

### Common runtime overrides

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
- `PYTHON_EXECUTABLE`
- `CANARY_PCT`
- `BACKEND_STORE_URI`
- `ARTIFACT_ROOT`

### Local object-store and Compose overrides

- `MLFLOW_S3_ENDPOINT_URL`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `MLP_COMPOSE_FILE`
- `MLP_COMPOSE_TRACKING_URI`
- `MLP_COMPOSE_REGISTRY_URI`
- `MLP_COMPOSE_S3_ENDPOINT_URL`
- `MLP_COMPOSE_SERVE_URL`
- `MLP_HOST_MLFLOW_PORT`
- `MLP_HOST_MINIO_PORT`
- `MLP_HOST_MINIO_CONSOLE_PORT`
- `MLP_HOST_SERVE_PORT`
- `SERVE_URL`
- `MLFLOW_HOST`
- `MLFLOW_PORT`

Non-obvious local-only override:

- `MLP_HOST_MLFLOW_PORT` changes the host-side port for the local MLflow UI.
- `MLP_HOST_MINIO_PORT` changes the host-side port for the MinIO API.
- `MLP_HOST_MINIO_CONSOLE_PORT` changes the host-side port for the MinIO console.
- `MLP_HOST_SERVE_PORT` changes the host-side published port for the local `serving` container without changing the in-network smoke-test URL. Use it when `localhost:8000` is already occupied.

## Serving settings

The serving container has a smaller config surface than the full runtime profile.

| Env var | Default | Used by |
| --- | --- | --- |
| `MODEL_NAME` | `breast_cancer_clf` | MLflow alias resolution |
| `MLP_MODEL_SPEC_PATH` | `configs/models/breast_cancer_demo.yaml` | feature contract loading |
| `PROD_ALIAS` | `prod` | primary registry alias |
| `CANDIDATE_ALIAS` | `candidate` | secondary registry alias |
| `CANARY_PCT` | `10` | deterministic canary split |
| `MODEL_CACHE_TTL_SEC` | `60.0` | in-process model refresh cache |
| `LOG_LEVEL` | `INFO` | serving logs |
| `UNIT_TESTING` | `false` | disables real MLflow model loads in unit tests |
| `MLFLOW_CLOUD_RUN_AUDIENCE` | unset | when set, MLflow requests carry a Cloud Run ID token for the hosted MLflow service |

Non-obvious constraint:

- `MODEL_NAME` and `MLP_MODEL_SPEC_PATH` must describe the same model.
- If they drift, serving fails on startup or request validation with an explicit error.

## Hosted staging secrets (advanced — maintainer only)

`UP-16` created the active staged MLflow secret contract:

- `mlp-mlflow-db-user`
- `mlp-mlflow-db-password`
- `mlp-mlflow-db-name`
- `mlp-mlflow-instance-connection-name`
- `mlp-mlflow-artifact-root`

These secrets exist now and are consumed by the hosted MLflow Cloud Run service.

The current values back the hosted MLflow Cloud Run deploy contract:

- DB user: `mlflow`
- DB name: `mlflow`
- artifact root: `gs://fpl-project-jelle-mlp-artifacts/mlflow/`
- instance connection name: from Terraform output `mlflow_sql.connection_name`

Legacy foundation placeholders still exist:

- `mlp-mlflow-tracking-uri`
- `mlp-mlflow-tracking-username`
- `mlp-mlflow-tracking-password`

Treat those as reserved foundation names, not the active hosted-staging contract.

## Hosted MLflow runtime env (advanced — maintainer only)

The hosted MLflow Cloud Run service uses a narrower env surface than the local Compose server.

| Env var | Source | Purpose |
| --- | --- | --- |
| `MLFLOW_HOST` | plain env | bind host inside the container |
| `MLFLOW_PORT` | plain env | bind port inside the container |
| `DB_HOST` | Terraform output | Cloud SQL private IP |
| `DB_PORT` | plain env | Postgres port, currently `5432` |
| `DB_NAME` | Secret Manager | MLflow metadata database |
| `DB_USER` | Secret Manager | MLflow DB user |
| `DB_PASSWORD` | Secret Manager | MLflow DB password |
| `ARTIFACTS_DESTINATION` | Secret Manager | GCS artifact root for MLflow artifact proxying |

Hosted MLflow does not use the local Compose-only settings such as:

- `BACKEND_STORE_URI`
- `ARTIFACT_ROOT`
- `MLFLOW_S3_ENDPOINT_URL`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

Those remain local-runtime concerns.

## Hosted serving runtime env (advanced — maintainer only)

The hosted serving Cloud Run service uses plain env vars, not new secrets.

| Env var | Source | Purpose |
| --- | --- | --- |
| `MLP_ENV` | plain env | select the staging runtime profile name for logs and context |
| `MLFLOW_TRACKING_URI` | Terraform output | hosted MLflow tracking URL |
| `MLFLOW_REGISTRY_URI` | Terraform output | hosted MLflow registry URL |
| `MLFLOW_CLOUD_RUN_AUDIENCE` | Terraform output | audience used to mint an ID token for hosted MLflow |
| `MODEL_NAME` | plain env | active registered model name |
| `MLP_MODEL_SPEC_PATH` | plain env | active request/feature contract |
| `PROD_ALIAS` | plain env | primary alias resolved by serving |
| `CANDIDATE_ALIAS` | plain env | optional secondary alias |
| `CANARY_PCT` | plain env | canary routing percentage |
| `MODEL_CACHE_TTL_SEC` | plain env | in-process refresh TTL |
| `LOG_LEVEL` | plain env | serving logs |

Hosted serving does not use direct MLflow credentials.
Instead it relies on the runtime service account and Cloud Run IAM-authenticated service-to-service requests.

## Current operator rules

- Prefer editing committed runtime profiles and model specs over piling on shell-only overrides.
- Use env var overrides for local experiments, CI, or one-off debugging.
- Do not introduce a second config layer for hosted deploys when Terraform outputs and Secret Manager already provide the needed contract.
- Keep model name, model spec, and MLflow aliases aligned. Most serving breakage comes from drifting those independently.
- Keep hosted MLflow audience and MLflow tracking URI aligned. If the audience points at a different service URL, registry calls fail at runtime.
