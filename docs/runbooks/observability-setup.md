# Observability Setup

Last verified: 2026-04-18

This runbook covers the one-time, partially out-of-band bootstrap for the
Grafana Cloud backend that staging exports to. Once this is done,
[observability.md](observability.md) is the day-to-day reference.

Two things are managed out-of-band (same pattern as the `mlp-ci` bucket IAM
in [gcp-bootstrap.md](gcp-bootstrap.md)):

- the Grafana Cloud account and stack (created in the web UI)
- a service account token scoped to the stack (created in the web UI, then
  fed to Terraform via an env var)

Everything else — datasources, the email contact point, and the Cloud Run
env vars that point serving and jobs at the OTLP gateway — is Terraform-managed.

## What lands

Two Terraform roots are involved:

- `deployments/grafana/terraform/` — manages datasources (hosted Prometheus,
  hosted Tempo) and a default email contact point inside the Grafana Cloud
  stack
- `deployments/gcp/terraform/` — stores the OTLP auth header in Secret
  Manager and wires `OTEL_EXPORTER_OTLP_ENDPOINT`,
  `OTEL_EXPORTER_OTLP_PROTOCOL`, and `OTEL_EXPORTER_OTLP_HEADERS` onto the
  hosted serving service and every platform job

No dashboards (UP-24) and no alert rules (UP-25) land here.

## One-time: create the Grafana Cloud stack

1. Sign up at <https://grafana.com> using the free tier. 10k active series,
   14-day retention. Use the EU region to stay local to `europe-west1`.
2. In **My Account**, create a stack. Note the stack URL, it has the form
   `https://<org>.grafana.net`.
3. In the stack, open **Connections → Data sources → Hosted Prometheus**
   and capture:
   - the remote-write / query URL (`https://prometheus-prod-XX-prod-eu-west-0.grafana.net/api/prom`)
   - the instance ID (numeric username)
4. Do the same for **Hosted Tempo**:
   - the base URL (`https://tempo-prod-XX-prod-eu-west-0.grafana.net`)
   - the instance ID
5. Open **Security → Access policies**. Create an access policy with
   scopes `metrics:write`, `traces:write`, and `stacks:read`. Mint a token
   from it. This is the value you will export as `TF_VAR_grafana_service_account_token`.
6. For the Prom and Tempo datasources, also mint read tokens (stack-scoped
   with `metrics:read` / `traces:read`). These are the `prometheus_token`
   and `tempo_token` tfvar values.
7. Open **Connections → OpenTelemetry**. Capture:
   - the OTLP/HTTP endpoint
     (`https://otlp-gateway-prod-eu-west-0.grafana.net/otlp`)
   - the `Authorization: Basic <...>` header value minted for OTLP ingest.
     Format: `Authorization=Basic <base64 of "instance_id:token">`. This
     is what goes into Secret Manager.

## Apply the Grafana Cloud Terraform root

```bash
cd deployments/grafana/terraform

export TF_VAR_grafana_stack_url="https://<org>.grafana.net"
export TF_VAR_grafana_service_account_token="glsa_..."
export TF_VAR_prometheus_url="https://prometheus-prod-XX-prod-eu-west-0.grafana.net/api/prom"
export TF_VAR_prometheus_user="1234567"
export TF_VAR_prometheus_token="glc_..."
export TF_VAR_tempo_url="https://tempo-prod-XX-prod-eu-west-0.grafana.net"
export TF_VAR_tempo_user="7654321"
export TF_VAR_tempo_token="glc_..."

terraform init -backend-config="bucket=fpl-tf-state-jelle" \
  -backend-config="prefix=ml-lifecycle-platform/grafana"
terraform plan
terraform apply
```

`terraform.tfvars.example` documents the same set for local use.

## Apply the GCP OTLP wiring

Add to the GCP root's tfvars (or export as `TF_VAR_*`):

```hcl
grafana_cloud_otlp_endpoint    = "https://otlp-gateway-prod-eu-west-0.grafana.net/otlp"
grafana_cloud_otlp_auth_header = "Authorization=Basic <base64>"
```

Then from `deployments/gcp/terraform/`:

```bash
terraform plan
terraform apply
```

The plan should show additions only: the new `otlp-auth-header` secret,
secret version, IAM binding, and three env vars on each Cloud Run service
and job.

Leaving `grafana_cloud_otlp_endpoint` empty skips the entire wiring — the
apps fall back to the no-op exporter path from
[telemetry.py](../../src/ml_lifecycle_platform/common/telemetry.py) and
continue to boot cleanly.

## Verify end-to-end

After redeploying serving and the jobs image:

1. Hit a few requests against the serving URL.
2. Trigger a dry-run promote via the Cloud Run Job:
   `gcloud run jobs execute mlp-promote-staging --region europe-west1 \
    --args='--model-name,breast_cancer_clf,--dry-run,--format,json'`.
3. In Grafana Cloud open **Explore → grafana-cloud-prometheus** and query
   `requests_total` — non-zero samples labelled
   `service_name="serving"` confirm the metric path.
4. Open **Explore → grafana-cloud-tempo** and search traces for
   `service.name = promote`. The dry-run run should appear as a single
   trace with a `promote.main` span.

If no data appears after two minutes, check Cloud Logging for
`otel trace exporter init failed` or `otel metric exporter init failed`
warnings from the service — those are emitted by `telemetry.py` when the
endpoint is unreachable or the auth header is malformed.

## Rotate the OTLP auth header

1. Mint a new OTLP write token in the Grafana Cloud UI.
2. Compose the new header value: `Authorization=Basic <base64 of "instance_id:token">`.
3. Update the `grafana_cloud_otlp_auth_header` tfvar and
   `terraform apply`. The Secret Manager secret version is replaced;
   serving and jobs pick up the new value on next revision.
4. Revoke the old Grafana Cloud token once the new revision is healthy.

## Rotate the Grafana provider token

The service account token used by the Grafana Terraform provider is held
only in the operator's shell (`TF_VAR_grafana_service_account_token`). To
rotate: mint a new token, re-run `terraform apply`, delete the old token
in the Grafana Cloud UI. No state changes.
