# Security hygiene

This page is the contributor and maintainer contract for secret, credential, and
workflow-log hygiene in this repo. It is not a compliance standard; it is the
minimum bar the repo already meets and expects every contributor to preserve.

## Rules

### Do not commit credentials

- No API keys, bearer tokens, private keys, service-account JSON, or database
  passwords in `configs/`, `deployments/`, `scripts/`, or any tracked file.
- No real tenant IDs, workload identity pool IDs, or service-account emails in
  example configs. Use `unused` or `*.invalid` markers in non-default runtime
  profiles.
- Local-only Compose defaults (`minioadmin` in `deployments/local/docker-compose.yml`)
  are acceptable because they are scoped to the local stack and documented as such.

### Do not log secret values in workflows

- Never `echo`, `cat`, or `tee` a token, bearer credential, access key, or
  password into workflow logs or `GITHUB_STEP_SUMMARY`.
- Never dump the runner environment (`env`, `printenv`, `set`) in a step. If a
  debug dump is genuinely needed, gate it behind `ACTIONS_STEP_DEBUG` and filter
  to known non-secret names.
- Step summaries should contain image refs, service URLs, and operator
  outcomes — not auth headers or credential file paths.

### Keep credentials short-lived and runner-local

- Use Workload Identity Federation (WIF) via `google-github-actions/auth` with
  the repo's existing `GCP_WIF_PROVIDER` variable. No long-lived service
  account keys.
- Only request an ADC credentials file (`create_credentials_file: true`) when a
  later step actually needs ADC (gcloud, Terraform, Docker registry login).
  Auth steps that only mint an ID token (`token_format: id_token`) should set
  `create_credentials_file: false` to avoid emitting a redundant `gha-creds-*.json`
  file path into logs.
- The v3 auth action cleans up the credentials file at job end by default.
  Do not disable `cleanup_credentials`.
- Use `docker login --password-stdin` so the access token never appears on the
  command line.

### Prefer resource names by reference

- When a workflow needs a Secret Manager name, Cloud Run service URL, or
  Artifact Registry repository, pull it from a GitHub Actions variable
  (`vars.GCP_PROJECT_ID`, etc.) or a Terraform output resolved at runtime.
- Do not paste operational identifiers into step scripts when they can be
  resolved from the environment.

### Tighten config hygiene

- Every field in a runtime profile is consumed by `runtime/profile.py`.
  When a field is not meaningful for a given environment (for example,
  `compose_*` in staging), set it to an explicit `unused` or `*.invalid`
  marker rather than leaving a local-looking value that implies the profile
  runs Compose.
- Do not duplicate secret names across config files. Secret names live in
  Terraform; runtime profiles reference them by environment variable.

## Scope and non-goals

- This page is a hygiene contract, not an IAM or ingress design document.
- It does not attempt to hide all resource names from operators. Resource
  names that aid operator debugging (project IDs, service account emails in
  error messages) are intentionally visible.
- It does not replace `CodeQL`, `Gitleaks`, or `Zizmor`. Those run on every
  PR and are the enforcement layer.

## Where enforcement lives

- `Gitleaks` scans every PR for committed credentials.
- `CodeQL` scans source for auth-path vulnerabilities.
- `Zizmor` lints the workflow surface for Actions-specific security smells.
- `scripts/precommit_block_forbidden_tracked_paths.sh` blocks generated or
  cache paths from entering the index.

See [`ci.md`](../ci.md) for the full security-workflow matrix.
