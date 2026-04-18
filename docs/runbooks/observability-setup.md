# Observability Setup

Last verified: 2026-04-18

This runbook covers the one-time bootstrap for the self-hosted observability
stack that staging exports to. Day-to-day telemetry reference lives in
[observability.md](observability.md).

The stack is one GCE VM in the staging VPC running four containers via
docker compose:

- **OpenTelemetry Collector** (contrib) — OTLP/gRPC ingest from Cloud Run
- **Prometheus 3.x** — metrics TSDB, 30-day local retention on a persistent
  disk, OTLP receiver + native histograms enabled
- **Grafana Tempo** — traces on GCS (S3-compatible via HMAC, so the AWS
  port is an endpoint flip); `metrics_generator` emits RED metrics and
  service graphs back into Prometheus
- **Grafana OSS** — UI with Prometheus + Tempo datasources provisioned from
  a config bucket

Two Terraform roots are involved:

- `deployments/observability/terraform/` — VM, firewall, Tempo bucket,
  config bucket, Grafana admin password + HMAC creds in Secret Manager
- `deployments/gcp/terraform/` — wires `OTEL_EXPORTER_OTLP_ENDPOINT`,
  `OTEL_EXPORTER_OTLP_PROTOCOL`, and `OTEL_EXPORTER_OTLP_INSECURE` onto the
  hosted serving service and every platform job; jobs now use Direct VPC
  Egress into the staging subnet so they can reach the collector privately

No dashboards (UP-24) and no alert rules (UP-25) land here.

## Prerequisites

- `deployments/gcp/terraform/` is already applied (staging VPC + subnet
  exist). The observability root looks up both by name via `data`.
- You know the operator public IP you want to whitelist for Grafana UI.

## Apply the observability root

```bash
cd deployments/observability/terraform

cp terraform.tfvars.example terraform.tfvars
# Edit grafana_admin_cidr to <your.ip>/32

terraform init -backend-config="bucket=fpl-tf-state-jelle" \
  -backend-config="prefix=ml-lifecycle-platform/observability"
terraform plan
terraform apply
```

The apply creates:

- a GCE VM `mlp-obs-vm` (`e2-medium`, Debian 12) on the existing staging
  subnet, with a reserved internal IP (`10.42.0.100` by default)
- a persistent disk for the Prometheus TSDB (`pd-balanced`, 50GB)
- firewall rules: `4317/tcp` from the staging subnet to the VM tag,
  `3000/tcp` from `grafana_admin_cidr`, and IAP SSH (`35.235.240.0/20`)
- a GCS bucket for Tempo blocks, with a 30-day NEARLINE transition
- a GCS config bucket holding the compose files (`docker-compose.yml`,
  `otel-collector.yaml`, `prometheus.yml`, `tempo.yaml`, Grafana datasource
  + dashboard provisioning)
- Secret Manager entries for the Grafana admin password (generated) and
  GCS HMAC credentials used by Tempo
- VM service account with `storage.objectAdmin` on the Tempo bucket and
  `secretmanager.secretAccessor` on the three secrets

Note the outputs — you'll need `otlp_collector_endpoint` for the next step.

## Wire hosted Cloud Run to the collector

In `deployments/gcp/terraform/`, set:

```hcl
otlp_collector_endpoint = "10.42.0.100:4317"
```

Then:

```bash
cd deployments/gcp/terraform
terraform plan
terraform apply
```

The plan should show additions only: three env vars on the serving service
and on each of the five platform jobs, plus Direct VPC Egress on the jobs
(jobs previously had no VPC access).

Leaving `otlp_collector_endpoint` empty skips the wiring — the apps fall
back to the no-op exporter path from
[telemetry.py](../../src/ml_lifecycle_platform/common/telemetry.py) and
continue to boot cleanly.

## First-login: rotate the Grafana admin password

The Terraform apply generates a random admin password and stores it in
Secret Manager. Fetch it, log in, rotate it.

```bash
gcloud secrets versions access latest \
  --secret=mlp-obs-grafana-admin-password \
  --project=fpl-project-jelle
```

SSH to the VM over IAP if your operator CIDR is dynamic:

```bash
gcloud compute ssh mlp-obs-vm --zone=europe-west1-b --tunnel-through-iap
```

Or point a browser at `http://10.42.0.100:3000` from an IP inside
`grafana_admin_cidr`.

Rotate the admin password inside Grafana (Settings → Users), then update
the Secret Manager secret with the new value so a VM rebuild picks it up:

```bash
echo -n "<new-password>" | gcloud secrets versions add \
  mlp-obs-grafana-admin-password --data-file=- \
  --project=fpl-project-jelle
```

## Verify end-to-end

After redeploying serving and the platform jobs image (`platform-jobs`
deploy workflow):

1. Hit a few requests against the serving URL.
2. Trigger a dry-run promote:
   ```bash
   gcloud run jobs execute mlp-promote-staging --region europe-west1 \
     --args='--model-name,breast_cancer_clf,--dry-run,--format,json'
   ```
3. In Grafana, open **Explore → Prometheus** and query
   `requests_total` — non-zero samples labelled `service_name="serving"`
   confirm the metric path.
4. Open **Explore → Tempo** and search `service.name = promote`. The
   dry-run run appears as a single trace with a `promote.main` span.
5. Back in Prometheus, query
   `traces_spanmetrics_calls_total{service_name="serving"}` — Tempo's
   `metrics_generator` auto-populates this from trace data. Non-zero
   values prove the trace→metric path works end-to-end.

If no data appears after two minutes, SSH to the VM and inspect:

```bash
cd /opt/observability
docker compose ps
docker compose logs otel-collector | tail -50
docker compose logs tempo | tail -50
```

Cloud Logging filters for `otel trace exporter init failed` or
`otel metric exporter init failed` surface client-side OTLP problems.

## Update compose config

Config lives in the GCS config bucket. A `terraform apply` in the
observability root re-uploads changed files. SSH to the VM and reload:

```bash
cd /opt/observability
gcloud storage rsync -r gs://fpl-project-jelle-mlp-obs-config .
docker compose up -d
```

A VM reboot also resyncs from the bucket via the startup script.

## Rotate the HMAC credentials

Tempo's GCS backend uses an HMAC key on the VM service account.

```bash
cd deployments/observability/terraform
terraform taint google_storage_hmac_key.tempo
terraform apply
```

Terraform creates a new HMAC pair, updates both Secret Manager versions,
and the next VM boot (or `docker compose up -d` after an SSH rsync) picks
them up.

## When to upgrade the stack

Single-VM is acceptable at the current scale. Revisit when any of these
land:

- **sub-second scrape intervals** (crypto 15s-ahead forecasting) —
  Prometheus copes but is not its sweet spot; swap to VictoriaMetrics
  single-node or cluster (PromQL-compatible, ~3-5× less RAM) or Mimir (if
  you also want S3-native long-term storage). `remote_write` is a config
  edit, no data migration.
- **months of metric history** — add a `remote_write` block in
  `prometheus.yml` pointing at Mimir or a VM cluster; Tempo already lives
  on GCS so long-term trace storage is only a retention bump.
- **HA for the stack itself** — replace single-VM with a Managed Instance
  Group + regional load balancer, or move to Kubernetes with the
  `mimir-distributed` / `tempo-distributed` Helm charts.
- **AWS port** — re-apply the same compose stack on EC2, flip the Tempo
  `endpoint` to `s3.amazonaws.com`, point IAM at an S3 bucket. Tempo's
  S3-compatible config is already the default here.
