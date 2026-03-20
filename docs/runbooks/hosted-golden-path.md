# Hosted Golden Path Staging

Last verified: 2026-03-20

This runbook covers the canonical hosted end-to-end validation path for staging.

Current scope:

- publish hosted runtime images once
- deploy MLflow, serving, and platform jobs from digest-pinned Artifact Registry refs
- validate the staged hosted path in one documented order

Out of scope here:

- package release management
- production rollout
- Cloud Deploy adoption

## Contract

Runtime release identity:

- Artifact Registry image refs pinned by digest
- `Publish Images` is the only image producer

Transport path:

- reusable workflow outputs are the normal deploy path
- `image-digests.json` remains the human/debug artifact

Model-state boundary:

- image deploy chooses the runtime container
- MLflow alias state chooses the served model
- do not collapse those two release identities

## Canonical order

Run the GitHub Actions workflow:

- `Hosted Golden Path Staging`

What it does:

1. runs `Publish Images`
2. deploys hosted MLflow staging
3. deploys hosted serving staging
4. deploys hosted platform jobs staging
5. checks the staged `prod` alias precondition
6. runs hosted `maintenance`
7. runs hosted `reproduce`
8. runs hosted `promote` in `dry_run`
9. runs hosted `rollback` in `dry_run`
10. runs hosted `pipeline`
11. runs hosted serving smoke validation

## Important precondition

The hosted golden path does not silently seed staged MLflow model state.

If hosted MLflow does not currently resolve:

- `breast_cancer_clf@prod`

the golden path fails with an explicit message and points the operator to:

- `Seed Hosted Staging Model`

That is intentional.
Model-state bootstrapping should stay explicit instead of being hidden inside serving deploy or the hosted golden path.

## Expected success state

After a good hosted golden-path run you should have:

- one source Git SHA
- one digest-pinned MLflow image
- one digest-pinned serving image
- one digest-pinned platform image
- hosted MLflow reachable
- hosted serving reachable
- hosted platform jobs runnable
- one workflow summary showing the end-to-end pass/fail state

## Failure interpretation

Treat these as different failures:

- deploy failure: runtime did not roll out correctly
- runtime regression: deployed service or job behavior is broken
- model-state-precondition failure: staged alias state was not ready
- expected policy-blocked dry-run: promotion or rollback dry-run returned a safe policy block

Do not treat those as the same incident.
