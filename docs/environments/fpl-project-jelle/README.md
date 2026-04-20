# Environment: `fpl-project-jelle`

Last verified: 2026-04-20

This is the primary maintainer's deployment. The runbooks in
[`../../runbooks/`](../../runbooks/) use these concrete values as examples.
If you forked the repo, see [`oss-deploy.md`](../../runbooks/oss-deploy.md)
instead — it walks through the same path with placeholders you swap.

## Pinned identifiers

| Variable | Value |
|---|---|
| `project_id` | `fpl-project-jelle` |
| `region` | `europe-west1` |
| `zone` | `europe-west1-b` |
| Terraform state bucket | `fpl-tf-state-jelle` |
| Artifact Registry repo | `europe-west1-docker.pkg.dev/fpl-project-jelle/mlp-images` |
| `alert_email` | `jwillekes18@gmail.com` |
| Hosted serving service | `mlp-serving-staging` |
| Hosted MLflow service | `mlp-mlflow-staging` |
| Alert router service | `mlp-obs-alert-router` |
| Observability VM | `mlp-obs-vm` (internal IP `10.42.0.100`) |
| GitHub repo | `jellewillekes/ml-lifecycle-platform` |

## Terraform backend-configs

Each root uses the same state bucket with a distinct prefix.

### GCP bootstrap / foundation / staging-infra / MLflow / serving

```bash
cd deployments/gcp/terraform
terraform init \
  -backend-config="bucket=fpl-tf-state-jelle" \
  -backend-config="prefix=ml-lifecycle-platform/gcp/bootstrap"
```

### Observability stack + alerts

```bash
cd deployments/observability/terraform
terraform init \
  -backend-config="bucket=fpl-tf-state-jelle" \
  -backend-config="prefix=ml-lifecycle-platform/observability"
```

## Observability `terraform.tfvars`

The file is gitignored. The committed template is
[`deployments/observability/terraform/terraform.tfvars.example`](../../../deployments/observability/terraform/terraform.tfvars.example).
Current pinned values:

```hcl
project_id = "fpl-project-jelle"
region     = "europe-west1"
zone       = "europe-west1-b"

staging_network_name    = "mlp-staging-vpc"
staging_subnetwork_name = "mlp-staging-subnet"

vm_machine_type         = "e2-medium"
vm_static_internal_ip   = "10.42.0.100"
prometheus_disk_size_gb = 50

grafana_admin_cidr = "127.0.0.1/32"

alert_email        = "jwillekes18@gmail.com"
alert_router_image = "europe-west1-docker.pkg.dev/fpl-project-jelle/mlp-images/alert-router@sha256:<DIGEST>"
```

Pin `alert_router_image` by digest, not `:latest`. Find the current digest
with:

```bash
gcloud artifacts docker images list \
  europe-west1-docker.pkg.dev/fpl-project-jelle/mlp-images/alert-router \
  --include-tags --sort-by=~UPDATE_TIME --limit=1
```

## Cheatsheet

### Trigger alert-router image build

```bash
gh workflow run build-alert-router.yml --ref master
```

### Synthetic webhook test (acceptance)

```bash
TOKEN=$(gcloud secrets versions access latest --secret=mlp-obs-alert-router-token)
ROUTER_URL=$(terraform -chdir=deployments/observability/terraform output -raw alert_router_url)
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)

curl -X POST "$ROUTER_URL" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"alerts\":[{\"status\":\"firing\",\"labels\":{\"alertname\":\"SyntheticTest\"},\"annotations\":{\"summary\":\"manual check\"},\"startsAt\":\"$NOW\",\"fingerprint\":\"manual-$(date +%s)\"}]}"
```

Expect `204`. An email from `Cloud Monitoring <no-reply@google.com>` arrives
at `jwillekes18@gmail.com` within ~3 minutes. A recovery email follows when
the log-based metric drops back to zero.

### Break staging serving on purpose (real alert path)

```bash
gcloud run services update mlp-serving-staging \
  --region=europe-west1 \
  --update-env-vars=FORCE_5XX=1
# revert:
gcloud run services update mlp-serving-staging \
  --region=europe-west1 \
  --remove-env-vars=FORCE_5XX
```

### Rotate the alert-router shared token

```bash
terraform -chdir=deployments/observability/terraform apply \
  -replace=random_password.alert_router_token
```

Then SSH to `mlp-obs-vm` and re-run the startup script (or reboot) so
`grafana.env` re-reads the new secret.

### Grafana admin password

```bash
gcloud secrets versions access latest --secret=mlp-obs-grafana-admin-password
```

UI is at `http://<mlp-obs-vm-external-ip>:3000`, reachable only from the
`grafana_admin_cidr` range set in tfvars.

## Recovery recipes

### Cloud Run v2 service tainted (alert-router)

Symptom: `terraform apply` fails with
`cannot destroy service without setting deletion_protection=false`. Flipping
`deletionProtection` via `gcloud` or REST does not work — it is a
Terraform-provider attribute, not a real Cloud Run API field.

```bash
cd deployments/observability/terraform
terraform untaint google_cloud_run_v2_service.alert_router
terraform apply
```

`deletion_protection = false` is already set in
[`alert_router.tf`](../../../deployments/observability/terraform/alert_router.tf),
so this is an in-place update.

### `Image not found` during alert-router apply

```bash
# confirm the image exists
gcloud artifacts docker images list \
  europe-west1-docker.pkg.dev/fpl-project-jelle/mlp-images/alert-router \
  --include-tags --limit=5

# pin by digest in terraform.tfvars:
# alert_router_image = "...alert-router@sha256:<DIGEST>"

terraform apply
```

Tag-resolution against `:latest` can 404 even when the tag is present in
Artifact Registry. Digest pins do not.
