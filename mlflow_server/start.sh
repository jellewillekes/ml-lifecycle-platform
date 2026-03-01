#!/usr/bin/env sh
set -eu

# Defaults
: "${MLFLOW_HOST:=0.0.0.0}"
: "${MLFLOW_PORT:=5000}"

# Required config
: "${BACKEND_STORE_URI:?BACKEND_STORE_URI must be set}"
: "${ARTIFACT_ROOT:?ARTIFACT_ROOT must be set}"

# Optional: helpful to see what config the container got
echo "[mlflow-server] starting"
echo "[mlflow-server] host=${MLFLOW_HOST} port=${MLFLOW_PORT}"
echo "[mlflow-server] backend_store_uri=${BACKEND_STORE_URI}"
echo "[mlflow-server] artifact_root=${ARTIFACT_ROOT}"
if [ -n "${MLFLOW_S3_ENDPOINT_URL:-}" ]; then
  echo "[mlflow-server] s3_endpoint=${MLFLOW_S3_ENDPOINT_URL}"
fi

# NOTE:
# We intentionally do NOT pass --serve-artifacts.
# With S3/MinIO artifact stores, clients upload artifacts directly using boto3.
# This keeps the MLflow server simple and avoids version/flag mismatches.
exec mlflow server \
  --host "${MLFLOW_HOST}" \
  --port "${MLFLOW_PORT}" \
  --backend-store-uri "${BACKEND_STORE_URI}" \
  --default-artifact-root "${ARTIFACT_ROOT}"