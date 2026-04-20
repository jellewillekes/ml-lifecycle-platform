# alert-router

Tiny HTTP receiver for Grafana managed-alert webhooks. Runs on Cloud Run.
Verifies a shared bearer token, fans each alert out to stdout as a
structured JSON log line, returns 204. A log-based metric + Cloud
Monitoring alert policy turns those log entries into an email.

Stdlib-only Python. One file. No dependencies.

See [`docs/runbooks/observability-alerts.md`](../../../docs/runbooks/observability-alerts.md)
for the end-to-end escalation path and bootstrap instructions.
