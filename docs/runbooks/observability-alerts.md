# Observability Alerts Runbook

Last verified: 2026-04-20

> Forking the repo? Start from [`oss-deploy.md`](./oss-deploy.md). The
> Bootstrap section at the bottom of this doc is the final step of that
> walkthrough.

Something is red in Grafana — here's what to check.

Alerts are provisioned from
[`deployments/observability/grafana/provisioning/alerting/rules.yaml`](../../deployments/observability/grafana/provisioning/alerting/rules.yaml)
and evaluated by Grafana OSS against the Prometheus datasource on the
self-hosted observability VM (see [`observability-setup.md`](observability-setup.md)).

## Escalation path

Firing alerts reach a human via a GCP-native chain — no third-party SaaS,
no tokens outside Secret Manager:

```
Grafana alert → webhook contact point
             → Cloud Run `mlp-obs-alert-router` (shared-bearer auth)
             → structured log entry (severity=WARNING, message=grafana_alert)
             → log-based metric mlp-obs/grafana_alert_firing
             → Cloud Monitoring alert policy "Grafana alert firing (via alert-router)"
             → email notification channel (alert_email var)
```

Expect total time-to-email of roughly three to four minutes: Grafana's
evaluation window, plus the log-based metric's ~60s aggregation, plus
Cloud Monitoring's alignment period. That's acceptable for the SLOs in
scope today; if it starts mattering, push evaluation intervals down
first — the log-based metric floor is what it is.

### Rotating the shared token

```
gcloud secrets versions add mlp-obs-alert-router-token --data-file=-
# then redeploy the observability VM (or bounce the startup script) so
# grafana.env re-reads the secret.
```

Terraform regenerates the token on `random_password` drift; running
`terraform apply` with `-replace=random_password.alert_router_token`
forces a rotation.

### Silencing during incident work

Use Grafana's built-in silence UI (Alerting → Silences) for per-alert or
per-label muting. Silence at the Grafana layer, not at Cloud Monitoring —
muting at CM means you lose the log record that the alert ever fired.

## Where to look first

1. Grafana → **Alerting → Alert rules** for the firing list and evaluation history.
2. Grafana → **Dashboards → Serving SLOs**
   ([`slo.json`](../../deployments/observability/grafana/dashboards/slo.json))
   for availability, p95, and burn rate at a glance.
3. Grafana → **Dashboards → Serving / Jobs / Releases** for the underlying
   signal the alert is reading from.

## Alerts

### ServingHighErrorRate (fast, 5xx)

- **What fires it:** `serving:errors:ratio5m > 0.01` for 5m.
- **Check:** serving dashboard "Error rate" panel, then Tempo traces for the
  same window filtered by `service.name=serving` and `status_code=ERROR`.
- **Likely causes:** bad recent deploy, downstream (MLflow, model artifact
  fetch) throwing, malformed traffic.

### ServingHighLatencyP95 (slow)

- **What fires it:** `serving:predict_latency:p95_5m > 1.0s` for 10m.
- **Check:** serving dashboard latency panel; cold-start startup latency
  panel; `predict_latency_seconds_bucket` histogram. Check Cloud Run revision
  min-instance count.
- **Likely causes:** cold starts, model swap without prewarm, container
  CPU throttling.

### ServingHealthProbeDown / MlflowHealthProbeDown

- **What fires it:** `probe_success{instance=~...} < 1` for 2m, from
  blackbox_exporter hitting the configured `/health` URL.
- **Check:** the target URL in `terraform.tfvars` (`serving_probe_url`,
  `mlflow_probe_url`). Try the URL from your laptop — if it also fails,
  the service is actually down; if it succeeds, the VM can't reach it
  (network / egress issue).
- **Likely causes:** revision not receiving traffic, Cloud Run cold-start
  exceeded probe timeout, service deleted.

### MaintenanceJobStale

- **What fires it:** `time() - maintenance_job_last_success_seconds > 26h`
  (gauge landed in UP-24). The scheduler runs maintenance every 24h; 26h
  covers one missed run.
- **Check:** Cloud Scheduler logs for the maintenance job; last job
  execution's Cloud Run Jobs logs.
- **Likely causes:** scheduler paused, job image broken, job auth
  regression.

### DriftKsBreach

- **What fires it:** `max by (model, feature) (mlp_drift_ks_statistic) > 0.3`
  for 10m. The gauge lands from the daily batch-drift job (UP-32); the
  alert query looks back 48h so one missed run does not clear it. `0.3`
  matches the job's `DEFAULT_KS_THRESHOLD`, so a firing alert means the job
  already flagged that feature and wrote a flagging `drift_report.json`.
- **Check:** the model/feature label on the alert, then the latest
  `drift_report.json` in that model's release evidence (`reports/drift/...`)
  for the per-feature KS and mean/std deltas. See
  [`drift.md`](drift.md) for how to re-run the comparison.
- **Likely causes:** genuine feature-distribution shift in live prediction
  events versus the release baseline, a stale baseline after a data-schema
  change, or a thin event window (few events → noisy empirical CDF).

