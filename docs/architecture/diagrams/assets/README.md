# Brand assets

Custom logos used in the architecture diagrams.  Built-in icons from
`mingrammer/diagrams` (Cloud Run, BigQuery, Postgres, Redis, MinIO, Grafana,
Prometheus, MLflow, GitHub Actions, FastAPI, Docker, etc.) ship with that
package and are not duplicated here.

## How to populate

```sh
bash docs/architecture/diagrams/assets/fetch.sh
```

The script attempts a single download per logo.  Anything that fails is left
unwritten; `_common.brand()` then falls back to a labelled box at render
time, so `make diagrams` still produces valid SVGs.

## Logos and sources

Each entry: filename, where it comes from, intended use in diagrams.

| File | Source URL | Used for |
|---|---|---|
| `mlflow.png` | https://raw.githubusercontent.com/mlflow/mlflow/master/assets/icon.png | MLflow control plane (registry, tracking) |
| `opentelemetry.png` | https://opentelemetry.io/img/logos/opentelemetry-icon-color.png | OTel SDK / Collector hops |
| `victoriametrics.png` | https://raw.githubusercontent.com/VictoriaMetrics/VictoriaMetrics/master/docs/assets/images/victoria-metrics-card-logo.png | Self-hosted metrics TSDB |
| `redpanda.png` | https://avatars.githubusercontent.com/u/52910718 | Local Kafka-protocol broker (M6 stream port) |
| `duckdb.png` | https://duckdb.org/images/logo-dl/DuckDB_Logo-stacked.png | Local equivalent of BigQuery |
| `binance.png` | https://avatars.githubusercontent.com/u/12397512 | Binance public REST and WS data source |
| `coinbase.png` | https://avatars.githubusercontent.com/u/1885080 | Coinbase public REST data source |
| `open_meteo.png` | https://avatars.githubusercontent.com/u/86407363 | Open-Meteo forecast + ERA5 data source |

## License

Each logo remains the trademark of its respective project.  These files are
included only for documentation purposes — to help readers identify the
component a node represents in an architecture diagram.  No endorsement is
implied by inclusion.  Replace or remove any logo whose license you cannot
honour for your fork.
