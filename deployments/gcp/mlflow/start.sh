#!/usr/bin/env sh
set -eu

: "${MLFLOW_HOST:=0.0.0.0}"
: "${MLFLOW_PORT:=5000}"
: "${DB_HOST:?DB_HOST must be set}"
: "${DB_PORT:=5432}"
: "${DB_NAME:?DB_NAME must be set}"
: "${DB_USER:?DB_USER must be set}"
: "${DB_PASSWORD:?DB_PASSWORD must be set}"
: "${ARTIFACTS_DESTINATION:?ARTIFACTS_DESTINATION must be set}"

backend_store_uri="postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"

echo "[mlflow-server] starting"
echo "[mlflow-server] host=${MLFLOW_HOST} port=${MLFLOW_PORT}"
echo "[mlflow-server] db_host=${DB_HOST} db_port=${DB_PORT} db_name=${DB_NAME} db_user=${DB_USER}"
echo "[mlflow-server] artifacts_destination=${ARTIFACTS_DESTINATION}"

exec mlflow server \
  --host "${MLFLOW_HOST}" \
  --port "${MLFLOW_PORT}" \
  --backend-store-uri "${backend_store_uri}" \
  --artifacts-destination "${ARTIFACTS_DESTINATION}" \
  --serve-artifacts
