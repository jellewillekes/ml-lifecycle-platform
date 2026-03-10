# Deploy MLflow Staging

Last verified: 2026-03-10

This runbook covers the hosted MLflow staging deploy path added in `UP-17`.

Current scope:

- build the hosted MLflow image from committed source
- push the image to Artifact Registry
- deploy Cloud Run service `mlp-mlflow-staging`
- use Cloud SQL as the backend store
- use GCS through MLflow artifact proxying
- verify the service with an authenticated smoke test

Out of scope here:

- serving deploy
- ALB or custom domain
- public anonymous access

## Resource contract

Service:

- Cloud Run service: `mlp-mlflow-staging`
- port: `5000`
- access: IAM-authenticated only

Image:

- Artifact Registry repository: `europe-west1-docker.pkg.dev/fpl-project-jelle/mlp-images`
- image name: `mlflow`
- deploy by digest, not tag

Runtime wiring:

- Cloud SQL instance: `mlp-mlflow-staging`
- database: `mlflow`
- artifact destination: `gs://fpl-project-jelle-mlp-artifacts/mlflow/`
- runtime service account: `mlp-runtime@fpl-project-jelle.iam.gserviceaccount.com`

## Important bootstrapping rule

The deploy workflow uses the CI service account through GitHub OIDC.

That service account cannot grant itself new deploy permissions from nothing.
So the first apply for this PR still has a manual bootstrap step:

1. apply the Terraform root once with local operator credentials so the new CI deploy IAM bindings and `run.googleapis.com` exist
2. after that, use the `Deploy MLflow Staging` workflow for normal image build, deploy, and smoke verification

Bootstrap apply:

```bash
make terraform-gcp-init
make terraform-gcp-apply
```

That first apply can run with `mlflow_image = ""`. It enables the API and grants the CI service account the deploy permissions it needs later.

## Normal deploy path

Run the GitHub Actions workflow:

- `Deploy MLflow Staging`

What it does:

1. authenticate to GCP with WIF
2. build the hosted MLflow image from `deployments/gcp/mlflow/`
3. push `mlflow:<git-sha>` to Artifact Registry
4. resolve the pushed digest
5. apply Terraform with `TF_VAR_mlflow_image=<ref@sha256:...>`
6. mint an identity token for the Cloud Run URL
7. verify authenticated MLflow metadata and artifact writes

## Runtime env contract

The hosted MLflow image expects:

- `MLFLOW_HOST`
- `MLFLOW_PORT`
- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `ARTIFACTS_DESTINATION`

The service starts MLflow with:

- `--backend-store-uri postgresql://...`
- `--artifacts-destination gs://...`
- `--serve-artifacts`

This is intentional. Artifact proxying keeps Cloud Run clients from needing direct GCS credentials.

## Smoke verification

The smoke path proves three things:

1. authenticated HTTP access works
2. MLflow can write metadata to Cloud SQL
3. MLflow can log and list an artifact through the proxied artifact path

The workflow uses:

- `gcloud auth print-identity-token`
- `MLFLOW_TRACKING_TOKEN`
- `scripts/verify_mlflow_staging.py`

The smoke script creates a unique experiment, starts a run, logs one param, logs one text artifact, and checks that the artifact can be listed back through MLflow.

## Manual verification

After a successful deploy:

```bash
terraform -chdir=deployments/gcp/terraform output
gcloud run services describe mlp-mlflow-staging --region=europe-west1 --project=fpl-project-jelle
```

To test the root path manually:

```bash
SERVICE_URL="$(
  terraform -chdir=deployments/gcp/terraform output -json mlflow_service \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["value"]["uri"])'
)"
TOKEN="$(gcloud auth print-identity-token --audiences="${SERVICE_URL}")"
curl -fsS -H "Authorization: Bearer ${TOKEN}" "${SERVICE_URL}/"
```

If you need a richer check, rerun the workflow smoke step instead of ad hoc shell calls.

## Failure modes

If the service deploys but smoke fails:

- check Cloud Run revision logs first
- check the service can reach Cloud SQL private IP
- check the runtime service account still has bucket and secret access
- check the service is running the digest the workflow just pushed

Common root causes:

- `run.googleapis.com` not enabled yet
- CI service account missing `run.admin` or `iam.serviceAccountUser`
- bad Cloud SQL private IP or network wiring
- hosted MLflow image missing `google-cloud-storage`
- artifact proxying not enabled