### ServingAvailabilityBurnFast / BurnSlow

- **What fires it:** multi-window burn against a 99.5% availability SLO.
  Fast = 1h error ratio > 14.4× budget; Slow = 6h > 6× budget.
- **Caveat:** staging traffic is low, so burn math can be noisy — a handful
  of 5xx during a 10-request window crosses the fast threshold. Treat as
  directional, not ground truth, until real traffic exists.
- **Check:** Serving SLOs dashboard → "Error ratio across windows";
  correlate with request rate.

## Tuning

Thresholds are first-pass defaults. Expect a tuning commit in the same
phase as this change after one full staging cycle produces real data.
Update the thresholds in
[`rules.yaml`](../../deployments/observability/grafana/provisioning/alerting/rules.yaml)
and re-apply the observability Terraform root to push them to the bucket;
the VM picks them up on the next config rsync (startup script runs on
reboot, or run `gcloud storage rsync` manually in an SSH session).

## Intentionally breaking staging

To exercise the acceptance path end-to-end (including email delivery):

1. `gcloud run services update mlp-serving-staging --region=europe-west1
   --update-env-vars=FORCE_5XX=1` (or deploy an image that always 500s).
2. Watch Grafana → Alerting. `ServingHighErrorRate` should flip to Firing
   inside its evaluation window (~5m pending + 1m eval).
3. `ServingHealthProbeDown` will also flip once the probe catches a failing
   `/health`.
4. Check the alert-router's Cloud Run logs
   (`gcloud logging read 'resource.labels.service_name=mlp-obs-alert-router AND jsonPayload.message=grafana_alert' --limit=10`);
   one entry per firing alert should appear within a minute of the
   Grafana transition.
5. An email from `Cloud Monitoring <no-reply@google.com>` should arrive
   at the configured `alert_email` within the next eval window.
6. Roll back the change; Grafana alerts resolve; no further emails fire.

## Bootstrap (first-time setup)

Before the first `terraform apply` of `deployments/observability/terraform/`:

1. Build and push the alert-router image:
   `gh workflow run build-alert-router.yml` (or wait for a push to
   `master` that touches `deployments/observability/alert-router/**`).
   Verify the image exists in Artifact Registry, then capture the
   digest:

   ```bash
   gcloud artifacts docker images list \
     europe-west1-docker.pkg.dev/<PROJECT_ID>/mlp-images/alert-router \
     --include-tags --sort-by=~UPDATE_TIME --limit=1
   ```

2. `terraform init` with an explicit backend-config (the state bucket
   is external to this root):

   ```bash
   terraform init \
     -backend-config="bucket=<TF_STATE_BUCKET>" \
     -backend-config="prefix=ml-lifecycle-platform/observability"
   ```

3. Set `alert_email` and `alert_router_image` in `terraform.tfvars`.
   Pin `alert_router_image` by digest (`@sha256:<DIGEST>`), not
   `:latest` — tag-resolution against `:latest` can 404 even when the
   tag is present.
4. `terraform apply` — creates the router, secret, log-based metric,
   alert policy, and email notification channel.
5. Email-type Cloud Monitoring channels do **not** send a verification
   email on creation. The first real (or synthetic) alert is also the
   first delivery — use the synthetic curl in the acceptance test below
   to prove the chain end-to-end.

### Acceptance test (synthetic webhook)

Fastest proof the full chain works, without needing real traffic:

```bash
TOKEN=$(gcloud secrets versions access latest --secret=mlp-obs-alert-router-token)
ROUTER_URL=$(terraform -chdir=deployments/observability/terraform output -raw alert_router_url)
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)

curl -X POST "$ROUTER_URL" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"alerts\":[{\"status\":\"firing\",\"labels\":{\"alertname\":\"SyntheticTest\"},\"annotations\":{\"summary\":\"acceptance check\"},\"startsAt\":\"$NOW\",\"fingerprint\":\"synthetic-$(date +%s)\"}]}"
```

Expect `204`. Within ~1 minute the log entry appears:

```bash
gcloud logging read \
  'resource.labels.service_name=mlp-obs-alert-router AND jsonPayload.message=grafana_alert' \
  --limit=5 --format=json
```

Email from `Cloud Monitoring <no-reply@google.com>` arrives within ~3
minutes (check spam / Promotions). A recovery email follows when the
log-based metric drops back to zero.

### Recovery: Cloud Run v2 service tainted

If an apply leaves `mlp-obs-alert-router` tainted and the next apply
errors with `cannot destroy service without setting deletion_protection=false`:

```bash
terraform untaint google_cloud_run_v2_service.alert_router
terraform apply
```

`deletion_protection = false` is already set in
[`alert_router.tf`](../../deployments/observability/terraform/alert_router.tf),
so this runs as an in-place update. Flipping `deletionProtection` via
`gcloud` or the REST API does not work — it is a Terraform-provider
attribute, not a real Cloud Run API field.
