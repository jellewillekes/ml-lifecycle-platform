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
- `CD / Publish Hosted Images` is the only image producer

Transport path:

- reusable workflow outputs are the normal deploy path
- `image-digests.json` remains the human/debug artifact

Model-state boundary:

- image deploy chooses the runtime container
- MLflow alias state chooses the served model
- do not collapse those two release identities

## Canonical order

Run the GitHub Actions workflow:

- `CD / Release Validation / Staging`

What it does:

1. runs `CD / Publish Hosted Images`
2. deploys hosted MLflow staging
3. deploys hosted serving staging
4. deploys hosted platform jobs staging
5. runs `Ops / Seed Staging Fixture` to create a deterministic hosted release fixture
6. runs hosted `maintenance`
7. runs hosted `reproduce`
8. runs hosted `promote` in `dry_run`
9. runs hosted `rollback` in `dry_run`
10. runs hosted `pipeline`
11. runs hosted serving smoke validation

## Deterministic Fixture

The hosted golden path now prepares staged model state explicitly.

`Ops / Seed Staging Fixture` is an explicit workflow stage. It is not hidden inside MLflow deploy, serving deploy, or Terraform apply.

That stage leaves staging with:

- `breast_cancer_clf@prod` pointing to a promoted version with rollback metadata
- `breast_cancer_clf@candidate` pointing to a newer distinct version
- a candidate that already satisfies the configured promotion policy

This is the state required for both:

- `promote --dry-run`
- `rollback --dry-run`

to be stable golden-path checks instead of depending on whatever staging history was already there.

## Expected success state

After a good hosted golden-path run you should have:

- one source Git SHA
- one digest-pinned MLflow image
- one digest-pinned serving image
- one digest-pinned platform image
- hosted MLflow reachable
- hosted serving reachable
- hosted platform jobs runnable
- `@prod` rollback-ready
- `@candidate` distinct from `@prod` and promotable
- one workflow summary showing the end-to-end pass/fail state

## Failure interpretation

Treat these as different failures:

- deploy failure: runtime did not roll out correctly
- runtime regression: deployed service or job behavior is broken
- fixture-preparation failure: the hosted release fixture was not created correctly
- expected policy-blocked dry-run: promotion or rollback dry-run returned a safe policy block

Do not treat those as the same incident.

## Tearing down

To bring the whole hosted footprint to near-zero cost and rebuild it later from
the same state bucket, see [`teardown-and-restore.md`](teardown-and-restore.md)
(`make gcp-teardown`).
