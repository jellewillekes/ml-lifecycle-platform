# Batch Drift Runbook

Last verified: 2026-07-03

Batch drift (UP-32) reads a rolling window of prediction events, compares each
feature against the model's release baseline, writes a `drift_report.json` into
release evidence, and exposes a `mlp_drift_ks_statistic{model, feature}`
Prometheus gauge for alerting. It runs on demand locally (`make drift`) and on a
daily Cloud Scheduler cadence in staging. It is read-only: it mutates no model
state.

## How it works

- **Port:** [`BatchEventReader`](../../src/ml_lifecycle_platform/core/ports.py) —
  the cold-path read counterpart to the `PredictionEventSink`. It returns one
  row per event with the event's features expanded into columns.
  - Local: [`DuckDBEventReader`](../../src/ml_lifecycle_platform/backends/local/event_reader.py)
    over the JSONL event file.
  - Hosted: [`BigQueryEventReader`](../../src/ml_lifecycle_platform/backends/gcp/bigquery_event_reader.py)
    over the partitioned `prediction_events_v1` table.
- **Comparison:** [`core/drift.py`](../../src/ml_lifecycle_platform/core/drift.py)
  computes the KS statistic per feature from the baseline's quantile grid versus
  the live window's empirical CDF, plus the mean/std delta. A feature is flagged
  when its KS statistic exceeds the threshold (default `0.3`).
- **Baseline:** the release-linked `DriftBaseline` on the model's `prod` version
  (UP-31). No `prod` alias or no baseline means the model is skipped, not failed.
- **Output:** `drift_report.json` written to
  `reports/drift/<model>/v<version>/` in release evidence (MLflow artifact and
  the local artifact-store mirror), and the `mlp_drift_ks_statistic` gauge
  flushed to the OTel collector before the job exits.

The event sink and reader are two halves of the same plane; see
[`event-plane.md`](event-plane.md).

## Run it locally

The default local path reads the JSONL event file the serving container writes
(`MLP_EVENT_SINK=jsonl`). Generate events first by serving traffic (see
[`local-bootstrap.md`](local-bootstrap.md)), then:

```bash
make drift                       # every model spec with a prod baseline
make drift MODEL=binance_btc_1m  # one model
make drift WINDOW_HOURS=6 THRESHOLD=0.2
```

Environment knobs (all optional):

| Variable | Default | Purpose |
| --- | --- | --- |
| `MODEL` | _all specs_ | run drift for one model instead of `--all` |
| `WINDOW_HOURS` | `24` | rolling window read back from now |
| `THRESHOLD` | `0.3` | KS flag threshold |
| `MLP_EVENT_SINK` | `jsonl` | reader backend (`jsonl` or `bigquery`) |
| `MLP_EVENT_JSONL_PATH` | `artifacts/prediction-events.jsonl` | JSONL source for the DuckDB reader |

A model with no `prod` baseline or no events in the window is skipped; if nothing
could be compared the job prints a single "no model had a baseline and events"
line and exits `0`.

### Local schedule parity

Staging runs drift on Cloud Scheduler (below). The local parity is the same job
entrypoint on the host crontab — no extra container. To mirror the `17 5 * * *`
UTC cadence against a running local stack:

```cron
17 5 * * * cd /path/to/ml-lifecycle-platform && make drift >> /tmp/mlp-drift.log 2>&1
```

For local development, running `make drift` by hand after generating traffic is
the normal path.

## Run it in staging

The hosted job is `mlp-drift-staging` (Cloud Run Job), scheduled by
`mlp-drift-staging-schedule` at `17 5 * * *` UTC. It reads the BigQuery event
plane (`MLP_EVENT_SINK=bigquery`, `MLP_EVENT_BQ_TABLE` pointing at
`prediction_events_v1`) and runs `--all`.

The runtime service account needs `roles/bigquery.jobUser` at the project level
to run the query job (granted in
[`foundation.tf`](../../deployments/gcp/terraform/foundation.tf); apply with
owner credentials). Table-level read access is already granted in `events.tf`.

Force-run it two ways:

```bash
# directly
gcloud run jobs execute mlp-drift-staging \
  --region europe-west1 --project fpl-project-jelle --wait

# or the schedule
gcloud scheduler jobs run mlp-drift-staging-schedule \
  --location europe-west1 --project fpl-project-jelle
```

`drift` is also a selectable job in the
[`Ops / Run Platform Job / Staging`](../../.github/workflows/run-platform-job-staging.yml)
workflow (`workflow_dispatch` → `job_name: drift`, default execution mode). It
uses the job's deployed args; `dry_run` is not supported.

Scheduler inspect/pause/resume and the failure model are shared with the other
hosted jobs — see [`schedule-platform-jobs.md`](schedule-platform-jobs.md).

## Read the report

`drift_report.json` (schema `drift_report/v1`) carries, per feature, the KS
statistic against the baseline, the mean/std deltas, the event count, and the
flag. The top-level `drifted` is true when any feature is flagged. Pull the
latest for a model from its release evidence:

```bash
mlp registry show-baseline --model-name binance_btc_1m --alias prod
# drift reports live alongside under reports/drift/<model>/v<version>/
```

## Metric and alert

The `mlp_drift_ks_statistic{model, feature}` gauge is dual-emitted to the OTel
collector on job exit and scraped into the observability stack. The
`DriftKsBreach` Grafana alert fires when
`max by (model, feature) (mlp_drift_ks_statistic) > 0.3` for 10m (query lookback
48h, so one missed daily run does not clear it). Triage steps are in
[`observability-alerts.md`](observability-alerts.md).

## Non-goals

- in-request (online) drift — this is batch only
- auto promote/demote on drift — promotion gates (UP-35) consume the report; the
  drift job never changes model state
