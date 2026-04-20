# Observability

The platform emits structured JSON logs and OpenTelemetry traces and metrics
from the serving API and from every Cloud Run Job (`pipeline`, `promote`,
`rollback`, `reproduce`, `maintenance`). Traces and metrics ship via OTLP to
the collector named in `OTEL_EXPORTER_OTLP_ENDPOINT`; the serving Prometheus
`/metrics` endpoint stays available for local scrape.

Bootstrap for the self-hosted Grafana/Prometheus/Tempo stack and how to
wire staging to it are in
[observability-setup.md](observability-setup.md). This page is the
day-to-day reference for the telemetry surface itself.

## Environment

| Variable | Purpose |
| --- | --- |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP collector endpoint. Local dev: `http://otel-collector:4317`. Hosted staging: `http://<obs-vm-internal-ip>:4317` (default `10.42.0.100:4317`). When unset, boot still succeeds and exporters become no-ops. |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `grpc` end-to-end (default). `http/protobuf` is kept as a fallback for any future managed OTLP/HTTP gateway. |
| `OTEL_EXPORTER_OTLP_INSECURE` | `true` when targeting the internal collector over plain gRPC (no TLS inside the VPC). |
| `GOOGLE_CLOUD_PROJECT` | When set, logs emit `logging.googleapis.com/trace` as `projects/<id>/traces/<trace_id>` so Cloud Logging Explorer resolves the jump to trace. |
| `MLP_RUN_ID` | Overrides the generated run_id inside `start_job`. Set this to the Cloud Run execution ID so one log/trace group per run is visible end-to-end. |

## Run locally against a mock collector

```bash
docker run --rm -p 4317:4317 \
  -v "$PWD/scripts/otel-collector-local.yaml:/etc/otel/config.yaml" \
  otel/opentelemetry-collector:0.102.1 \
  --config=/etc/otel/config.yaml
```

Then launch serving or a job with:

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4317 \
  uv run uvicorn ml_lifecycle_platform.serving.app:app
```

The collector's debug exporter prints received spans and metrics to stdout.

## Log → trace workflow

Every log line carries these fields when a span is active:

- `severity`
- `logging.googleapis.com/trace`
- `logging.googleapis.com/spanId`
- `logging.googleapis.com/trace_sampled`

Workflow in Cloud Logging Explorer:

1. Filter for the service: `jsonPayload.service="serving"` (or `promote`, etc.).
2. Open a log record and click the trace icon. Cloud Logging resolves the
   trace ID and opens the matching span in Cloud Trace. Full-detail trace
   view lives in the self-hosted Grafana → Tempo datasource once staging
   is wired up per [observability-setup.md](observability-setup.md).
3. From the span, use the same trace ID to find every other log line in the
   request or job run.

For job runs, filter on `jsonPayload.run_id="<id>"` to see every log line
and span emitted under a single Cloud Run execution.

## Verify a job emitted a span

With the local collector running:

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4317 \
  MLP_RUN_ID=verify-1 \
  uv run mlp --env local maintenance check --alias prod
```

In the collector output, confirm:

- a span with `name=maintenance.main` and attributes `job_name=maintenance`
  and `run_id=verify-1`
- a log record emitted with `event=job.start`, the same `job_name`, and the
  same `run_id`

Repeat against `promote`, `rollback`, `reproduce`, and `pipeline` to cover
every job family.

## Serving metrics

The serving API dual-emits three metrics to Prometheus and to OTel meters
under the same names and label keys:

- `requests_total{endpoint,mode,status}`
- `predict_latency_seconds{mode,status,chosen}`
- `shadow_diff_mae{mode}`

`/metrics` continues to serve the Prometheus exposition format unchanged.
OTLP metrics flow through the collector into the self-hosted Prometheus
TSDB. Tempo's `metrics_generator` adds `traces_spanmetrics_*` and
`traces_service_graph_*` series automatically from span data.

Additional OTel-only signals:

- `serving_startup_seconds` — histogram recorded once per container boot,
  measuring wall time from FastAPI lifespan start to ready.
- `releases_total{op,model}` — counter incremented on successful
  `promote`, `rollback`, and `reproduce` registry operations.
- `maintenance_job_last_success_seconds{job}` — observable gauge set to
  the Unix timestamp of the most recent successful maintenance check.
  Render staleness as `time() - maintenance_job_last_success_seconds`.

## Dashboards

Three dashboards ship in-repo and are loaded via Grafana's file-based
provisioning:

- **Serving health** (`mlp-serving`) — request rate, error rate, latency
  p50/p95/p99, startup latency.
- **Jobs health** (`mlp-jobs`) — maintenance freshness, per-job span
  duration and failure counts from Tempo's span metrics.
- **Release cadence** (`mlp-releases`) — promote / rollback / reproduce
  counts, prod-version freshness.

Start here when something feels off. Every panel resolves trace exemplars
in Tempo via the Prometheus ↔ Tempo datasource link.

### Authoring workflow

The provisioning provider runs with `allowUiUpdates: true`, so UI edits
persist to Grafana's local DB but **not** to the committed JSON. A
container restart reloads from disk and UI-only edits are lost. That is
the enforcement mechanism.

To change a dashboard:

1. Edit it in the Grafana UI.
2. Share → Export → Save to file.
3. Normalise and commit:

   ```bash
   python scripts/normalize_grafana_dashboard.py \
     < ~/Downloads/serving-<timestamp>.json \
     > deployments/observability/grafana/dashboards/serving.json
   ```

   The normalise script strips `id`, `version`, `iteration`, `gnetId` so
   the diff reflects real changes only.

4. Commit, open a PR, merge. Then apply to staging as in
   [Apply a dashboard change to staging](#apply-a-dashboard-change-to-staging).

## Apply a dashboard change to staging

Dashboard JSONs under `deployments/observability/grafana/dashboards/`
are uploaded to the observability config bucket by a dynamic
`fileset(...)` map in
`deployments/observability/terraform/config.tf`, so a new or edited
file is picked up on the next `terraform apply` with no Terraform
edit. The VM startup script only syncs the bucket to
`/opt/observability/` on boot; post-boot changes need a manual
rsync.

From a checkout on master:

```bash
cd deployments/observability/terraform
terraform apply   # uploads changed JSONs to gs://<project>-<config_bucket_suffix>
```

Then on the observability VM:

```bash
sudo gcloud storage rsync --recursive --delete-unmatched-destination-objects \
  gs://<project>-<config_bucket_suffix> /opt/observability
sudo docker compose -f /opt/observability/docker-compose.yml up -d
```

`docker compose up -d` re-reads the bind-mounted dashboard directory
without a full restart. Use `restart grafana` only if provisioning
config (not dashboard JSON) changed.
