# Adding a data source

The pipeline is source-agnostic. Every source is a `DataSource` adapter behind
one port, so `ingest → featurize → train → evaluate → register → promote →
serve` never changes when you add one. Only the triple **(adapter + model spec
+ runtime profile)** is per-model.

## The port

`DataSource` lives in [`../../src/ml_lifecycle_platform/core/ports.py`](../../src/ml_lifecycle_platform/core/ports.py):

```python
class DataSource(Protocol):
    def fetch(self) -> pd.DataFrame: ...
```

`fetch()` returns a model-ready labeled frame: exactly the features declared in
the spec's `feature_contract` plus the int `{0, 1}` `label_column`, and nothing
else (with `allow_unknown_fields: false`, any extra column would become a model
feature and fail dataset-contract validation). Adapters live under
[`../../src/ml_lifecycle_platform/backends/common/data_sources/`](../../src/ml_lifecycle_platform/backends/common/data_sources/)
and the resolver maps a spec's source kind to its adapter.

The first real source is Binance OHLCV klines
([`binance_rest.py`](../../src/ml_lifecycle_platform/backends/common/data_sources/binance_rest.py)),
pulled from the public market-data mirror `data-api.binance.vision` (no API key,
no geo-block). It reuses the shared OHLCV transform
([`ohlcv_features.py`](../../src/ml_lifecycle_platform/backends/common/data_sources/ohlcv_features.py)),
which derives the alpha features and the next-bar direction label.

Run it end-to-end:

```bash
make e2e-binance          # = make e2e-clean MLP_ENV_NAME=local_binance
```

(The dedicated `local_binance` profile keeps the registered, promoted, and
served model name aligned with the spec — register reads the spec's model name,
but promote and serve read the profile, so they must agree.)

## Run on hosted staging

The same adapter runs unchanged on GCP — it is plain public HTTPS, which is why
the `backends/common` location is deliberate. Model identity is injected per job
via env (`MLP_ENV` plus the `MODEL_NAME` / `MLP_MODEL_SPEC_PATH` /
`EXPERIMENT_NAME` overrides), so one platform image drives both the demo and the
Binance pipelines side by side.

- **Job** — `mlp-pipeline-binance-staging`, defined in
  [`jobs_platform.tf`](../../deployments/gcp/terraform/jobs_platform.tf) next to
  the demo jobs. `terraform apply` (the *Deploy Platform Jobs / Staging*
  workflow) creates it; there is no allow-list to update.
- **Run it** — dispatch *Run Platform Job / Staging* with
  `job_name: pipeline-binance`. It executes the job, running
  `ingest → … → register` against hosted MLflow.
- **Egress** — the job uses `egress = "PRIVATE_RANGES_ONLY"`, which routes only
  RFC-1918 traffic through the VPC; public `data-api.binance.vision` egresses
  directly, so no Cloud NAT is needed.
- **Confirm the model** — a gated run registers `binance_btc_1m` and points its
  `candidate` alias at the new version. Check the MLflow registry, or run
  `scripts/verify_hosted_model_alias.py --tracking-uri <mlflow-url> --model-name
  binance_btc_1m --alias candidate`. The POC gate (`roc_auc >= 0.50`) is a low
  mechanics bar by design — 1-minute direction is near-random, so on a thin
  slice a run can miss the gate and skip registration; just re-run.

Hosting a *new* source is the same small pattern: add a `model_env` entry to
`platform_jobs` and a `job_name` choice to the staging platform-job workflow.

## Add a new source in 5 steps

Worked example: a second exchange, Coinbase, that produces the same OHLCV shape.

1. **Spec type + parser** — add `CoinbaseSourceSpec` to
   [`core/model_spec_types.py`](../../src/ml_lifecycle_platform/core/model_spec_types.py)
   (add the kind to `SUPPORTED_SOURCE_KINDS`) and an arm in `_parse_source` in
   [`core/model_specs.py`](../../src/ml_lifecycle_platform/core/model_specs.py).
2. **Adapter** — add `coinbase_rest.py`: `fetch_candles()` for the I/O, then
   **reuse `build_ohlcv_features()`** so there is no duplicated feature logic.
   A non-OHLCV source (for example weather) ships its own transform instead.
3. **Resolver** — add one arm to `build_data_source` in
   [`resolver.py`](../../src/ml_lifecycle_platform/backends/common/data_sources/resolver.py).
4. **Config** — add `configs/models/coinbase_btc_1m.yaml` and
   `configs/env/local_coinbase.yaml` (copy `local_binance.yaml`, change the
   three identity fields).
5. **Run** — `make e2e-clean MLP_ENV_NAME=local_coinbase`.

No changes to ingest, featurize, train, evaluate, register, promote, or serve.

## Testing

Keep `make check` hermetic: unit-test the adapter with `requests` mocked and the
feature transform with a synthetic frame. The live network call runs only under
`make e2e-binance` (Docker + outbound HTTPS), never in CI.
