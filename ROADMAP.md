# ML Lifecycle Platform — Roadmap

Last updated: 2026-04-20.
Status snapshot: M0 ✅, M1 ✅, M2 ✅ (closing via [#165](https://github.com/jellewillekes/ml-lifecycle-platform/issues/165), [#168](https://github.com/jellewillekes/ml-lifecycle-platform/issues/168)), M3 in progress, M4/M5/M6/M7 planned.

## Purpose

This file is the single public roadmap for the platform. It replaces the piecemeal planning in [#53](https://github.com/jellewillekes/ml-lifecycle-platform/issues/53) with one document that:

- lists every planned ticket with enough detail to open as a GitHub issue,
- makes dependencies explicit,
- records the constraints (cost, portability, latency) that shape decisions,
- describes how to track progress without re-reading this file every week.

The ticket template is deliberately the same one the closed issues already use (Goal / Context / Scope / Non-goals / Risks / Acceptance criteria / Dependencies). Each ticket in this file can be pasted into `gh issue create --body-file` as-is.

The plan has two goals, in order. Goal 1 (primary): demonstrate a complete MLOps-L2 platform on real data — multi-source, multi-model, with a research lane. Goal 2 (secondary, after goal 1): stand up a low-latency path for short-horizon crypto forecasting.

## How to read this

- **Milestones** (M3 → M7) are the GitHub milestones — one milestone per phase.
- **Sub-milestones** (M4a, M4b, …) are dependency-grouped PR clusters inside a milestone. Each sub-milestone ships independently and closes with a visible increment in the repo or a dashboard.
- Sub-milestone N cannot meaningfully start before sub-milestone N-1 has landed the contract or port it depends on.
- Tickets keep the `UP-XX` identifier so cross-referencing with prior backlog stays stable. New tickets take the next free numbers (UP-49 onwards).
- M3 and M4a tickets are fully drafted. Later sub-milestones are progressively terser — enough to slot into the backlog, still need one polishing pass before opening.
- Every ticket includes `Labels` and `Milestone` so the grooming step is mechanical.

## Guiding constraints

These are hard rules. A ticket that violates them gets rewritten, not accepted.

1. **Cost rule — GCP / AWS only.** No third-party SaaS subscriptions or tokens, even free-tier (no Slack/PagerDuty/SendGrid/Grafana Cloud tokens). Self-host on cloud compute instead.
2. **Portability — local → GCP → AWS behind one port.** Every new subsystem gets a `core/ports/*.py` Protocol plus at least a local adapter + GCP adapter in the same PR. AWS is a third adapter later; the port must not leak GCP types.
3. **OSS local equivalents — the local path always runs a real OSS equivalent of every GCP API used.** Stubs and in-memory shims are not acceptable substitutes. When no OSS equivalent fits, the ticket documents the gap and opens a follow-up. Canonical mappings:

   | GCP service | Local OSS equivalent |
   |---|---|
   | BigQuery | DuckDB over parquet on local FS |
   | Pub/Sub | Redpanda (Kafka protocol, single-node) |
   | Memorystore (Redis) | Redis in Compose |
   | Cloud Storage | MinIO in Compose |
   | Cloud Scheduler | Compose-based cron / APScheduler |
   | Cloud Run / Jobs | Docker Compose services |
   | Secret Manager | dotenv |
   | Cloud Monitoring + Logging | UP-27 self-hosted VictoriaMetrics + Tempo + Grafana OSS |
   | Vertex AI Training / Metadata | MLflow + the existing pipeline |
   | Cloud Build / Artifact Registry | local Docker + file-system registry |

4. **Local-first invariant.** `make check` passes with no cloud account after every PR. The local golden path stays the contributor's entry point.
5. **Latency budget as an axis.** Every M6 ticket is graded against a p99 latency budget (see [M6](#m6--low-latency-crypto-forecasting)). UP-60 creates the harness that enforces it.
6. **One PR per issue.** Every issue ships end-to-end in one PR. No "Suggested PR slices" sections.

## Current state snapshot

Taken from [docs/architecture.md](docs/architecture.md) plus a scan of closed issues.

**Implemented and green:**

- Local golden path: `ingest → featurize → train → evaluate → register → promote → serve`
- MLflow as control plane; alias-based release (`prod`, `candidate`, `champion`); release evidence bundles
- Hosted GCP staging: MLflow on Cloud Run, serving on Cloud Run, platform Cloud Run Jobs, Cloud Scheduler maintenance cadence
- Hosted CI via GitHub Actions with OIDC, image digest pinning, authenticated smoke verification
- UP-23 OTel runtime instrumentation ([#171](https://github.com/jellewillekes/ml-lifecycle-platform/issues/171), [#176](https://github.com/jellewillekes/ml-lifecycle-platform/pull/176))
- UP-27 self-hosted observability stack on GCE (OTel Collector + VictoriaMetrics + Tempo + Grafana OSS) ([#172](https://github.com/jellewillekes/ml-lifecycle-platform/issues/172))
- UP-24 observability dashboards ([#173](https://github.com/jellewillekes/ml-lifecycle-platform/issues/173), [#184](https://github.com/jellewillekes/ml-lifecycle-platform/pull/184))
- UP-25 alerts + serving SLOs + GCP-native alert routing ([#174](https://github.com/jellewillekes/ml-lifecycle-platform/issues/174), [#189](https://github.com/jellewillekes/ml-lifecycle-platform/issues/189), [#190](https://github.com/jellewillekes/ml-lifecycle-platform/pull/190), [#191](https://github.com/jellewillekes/ml-lifecycle-platform/pull/191))
- `RuntimeEvent` Pydantic contract at [src/ml_lifecycle_platform/contracts/runtime_event.py](src/ml_lifecycle_platform/contracts/runtime_event.py)
- `LocalEventStore` JSONL sink at [src/ml_lifecycle_platform/backends/local/event_store.py](src/ml_lifecycle_platform/backends/local/event_store.py)

**Open gaps vs. a complete L2 platform:**

- No GitHub Environments / prod approvals (UP-26 drafted as [#175](https://github.com/jellewillekes/ml-lifecycle-platform/issues/175))
- No `DataSource` port; ingest is synthetic; no real API wired in
- No explicit data-validation or model-validation stages in the pipeline
- No multi-model orchestration — pipeline trains one model at a time
- No research tier for experimental models; no feature catalog
- No portable event plane (hot or cold) in production
- No drift, replay, feedback, or decay detection on real data
- No automated retraining trigger or env-aware promotion
- No pipeline-as-artifact CD; no signed model artifacts
- No platform smoke test or auto-generated model cards
- No AWS adapter for any port (port definitions don't exist yet)
- **Low-latency path (M6) unscoped:** no online feature store, no tick ingestion, no hot stream, no low-latency serving

## Tracking and overview workflow

Three layers, each answering a different question. Pick any two to start; the third is optional.

1. **Milestones (M3 → M7)** — the "are we done with M4?" bar. Close a milestone when every issue closes.
2. **Labels** — existing `phase:m0..m5`, `type:*`, `status:*` already cover most cases. Add `phase:m6`, `phase:m7`, `sub:m4a` through `sub:m4f`, and `tier:research`.
3. **Dependencies** — continue the `## Dependencies` block you already use in issue bodies. Query blocked work with `gh issue list --label status:blocked`.
4. **Optional: one GitHub Project (v2) board** grouped by milestone with columns `Backlog → Ready → In progress → Review → Done`. One bookmark, whole plan visible.

Day-to-day commands:

```
gh issue list --milestone M4 --state open              # what's left in current phase
gh issue list --label sub:m4a                          # current sub-milestone only
gh issue list --label phase:m6                         # every low-latency ticket
gh issue list --label tier:research                    # experimental models
gh issue list --label status:blocked                   # waiting
gh issue list --search "UP-51" --state all             # specific ticket
gh issue list --milestone M4 --state closed \
  --json closedAt,number,title --jq 'sort_by(.closedAt)'   # velocity
```

## Milestone map

| Milestone | Theme | Sub-milestones / tickets |
|---|---|---|
| **M3** close-out | Operable GCP platform | UP-26 |
| **M4** | Complete L2 ML platform on real data | **M4a** UP-28, UP-49, UP-50, UP-51, UP-52 — multi-source foundation<br>**M4b** UP-29a — event plane (cold)<br>**M4c** UP-53 — second + third data sources<br>**M4d** UP-30, UP-31, UP-32, UP-33, UP-34, UP-42 — feedback loop on real data<br>**M4e** UP-35, UP-36, UP-41, UP-43, UP-44, UP-45, UP-54 — release gating + CT + lineage<br>**M4f** UP-48, UP-55, UP-56, UP-57, UP-58, UP-59 — research lane + platform cohesion |
| **M5** | Scale-out + AWS foundation | UP-37, UP-40, UP-46, UP-47 (UP-38/39 deferred) |
| **M6** | Low-latency crypto forecasting | UP-29b, UP-60, UP-61, UP-62, UP-63, UP-64, UP-65, UP-66, UP-67, UP-68, UP-69, UP-71 |
| **M7** | AWS low-latency parity | UP-70 |

## Dependency graph

```
M3   UP-26
         │
M4a      ├── UP-28 ── UP-49 ── UP-50 ── UP-51 ── UP-52
         │                                       │
M4b      │                                       └── UP-29a
         │                                                │
M4c      │                                                ├── UP-53 (Coinbase + Open-Meteo)
         │                                                │
M4d      │                                                ├── UP-31 ── UP-33 ── UP-34 ── UP-32 ── UP-42
         │                                                │                              └── UP-30 (walk-forward CV)
         │                                                │
M4e      │                                                ├── UP-45 ── UP-54 ── UP-35 ── UP-44 ── UP-43 ── UP-36
         │                                                │                                               └── UP-41
         │                                                │
M4f      │                                                └── UP-55 ── UP-56 ── UP-57 ── UP-58 ── UP-48
         │                                                                                        └── UP-59 (on demand)
M5       └── UP-47, UP-37, UP-46, UP-40                        (UP-38/39 deferred)

M6       UP-60 ── UP-29b ── UP-62 ── UP-63 ── UP-64 ── UP-61 ── UP-65 ── UP-66 ── UP-67 ── UP-68 ── UP-69 ── UP-71
M7       UP-70 (after UP-40 + UP-68)
```

---

# M3 — close operable GCP platform

## UP-26 — GitHub Environments (staging + prod), scoped secrets, env-bound SAs

- **Labels:** `phase:m3`, `type:ci`, `status:planned`
- **Milestone:** M3
- **Status:** exists as [#175](https://github.com/jellewillekes/ml-lifecycle-platform/issues/175); the lighter scope is already drafted there. The additions below turn it into a complete L2 governance gate.

### Goal

Move deploy workflows onto declared GitHub Environments with env-scoped secrets and env-bound service accounts, so staging and prod have separate auth surfaces and prod requires an approver.

### Context

#175 creates the environments and skeleton prod workflows. It does not migrate the existing staging workflows onto `environment: staging`, does not split the `mlp-ci` service account, and does not scope OIDC subject-claims per environment. Without those, the governance story is incomplete: a compromised staging workflow can still theoretically reach prod because they share secrets and SA.

### Scope (additions to #175)

- migrate each deploy workflow under [.github/workflows](.github/workflows) onto `environment: staging` — `deploy-mlflow-staging.yml`, `deploy-platform-jobs-staging.yml`, `deploy-serving-staging.yml`, `run-platform-job-staging.yml`, `seed-staging-model.yml`, `serving-staging-baseline.yml`, `hosted-golden-path-staging.yml`
- split `mlp-ci` SA into `mlp-ci-staging` and (reserved, unused) `mlp-ci-prod` in [deployments/gcp/terraform/foundation.tf](deployments/gcp/terraform/foundation.tf); bind Workload Identity Federation subject-claim to match env name
- move `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT`, `GCP_PROJECT_ID` from repo-level to env-level
- new runbook `docs/runbooks/github-environments.md` — approval flow, what moves between envs, secret rotation
- update [docs/runbooks/gcp-ci-auth.md](docs/runbooks/gcp-ci-auth.md) with the split

### Non-goals

- prod Cloud Run infra (UP-47)
- per-env Terraform workspace separation beyond SA split
- branch protection changes (separate policy issue)

### Risks

- OIDC subject-claim mismatch during cutover — stage behind a branch + `workflow_dispatch` smoke
- missing env-scoped secret would fail at auth — AC includes a dry run of every workflow

### Acceptance criteria

- every deploy workflow runs under `environment: staging`
- `mlp-ci` split visible in Terraform state; staging WIF subject-claim binds to `environment:staging`
- `workflow_dispatch` dry run of each workflow succeeds
- new runbook exists, `gcp-ci-auth.md` updated

### Dependencies

- none; foundational for every gated CD ticket

---

# M4 — complete L2 ML platform on real data

Six sub-milestones. Each ships independently and leaves the repo in a coherent state.

## M4a — multi-source foundation

Goal: the "platform" claim becomes architecturally true; real data flows from day one.

### UP-28 — `PredictionEvent` Pydantic contract with ns-precision envelope

- **Labels:** `phase:m4`, `sub:m4a`, `type:feat`, `status:planned`
- **Milestone:** M4

#### Goal

A canonical, versioned Pydantic model describing a single prediction, with an envelope designed to later carry tick-level latency attribution. Contract-only — no sink, no emitter.

#### Context

[src/ml_lifecycle_platform/contracts/runtime_event.py](src/ml_lifecycle_platform/contracts/runtime_event.py) is a generic `RuntimeEvent`. `PredictionEvent` is narrower and drives observability, drift, replay, and feedback. It must land before UP-29a/b. ns-precision timestamps are mandatory now — retrofitting them when M6 starts would be a breaking schema change.

#### Scope

- new `src/ml_lifecycle_platform/contracts/prediction_event.py` with:
  - `PredictionEvent` (Pydantic v2): `schema_version: Literal["1"]`, `event_id: UUID`, `corr_id: str`, `event_time_ns: int`, `ingest_time_ns: int`, `model_ref: ModelRef`, `features: dict[str, JsonValue]`, `prediction: JsonValue`, `latency_ns: int`, `envelope: EventEnvelope`
  - `EventEnvelope`: `service: str`, `env: Literal["local","staging","prod"]`, `run_id: str | None`, `git_sha: str | None`
  - `.to_dict()` / `.from_dict()` matching `RuntimeEvent` style
- schema-evolution rule documented in [docs/reference/release-contract.md](docs/reference/release-contract.md): breaking → bump `schema_version`; reader refuses unknown major
- unit tests in `tests/unit/test_prediction_event.py` — round-trip, forbidden extras, ns overflow, idempotency-key equivalence
- **do not** emit from serving yet (UP-29a wires the emitter)

#### Non-goals

- sink/stream implementation (UP-29a, UP-29b)
- BigQuery schema (belongs to UP-29a)
- drift logic (UP-32)

#### Risks

- envelope bikeshedding — keep minimal; reject anything not needed by a concrete downstream
- `features` cardinality at tick volume — call out in the schema doc that UP-29a will columnar-break when needed

#### Acceptance criteria

- `make check` green
- unit tests cover valid event, missing required field, unknown `schema_version` refused, ns overflow
- schema doc lists every field + stability guarantee
- no call site imports from `contracts/__init__.py` re-exports

#### Dependencies

- none; blocks UP-29a, UP-29b, UP-49, UP-51

### UP-49 — data validation pipeline stage

- **Labels:** `phase:m4`, `sub:m4a`, `type:feat`, `status:planned`
- **Milestone:** M4

#### Goal

Add an explicit `validate_data` stage between `ingest` and `train` that checks training input against a per-source Pandera schema and basic distribution assumptions. Fail the run; do not produce a candidate model.

#### Context

Today the pipeline is `ingest → featurize → train → evaluate`. There is no first-class data validation between ingest and train, so a malformed ingest silently trains a broken model that only fails at evaluate or at promotion (UP-35). MLOps L2 bakes validation into the pipeline itself so the registry never fills with bad candidates in the first place.

#### Scope

- new `src/ml_lifecycle_platform/pipeline/validate_data.py` step
- Pandera schema per source (schema surfaced by UP-51's `DataSource.schema()` when it lands; stubbed against the current synthetic source until then)
- basic distribution checks: row count ≥ spec-declared minimum, no fully-null columns, numeric ranges within source-declared bounds
- pipeline spec gains an optional `validation:` block
- failing validation aborts the pipeline before train; writes `validation_report.json` to MLflow artifacts and surfaces a one-line reason in the run summary
- integration test in `tests/integration/test_validate_data.py` asserts malformed input is caught and well-formed input passes

#### Non-goals

- drift detection (UP-32)
- production-tuned thresholds (ship reasonable defaults; tune per model in UP-50)

#### Risks

- false positives on legitimate edge data → thresholds are spec-declared per source, not global
- schema evolution breaks old runs → pin schema version alongside `schema_version` on the event contract

#### Acceptance criteria

- malformed training DataFrame fails validation with a specific error and does not reach train
- passing data produces `validation_report.json` attached to the MLflow run
- `make check` green; integration test covers pass + fail paths

#### Dependencies

- UP-28 (envelope convention); blocks UP-51 (which injects per-source schemas) and UP-52

### UP-50 — model validation pipeline stage

- **Labels:** `phase:m4`, `sub:m4a`, `type:feat`, `status:planned`
- **Milestone:** M4

#### Goal

Split `evaluate` into `evaluate → validate_model` so only candidates passing explicit segment and baseline gates reach the registry.

#### Context

Today every trained model registers regardless of quality; bad candidates are only caught at promotion (UP-35) or not at all. L2 wants model validation inside the pipeline — the registry holds only candidates worth promoting.

#### Scope

- new `src/ml_lifecycle_platform/pipeline/validate_model.py` step
- checks: overall metric ≥ spec floor, per-segment minimums (segments declared on spec), regression vs. baseline (from UP-31 when landed; "don't regress vs. previous run" until then)
- writes `model_validation_report.json` to MLflow artifacts
- failing validation aborts the pipeline before `register`
- unit tests cover pass, fail-on-segment, fail-on-regression

#### Non-goals

- promotion gates (UP-35)
- challenger selection (UP-36)

#### Risks

- overly strict thresholds block legitimate improvements → thresholds are per-model and spec-declared; changes land in the model's PR

#### Acceptance criteria

- a deliberately-degraded candidate fails validation and is not registered
- a legitimate candidate passes and registers normally
- report visible as an MLflow artifact on every training run

#### Dependencies

- UP-49; UP-31 enriches baseline comparison later

### UP-51 — `DataSource` port with Binance REST adapter and first real-data model

- **Labels:** `phase:m4`, `sub:m4a`, `type:feat`, `status:planned`
- **Milestone:** M4

#### Goal

Formalize data ingestion as a port with adapters, ship Binance REST 1-minute klines as the first real-data adapter, and train the first real-data model through the existing pipeline. The REST adapter runs identically from local (Compose cron) and GCP (Cloud Scheduler + Cloud Run Job).

#### Context

The current pipeline ingests synthetic data. Real data from day one makes every downstream L2 feature — drift, decay, retraining, promotion gates — measure true signal rather than fabricated fixtures. The port pattern mirrors the existing `EventSink`/`EventStream` design (see UP-29a/b). Binance public REST is zero-cost, unauthenticated, and aligned with the eventual M6 goal (same instrument) — the M6 WS ingestor (UP-61) later swaps the adapter without changing the model spec.

#### Scope

- new `src/ml_lifecycle_platform/core/ports/data_source.py` — Protocol: `fetch(window) -> Iterator[RawRecord]`, `schema() -> pa.DataFrameSchema`, `rate_limits() -> Limits`
- adapter: `src/ml_lifecycle_platform/backends/common/data_sources/binance_rest.py` (single adapter works identically for local and GCP) using the public klines endpoint; polite rate limiting; retry with backoff
- new `configs/sources/binance_btc_1m.yaml` declaring adapter + config
- scheduled ingestion job — Compose-cron service locally, Cloud Run Job + Cloud Scheduler on GCP — pulling klines every minute and writing to the existing object-store port (local FS / GCS)
- new `configs/models/binance_btc_1m.yaml` — EMA/momentum features, logistic on next-bar return sign; uses the existing pipeline end-to-end
- UP-49 and UP-50 gate the run; `validate_data` receives the schema from `DataSource.schema()`
- new runbook `docs/runbooks/data-sources.md` — adding a new REST source in 6 steps

#### Non-goals

- WS streaming (UP-61 in M6)
- multi-exchange consumers (UP-53)
- online feature store (UP-63)
- merging across sources

#### Risks

- Binance rate-limiting → polite client, cached symbols, exponential backoff; scheduled job is idempotent so missing a minute is recoverable
- data licensing — Binance public market data is free for general use; documented in the new runbook
- "common" adapter location — REST semantics are identical from local and GCP; only the **scheduler** differs (Compose cron vs. Cloud Scheduler). Document this split clearly so future auth-required sources know where to live

#### Acceptance criteria

- `make e2e-clean` trains `binance_btc_1m` end-to-end locally on real data
- staging Cloud Run Job ingests Binance klines and produces a registered model
- UP-49/UP-50 gates exercised on real data
- `data-sources.md` runbook takes a contributor from "I have an API in mind" to a merged new-source PR

#### Dependencies

- UP-28 (envelope), UP-49, UP-50

### UP-52 — multi-model spec-driven orchestration

- **Labels:** `phase:m4`, `sub:m4a`, `type:feat`, `status:planned`
- **Milestone:** M4

#### Goal

The pipeline iterates over every model spec in [configs/models/](configs/models/) and runs each through the full training path with per-model isolation in BigQuery and MLflow.

#### Context

Today the pipeline trains one model. To be a platform, N specs must run side-by-side with no code changes. Per-model isolation is by convention, not by infrastructure: one MLflow experiment per model, one BQ table partition per model, alert-router keyed by `model_ref.name`.

#### Scope

- refactor pipeline entry point to accept `--model=<name>` and a `--all` mode iterating [configs/models/](configs/models/)
- MLflow: one experiment per model (created lazily); run tags include `model_name`, `source_name`, and a placeholder `tier` (replaced by UP-55)
- BQ (wired fully once UP-29a lands): prediction_events partitioned by `model_ref.name`
- training job parameterized by model name; scheduler runs one job per model
- serving exposes `/predict/<model_name>` per spec, loading from alias
- hard-cap this ticket at ~200 LOC of new code. If it grows, defer scope

#### Non-goals

- tier field and research-only branching (UP-55)
- cross-model joins (a separate ticket only if a model needs them)
- dynamic model loading / plugin registries — deliberately avoided per CLAUDE.md style rules

#### Risks

- scope creep into "framework" territory → stays a for-loop with per-model parameters; no factories or plugins
- alias collisions across models → promotion already keys per-model; confirm in AC

#### Acceptance criteria

- `mlp train --all` trains every spec in [configs/models/](configs/models/); each lands a separately-registered model
- MLflow shows one experiment per model with a clean run history
- serving exposes `/predict/<model_name>` per spec
- added code stays under ~200 LOC (enforced by review)

#### Dependencies

- UP-51 (provides the first real source + second model spec); blocks UP-53, UP-55

## M4b — event plane (cold path)

### UP-29a — `EventSink` port with local JSONL and BigQuery adapters

- **Labels:** `phase:m4`, `sub:m4b`, `type:feat`, `status:planned`
- **Milestone:** M4

#### Goal

Introduce the `EventSink` port for the cold write path, ship both a local JSONL adapter and a GCP BigQuery adapter in the same PR, and emit `PredictionEvent` from serving through the port. Call sites must not know which adapter is live.

#### Context

L2 needs a durable event plane that drift, replay, and feedback read from. Defining the port now with two adapters is the only way to honor portability: AWS adds a third adapter, never a rewrite. Splitting hot stream (UP-29b) from cold sink keeps M6 unblocked without coupling it to BigQuery. Local parity uses DuckDB over parquet in downstream consumers; the JSONL adapter here is the write path.

#### Scope

- new `src/ml_lifecycle_platform/core/ports/event_sink.py` — `EventSink` Protocol: `write`, `write_batch`, `flush(timeout_s)`, `close`
- adapter 1: `src/ml_lifecycle_platform/backends/local/prediction_event_sink.py` — async-buffered JSONL writer backed by `LocalEventStore`, configurable fsync
- adapter 2: `src/ml_lifecycle_platform/backends/gcp/bigquery_event_sink.py` — batched BQ streaming; schema from `PredictionEvent.model_json_schema()`; retries on 5xx; drops to DLQ (UP-41 ships the DLQ itself)
- Terraform under [deployments/gcp/terraform](deployments/gcp/terraform):
  - dataset `mlp_events` (regional, same as Cloud Run)
  - table `prediction_events_v1` partitioned by `DATE(event_time_ns)`, clustered on `model_ref.name, env`
  - IAM: `mlp-ci-staging` → `bigquery.dataEditor` on dataset; serving runtime SA → `bigquery.dataEditor` scoped to the one table
- serving wiring: [src/ml_lifecycle_platform/serving/app.py](src/ml_lifecycle_platform/serving/app.py) resolves sink from runtime profile; emit from a background task so predict path is never blocked
- new `docs/runbooks/event-plane.md` — schema evolution, add a column, tail locally, query BQ (and query the local JSONL with DuckDB as the portable equivalent)
- tests: unit for both adapters; integration `tests/integration/test_bigquery_event_sink.py` guarded by `GCP_PROJECT_ID`; e2e row-in-BQ within 10s

#### Non-goals

- DLQ/backfill (UP-41)
- hot streaming (UP-29b)
- feature-level columnar breakout

#### Risks

- predict-path latency regression — drop-on-full ring buffer + Prometheus counter + alert (piggyback UP-25)
- BQ streaming cost at tick volume — explicit: cold sink is not the tick path; M6 uses UP-29b
- partition-pruning misuse — AC includes a BQ query proving the partition filter kicks in

#### Acceptance criteria

- single `EventSink` Protocol is the only type serving + runtime reference
- `make e2e-clean` green with JSONL; staging e2e green with BQ adapter
- predict p95 within ±5% of pre-change baseline (UP-23 metrics)
- BQ table fully Terraform-managed; no UI-created resources
- runbook covers add-column, tail-local, query-bq, and query-local-jsonl-via-DuckDB

#### Dependencies

- depends on UP-28, UP-52
- blocks UP-30, UP-31, UP-32, UP-34, UP-41

## M4c — second and third data sources

### UP-53 — Coinbase REST + Open-Meteo data source adapters

- **Labels:** `phase:m4`, `sub:m4c`, `type:feat`, `status:planned`
- **Milestone:** M4

Scope: two new adapters under `backends/common/data_sources/` — Coinbase public candles REST (no auth) and Open-Meteo forecast API (no auth, returns both forecast and ERA5 realized). Two new source YAMLs. Two new model specs: `configs/models/coinbase_btc_1m.yaml` (cross-exchange basis direction) and `configs/models/weather_temp_1h.yaml` (1h temperature forecast error; realized labels from the same API).

Non-goals: merging across sources (open a separate ticket if a model needs joins); authenticated Kraken/Alpha Vantage-style sources (UP-59).

AC: `mlp train --all` trains three models in parallel; dashboards show Binance, Coinbase, and weather models side by side; `make e2e-clean` covers all three; runbook `docs/runbooks/data-sources.md` is the only change a future contributor needs to add a fourth source.

Depends on: UP-51, UP-52.

## M4d — feedback loop on real data

### UP-31 — release-linked drift baselines

- **Labels:** `phase:m4`, `sub:m4d`, `type:feat`, `status:planned` — **Milestone:** M4
- **Scope:** `DriftBaseline` artifact (Pandera schema for feature + label stats) computed at promotion and attached to `release_manifest.json`; stored via object-store port (local FS / GCS); `registry/release_evidence.py` extends with `baseline_ref`.
- **Non-goals:** drift computation (UP-32); stat-test debate — pick KS + mean/std for v1, documented.
- **AC:** promoting writes a baseline artifact; `mlp registry show-baseline <version>` prints it; Pandera validates.
- **Depends on:** UP-29a.

### UP-33 — delayed-label ingestion contracts

- **Labels:** `phase:m4`, `sub:m4d`, `type:feat`, `status:planned` — **Milestone:** M4
- **Scope:** Pydantic `LabelEvent` for ingestion/API; Pandera for batch `labels` table; join keys + freshness SLO + late-arrival policy. Natural for all three UP-53 sources (Binance/Coinbase bar close; ERA5 realized).
- **AC:** Pandera catches bad join keys; freshness SLO published in [docs/reference/release-contract.md](docs/reference/release-contract.md).
- **Depends on:** UP-28.

### UP-34 — feedback capture and realized-performance table

- **Labels:** `phase:m4`, `sub:m4d`, `type:feat`, `status:planned` — **Milestone:** M4
- **Scope:** Cloud Run Job joining `prediction_events_v1` ⋈ `labels`; Pandera on joined output; `realized_performance_v1` BQ table + DuckDB local equivalent.
- **AC:** local + staging e2e write a realized-performance row for each of the three M4c models; UP-42 consumes it.
- **Depends on:** UP-29a, UP-33.

### UP-32 — batch drift MVP against windowed events

- **Labels:** `phase:m4`, `sub:m4d`, `type:feat`, `status:planned` — **Milestone:** M4
- **Scope:** Cloud Run Job reading a window through `BatchEventReader` port (DuckDB local, BQ hosted), comparing against UP-31 baseline, emitting `drift_report.json` into release evidence + a Prometheus gauge for UP-42.
- **Non-goals:** in-request drift; auto-promote/demote on drift.
- **AC:** synthetic shifted window produces KS > threshold; stable window shows no drift; real Binance data drives a genuine baseline.
- **Depends on:** UP-29a, UP-31.

### UP-42 — model-quality dashboards and decay alerts

- **Labels:** `phase:m4`, `sub:m4d`, `type:infra`, `status:planned` — **Milestone:** M4
- **Scope:** Grafana OSS panels for realized-accuracy / calibration / per-segment from UP-34; burn-rate alert on decay; routed via UP-25 alert-router. Panels aggregate across all prod-tier models.
- **AC:** synthetic accuracy drop produces a delivered alert; real decay on one of the three M4c models shows on the dashboard within one retraining cadence.
- **Depends on:** UP-34, UP-25.

### UP-30 — offline replay harness (with walk-forward CV mode)

- **Labels:** `phase:m4`, `sub:m4d`, `type:feat`, `status:planned` — **Milestone:** M4
- **Scope:** `mlp replay --from=<ts> --to=<ts> --candidate=<model@alias>` pulls events via `BatchEventReader`, reruns through candidate, writes `replay_report.json` (agreement rate, regression metrics, per-segment breakdown) into MLflow artifacts.
- **M4 extension — walk-forward CV:** add `--mode=walk-forward --step=<interval>` that respects data-availability windows (needed for time-series sources like Binance/Coinbase/weather and required by M6's UP-66).
- **Non-goals:** live shadow replay (already available via serving shadow mode); distributed replay.
- **AC:** replay against known-equivalent candidate returns 100% agreement; known-worse candidate flags the gap; walk-forward CV produces a fold-by-fold report.
- **Depends on:** UP-29a.

## M4e — release gating, continuous training, lineage

### UP-45 — ML metadata lineage over MLflow + BigQuery

- **Labels:** `phase:m4`, `sub:m4e`, `type:feat`, `status:planned` — **Milestone:** M4
- **Scope:** BQ views over MLflow tags + `prediction_events_v1` + release evidence surfacing: dataset fingerprint → pipeline run → model version → release → prediction-event window. Queryable by UP-43.
- **M4 extension — fingerprint as required tag:** every training run must carry a `dataset_fingerprint` tag; CI gate refuses untagged runs. Makes "which data produced this model?" an always-answerable query.
- **Non-goals:** Vertex ML Metadata (revisit only if views insufficient).
- **AC:** one SQL view answers "which dataset produced the current prod model?" and "which events were scored by which version?"; CI refuses a run that omits `dataset_fingerprint`.
- **Depends on:** UP-29a, UP-35.

### UP-54 — auto-generated model cards

- **Labels:** `phase:m4`, `sub:m4e`, `type:feat`, `status:planned` — **Milestone:** M4
- **Scope:** at register time, generate a markdown model card per version combining evaluation output (from UP-50), drift baseline summary (from UP-31), lineage pointer (from UP-45), and the source + model YAML. Attached as an MLflow artifact; rendered in the MLflow UI.
- **Non-goals:** full responsible-AI framework, bias audits (covered in UP-48's descope ADR if needed for the current model set).
- **AC:** every registered model has `model_card.md` as an artifact; cards exist for all three M4c models.
- **Depends on:** UP-45, UP-50, UP-31.

### UP-35 — env-aware promotion with replay/drift/health gates and progressive rollout

- **Labels:** `phase:m4`, `sub:m4e`, `type:feat`, `status:planned` — **Milestone:** M4
- **Scope:** replace alias-only promotion — `mlp promote --to=staging|prod` runs UP-30 replay + UP-32 drift + serving-health probe; emits `promotion_decision.json` with each gate's verdict; `prod` requires UP-26 approval; extend release evidence.
- **M4 extension — progressive rollout + auto-rollback:** `prod` promotion shifts traffic through a configurable step sequence (e.g. 5% → 25% → 100%) using the existing router; auto-rollback to previous alias if a UP-25 SLO burn alert fires during any step.
- **Non-goals:** blue/green at infra level (comes later if needed); manual canary traffic shifts (superseded by the progressive rollout above).
- **AC:** failing gate blocks promotion; evidence records the failing gate; `prod` requires env approval; a synthetic SLO burn during a 25% step triggers automated rollback with evidence.
- **Depends on:** UP-26, UP-30, UP-32, UP-34.

### UP-44 — pipeline versioning, pipeline CD workflow, and signed model artifacts

- **Labels:** `phase:m4`, `sub:m4e`, `type:ci`, `status:planned` — **Milestone:** M4
- **Scope:** treat pipeline image as deployable artifact distinct from serving/jobs; pin pipeline image digest + `PipelineSpec` hash in every training run's tags; new `deploy-pipeline-staging.yml` publishes, runs synthetic end-to-end pipeline, promotes by digest; `promotion_decision.json` records pipeline digest.
- **M4 extension — supply chain:** cosign-signed model artifacts pushed alongside the pipeline image; SLSA provenance attestation attached to every training run; UP-35 verifies signatures before promotion.
- **AC:** breaking pipeline change caught by synthetic run; every training run carries pipeline-digest tag; unsigned or invalid-provenance model artifacts fail promotion.
- **Depends on:** UP-26.

### UP-43 — continuous-training trigger

- **Labels:** `phase:m4`, `sub:m4e`, `type:feat`, `status:planned` — **Milestone:** M4
- **Scope:** `RetrainTrigger` port — local cron+file watcher adapter, Cloud Scheduler + Eventarc filter over drift/decay adapter; Cloud Run Job that retrains → registers candidate → invokes UP-35 in staging.
- **Non-goals:** auto-promote to prod.
- **AC:** real drift event on a live M4c model kicks retrain; staging-only promotion visible in evidence.
- **Depends on:** UP-29b, UP-32, UP-34, UP-35.

### UP-36 — challenger automation

- **Labels:** `phase:m4`, `sub:m4e`, `type:feat`, `status:planned` — **Milestone:** M4
- **Scope:** job generating challenger specs from staleness / UP-32 drift / UP-34 decay; trains + registers as `candidate`; no auto-prod.
- **AC:** synthetic trigger produces registered challenger; UP-35 gates run against it on next promotion.
- **Depends on:** UP-43.

### UP-41 — event-plane DLQ, retry policy, and backfill CLI

- **Labels:** `phase:m4`, `sub:m4e`, `type:feat`, `status:planned` — **Milestone:** M4
- **Scope:** `DeadLetterSink` port; local JSONL DLQ + GCP DLQ topic + `prediction_events_dlq_v1` BQ table; retry policy shared by sink/stream; new CLI `mlp events replay --from-dlq --since=<ts>` that re-emits failed events deduped on `event_id`.
- **Non-goals:** PII scrub, cross-region DR.
- **AC:** forced BQ 503s drain to DLQ; `mlp events replay` drains DLQ into live sink with zero duplicates.
- **Depends on:** UP-29a, UP-29b.

## M4f — research lane and platform cohesion

### UP-55 — model `tier` field and research lane

- **Labels:** `phase:m4`, `sub:m4f`, `type:feat`, `status:planned` — **Milestone:** M4
- **Scope:** add `tier: research | staging | prod` to each `configs/models/*.yaml`. UP-35 branches on tier: research tier skips replay/drift/health gates but still produces the evidence bundle. Alert-router (UP-25) fans out by `model_ref.name + tier`; research-tier alerts route to UP-56's diagnostic dashboard only, never to pagers. Graduation = one PR changing the tier field; UP-35 full gate set runs.
- **Non-goals:** parallel infrastructure for research (no separate cluster, no separate repo, no separate MLflow instance); bandit / multi-armed orchestration.
- **AC:** one research-tier experimental model lives alongside prod models; alerts for it appear on UP-56 dashboard but never page; graduating the tier in a PR triggers the full UP-35 gate set.
- **Depends on:** UP-35, UP-25, UP-52.

### UP-56 — research-tier diagnostic dashboard

- **Labels:** `phase:m4`, `sub:m4f`, `type:infra`, `status:planned` — **Milestone:** M4
- **Scope:** Grafana OSS dashboard showing all `tier:research` models' drift, decay, and realized-performance side-by-side. Terraform-managed like existing dashboards. No pager routes. Extend [docs/runbooks/observability.md](docs/runbooks/observability.md) with a "research models" section.
- **AC:** dashboard renders real data for the experimental model from UP-55; panel appears in the observability runbook.
- **Depends on:** UP-55, UP-42, UP-34.

### UP-57 — feature catalog

- **Labels:** `phase:m4`, `sub:m4f`, `type:docs`, `status:planned` — **Milestone:** M4
- **Scope:** generate `docs/reference/feature-catalog.md` at CI time from `configs/sources/*.yaml` + `configs/models/*.yaml`. For each feature: source, derivation, which models consume it, last-updated timestamp.
- **AC:** `make docs-check` regenerates the catalog; CI fails if the committed file is stale; catalog lists every feature used by the three M4c models plus the UP-55 research model.
- **Depends on:** UP-51, UP-52, UP-53.

### UP-58 — platform smoke test

- **Labels:** `phase:m4`, `sub:m4f`, `type:ci`, `status:planned` — **Milestone:** M4
- **Scope:** nightly workflow `.github/workflows/platform-smoke.yml` asserting:
  - every source in `configs/sources/*.yaml` ingested rows in last 24h
  - every prod-tier model produced ≥ expected-rate predictions
  - realized_performance rows exist for every model with matured labels
  - no open drift-alert incidents for ≥ 30 minutes

  Failure opens a GH issue tagged `status:incident`. Research-tier models with no run in 30 days open a separate `status:stale-research` issue for cleanup review.
- **AC:** synthetic failure (disable one source cron) triggers a real incident issue within 24h; green state produces no noise.
- **Depends on:** UP-29a, UP-34, UP-42, UP-55.

### UP-48 — ADR on deliberate MLOps-L2 descopes

- **Labels:** `phase:m4`, `sub:m4f`, `type:docs`, `status:planned` — **Milestone:** M4
- **Scope:** ADR listing L2 criteria intentionally not implemented (managed feature store, separate prod GCP project if still deferred, Vertex Pipelines, bias audits, etc.) and why. Keeps the simplification charter coherent.
- **Depends on:** none; lands once the rest of M4 is in review so descopes reflect reality.

### UP-59 — source credentials + rate-limit primitives (on demand)

- **Labels:** `phase:m4`, `sub:m4f`, `type:feat`, `status:planned` — **Milestone:** M4
- **Scope:** opened only when a keyed source lands. Adds:
  - `core/ports/secrets.py` — port with dotenv local adapter + GCP Secret Manager adapter (OSS parity per constraint 3)
  - shared async rate limiter + backoff under `common/rate_limit.py`
  - `configs/sources/*.yaml` gains optional `credentials_ref` and `rate_limits` fields
- **AC:** a concrete authenticated source (e.g., Alpha Vantage demo endpoint) consumes credentials through the port; rate limiter proven under a synthetic 429 storm.
- **Depends on:** a concrete keyed-source need arising.

---

# M5 — scale-out and AWS foundation

Post-M4. Most of this was already scoped in prior backlog; scope trimmed to what's actually needed once L2 runs on real data.

## UP-47 — production environment decision

- **Labels:** `phase:m5`, `type:docs`, `status:planned` — **Milestone:** M5
- **Scope:** decide — does the repo take on a prod GCP project, or stay staging-only? L2 formally needs prod. If yes, mirror staging foundation + UP-26 approvals in a new project. If no, UP-48 already records the descope.
- **Depends on:** UP-26. **Blocks:** any real rollout claim.

## UP-37 — Vertex JobRunner adapter

- **Labels:** `phase:m5`, `type:feat`, `status:planned` — **Milestone:** M5
- **Scope:** third `JobRunner` adapter for workloads outgrowing Cloud Run Jobs. Only open once a concrete job justifies it.
- **Depends on:** UP-29a.

## UP-46 — feature store evaluation PR

- **Labels:** `phase:m5`, `type:docs`, `status:planned` — **Milestone:** M5
- **Scope:** evaluation PR: BQ views + `FeatureSpec` contracts (current state) vs. Feast vs. Vertex Feature Store. Default to views unless the data demonstrates a real need.
- **Depends on:** UP-63.

## UP-40 — AWS foundation

- **Labels:** `phase:m5`, `type:infra`, `status:planned` — **Milestone:** M5
- **Scope:** AWS adapter for every M4 port; mirrors GCP foundation. Explicit per-port mapping: BigQuery → Athena on S3 Parquet, Pub/Sub → MSK (Kafka), Memorystore → ElastiCache, Cloud Scheduler → EventBridge, Cloud Run → Fargate, Secret Manager → AWS Secrets Manager.
- **Depends on:** all M4 ports.

(UP-38 K8s backend and UP-39 K8s extensions are **explicitly deferred** — only open if a second K8s-requiring consumer appears that Vertex/GCE can't carry.)

---

# M6 — low-latency crypto forecasting

Phase 2. All M6 tickets are gated behind "M4 demonstrably closed on real data." Every M6 ticket is graded against the latency harness built in UP-60.

## UP-60 — latency SLO harness with waterfall dashboard and CI regression gate

- **Labels:** `phase:m6`, `type:feat`, `status:planned`
- **Milestone:** M6

### Goal

Make latency a first-class, measurable signal at every port boundary, render a waterfall in Grafana, and fail CI on regression beyond a declared budget.

### Context

M6 is graded against a p99 end-to-end budget (~35ms target). Code added before this harness exists will accrue latency silently. Shipping the harness first means every later M6 ticket has a measurable pass/fail. This is the single most commonly skipped and most expensive-to-retrofit ticket in a low-latency buildout.

### Scope

- new `src/ml_lifecycle_platform/common/latency.py`:
  - `LatencyClock` wrapping `time.monotonic_ns()` with `record(hop, start_ns)` emitting OTel histogram samples keyed by `hop`, `service`
  - `@timed_hop("predict.featurize")` async context manager
- annotate predict path in [src/ml_lifecycle_platform/serving/app.py](src/ml_lifecycle_platform/serving/app.py) and [src/ml_lifecycle_platform/serving/prediction.py](src/ml_lifecycle_platform/serving/prediction.py) with hops: `http.receive`, `auth`, `featurize`, `model.predict`, `emit.sink`, `http.respond`
- new `deployments/observability/grafana/dashboards/latency.json` — waterfall heatmap per hop, e2e p99 stat, per-hop burn
- new `tests/perf/test_predict_latency.py` (pytest + httpx) — 1k requests against warm compose, asserts p99 < `LATENCY_BUDGET_P99_MS` (env var, default 200ms for current FastAPI path; M6 tickets tighten per-path)
- `make perf` target + nightly `.github/workflows/perf-regression.yml` running against staging; opens an issue on regression
- extend [docs/runbooks/observability.md](docs/runbooks/observability.md) with a "latency waterfall" section — reading the dashboard, diagnosing p99, pulling a slow trace from Tempo

### Non-goals

- tightening budget to 35ms today — current FastAPI path will not meet that; M6 budgets attach to UP-65's fast path
- replacing FastAPI
- hardware clock / PTP (UP-68)

### Risks

- histogram cardinality — bound hop labels to the enumerated set; document the rule
- `monotonic_ns()` is process-local — cross-service p99 is trace-based, per-process is histogram-based; document in runbook

### Acceptance criteria

- every hop in predict path emits a histogram; waterfall renders real data after one staging cycle
- `make perf` green locally; nightly workflow green on staging
- a deliberately-slowed hop (50ms sleep in `model.predict`) fails the perf gate and triggers regression issue
- runbook explains reading the waterfall end-to-end

### Dependencies

- depends on UP-23 (landed)
- blocks every UP-6x

## UP-29b — `EventStream` port with local Redpanda and GCP Pub/Sub adapters

- **Labels:** `phase:m6`, `type:feat`, `status:planned`
- **Milestone:** M6

### Goal

Introduce the `EventStream` port for the hot path, ship local Redpanda + GCP Pub/Sub adapters. Serving does not use it yet — this is the seam M6 plugs into without touching M4 code.

### Context

UP-29a is fine for batch analytics. It is not fine for 15s-ahead tick forecasting. Hot-path consumers need pub/sub semantics, at-least-once delivery, and sub-second latency. Drawing the port now, before any consumer exists, gives UP-61 and UP-65 a stable target. Redpanda chosen locally because it speaks Kafka protocol (portable to MSK) without a JVM; NATS is an alternative if Redpanda operational weight becomes a problem.

### Scope

- new `src/ml_lifecycle_platform/core/ports/event_stream.py` — Protocols:
  - `EventPublisher.publish(topic, event, key) -> PublishAck`
  - `EventSubscriber.subscribe(topic, group) -> AsyncIterator[Envelope]` + `ack(envelope)`
- adapter 1 (local): `src/ml_lifecycle_platform/backends/local/redpanda_stream.py` using `aiokafka`; Compose profile adds single-node Redpanda
- adapter 2 (GCP): `src/ml_lifecycle_platform/backends/gcp/pubsub_stream.py` using async `google-cloud-pubsub`; topics + subs Terraform-managed
- new [deployments/gcp/terraform/pubsub.tf](deployments/gcp/terraform/pubsub.tf) — topics `predictions`, `ticks`, `decisions`; DLQ per topic; subscriptions added per consumer
- extend [docker-compose.yml](docker-compose.yml) with a `redpanda` service (opt-in via `COMPOSE_PROFILES=stream`)
- contract tests against both adapters via a shared fixture
- no serving wiring in this ticket

### Non-goals

- actual producer (UP-61) or consumer (UP-65)
- schema registry — reuse `schema_version` until contract tests force a move
- cross-region replication

### Risks

- Redpanda footprint in Compose — keep it a named profile; `make e2e-clean` stays lean by default
- Pub/Sub per-message billing at tick volume — UP-65 documents per-topic whether it uses `EventStream` or an in-process ring

### Acceptance criteria

- identical contract test passes against both adapters
- `docker compose --profile stream up` starts Redpanda + existing stack
- `terraform plan` shows Pub/Sub topics + DLQs; no IAM leaks
- nothing outside `backends/` imports either adapter directly

### Dependencies

- depends on UP-28
- blocks UP-61, UP-65, UP-67

## UP-62 — tick feature contracts

- **Labels:** `phase:m6`, `type:feat`, `status:planned` — **Milestone:** M6
- **Scope:** new `src/ml_lifecycle_platform/contracts/tick_event.py` (Pydantic) for Binance depth / trade / kline payloads; [src/ml_lifecycle_platform/core/feature_contracts.py](src/ml_lifecycle_platform/core/feature_contracts.py) extended with rolling-window feature specs (mid, imbalance, microprice, realized vol at 1s/5s/15s); Pandera schema for offline tick tables.
- **Non-goals:** ingestion (UP-61), online store (UP-63).
- **AC:** round-trip Pydantic tests; Pandera green on a fixture; one `FeatureSpec` shared by offline + online paths.
- **Depends on:** UP-28.

## UP-63 — online feature store port (Redis local, Memorystore GCP)

- **Labels:** `phase:m6`, `type:feat`, `status:planned` — **Milestone:** M6
- **Scope:** `OnlineFeatureStore` port; local Redis (Compose) + GCP Memorystore (Terraform) adapters; writer path from UP-61 ingestor, reader path from UP-65 fast serving; TTL per feature.
- **Non-goals:** Vertex Feature Store; offline/online join (UP-64).
- **AC:** ingestor write → serving read round-trip p99 < 5ms locally; Terraform-managed.
- **Depends on:** UP-62.

## UP-64 — offline/online feature symmetry check

- **Labels:** `phase:m6`, `type:feat`, `status:planned` — **Milestone:** M6
- **Scope:** single `FeatureSpec` drives offline batch (UP-32) + online streaming (UP-63); CI job recomputes online-logged features offline, fails on ε drift.
- **AC:** synthetic divergence fails CI; matched implementations pass.
- **Depends on:** UP-62, UP-63.

## UP-61 — Binance WS ingestor (upgrade of UP-51's REST adapter to WS)

- **Labels:** `phase:m6`, `type:feat`, `status:planned` — **Milestone:** M6
- **Scope:** async WS client (uvloop) for depth + trades + klines; reconnect with jitter; NTP skew probe gauge; backpressure policy; publishes `TickEvent` to `EventStream` (UP-29b) + feature updates to `OnlineFeatureStore` (UP-63). Formally a second adapter of the UP-51 `DataSource` port — same source identity (`binance`), new transport. Model spec points at the faster adapter via config.
- **Non-goals:** execution, broker integration.
- **AC:** staging ingestor sustains Binance mainnet stream 1h, zero dropped sequence numbers; UP-60 waterfall shows ingest→feature-update p99 < 5ms; `configs/models/binance_btc_1m.yaml` keeps training through UP-51 REST while a new M6 model spec reads from the WS adapter.
- **Depends on:** UP-29b, UP-51, UP-60, UP-62, UP-63.

## UP-65 — low-latency serving path (`serving/fast/`)

- **Labels:** `phase:m6`, `type:feat`, `status:planned` — **Milestone:** M6
- **Scope:** second serving surface: gRPC on uvloop, msgpack payloads, model warm at start, feature read via UP-63, fire-and-forget emit to `EventStream`; existing FastAPI path untouched.
- **Non-goals:** replace FastAPI; in-request drift.
- **AC:** predict p99 < 10ms under 1k rps locally; UP-60 budget enforced in CI.
- **Depends on:** UP-60, UP-63.

## UP-66 — first tick-level 15s-ahead forecasting model spec

- **Labels:** `phase:m6`, `type:feat`, `status:planned` — **Milestone:** M6
- **Scope:** new `configs/models/binance_btc_15s.yaml`; trained on replayed Binance history via UP-30 walk-forward CV; realized-PnL proxy metric; standard registration path.
- **AC:** `mlp train` → `register` → `promote staging` works with no bespoke path.
- **Depends on:** UP-30, UP-62, UP-35.

## UP-67 — decision emitter

- **Labels:** `phase:m6`, `type:feat`, `status:planned` — **Milestone:** M6
- **Scope:** after each tick prediction, UP-65 emits `DecisionEvent` (hold/long/short + confidence) to the `decisions` topic.
- **Non-goals:** execution / broker (stays out until broker ADR).
- **AC:** decision events visible in local + staging streams; UP-60 budget honored.
- **Depends on:** UP-29b, UP-65.

## UP-68 — GCP low-latency topology (pinned GCE VM, no cold-start)

- **Labels:** `phase:m6`, `type:infra`, `status:planned` — **Milestone:** M6
- **Scope:** move UP-65 off Cloud Run onto pinned GCE VM in same zone as Memorystore; private networking; startup script pulls pinned digest; Terraform under [deployments/gcp/terraform](deployments/gcp/terraform); Cloud Run remains for batch + classic serving.
- **Non-goals:** multi-zone HA — deferred until a second VM is justified.
- **AC:** p99 end-to-end ≤ UP-60 budget for 1h sustained run; zero cold starts.
- **Depends on:** UP-65.

## UP-69 — chaos and backpressure tests for the tick path

- **Labels:** `phase:m6`, `type:feat`, `status:planned` — **Milestone:** M6
- **Scope:** automated chaos cases — WS disconnect, Redis stall, stream slow-consumer, clock skew >100ms; each asserts latency SLO preserved or explicit load shed; scheduled on staging.
- **AC:** every case produces pass/fail on a dashboard; regressions alert via UP-25 router.
- **Depends on:** UP-68.

## UP-71 — latency operability runbook

- **Labels:** `phase:m6`, `type:docs`, `status:planned` — **Milestone:** M6
- **Scope:** "how to diagnose a p99 regression, which dashboards in which order, how to replay a bad window". Lands with UP-69.

---

# M7 — AWS low-latency parity

## UP-70 — AWS low-latency parity (EC2 + ElastiCache in Tokyo)

- **Labels:** `phase:m7`, `type:infra`, `status:planned` — **Milestone:** M7
- **Scope:** EC2 + ElastiCache mirror of UP-68 in Tokyo region; reuses UP-40 foundation. Only opened if multi-cloud matters after M6 is observed running.
- **Depends on:** UP-40, UP-68.

---

# Suggested execution order

1. **Now:** UP-26 (extend [#175](https://github.com/jellewillekes/ml-lifecycle-platform/issues/175)) + UP-28 + UP-49 + UP-50 in parallel (M3 close-out and M4a foundations are independent).
2. **Next:** UP-51 then UP-52 to close M4a.
3. **Then:** UP-29a (M4b) → UP-53 (M4c).
4. **Feedback loop (M4d):** UP-31 → UP-33 → UP-34 → UP-32 → UP-42; UP-30 in parallel once UP-29a lands.
5. **Release gates (M4e):** UP-45 → UP-54 → UP-35 → UP-44 → UP-43 → UP-36 → UP-41.
6. **Research lane (M4f):** UP-55 → UP-56 → UP-57 → UP-58 → UP-48; UP-59 on demand.
7. **M5:** UP-47 first (decision); then UP-37, UP-46, UP-40 in parallel.
8. **M6:** do not start before M4 closes. Order: UP-60 → UP-29b → UP-62 → UP-63 → UP-64 → UP-61 → UP-65 → UP-66 → UP-67 → UP-68 → UP-69 → UP-71.
9. **M7:** UP-70 only after UP-40 and UP-68 both land.

---

# Appendix — tracking setup checklist

Do these once, then the day-to-day `gh` commands in [Tracking and overview workflow](#tracking-and-overview-workflow) give you a complete view.

- [ ] Rename milestone `M4` to `M4 — Complete L2 ML platform on real data`
- [ ] Create milestone `M5 — Scale-out and AWS foundation`
- [ ] Create milestone `M6 — Low-latency crypto forecasting`
- [ ] Create milestone `M7 — AWS low-latency parity`
- [ ] Create labels `sub:m4a`, `sub:m4b`, `sub:m4c`, `sub:m4d`, `sub:m4e`, `sub:m4f` (color suggestion: shades of purple)
- [ ] Create label `phase:m6` (color `#B60205`, description "Low-latency crypto forecasting")
- [ ] Create label `phase:m7` (color `#B60205`, description "AWS low-latency parity")
- [ ] Create label `tier:research` (color `#C5DEF5`, description "Experimental model; diagnostic dashboards only, no paging")
- [ ] Extend [#175](https://github.com/jellewillekes/ml-lifecycle-platform/issues/175) UP-26 scope with the additions in this roadmap, or close it and reopen with the extended scope
- [ ] Close [#53](https://github.com/jellewillekes/ml-lifecycle-platform/issues/53) once [#165](https://github.com/jellewillekes/ml-lifecycle-platform/issues/165) lands
- [ ] Optional: create a GitHub Project (v2) board, group by milestone, columns `Backlog → Ready → In progress → Review → Done`
- [ ] Open M4a issues (UP-28, UP-49, UP-50, UP-51, UP-52) from the drafts above
- [ ] Open later sub-milestone issues as their predecessor PRs enter review — dependencies resolve to real issue numbers
