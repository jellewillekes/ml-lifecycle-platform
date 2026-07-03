# Teardown and Restore Runbook

Last verified: 2026-07-03

Bring the hosted GCP footprint to near-zero cost with one command, and rebuild
it later from the same Terraform state bucket. Use this when you are stepping
away from the project and do not want the always-on Cloud SQL instance and
observability VM to keep billing.

Everything hosted lives in two independent Terraform roots:

- [`deployments/gcp/terraform`](../../deployments/gcp/terraform) — foundation +
  staging: Cloud SQL, Cloud Run (MLflow/serving), BigQuery event plane, platform
  jobs, schedulers, service accounts, Workload Identity Federation, Artifact
  Registry, artifact buckets.
- [`deployments/observability/terraform`](../../deployments/observability/terraform) —
  the always-on GCE VM (Grafana/Prometheus/Tempo), its Prometheus TSDB disk, the
  alert-router Cloud Run service, and the Tempo/config buckets. Teardown deletes
  the TSDB disk, so metric history does not survive; the dashboards and rules are
  reprovisioned from code on restore.

## Tear it down

```bash
gcloud auth application-default login   # owner credentials — see below
make gcp-teardown
```

`make gcp-teardown` destroys the **observability root first** (the leaf), then
the **gcp root**. For each root it auto-approves a guard-clearing apply, then
prompts for `yes` on the destroy.

**Why owner credentials.** The gcp root owns project-level IAM bindings and the
WIF pool. Removing those needs `setIamPolicy`, which the scoped staging CI
service account does not have. Run the teardown yourself with owner creds, the
same way the one-off `roles/bigquery.jobUser` grant is applied.

### What survives

- The **external Terraform state bucket** (`fpl-tf-state-jelle`). It is
  referenced by name, never managed by either root, so `destroy` cannot brick
  its own backend. Its state files remain — now describing zero resources — so a
  later `apply` rebuilds from a clean slate.
- The **GCP project** itself. An empty project bills nothing.

Everything else — Cloud SQL, the VM, Cloud Run, BigQuery data, buckets and their
objects, service accounts, WIF, secrets, the Artifact Registry repo and its
images — is deleted.

### How the guards are handled

Stateful resources normally carry `deletion_protection = true` (Cloud SQL, the
Cloud Run services and jobs, the BigQuery events table) or `force_destroy =
false` (artifact and Tempo buckets), so a stray `terraform destroy` fails
safely. All are wired to a single variable `enable_deletion_protection`
(default `true`).

The Google provider reads these guards from **state**, not from destroy-time
args, so flipping the variable on `terraform destroy` alone is rejected. The
teardown target therefore runs two steps per root: `terraform apply -var
enable_deletion_protection=false` to persist the cleared guards into state (an
in-place update that recreates nothing on a healthy state), then `terraform
destroy`. The MLflow Cloud Run service is torn down before Cloud SQL so no live
connection blocks the database drop, and the `mlflow` database/user use
`deletion_policy = "ABANDON"` so the instance deletion cascades them away.
Normal applies keep protection on; the variable only ever flips during teardown.

### Confirm zero billed resources

```bash
gcloud sql instances list      --project fpl-project-jelle   # expect: Listed 0 items
gcloud compute instances list  --project fpl-project-jelle   # expect: Listed 0 items
gcloud run services list       --region europe-west1 --project fpl-project-jelle
gcloud run jobs list           --region europe-west1 --project fpl-project-jelle
```

Storage on the surviving state bucket is a few cents per month; the empty
project and disabled APIs cost nothing.

## Restore it

Order matters: the first apply recreates the CI identity, so it cannot run in
CI. Do the foundation apply locally with owner credentials, then let the normal
CD workflows take over.

1. **Owner-credentialed foundation apply.** Recreates APIs, service accounts,
   WIF, Artifact Registry, the VPC, Cloud SQL, and buckets. Cloud Run image vars
   default to `""` on a fresh apply, so services come up as IAM/skeletons first
   — same as the original bootstrap.

   ```bash
   gcloud auth application-default login
   make terraform-gcp-init
   terraform -chdir=deployments/gcp/terraform apply
   ```

   Detailed walkthrough: [`gcp-bootstrap.md`](gcp-bootstrap.md) →
   [`gcp-foundation.md`](gcp-foundation.md) →
   [`gcp-staging-infra.md`](gcp-staging-infra.md).

2. **Verify CI auth is back.** WIF was just recreated; confirm GitHub Actions can
   federate before relying on CD: [`gcp-ci-auth.md`](gcp-ci-auth.md).

3. **Publish images and deploy.** The CD workflows build and push the MLflow,
   serving, and platform-jobs images, then re-apply the gcp root with the real
   image refs. Follow the canonical path:
   [`hosted-golden-path.md`](hosted-golden-path.md), or step-by-step via
   [`deploy-mlflow.md`](deploy-mlflow.md) → [`deploy-serving.md`](deploy-serving.md)
   → [`deploy-platform-jobs.md`](deploy-platform-jobs.md).

4. **Schedulers.** Cloud Scheduler jobs are recreated by the platform-jobs apply;
   confirm cadence and paused state with
   [`schedule-platform-jobs.md`](schedule-platform-jobs.md).

5. **Rebuild observability.** Rebuild the alert-router image, re-init the
   observability root against its own state prefix, and apply. Then feed the
   collector endpoint back into the gcp root's `otlp_collector_endpoint` so the
   drift and maintenance gauges export again. See
   [`observability-setup.md`](observability-setup.md) and the Bootstrap section
   of [`observability-alerts.md`](observability-alerts.md).

6. **Re-seed anything TF does not own.** Secret Manager *versions* that are not
   generated by `random_password` (none today — the MLflow DB password and the
   alert-router token are both TF-generated) and any manually pushed data. If you
   add such secrets later, note them here.

Forking into a fresh project instead of restoring this one? Start from
[`oss-deploy.md`](oss-deploy.md), which walks the same graph from an empty GCP
project.

## Non-goals

- deleting the GCP project or the Terraform state bucket — both are near-zero
  cost and are what make restore a single `apply`; delete them by hand only if
  you are abandoning the project entirely
- partial / per-service teardown — this is all-or-nothing by design; scale a
  single Cloud Run service to zero instead if that is all you need
