#!/usr/bin/env bash

set -euo pipefail

max_attempts="${TERRAFORM_GCP_INIT_MAX_ATTEMPTS:-5}"
sleep_seconds="${TERRAFORM_GCP_INIT_INITIAL_BACKOFF_SEC:-2}"

attempt=1
while true; do
  if make terraform-gcp-init; then
    exit 0
  fi

  if (( attempt >= max_attempts )); then
    echo "terraform-gcp-init failed after ${attempt} attempts"
    exit 1
  fi

  echo "terraform-gcp-init failed on attempt ${attempt}; retrying in ${sleep_seconds}s"
  sleep "${sleep_seconds}"
  attempt=$((attempt + 1))
  sleep_seconds=$((sleep_seconds * 2))
done
