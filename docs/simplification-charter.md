# Simplification charter

This document is the control point for the simplification program.
It defines what "simpler" means in this repo, the execution order, what is in scope, what is not, and the guardrails that apply to every cleanup PR.

## Why this exists

The repo has the right raw material: clean layering, MLflow as the control plane, a local-first golden path, and a working hosted staging path. What was missing was one written contract that gives contributors and maintainers a shared definition of "simpler" before structural cleanup starts.

Without it: cleanup PRs re-open settled boundaries, refactors accidentally mix behavior changes with restructuring, and contributors have to infer which surfaces are core versus advanced.

## What "simpler" means here

Simpler means a contributor can open any module, read it top to bottom once, and understand what it does and why.

| Simpler | Not simpler |
| --- | --- |
| Module job is clear from its file name | Module whose only job is to forward calls to another |
| Step traceable start-to-finish in one read | Step that dispatches through a registry at runtime |
| Config in YAML, behavior in Python | Constants or behavior embedded in config loading logic |
| `make check` passes with no cloud account | Tests that require Compose or GCP credentials to run |
| One canonical import path per concept | Re-exports from `__init__.py` that shadow the origin module |
| Explicit control flow | Generic wrappers that hide where execution goes |

Simpler does not mean:

- rewriting modules into tutorial-style code
- flattening meaningful runtime or deployment boundaries to reduce file count
- adding generic abstractions in the name of future flexibility
- making the local path look identical to the hosted path

## Repo surface split

Contributors can reach the local golden path (`make e2e-clean`) without touching anything in the hosted column.

| Surface | Core OSS | Advanced hosted |
| --- | --- | --- |
| `pipeline/`, `registry/`, `core/`, `contracts/` | ✓ | — |
| `backends/local/`, `runtime/`, `configs/env/local.yaml` | ✓ | — |
| `serving/app.py`, `serving/prediction.py`, `serving/router.py` (prod + candidate modes) | ✓ | — |
| `serving/router.py` (canary + shadow modes), `serving/metrics.py` | — | ✓ |
| `ci/` | — | ✓ |
| `deployments/gcp/`, `configs/env/staging.yaml` | — | ✓ |
| `common/mlflow_cloud_run_auth.py` | — | ✓ |

When a cleanup PR touches a core surface, it must not force contributors through a hosted surface to understand or verify it.

## Execution order

| Phase | Focus | Verification |
| --- | --- | --- |
| P01 | Simplification charter (this document) | `make docs-check` |
| P02 | Issue ordering and dependency cleanup | no code change |
| P03 | Handbook pointer updates | `make docs-check` |
| P04 | Canonical module ownership, remove compatibility shims | `make check` |
| P05 | Remove config accessor layer, inline `get_runtime_context` | `make check` |
| P06 | Make pipeline and model-spec path linear to read | `make e2e-clean` |
| P07 | Narrow exception handling to specific exception types | `make check` |
| P08 | Decompose serving package | `make check` + `make test-integration` |
| P09 | Move `core/policy_engine.py` into `policy/`, delete the thin `policy/` wrapper | `make check` + `make test-integration` |
| P10 | Audit `common/` — move anything that belongs in `core/` or `contracts/`, delete anything that belongs nowhere | `make check` |
| P11 | Docs pass — every architecture doc describes the running system, not aspirations | `make docs-check` |

P04–P08 are complete as of branch `refactor/pipeline-linear`.

## Refactor guardrails

These apply to every PR in this program.

**Ownership**
- One canonical import path per concept. If the old path is kept, the deadline for deleting it goes in the same PR.
- No `policy/` or `common/` file whose only job is to import from `core/`. Delete it.
- No new protocol or port unless two concrete implementations already exist.

**Scope isolation**
- A cleanup PR must not also change observable behavior. If both are needed, use two commits in the same PR with a clear boundary between them, or split into two PRs.
- No module split that requires changes to two or more existing import sites unless the old site is deleted in the same PR.
- No broad exception-handling or logging changes mixed with structural cleanup.

**Abstraction**
- No new compatibility shim or re-export without a named phase (above) as the deletion target.
- No generic wrapper, factory, or plugin hook introduced "for later." Add it when the second real use case exists.
- No base class hierarchy where flat composition is readable.

**Local-first invariant**
- `make check` must pass with no cloud account after every PR.
- Changes to a hosted surface must not require updates to a core surface to stay green.

## PR slicing pattern

One PR = one of:

1. A module ownership move (one concept, one canonical home)
2. A layer deletion (remove indirection that adds no value)
3. A documentation update

Never combine (1) or (2) with a behavior change. Never combine two module moves that touch overlapping import sites.

Commit message format follows the repo convention: `refactor: <what changed> (P<phase>)`.

## Issue and label conventions

- Each phase above maps to one GitHub issue.
- Issue title format: `refactor: <short description> (P<phase>)`.
- Issues that have a phase dependency list it explicitly in the body.
- Label `simplification` marks issues in this program.
- Label `hosted` marks issues that touch the advanced hosted surface.

## What this program does not do

- No repo split.
- No new abstraction layer or portability program.
- No workflow behavior change.
- No production rollout work.
- No scheduled promotion or rollback.

These are separate decisions that belong in separate ADRs if and when they arise.
