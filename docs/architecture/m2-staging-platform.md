# M2 Staging Platform

Last verified: 2026-03-10

This document locks the intended shape for `M2`: the first hosted GCP staging platform.

The goal is simple:

- stand up one boring hosted staging path on GCP
- prove MLflow and serving work end to end
- add edge and orchestration only after the runtime path is already healthy

## Fixed decisions

These decisions should not be reopened in every PR unless a concrete blocker appears.

- MLflow remains the control plane.
- Deploy workloads by image digest, not mutable tag.
- Reuse `gs://fpl-project-jelle-mlp-artifacts` for hosted MLflow artifacts.
- Use Cloud SQL Postgres with private IP for hosted MLflow metadata.
- Use direct Cloud Run URLs plus IAM auth for staging before adding an external load balancer.
- Reuse `mlp-runtime@<project>.iam.gserviceaccount.com` for early hosted workloads unless tighter separation is clearly needed.

## Naming

Use fixed boring names:

- Cloud SQL instance: `mlp-mlflow-staging`
- MLflow service: `mlp-mlflow-staging`
- serving service: `mlp-serving-staging`

Do not rename targets or introduce alternate image names in `M2`.

## Implementation order

The intended order is:

1. `UP-16`: Cloud SQL, artifact root, secrets, and network wiring
2. `UP-17`: hosted MLflow on Cloud Run
3. `UP-18`: hosted serving on Cloud Run staging
4. `UP-19`: `k6` baseline against hosted serving
5. `UP-20`: HTTPS edge with external Application Load Balancer
6. `UP-21`: Cloud Run jobs for platform actions
7. `UP-22`: Cloud Scheduler on top of existing hosted jobs

Do not skip ahead. Each step depends on the previous one being operationally boring first.

## Deploy contracts

Hosted deploys should consume image digests from the publish workflow artifact contract in [`../ci.md`](../ci.md).

Expected pattern:

- `platform` image digest for jobs
- `serving` image digest for the inference API

Container image identity and model release identity stay separate:

- image deploy chooses the runtime bits
- MLflow alias and model version choose the served model

## Staging access model

Until `UP-20` lands:

- MLflow staging uses Cloud Run direct URL plus IAM auth
- serving staging uses Cloud Run direct URL plus IAM auth
- CI smoke tests must authenticate as an allowed invoker

Do not add public anonymous staging endpoints first and tighten them later unless there is a concrete need.

## Smoke tests by phase

`UP-17` should prove:

- MLflow revision is ready
- authenticated request succeeds
- MLflow can use Cloud SQL and GCS

`UP-18` should prove:

- serving revision is ready
- `/health` succeeds
- `/metadata/model` succeeds
- `/metadata/schema` succeeds
- `/predict` succeeds against staged model state

`UP-19` should establish:

- one realistic `/predict` path
- one light sustained-load path
- latency and error thresholds

`UP-21` should prove:

- at least one safe hosted execution path per job family
- `promote --dry-run` is a good first hosted proof

## New invariant after UP-18

Once hosted serving staging is live:

- local green
- GCP staging green

Do not merge follow-up hosted changes that only work locally after this point.

## Explicitly deferred from M2

Still out of scope here:

- production rollout
- environment promotion logic
- multi-region topology
- alternate release-control system
- scheduler-driven orchestration before jobs are already healthy
- ALB before direct hosted serving is already proven
