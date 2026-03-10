# GCP Staging Infra

Last verified: 2026-03-10

This runbook covers the stateful hosted staging layer added in `UP-16`.

Current scope:

- staging VPC and subnet
- private service access for Cloud SQL
- Cloud SQL Postgres for hosted MLflow metadata
- MLflow staging secrets in Secret Manager
- outputs for later hosted deploy workflows

Out of scope here:

- MLflow deployment
- serving deployment
- load balancing
- Cloud Run jobs
- scheduler

## Resource contract

Committed staging names:

- VPC: `mlp-staging-vpc`
- subnet: `mlp-staging-subnet`
- Cloud SQL instance: `mlp-mlflow-staging`
- database: `mlflow`
- database user: `mlflow`
- artifact root: `gs://fpl-project-jelle-mlp-artifacts/mlflow/`

The runtime service account remains:

- `mlp-runtime@<project>.iam.gserviceaccount.com`

## Managed APIs

This layer extends the Terraform root with:

- `compute.googleapis.com`
- `servicenetworking.googleapis.com`
- `sqladmin.googleapis.com`

## Secrets added for hosted MLflow staging

- `mlp-mlflow-db-user`
- `mlp-mlflow-db-password`
- `mlp-mlflow-db-name`
- `mlp-mlflow-instance-connection-name`
- `mlp-mlflow-artifact-root`

These are the active hosted-staging MLflow secrets.

The older placeholder secrets from the foundation layer still exist, but they are not the primary `UP-16` contract.

## Operator flow

From the repo root:

```bash
make terraform-gcp-fmt
make terraform-gcp-init
make terraform-gcp-validate
make terraform-gcp-plan
make terraform-gcp-apply
```

## Outputs used by later tickets

Most important outputs:

- `staging_network`
- `mlflow_sql`
- `mlflow_secret_ids`

These outputs should feed:

- `UP-17` hosted MLflow deploy wiring
- `UP-18` serving runtime wiring

## Manual verification

After apply:

```bash
gcloud compute networks describe mlp-staging-vpc --project fpl-project-jelle
gcloud sql instances describe mlp-mlflow-staging --project fpl-project-jelle
gcloud sql databases list --instance mlp-mlflow-staging --project fpl-project-jelle
gcloud secrets list --project fpl-project-jelle
terraform -chdir=deployments/gcp/terraform output
```

Check specifically:

- Cloud SQL has private IP only
- the `mlflow` database exists
- the new MLflow secrets exist
- outputs expose enough data for later deploy work

## What comes next

`UP-17` should deploy hosted MLflow on Cloud Run using:

- `mlflow_sql.connection_name`
- `mlflow_sql.artifact_root`
- `mlflow_secret_ids`

Do not deploy MLflow or serving from this ticket.
