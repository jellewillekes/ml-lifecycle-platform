# Changelog

All important changes and updates to this project are documented here.

This repo uses Conventional Commits and Release Please.

## [0.3.1](https://github.com/jellewillekes/ml-lifecycle-platform/compare/v0.3.0...v0.3.1) (2026-03-04)


### Bug Fixes

* **ci:** pin Python 3.11.7 for uv in GitHub Actions ([#38](https://github.com/jellewillekes/ml-lifecycle-platform/issues/38)) ([f00f853](https://github.com/jellewillekes/ml-lifecycle-platform/commit/f00f853f5182240d40500ddef7adb8b86f393733))


### Dependencies

* **docker:** bump python from 3.11-slim to 3.14-slim ([#42](https://github.com/jellewillekes/ml-lifecycle-platform/issues/42)) ([a989897](https://github.com/jellewillekes/ml-lifecycle-platform/commit/a989897c83245b4021b79ca8a4c95c42897c4323))


### Documentation

* add verified current-state architecture baseline ([#40](https://github.com/jellewillekes/ml-lifecycle-platform/issues/40)) ([d84c353](https://github.com/jellewillekes/ml-lifecycle-platform/commit/d84c353d2c14f5c821adf79851f5aec796a2592c))
* freeze m0 portability charter and adrs ([#55](https://github.com/jellewillekes/ml-lifecycle-platform/issues/55)) ([5a1f0f4](https://github.com/jellewillekes/ml-lifecycle-platform/commit/5a1f0f4eb54791ef12bd7b9406aec6ee5561d3be))

## [0.3.0](https://github.com/jellewillekes/ml-lifecycle-platform/compare/v0.2.1...v0.3.0) (2026-03-02)


### Features

* reproduce registered models from source runs ([#35](https://github.com/jellewillekes/ml-lifecycle-platform/issues/35)) ([bc98ed8](https://github.com/jellewillekes/ml-lifecycle-platform/commit/bc98ed8bba36d920aecacccd212193c1e9617019))


### Dependencies

* **actions:** bump the github-actions group with 4 updates ([#37](https://github.com/jellewillekes/ml-lifecycle-platform/issues/37)) ([f7632f8](https://github.com/jellewillekes/ml-lifecycle-platform/commit/f7632f8001f535b2e20e1414010ea5b4f93b50eb))

## [0.2.1](https://github.com/jellewillekes/ml-lifecycle-platform/compare/v0.2.0...v0.2.1) (2026-03-01)


### Bug Fixes

* release please root config ([#27](https://github.com/jellewillekes/ml-lifecycle-platform/issues/27)) ([7fa2cea](https://github.com/jellewillekes/ml-lifecycle-platform/commit/7fa2cea63f4824e71a27e7c822e94f6bd94fed33))

## [0.2.0](https://github.com/jellewillekes/ml-lifecycle-platform/compare/v0.1.0...v0.2.0) (2026-02-17)

### Features

* add release policy module and dry-run promotion gate ([#24](https://github.com/jellewillekes/ml-lifecycle-platform/issues/24)) ([23e4818](https://github.com/jellewillekes/ml-lifecycle-platform/commit/23e48188fa3309cf45c8249ec3ff264f00f8343e))

---

## Historical Release Notes

The sections above are managed by Release Please.

The section below contains the initial platform release notes.

## [0.1.0](https://github.com/jellewillekes/ml-lifecycle-platform/releases/tag/v0.1.0)

Initial Platform Release

This release introduced the core model release platform with safe promotion,
progressive delivery, reproducibility, and operational basics.

### Highlights

- Alias-based model lifecycle using MLflow aliases (`candidate`, `prod`, `champion`) instead of stages.
- Safe rollouts with canary + shadow serving modes and deterministic traffic bucketing.
- Reproducibility and governance via dataset fingerprinting, lineage metadata, promotion guardrails, and deterministic rollback.
- Production operability with CI gating, health endpoints, Prometheus metrics, and structured logging.
- Repo standards including templates, CODEOWNERS, release automation, Dependabot, and security posture.

### Core Capabilities

#### Model Release Workflow

- Alias-based promotion flow (`candidate -> prod / champion`)
  PRs: #1, #2
- Promotion safety rails (required provenance tags, rollback metadata, one-command rollback)
  PR: #11

#### Progressive Delivery

- Serving modes: `prod`, `candidate`, `canary`, `shadow`
- Deterministic bucketing and request ID propagation for traceability
  PRs: #4, #8

#### Reproducibility And Lineage

- Dataset fingerprinting and lineage metadata on model versions
  PR: #6
- Contracts and constants to prevent interface drift
  PR: #7

#### Reliability, Observability, And Operations

- CI gating with fast checks and smoke/E2E validation on `master`
  PR: #3
- Typed settings and operational endpoints (`health`, `livez`, `readyz`)
  PR: #9
- Prometheus `/metrics` and structured logging
  PR: #10

#### Developer Experience And Governance

- Pre-commit hooks for consistent formatting and linting
  PR: #5
- Repo standards: PR template, CODEOWNERS, CONTRIBUTING, Release Please, Dependabot, security/legal baseline
  PR: #12

### Included Changes

- #1 `feat: switch to alias-based MLflow releases (candidate/prod)`
- #2 `feat: alias-based release with prod/champion + docs`
- #3 `ci: add gating with fast checks and smoke on master`
- #4 `feat: canary + shadow serving`
- #5 `chore: pre-commit hooks`
- #6 `feat: dataset fingerprinting and lineage metadata`
- #7 `feat: contracts and constants`
- #8 `feat: request ID and deterministic bucketing`
- #9 `feat: platform ops (typed settings, health endpoints, E2E workflow)`
- #10 `feat: Prometheus metrics endpoint and structured logging`
- #11 `feat: promotion guardrails and deterministic rollback`
- #12 `chore: repo standards, release automation and governance`
