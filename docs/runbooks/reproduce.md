# Reproduce

Use this runbook to rebuild a registered model from its source training run.

## Select the target model version

Pick exactly one selector:

- `--alias <alias>`
- `--model-version <version>`

Examples:

```bash
make reproduce ALIAS=prod MODEL_NAME=breast_cancer_clf
```

```bash
uv run mlp --env local registry reproduce --model-name breast_cancer_clf --model-version 1 --report-path reproduce_report.json --format json
```

## Outputs

Reproduce writes two outputs:

- a local JSON report at `--report-path`
- a release evidence bundle in MLflow under `reports/releases/reproduce/<model_name>/v<version>/`

The local report is the direct command result. The MLflow bundle keeps the same evidence shape used by promotion and rollback.

## What reproduce verifies

- the registered model version has `source_run_id`
- the current checkout git SHA matches the source training run
- the current `uv.lock` hash matches the source training run
- the logged repro contract reproduces the config hash
- downloaded training inputs reproduce the dataset fingerprint
- probe predictions match the logged expected outputs

## Common failure cases

Current failure reasons include:

- `missing_source_run_id`
- `missing_repro_contract`
- `git_sha_mismatch`
- `env_lock_mismatch`
- `config_hash_mismatch`
- `dataset_fingerprint_mismatch`
- `prediction_parity_failed`

The command exits non-zero and writes a failed report when one of these checks fails.

## Verify success

After a successful run:

- the local report has `status: matched`
- `reports/releases/reproduce/.../release_manifest.json` exists in MLflow
- the manifest records the same source run ID and model version you selected
