#!/usr/bin/env bash
set -euo pipefail

expected_mm="${1:-${SUPPORTED_PYTHON_MM:-}}"
dockerfile_path="${2:-Dockerfile}"

if [[ -z "${expected_mm}" ]]; then
  echo "error: expected Python major.minor is required (arg1 or SUPPORTED_PYTHON_MM)." >&2
  exit 2
fi

if [[ ! -f "${dockerfile_path}" ]]; then
  echo "error: Dockerfile not found at ${dockerfile_path}" >&2
  exit 2
fi

base_line="$(grep -E '^FROM python:[0-9]+\.[0-9]+-slim AS base$' "${dockerfile_path}" | head -n 1 || true)"
if [[ -z "${base_line}" ]]; then
  echo "error: could not find 'FROM python:X.Y-slim AS base' in ${dockerfile_path}" >&2
  exit 1
fi

actual_mm="$(echo "${base_line}" | sed -E 's/^FROM python:([0-9]+\.[0-9]+)-slim AS base$/\1/')"

if [[ "${actual_mm}" != "${expected_mm}" ]]; then
  echo "error: Docker runtime Python mismatch." >&2
  echo "expected: ${expected_mm}" >&2
  echo "actual:   ${actual_mm}" >&2
  echo "source:   ${dockerfile_path}" >&2
  exit 1
fi

echo "ok: Dockerfile base Python matches expected ${expected_mm}"
