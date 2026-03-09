# Handbook

Start here if you want to run or change the local platform.

## Golden path

1. Read [`runbooks/local-bootstrap.md`](./runbooks/local-bootstrap.md).
2. Follow the commands exactly in order.
3. Use the other runbooks only when you need a specific registry operation.

## Architecture

- [`architecture/overview.md`](./architecture/overview.md): platform shape, control plane, lifecycle
- [`architecture/local-runtime.md`](./architecture/local-runtime.md): runtime profiles, model specs, serving contract, local paths
- [`architecture/current-state.md`](./architecture/current-state.md): current M0 scope and non-goals

## Runbooks

- [`runbooks/local-bootstrap.md`](./runbooks/local-bootstrap.md): fresh-clone local setup and golden path
- [`runbooks/promotion.md`](./runbooks/promotion.md): dry-run and real promotion
- [`runbooks/rollback.md`](./runbooks/rollback.md): rollback current prod
- [`runbooks/reproduce.md`](./runbooks/reproduce.md): reproduce a registered model

## Delivery docs

- [`ci.md`](./ci.md): CI lanes and local mapping
- [`releases.md`](./releases.md): package releases and model release evidence
- [`adrs/ADR-0001-portability-surface.md`](./adrs/ADR-0001-portability-surface.md): M0 portability boundary
- [`adrs/ADR-0002-mlflow-control-plane.md`](./adrs/ADR-0002-mlflow-control-plane.md): MLflow as M0 control plane
