# Handbook

Start here if you want to run or change the local platform.

## Golden path

1. Read [`runbooks/local-bootstrap.md`](./runbooks/local-bootstrap.md).
2. Start with `uv sync --dev`.
3. Use `make e2e` for the fastest end-to-end validation.
4. Use the manual runbooks only when you need to inspect one step at a time.

## Architecture

- [`architecture/overview.md`](./architecture/overview.md): platform shape, control plane, lifecycle
- [`architecture/local-runtime.md`](./architecture/local-runtime.md): runtime profiles, model specs, serving contract, local paths
- [`architecture/current-state.md`](./architecture/current-state.md): current M0 scope and non-goals

## Runbooks

- [`runbooks/local-bootstrap.md`](./runbooks/local-bootstrap.md): fresh-clone local setup and golden path
- [`runbooks/gcp-bootstrap.md`](./runbooks/gcp-bootstrap.md): adopt the existing GCP project and Terraform backend
- [`runbooks/promotion.md`](./runbooks/promotion.md): dry-run and real promotion
- [`runbooks/rollback.md`](./runbooks/rollback.md): rollback current prod
- [`runbooks/reproduce.md`](./runbooks/reproduce.md): reproduce a registered model

## Delivery docs

- [`ci.md`](./ci.md): CI lanes and local mapping
- [`releases.md`](./releases.md): package releases and model release evidence
- [`reference/technology-stack.md`](./reference/technology-stack.md): primary tools, why they are used, and where they fit
- [`adrs/ADR-0001-portability-surface.md`](./adrs/ADR-0001-portability-surface.md): M0 portability boundary
- [`adrs/ADR-0002-mlflow-control-plane.md`](./adrs/ADR-0002-mlflow-control-plane.md): MLflow as M0 control plane
