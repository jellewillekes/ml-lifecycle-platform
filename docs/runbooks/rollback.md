# Rollback

Use this runbook to move `@prod` back to the recorded previous prod version.

## Preconditions

- the target model has a current `@prod`
- the current prod was previously promoted with rollback metadata recorded

## Run rollback

Default model:

```bash
make rollback-prod
```

Explicit model:

```bash
uv run mlp --env local registry rollback --model-name breast_cancer_clf
```

## How target resolution works

Rollback resolves in this order:

1. current prod model version tag `release_manifest_path`
2. current prod version's `release_manifest.json`
3. `previous_prod_version` tag fallback for older versions

The manifest is the primary operator-facing rollback record.

## What rollback changes

- moves `@prod` to the recorded previous prod version
- updates `previous_prod_version` on the rollback target to allow one-step undo
- emits release evidence under `reports/releases/rollback/<model_name>/v<current_prod_version>/`

## Verify rollback

Verify after the command:

- `@prod` points to the expected version in MLflow
- `rollback_target.json` records the resolved target version
- `release_manifest.json` records the before and after prod versions

If rollback fails because no previous prod exists, inspect the current prod model version tags and confirm `release_manifest_path` or `previous_prod_version` is present.
