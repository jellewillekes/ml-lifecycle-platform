# Deploy Serving Staging

Last verified: 2026-03-11

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

Use the manual workflow `.github/workflows/seed-staging-model.yml` to create that hosted staging model state from the committed demo pipeline when needed.

If staging MLflow does not have a `prod` alias yet, `/predict` fails and the deploy workflow should fail.

Serving also depends on hosted MLflow already being live.
If `mlflow_service` is still null in Terraform output, fix MLflow first and rerun serving later.

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
   - `TF_VAR_platform_image=<current-platform-ref@sha256:...>`
5. mint an identity token for the serving service URL
6. run authenticated smoke checks for:
   - `/health`
   - `/metadata/model`
   - `/metadata/schema`
   - `/predict`

The workflow preserves the current MLflow image input on apply.
It also preserves the current platform jobs image input.
That avoids accidental MLflow or platform-job removal when serving is deployed from the shared Terraform root.

Important auth note:

- the workflow mints the Cloud Run ID token with `google-github-actions/auth`
- do not use `gcloud auth print-identity-token --audiences` here
- that failed under the repo's WIF-based deploy path

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
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["uri"])'
)"
TOKEN="$(gcloud auth print-identity-token)"

curl -fsS -H "Authorization: Bearer ${TOKEN}" "${SERVICE_URL}/health"
curl -fsS -H "Authorization: Bearer ${TOKEN}" "${SERVICE_URL}/metadata/model"
curl -fsS -H "Authorization: Bearer ${TOKEN}" "${SERVICE_URL}/metadata/schema"
```

If you need to verify `/predict`, use the workflow smoke path instead of ad hoc requests.

If you need a staged performance reference, run the `Serving Staging Baseline` workflow described in [`serving-staging-baseline.md`](./serving-staging-baseline.md).

## Failure modes

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `mlflow_service output is null` | hosted MLflow not deployed yet | rerun `Deploy MLflow Staging` first |
| serving apply updates MLflow unexpectedly | shared Terraform root missing current MLflow image input | keep resolving `mlflow_service.image` before apply |
| `/health` works but `/predict` fails | no `prod` alias in staged MLflow | register the model and assign `prod` before rerunning |
| metadata endpoints work but model loading fails | serving cannot call hosted MLflow | check `MLFLOW_CLOUD_RUN_AUDIENCE` and `mlp-runtime` `run.invoker` on `mlp-mlflow-staging` |
| deploy workflow cannot resolve serving digest | image was not published for that SHA | rerun `Publish Images` or use the correct `git_sha` |
| response schema or prediction payload fails | model spec drift | check `MODEL_NAME` and `MLP_MODEL_SPEC_PATH` against the registered model |

## Expected success state

After a good deploy you should see:

- workflow summary showing the serving image digest and service URL
- Terraform output `serving_service.uri`
- Cloud Run service `mlp-serving-staging`
- authenticated smoke passed for `/health`, `/metadata/model`, `/metadata/schema`, and `/predict`
