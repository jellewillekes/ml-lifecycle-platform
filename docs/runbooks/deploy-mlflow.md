# Deploy MLflow Staging

Last verified: 2026-03-11

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

## Bootstrap prerequisites

The deploy workflow uses the CI service account through GitHub OIDC + Workload Identity Federation.

Two things must already exist before the workflow can work reliably:

1. the Terraform root must have been applied once with operator credentials so the Cloud Run API and CI deploy IAM bindings exist
2. `mlp-ci` must have manual bucket IAM outside this Terraform root

Bootstrap apply:

```bash
make terraform-gcp-init
make terraform-gcp-apply
```

Required manual grants:

- `roles/storage.objectAdmin` on `gs://fpl-tf-state-jelle`
- `roles/storage.admin` on `gs://fpl-project-jelle-mlp-artifacts`
- `roles/storage.admin` on `gs://fpl-project-jelle-mlp-data`

Why these are manual:

- the backend state bucket is not owned by this Terraform root
- Terraform cannot use `mlp-ci` to grant `mlp-ci` the bucket IAM it already needs to run Terraform

After that bootstrap apply, `Deploy MLflow Staging` is the normal deploy path.

## Normal deploy path

Run the GitHub Actions workflow:

- `Deploy MLflow Staging`

What it does:

1. authenticate to GCP with WIF
2. build the hosted MLflow image from `deployments/gcp/mlflow/`
3. push `mlflow:<git-sha>` to Artifact Registry
4. resolve the pushed digest
5. apply Terraform with `TF_VAR_mlflow_image=<ref@sha256:...>`
   and preserve:
   - `TF_VAR_serving_image=<current-serving-ref@sha256:...>`
   - `TF_VAR_platform_image=<current-platform-ref@sha256:...>`
6. mint an identity token for the Cloud Run URL
7. verify authenticated MLflow metadata and artifact writes

Important auth note:

- the workflow uses `google-github-actions/auth` to mint the Cloud Run ID token
- do not use `gcloud auth print-identity-token --audiences` here
- that fails under this WIF setup

Shared-root note:

- the Terraform root still manages MLflow, serving, and platform jobs together
- MLflow deploy must preserve the current serving and platform images on apply
- otherwise an MLflow-only apply can unintentionally remove those runtime paths

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

- `google-github-actions/auth`
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
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["uri"])'
)"
TOKEN="$(gcloud auth print-identity-token)"
curl -fsS -H "Authorization: Bearer ${TOKEN}" "${SERVICE_URL}/"
```

If you need a richer check, rerun the workflow smoke step instead of ad hoc shell calls.

## Failure modes

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `storage.objects.create` denied on `.tflock` | `mlp-ci` missing state bucket access | grant `roles/storage.objectAdmin` on `gs://fpl-tf-state-jelle` |
| `storage.buckets.getIamPolicy` denied on app bucket | `mlp-ci` missing app bucket IAM admin | grant `roles/storage.admin` on the artifacts and data buckets |
| `unexpected EOF while looking for matching ')'` | broken heredoc shell in workflow | keep Terraform output parsing as simple `python3 -c` commands |
| `KeyError: 'value'` while reading Terraform output | wrong assumption about `terraform output -json <name>` | parse the raw JSON object, not a nested `value` field |
| `Invalid account type for --audiences` | wrong token minting path under WIF | mint the ID token with `google-github-actions/auth` |
| MLflow deploy succeeds but smoke fails | runtime cannot reach Cloud SQL or GCS | check Cloud Run revision logs, secret access, network wiring, and artifact proxying |

## Expected success state

After a good deploy you should see:

- workflow summary showing image digest, service URL, and successful verification
- Terraform output `mlflow_service.uri`
- Cloud Run service `mlp-mlflow-staging`
- authenticated smoke passed for metadata write and artifact write
