# OSS Deploy Walkthrough

Last verified: 2026-04-20

This runbook is the end-to-end path for deploying this platform to your own
GCP project. If you are the primary maintainer (`fpl-project-jelle`), use
the per-topic runbooks directly and the concrete values in
[`docs/environments/fpl-project-jelle/`](../environments/fpl-project-jelle/).

If you forked the repo and want a working hosted stack, start here. Every
other runbook in [`docs/runbooks/`](./) uses the primary maintainer's
identifiers as concrete examples; this doc tells you what to swap.

## Who this is for

You have:

- forked `jellewillekes/ml-lifecycle-platform` to your own GitHub org
- a GCP account with billing you can attach to a new project
- `gcloud` (current stable), `terraform` 1.5.7, and `gh` CLI installed
- ~1 hour for the first walkthrough

You do not need to read the hosted runbooks first. Follow this doc and it
will link into them at the right point.

## What you'll have at the end

- a GCP project with the platform's staging VPC, Artifact Registry repo,
  and Workload Identity Federation pool wired to your fork
- hosted MLflow and serving on Cloud Run
- a self-hosted observability VM running Prometheus, Tempo, and Grafana
- Grafana-managed alerts emailing you when staging serving errors or
  latency cross thresholds

The platform's local path (`make e2e`) does not need any of this.

## Variables to choose

Decide these up front. Use the same values consistently across every
runbook you touch.

| Variable | What it is | Example |
|---|---|---|
| `<PROJECT_ID>` | GCP project ID (globally unique) | `mlp-acme-prod` |
| `<REGION>` | GCP region for all hosted resources | `europe-west1` |
| `<ZONE>` | GCP zone inside `<REGION>` | `europe-west1-b` |
| `<TF_STATE_BUCKET>` | GCS bucket holding Terraform state (globally unique) | `mlp-acme-tf-state` |
| `<ALERT_EMAIL>` | Where Grafana alerts are emailed | `oncall@acme.com` |
| `<GRAFANA_ADMIN_CIDR>` | Your public IP, `/32` | `203.0.113.4/32` |
| `<GITHUB_OWNER>` | Your GitHub org or user | `acme` |
| `<GITHUB_REPO>` | Repo name (typically unchanged) | `ml-lifecycle-platform` |
| `<GITHUB_REPO_ID>` | Numeric repo ID (see below) | `123456789` |

Find the numeric repo ID with:

```bash
gh api /repos/<GITHUB_OWNER>/<GITHUB_REPO> --jq .id
```

The numeric ID matters: the WIF trust condition pins authorization to the
repo ID, not its name, so renames do not silently expand access. If you
skip this, CI auth in your fork will fail with a 403.

## Manual pre-Terraform steps

Terraform cannot bootstrap its own state bucket, its own project, or its
own billing. Do these once with an operator identity (your laptop).

### 1. Create the project and attach billing

```bash
gcloud projects create <PROJECT_ID>
gcloud beta billing projects link <PROJECT_ID> \
  --billing-account=<YOUR_BILLING_ACCOUNT_ID>
gcloud config set project <PROJECT_ID>
```

### 2. Create the Terraform state bucket

```bash
gcloud storage buckets create gs://<TF_STATE_BUCKET> \
  --location=<REGION> \
  --uniform-bucket-level-access \
  --public-access-prevention
```

Enable object versioning so you can recover from accidental state edits:

```bash
gcloud storage buckets update gs://<TF_STATE_BUCKET> --versioning
```

### 3. Authenticate

```bash
gcloud auth login
gcloud auth application-default login
gcloud auth application-default set-quota-project <PROJECT_ID>
```

### 4. Fork-pin the WIF condition

The foundation Terraform root pins the GitHub Actions WIF trust to the
maintainer's repo ID. In your fork, edit the Terraform HCL to use your
`<GITHUB_OWNER>`, `<GITHUB_REPO>`, and `<GITHUB_REPO_ID>` before you apply
the foundation root. See [`gcp-foundation.md`](./gcp-foundation.md) for
the WIF block that needs updating.

## Terraform roots, in order

Apply these roots in this order. For each, use your `<TF_STATE_BUCKET>`
and a distinct `prefix` per root so the state layouts stay separate.

Each step below summarises *what to do differently from the linked
runbook*. Defer to the linked runbook for the authoritative procedure.

### Step 1 · Bootstrap

Runbook: [`gcp-bootstrap.md`](./gcp-bootstrap.md)

```bash
cd deployments/gcp/terraform
terraform init \
  -backend-config="bucket=<TF_STATE_BUCKET>" \
  -backend-config="prefix=ml-lifecycle-platform/gcp/bootstrap"
```

Set `project_id` and `region` in a local, gitignored `terraform.tfvars`.
Apply.

### Step 2 · Foundation

Same root, same state. This step adds Artifact Registry, buckets, service
accounts, and GitHub Actions WIF.

Runbook: [`gcp-foundation.md`](./gcp-foundation.md)

Before you apply: confirm you edited the WIF condition to your fork's
repo. After the apply: capture the outputs (`workload_identity_provider_name`,
`foundation_service_accounts`) — you will paste these into GitHub Actions
secrets in step 3.

