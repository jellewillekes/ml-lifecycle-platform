# Observability

The platform emits structured JSON logs and OpenTelemetry traces and metrics
from the serving API and from every Cloud Run Job (`pipeline`, `promote`,
`rollback`, `reproduce`, `maintenance`). Traces and metrics ship via OTLP to
the collector named in `OTEL_EXPORTER_OTLP_ENDPOINT`; the serving Prometheus
`/metrics` endpoint stays available for local scrape.

Bootstrap for the hosted Grafana Cloud backend and how to wire staging to
it are in [observability-setup.md](observability-setup.md). This page is
the day-to-day reference for the telemetry surface itself.

## Environment

| Variable | Purpose |
| --- | --- |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP collector endpoint. For local dev, gRPC, e.g. `http://otel-collector:4317`. For Grafana Cloud staging, the OTLP/HTTP gateway, e.g. `https://otlp-gateway-prod-eu-west-0.grafana.net/otlp`. When unset, boot still succeeds and exporters become no-ops. |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `grpc` (default, for the local collector) or `http/protobuf` (required by Grafana Cloud). |
| `OTEL_EXPORTER_OTLP_HEADERS` | Auth header for Grafana Cloud, e.g. `Authorization=Basic <token>`. |
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
   view lives in Grafana Cloud Tempo once staging is wired up per
   [observability-setup.md](observability-setup.md).
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
OTLP metrics flow through the collector to Grafana Cloud.
