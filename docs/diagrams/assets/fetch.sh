#!/usr/bin/env bash
# Fetch official brand PNGs for the architecture diagrams.
#
# The diagrams render either way — `_common.brand()` falls back to a labelled
# box when an asset is missing — but having the real logos makes the output
# significantly nicer.
#
# Usage:
#   bash docs/architecture/diagrams/assets/fetch.sh
#
# Re-run any time you want to refresh.  Failed downloads leave no file behind,
# so the next `make diagrams` run still produces a valid SVG.

set -euo pipefail

cd "$(dirname "$0")"

declare -a urls=(
  "mlflow.png|https://raw.githubusercontent.com/mlflow/mlflow/master/assets/icon.png"
  "opentelemetry.png|https://opentelemetry.io/img/logos/opentelemetry-icon-color.png"
  "victoriametrics.png|https://raw.githubusercontent.com/VictoriaMetrics/VictoriaMetrics/master/docs/assets/images/victoria-metrics-card-logo.png"
  "redpanda.png|https://avatars.githubusercontent.com/u/52910718?s=200&v=4"
  "duckdb.png|https://duckdb.org/images/logo-dl/DuckDB_Logo-stacked.png"
  "binance.png|https://avatars.githubusercontent.com/u/12397512?s=200&v=4"
  "coinbase.png|https://avatars.githubusercontent.com/u/1885080?s=200&v=4"
  "open_meteo.png|https://avatars.githubusercontent.com/u/86407363?s=200&v=4"
  "minio.png|https://avatars.githubusercontent.com/u/9116054?s=200&v=4"
)

ok=0
miss=0
for entry in "${urls[@]}"; do
  name="${entry%%|*}"
  url="${entry#*|}"
  if curl -fsSL --max-time 20 -o "$name" "$url"; then
    echo "OK   $name"
    ok=$((ok + 1))
  else
    echo "MISS $name  ($url)"
    rm -f "$name"
    miss=$((miss + 1))
  fi
done

echo
echo "Fetched: $ok   Missing: $miss"
[[ $miss -eq 0 ]] || echo "Missing logos render as labelled boxes; rerun this script to retry."