### Step 3 · CI auth

Runbook: [`gcp-ci-auth.md`](./gcp-ci-auth.md)

Set the GitHub Actions repo secrets in your fork so CI workflows can
impersonate the foundation CI service account.

### Step 4 · Staging infra

Runbook: [`gcp-staging-infra.md`](./gcp-staging-infra.md)

Creates the staging VPC, subnet, and Cloud SQL. The observability VM
later joins this VPC, so it must exist first.

### Step 5 · MLflow

Runbook: [`deploy-mlflow.md`](./deploy-mlflow.md)

### Step 6 · Serving

Runbook: [`deploy-serving.md`](./deploy-serving.md)

### Step 7 · Observability stack

Runbook: [`observability-setup.md`](./observability-setup.md)

Use `<TF_STATE_BUCKET>` with prefix `ml-lifecycle-platform/observability`:

```bash
cd deployments/observability/terraform
terraform init \
  -backend-config="bucket=<TF_STATE_BUCKET>" \
  -backend-config="prefix=ml-lifecycle-platform/observability"
```

Set `project_id`, `region`, `zone`, `grafana_admin_cidr` in a local
`terraform.tfvars`. Apply. This brings up the VM, Prometheus, Tempo, and
Grafana with no alerts wired yet.

### Step 8 · Alert routing

Runbook: [`observability-alerts.md`](./observability-alerts.md)

**Before the first `terraform apply` on this root**: you must build and
push the alert-router container image, otherwise the apply will fail with
`Image not found` and leave the Cloud Run service tainted. See the
Bootstrap section of `observability-alerts.md`.

Set `alert_email = "<ALERT_EMAIL>"` in the same `terraform.tfvars`.

## Common failures

### `Image not found` on first alert-router apply

The apply races the image build. Trigger the build workflow from your
fork first, wait for it to complete, and pin the image by digest in
`terraform.tfvars`:

```hcl
alert_router_image = "europe-west1-docker.pkg.dev/<PROJECT_ID>/mlp-images/alert-router@sha256:<DIGEST>"
```

Using `@sha256:` instead of `:latest` avoids tag-resolution flakiness
that can 404 even when Artifact Registry lists the tag.

### Cloud Run v2 service stuck tainted

If a prior apply left the service tainted and the next apply errors with
`cannot destroy service without setting deletion_protection=false`:

```bash
terraform untaint google_cloud_run_v2_service.alert_router
terraform apply
```

After the fix landed in
[`deployments/observability/terraform/alert_router.tf`](../../deployments/observability/terraform/alert_router.tf)
this is an in-place update, not a destroy.

Flipping `deletionProtection` via `gcloud` or the REST API does not work
— it is a Terraform-provider attribute, not a real Cloud Run API field.

### Workload Identity Federation rejects CI auth

The WIF condition pins to the maintainer's numeric repo ID. A fresh fork
will 403 with `Unable to acquire impersonation credentials`. Re-check
`<GITHUB_REPO_ID>` from step 0 matches the value in the foundation
Terraform and re-apply.

### State bucket "not found" during `terraform init`

The state bucket is external to every Terraform root (see
[`gcp-bootstrap.md`](./gcp-bootstrap.md) for why). It must exist before
`terraform init` runs. Re-do the pre-Terraform step 2.

### Notification channel silent

Cloud Monitoring email channels do not send a verification email. The
first real alert is also the first delivery. Use the acceptance test
below to prove the chain end-to-end instead of waiting for a
verification link that will not arrive.

## Acceptance test

This is the fastest proof that the full chain works, without needing
real serving traffic.

```bash
TOKEN=$(gcloud secrets versions access latest --secret=mlp-obs-alert-router-token)
ROUTER_URL=$(terraform -chdir=deployments/observability/terraform output -raw alert_router_url)

NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
curl -X POST "$ROUTER_URL" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"alerts\":[{\"status\":\"firing\",\"labels\":{\"alertname\":\"AcceptanceTest\"},\"annotations\":{\"summary\":\"oss-deploy.md acceptance test\"},\"startsAt\":\"$NOW\",\"fingerprint\":\"oss-deploy-acceptance\"}]}"
```

Expect `204`. Within ~1 minute:

```bash
gcloud logging read \
  'resource.labels.service_name=mlp-obs-alert-router AND jsonPayload.message=grafana_alert' \
  --limit=5 --format=json
```

Should show one entry with `alertname=AcceptanceTest`. An email from
`Cloud Monitoring <no-reply@google.com>` should arrive at `<ALERT_EMAIL>`
within ~3 minutes total — check spam and Promotions tabs, first delivery
often lands there.

A recovery email follows automatically when the log-based metric drops
back to zero.

## Next steps

- Customise alert thresholds in
  [`deployments/observability/grafana/provisioning/alerting/rules.yaml`](../../deployments/observability/grafana/provisioning/alerting/rules.yaml)
  and re-apply the observability root.
- Point Grafana dashboards at your own serving traffic by deploying the
  hosted serving path from step 6 and generating load.
- Read [`observability-alerts.md`](./observability-alerts.md) for the
  per-alert playbooks so future on-call rotations have a reference.
