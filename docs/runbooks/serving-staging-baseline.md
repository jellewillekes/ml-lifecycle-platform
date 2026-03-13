# Serving Staging Baseline

Last verified: 2026-03-11

This runbook covers the first hosted serving performance baseline added in `UP-19`.

Current scope:

- run one warmed realistic `/predict?mode=prod` scenario
- run one light sustained-load `/predict?mode=prod` scenario
- keep the baseline against the direct Cloud Run URL before `UP-20` adds an edge
- store machine-readable and human-readable baseline artifacts

Out of scope here:

- full performance suite
- autoscaling tuning
- merge-blocking performance gate
- ALB path validation

## Preconditions

Before this workflow is useful, staging serving must already be healthy:

- hosted MLflow staging is live
- hosted serving staging is live
- the staged model has a working `prod` alias
- the normal authenticated smoke path passes

If smoke is red, fix that first. `UP-19` is a baseline, not a deploy debugger.

## Workflow

Run the GitHub Actions workflow:

- `Serving Staging Baseline`

Inputs:

- `git_sha` optional label for the report
- `duration` default `5m`
- `rate` default `1`
- `realistic_iterations` default `25`
- `notes` optional operator notes

What it does:

1. authenticates to GCP with WIF
2. resolves the current `serving_service` Terraform output
3. mints an IAM-authenticated Cloud Run ID token
4. runs the existing hosted serving smoke test as a preflight
5. writes a baseline context artifact
6. runs k6 against the direct staging service URL
7. exports `k6-summary.json`, `k6-output.txt`, and `k6-summary.md`
8. uploads the artifacts for later comparison

The workflow is advisory for now.
Threshold failures should be investigated, but they do not act as a blocking performance gate in `M2`.

## Baseline shape

The baseline intentionally stays small:

- `realistic_predict`
  - one valid request body
  - 1 VU
  - default `25` iterations
- `light_sustained_predict`
  - `constant-arrival-rate`
  - default `1` request per second
  - default `5` minutes

Both scenarios hit:

- `POST /predict?mode=prod`

The request payload is the committed demo-model payload in:

- `perf/k6/payloads/breast_cancer_clf_prod.json`

## Thresholds

Current advisory thresholds:

- `http_req_failed`: `rate < 0.01`
- `checks`: `rate > 0.99`
- `http_req_duration{scenario:realistic_predict}`:
  - `p(95) < 1000`
  - `p(99) < 1500`
- `http_req_duration{scenario:light_sustained_predict}`:
  - `p(95) < 1500`
  - `p(99) < 2500`

These are intentionally conservative for the first direct-Cloud-Run hosted baseline.

## Artifacts

Each run uploads:

- `baseline-context.json`
- `k6-summary.json`
- `k6-output.txt`
- `k6-summary.md`

Use `baseline-context.json` to confirm:

- which service URL was tested
- which serving image was live
- which optional Git SHA label was attached
- which scenario settings were used

## Comparing baselines

Manual comparison is enough for `UP-19`.

Compare these fields between runs:

- error rate
- total request count
- `realistic_predict` p95 and p99
- `light_sustained_predict` p95 and p99
- serving image digest
- scenario settings

Do not compare two runs if:

- one was taken before a deploy and one after
- duration or rate changed
- the staging service was unhealthy before the run

## Expected success state

A good baseline run gives you:

- a green smoke preflight
- uploaded baseline artifacts
- a markdown summary in the workflow summary
- one concrete hosted performance reference before `UP-20`
