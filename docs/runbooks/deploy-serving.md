# Deploy Serving Staging

Last verified: 2026-03-10

This runbook covers the hosted serving staging deploy path added in `UP-18`.

Current scope:

- resolve a published `serving` image by immutable Git SHA
- deploy Cloud Run service `mlp-serving-staging` by digest
- point serving at the hosted MLflow staging service
- require IAM-authenticated access
- verify the service with authenticated smoke tests

Out of scope here:

- ALB or custom domain
- public anonymous access
- scheduler or hosted jobs
- model promotion automation

## Resource contract

Service:

- Cloud Run service: `mlp-serving-staging`
- port: `8000`
- access: IAM-authenticated only

Image:

- Artifact Registry repository: `europe-west1-docker.pkg.dev/fpl-project-jelle/mlp-images`
- image name: `serving`
- deploy by digest, not tag

Runtime wiring:

- MLflow service: `mlp-mlflow-staging`
- runtime service account: `mlp-runtime@fpl-project-jelle.iam.gserviceaccount.com`
- model name: `breast_cancer_clf`
- model spec: `configs/models/breast_cancer_demo.yaml`

## Important precondition

Serving deploy and model release are separate.

Before the first staging smoke test can pass, hosted MLflow must already contain:

- registered model `breast_cancer_clf`
- a `prod` alias pointing at a valid version

Do not hide that inside serving deploy.

If staging MLflow does not have a `prod` alias yet, `/predict` fails and the deploy workflow should fail.

## Normal deploy path

Run the GitHub Actions workflow:

- `Deploy Serving Staging`

Required input:

- `git_sha`: the immutable SHA tag published by `Publish Images`

What it does:

1. authenticate to GCP with WIF
2. resolve `serving:<git-sha>` from Artifact Registry
3. resolve the current hosted MLflow image from Terraform output
4. apply Terraform with:
   - `TF_VAR_mlflow_image=<current-mlflow-ref@sha256:...>`
   - `TF_VAR_serving_image=<serving-ref@sha256:...>`
5. mint an identity token for the serving service URL
6. run authenticated smoke checks for:
   - `/health`
   - `/metadata/model`
   - `/metadata/schema`
   - `/predict`

The workflow preserves the current MLflow image input on apply.
That avoids accidental MLflow removal when serving is deployed from the shared Terraform root.

## Runtime env contract

The hosted serving service uses:

- `MLP_ENV=staging`
- `MLFLOW_TRACKING_URI=<mlflow service URL>`
- `MLFLOW_REGISTRY_URI=<mlflow service URL>`
- `MLFLOW_CLOUD_RUN_AUDIENCE=<mlflow service URL>`
- `MODEL_NAME=breast_cancer_clf`
- `MLP_MODEL_SPEC_PATH=configs/models/breast_cancer_demo.yaml`
- `PROD_ALIAS=prod`
- `CANDIDATE_ALIAS=candidate`
- `CANARY_PCT=10`
- `MODEL_CACHE_TTL_SEC=60`
- `LOG_LEVEL=INFO`

The key hosted-only setting is:

- `MLFLOW_CLOUD_RUN_AUDIENCE`

When it is set, MLflow client requests carry a Google ID token for the hosted MLflow Cloud Run audience.

## Manual verification

After a successful deploy:

```bash
terraform -chdir=deployments/gcp/terraform output
gcloud run services describe mlp-serving-staging --region=europe-west1 --project=fpl-project-jelle
```

To call the service manually:

```bash
SERVICE_URL="$(
  terraform -chdir=deployments/gcp/terraform output -json serving_service \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["value"]["uri"])'
)"
TOKEN="$(gcloud auth print-identity-token --audiences="${SERVICE_URL}")"

curl -fsS -H "Authorization: Bearer ${TOKEN}" "${SERVICE_URL}/health"
curl -fsS -H "Authorization: Bearer ${TOKEN}" "${SERVICE_URL}/metadata/model"
curl -fsS -H "Authorization: Bearer ${TOKEN}" "${SERVICE_URL}/metadata/schema"
```

If you need to verify `/predict`, use the workflow smoke path instead of ad hoc requests.

## Failure modes

If the service deploys but smoke fails:

- check Cloud Run revision logs first
- check `mlp-runtime` still has `run.invoker` on `mlp-mlflow-staging`
- check serving env vars point at the hosted MLflow URL, not local defaults
- check the staged model really has a `prod` alias
- check `MODEL_NAME` and `MLP_MODEL_SPEC_PATH` still match

Common root causes:

- hosted MLflow not deployed yet
- hosted MLflow missing `prod` alias for the configured model
- serving image digest does not exist in Artifact Registry
- wrong Cloud Run audience token on MLflow requests
- model spec drift between committed config and the staged model
