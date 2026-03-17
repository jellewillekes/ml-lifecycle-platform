# Handbook

Start here if you want to run or change the local platform.

## Golden path

1. Read [`runbooks/local-bootstrap.md`](./runbooks/local-bootstrap.md).
2. Start with `uv sync --dev`.
3. Use `make e2e` for the fastest end-to-end validation.
4. Use the manual runbooks only when you need to inspect one step at a time.

## Architecture

- [`architecture/how-it-works.md`](./architecture/how-it-works.md): fastest current explanation of the local path, hosted staging path, operator flows, and live boundaries
- [`architecture/overview.md`](./architecture/overview.md): current local and hosted topology, boundaries, and lifecycle
- [`architecture/local-runtime.md`](./architecture/local-runtime.md): runtime profiles, model specs, serving contract, local paths
- [`architecture/current-state.md`](./architecture/current-state.md): current implemented scope and non-goals
- [`architecture/m2-staging-platform.md`](./architecture/m2-staging-platform.md): fixed decisions and execution order for the first hosted GCP staging platform

## Runbooks

- [`runbooks/local-bootstrap.md`](./runbooks/local-bootstrap.md): fresh-clone local setup and golden path
- [`runbooks/gcp-bootstrap.md`](./runbooks/gcp-bootstrap.md): adopt the existing GCP project and Terraform backend
- [`runbooks/gcp-foundation.md`](./runbooks/gcp-foundation.md): create the first hosted GCP foundation resources
- [`runbooks/gcp-staging-infra.md`](./runbooks/gcp-staging-infra.md): provision the stateful staging infra for hosted MLflow
- [`runbooks/deploy-mlflow.md`](./runbooks/deploy-mlflow.md): build, deploy, and verify hosted MLflow staging
- [`runbooks/deploy-serving.md`](./runbooks/deploy-serving.md): deploy the serving API to hosted staging and run authenticated smoke checks
- [`runbooks/deploy-platform-jobs.md`](./runbooks/deploy-platform-jobs.md): deploy hosted Cloud Run jobs and run them manually
- [`runbooks/schedule-platform-jobs.md`](./runbooks/schedule-platform-jobs.md): inspect, pause, resume, and verify Cloud Scheduler for hosted jobs
- [`runbooks/serving-staging-baseline.md`](./runbooks/serving-staging-baseline.md): run the first advisory k6 baseline against hosted serving staging
- [`runbooks/gcp-ci-auth.md`](./runbooks/gcp-ci-auth.md): verify GitHub Actions OIDC auth into GCP
- [`runbooks/promotion.md`](./runbooks/promotion.md): dry-run and real promotion
- [`runbooks/rollback.md`](./runbooks/rollback.md): rollback current prod
- [`runbooks/reproduce.md`](./runbooks/reproduce.md): reproduce a registered model

## Delivery docs

- [`ci.md`](./ci.md): CI lanes and local mapping
- [`releases.md`](./releases.md): package releases and model release evidence
- [`reference/technology-stack.md`](./reference/technology-stack.md): primary tools, why they are used, and where they fit
- [`reference/configuration.md`](./reference/configuration.md): runtime profiles, env vars, serving settings, and hosted staging secrets
- [`reference/release-contract.md`](./reference/release-contract.md): package, image, and model release identities
- [`reference/gcp-resources.md`](./reference/gcp-resources.md): current Terraform-managed GCP resource inventory and outputs
- [`adrs/ADR-0001-portability-surface.md`](./adrs/ADR-0001-portability-surface.md): M0 portability boundary
- [`adrs/ADR-0002-mlflow-control-plane.md`](./adrs/ADR-0002-mlflow-control-plane.md): MLflow as M0 control plane
