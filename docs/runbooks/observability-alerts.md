# Observability Alerts Runbook

Last verified: 2026-04-20

Something is red in Grafana — here's what to check.

Alerts are provisioned from
[`deployments/observability/grafana/provisioning/alerting/rules.yaml`](../../deployments/observability/grafana/provisioning/alerting/rules.yaml)
and evaluated by Grafana OSS against the Prometheus datasource on the
self-hosted observability VM (see [`observability-setup.md`](observability-setup.md)).

**Notifications are deferred.** Alerts fire inside Grafana and are visible
in the alerting UI; no email, Slack, or paging path is wired yet. Someone
has to be looking at Grafana — or come here from a dashboard red marker —
for an alert to produce action. Routing is tracked in [#189](https://github.com/jellewillekes/ml-lifecycle-platform/issues/189).

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

To exercise the acceptance path:

1. `gcloud run services update mlp-staging-serving --region=europe-west1
   --update-env-vars=FORCE_5XX=1` (or deploy an image that always 500s).
2. Watch Grafana → Alerting. `ServingHighErrorRate` should flip to Firing
   inside its evaluation window (~5m pending + 1m eval).
3. `ServingHealthProbeDown` will also flip once the probe catches a failing
   `/health`.
4. Roll back the change; both alerts should resolve within one window.

This test is blocked on [#185](https://github.com/jellewillekes/ml-lifecycle-platform/issues/185)
landing so dashboards reach the VM.
