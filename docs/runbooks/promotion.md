# Promotion

Use this runbook to move the current candidate to `prod`.

## Preconditions

- local infra is running when you use the Docker-backed Makefile path
- a candidate model version exists for the target model
- the candidate has the metadata required by the model spec policy

## Dry-run the policy

Default model from the active runtime profile:

```bash
make policy-check
```

Explicit model:

```bash
uv run mlp --env local registry promote --model-name breast_cancer_clf --dry-run --format json
```

Success means the command exits `0` and prints `allowed: true` in JSON output.

## Apply promotion

Default model:

```bash
make promote
```

Explicit model:

```bash
uv run mlp --env local registry promote --model-name breast_cancer_clf
```

## What promotion changes

- moves `@prod` to the candidate version
- moves `@champion` to the same version
- sets `release_status=prod` on the promoted model version
- records `promoted_from_alias=candidate`
- records `previous_prod_version` when an older prod version existed
- emits release evidence under `reports/releases/promote/<model_name>/v<version>/`

## Evidence to inspect

Promotion writes:

- `promotion_decision.json`
- `release_manifest.json`
- `rollback_target.json`
- `model_card.md`

The promoted model version also records the artifact paths in tags:

- `release_reports_path`
- `promotion_decision_path`
- `release_manifest_path`
- `rollback_target_path`
- `model_card_path`

## Common failure cases

- no candidate alias exists
- gate status is not `passed`
- required metadata tags are missing
- policy blocks noop promotion
- a model-spec policy override requires extra reproducibility evidence or metrics

If promotion fails, rerun the dry-run command with `--format json` and inspect the returned violations.
