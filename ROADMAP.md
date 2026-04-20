# ML Lifecycle Platform — Roadmap

Last updated: 2026-04-20.
Status snapshot: M0 ✅, M1 ✅, M2 ✅ (closing via [#165](https://github.com/jellewillekes/ml-lifecycle-platform/issues/165), [#168](https://github.com/jellewillekes/ml-lifecycle-platform/issues/168)), M3 in progress, M4/M5/M6 planned.

## Purpose

This file is the single public roadmap for the platform. It replaces the piecemeal planning in [#53](https://github.com/jellewillekes/ml-lifecycle-platform/issues/53) and [docs/simplification-charter.md](docs/simplification-charter.md) with one document that:

- lists every planned ticket with enough detail to open as a GitHub issue,
- makes dependencies explicit,
- records the constraints (cost, portability, latency) that shape decisions,
- describes how to track progress without re-reading this file every week.

The ticket template is deliberately the same one the closed issues already use (Goal / Context / Scope / Non-goals / Risks / Acceptance criteria / Dependencies). Each ticket in this file can be pasted into `gh issue create --body-file` as-is.

## How to read this

- **Waves** are the dependency-driven order. Wave N cannot meaningfully start before Wave N-1 has landed its port/contract parts.
- **Milestones** (M3, M4, M5, M6) are the phase grouping — one GitHub milestone per phase.
- Tickets keep the `UP-XX` identifier so cross-referencing with prior backlog stays stable.
- Wave 1 tickets are fully drafted. Later waves are progressively terser — enough to slot into the backlog, still need one polishing pass before opening.
- Every ticket includes `Labels` and `Milestone` so the grooming step is mechanical.

## Guiding constraints

These are hard rules. A ticket that violates them gets rewritten, not accepted.

1. **Cost rule — GCP / AWS only.** No third-party SaaS subscriptions or tokens, even free-tier (no Slack/PagerDuty/SendGrid/Grafana Cloud tokens). Self-host on cloud compute instead.
2. **Portability — local → GCP → AWS behind one port.** Every new subsystem gets a `core/ports/*.py` Protocol plus at least a local adapter + GCP adapter in the same PR. AWS is a third adapter later; the port must not leak GCP types.
3. **Local-first invariant.** `make check` passes with no cloud account after every PR. The local golden path stays the contributor's entry point.
4. **Latency budget as an axis.** Every M6 ticket is graded against a p99 latency budget (see [M6](#m6--low-latency-trading-path)). Wave 1's UP-60 creates the harness that enforces it.
5. **One PR per issue.** Every issue ships end-to-end in one PR. No "Suggested PR slices" sections.
6. **No Co-Authored-By or AI attribution lines** in commits or PR bodies.

## Current state snapshot

Taken from [docs/architecture/current-state.md](docs/architecture/current-state.md) plus a scan of closed issues.

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

**Open gaps vs. MLOps L2 + low-latency future:**

- No GitHub Environments / prod approvals (UP-26 drafted as [#175](https://github.com/jellewillekes/ml-lifecycle-platform/issues/175))
- No portable event plane (hot or cold) in production
- No drift, replay, feedback, or decay detection
- No automated retraining trigger or env-aware promotion
- No pipeline-as-artifact CD
- No online feature store, no tick ingestion, no low-latency serving path
- No AWS adapter for any port (port definitions don't exist yet)

## Tracking and overview workflow

Three layers, each answering a different question. Pick any two to start; the third is optional.

1. **Milestones (M3 → M6)** — the "are we done with M4?" bar. Close a milestone when every issue closes. Create `M5 — Scale-up and alternate backends` and `M6 — Low-latency trading path` milestones now.
2. **Labels** — existing `phase:m0..m5`, `type:*`, `status:*` already cover most cases. **Add `phase:m6 — Low-latency trading path`** (color suggestion: `#B60205`).
3. **Dependencies** — continue the `## Dependencies` block you already use in issue bodies. Query blocked work with `gh issue list --label status:blocked`.
4. **Optional: one GitHub Project (v2) board** grouped by milestone with columns `Backlog → Ready → In progress → Review → Done`. One bookmark, whole plan visible.

Day-to-day commands:

```
gh issue list --milestone M4 --state open              # what's left in current phase
gh issue list --label phase:m6                         # every low-latency ticket
gh issue list --label status:blocked                   # waiting
gh issue list --search "UP-29" --state all             # specific ticket
gh issue list --milestone M4 --state closed \
  --json closedAt,number,title --jq 'sort_by(.closedAt)'   # velocity
```

## Milestone map

| Milestone | Theme | Tickets |
|---|---|---|
| **M3** close-out | Operable GCP platform | UP-26 |
| **M4a** | Event plane (ports + adapters) | UP-28, UP-29a, UP-29b, UP-41 |
| **M4b** | Offline analytics | UP-31, UP-32, UP-30 |
| **M4c** | Feedback loop | UP-33, UP-34, UP-42 |
| **M4d** | Automated release gating | UP-35, UP-43, UP-44, UP-36, UP-45 |
| **M5** | Scale-up and AWS parity | UP-37, UP-38, UP-39, UP-40, UP-46, UP-47, UP-48, UP-70 |
| **M6** | Low-latency trading path | UP-60, UP-62, UP-63, UP-64, UP-61, UP-65, UP-66, UP-67, UP-68, UP-69, UP-71 |

## Dependency graph

```
UP-26 (M3 gov)
  │
  ├── UP-28 (event contract) ── UP-29a (cold sink port + adapters)
  │                              │          └── UP-31 ── UP-32 ── UP-30
  │                              │          └── UP-33 ── UP-34 ── UP-42
  │                              │          └── UP-35 ── UP-43 ── UP-44
  │                              │                                └── UP-36 ── UP-45
  │                              └── UP-41 (DLQ + backfill)
  │
  ├── UP-29b (hot stream port + adapters)
  │    └── UP-61 (Binance ingestor)
  │    └── UP-65 (fast serving)
  │    └── UP-67 (decision emitter)
  │
  └── UP-60 (latency harness) ── blocks every UP-6x

UP-62 (tick contracts) ── UP-63 (online store) ── UP-64 (symmetry check)
                                                   └── UP-65 ── UP-66 ── UP-68 ── UP-69

UP-35 (env-aware promote) ── UP-47 (prod env decision)
All M4 ports ── UP-40 (AWS foundation) ── UP-70 (AWS low-latency parity)
```

---

# Wave 1 — ready to open now

Four tickets. UP-26 already exists as [#175](https://github.com/jellewillekes/ml-lifecycle-platform/issues/175) with a lighter scope — either extend that issue with the additions noted below, or leave #175 as-is and track the extensions as follow-ups.

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

## UP-28 — `PredictionEvent` Pydantic contract with ns-precision envelope

- **Labels:** `phase:m4`, `type:feat`, `status:planned`
- **Milestone:** M4

### Goal

A canonical, versioned Pydantic model describing a single prediction, with an envelope designed to later carry tick-level latency attribution. Contract-only — no sink, no emitter.

### Context

[src/ml_lifecycle_platform/contracts/runtime_event.py](src/ml_lifecycle_platform/contracts/runtime_event.py) is a generic `RuntimeEvent`. `PredictionEvent` is narrower and drives observability, drift, replay, and feedback. It must land before UP-29a/b. ns-precision timestamps are mandatory now — retrofitting them when M6 starts would be a breaking schema change.

### Scope

- new `src/ml_lifecycle_platform/contracts/prediction_event.py` with:
  - `PredictionEvent` (Pydantic v2): `schema_version: Literal["1"]`, `event_id: UUID`, `corr_id: str`, `event_time_ns: int`, `ingest_time_ns: int`, `model_ref: ModelRef`, `features: dict[str, JsonValue]`, `prediction: JsonValue`, `latency_ns: int`, `envelope: EventEnvelope`
  - `EventEnvelope`: `service: str`, `env: Literal["local","staging","prod"]`, `run_id: str | None`, `git_sha: str | None`
  - `.to_dict()` / `.from_dict()` matching `RuntimeEvent` style
- schema-evolution rule documented in [docs/reference/release-contract.md](docs/reference/release-contract.md): breaking → bump `schema_version`; reader refuses unknown major
- unit tests in `tests/unit/test_prediction_event.py` — round-trip, forbidden extras, ns overflow, idempotency-key equivalence
- **do not** emit from serving yet (UP-29a wires the emitter)

### Non-goals

- sink/stream implementation (UP-29a, UP-29b)
- BigQuery schema (belongs to UP-29a)
- drift logic (UP-32)

### Risks

- envelope bikeshedding — keep minimal; reject anything not needed by a concrete downstream
- `features` cardinality at tick volume — call out in the schema doc that UP-29a will columnar-break when needed

### Acceptance criteria

- `make check` green
- unit tests cover valid event, missing required field, unknown `schema_version` refused, ns overflow
- schema doc lists every field + stability guarantee
- no call site imports from `contracts/__init__.py` re-exports

### Dependencies

- none; blocks UP-29a, UP-29b

---

## UP-29a — `EventSink` port with local JSONL and BigQuery adapters

- **Labels:** `phase:m4`, `type:feat`, `status:planned`
- **Milestone:** M4

### Goal

Introduce the `EventSink` port for the cold write path, ship both a local JSONL adapter and a GCP BigQuery adapter in the same PR, and emit `PredictionEvent` from serving through the port. Call sites must not know which adapter is live.

### Context

L2 needs a durable event plane that drift, replay, and feedback read from. Defining the port now with two adapters is the only way to honor portability: AWS adds a third adapter, never a rewrite. Splitting hot stream (UP-29b) from cold sink keeps M6 unblocked without coupling it to BigQuery.

### Scope

- new `src/ml_lifecycle_platform/core/ports/event_sink.py` — `EventSink` Protocol: `write`, `write_batch`, `flush(timeout_s)`, `close`
- adapter 1: `src/ml_lifecycle_platform/backends/local/prediction_event_sink.py` — async-buffered JSONL writer backed by `LocalEventStore`, configurable fsync
- adapter 2: `src/ml_lifecycle_platform/backends/gcp/bigquery_event_sink.py` — batched BQ streaming; schema from `PredictionEvent.model_json_schema()`; retries on 5xx; drops to DLQ (UP-41 ships the DLQ itself)
- Terraform under [deployments/gcp/terraform](deployments/gcp/terraform):
  - dataset `mlp_events` (regional, same as Cloud Run)
  - table `prediction_events_v1` partitioned by `DATE(event_time_ns)`, clustered on `model_ref.name, env`
  - IAM: `mlp-ci-staging` → `bigquery.dataEditor` on dataset; serving runtime SA → `bigquery.dataEditor` scoped to the one table
- serving wiring: [src/ml_lifecycle_platform/serving/app.py](src/ml_lifecycle_platform/serving/app.py) resolves sink from runtime profile; emit from a background task so predict path is never blocked
- new `docs/runbooks/event-plane.md` — schema evolution, add a column, tail locally, query BQ
- tests: unit for both adapters; integration `tests/integration/test_bigquery_event_sink.py` guarded by `GCP_PROJECT_ID`; e2e row-in-BQ within 10s

### Non-goals

- DLQ/backfill (UP-41)
- hot streaming (UP-29b)
- feature-level columnar breakout

### Risks

- predict-path latency regression — drop-on-full ring buffer + Prometheus counter + alert (piggyback UP-25)
- BQ streaming cost at tick volume — explicit: cold sink is not the tick path; M6 uses UP-29b
- partition-pruning misuse — AC includes a BQ query proving the partition filter kicks in

### Acceptance criteria

- single `EventSink` Protocol is the only type serving + runtime reference
- `make e2e-clean` green with JSONL; staging e2e green with BQ adapter
- predict p95 within ±5% of pre-change baseline (UP-23 metrics)
- BQ table fully Terraform-managed; no UI-created resources
- runbook covers add-column, tail-local, query-bq

### Dependencies

- depends on UP-28
- blocks UP-30, UP-31, UP-32, UP-34, UP-41

---

## UP-29b — `EventStream` port with local Redpanda and GCP Pub/Sub adapters

- **Labels:** `phase:m4`, `type:feat`, `status:planned`
- **Milestone:** M4

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

---

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

---

# Wave 2 — unlocked by Wave 1

Short drafts — Scope and AC are firm; fill Context and Risks before opening.

## UP-41 — event-plane DLQ, retry policy, and backfill CLI

- **Labels:** `phase:m4`, `type:feat`, `status:planned` — **Milestone:** M4
- **Scope:** `DeadLetterSink` port; local JSONL DLQ + GCP DLQ topic + `prediction_events_dlq_v1` BQ table; retry policy shared by sink/stream; new CLI `mlp events replay --from-dlq --since=<ts>` that re-emits failed events deduped on `event_id`.
- **Non-goals:** PII scrub, cross-region DR.
- **AC:** forced BQ 503s drain to DLQ; `mlp events replay` drains DLQ into live sink with zero duplicates.
- **Depends on:** UP-29a, UP-29b.

## UP-31 — release-linked drift baselines

- **Labels:** `phase:m4`, `type:feat`, `status:planned` — **Milestone:** M4
- **Scope:** `DriftBaseline` artifact (Pandera schema for feature + label stats) computed at promotion and attached to `release_manifest.json`; stored via object-store port (local FS / GCS); `registry/release_evidence.py` extends with `baseline_ref`.
- **Non-goals:** drift computation (UP-32); stat-test debate — pick KS + mean/std for v1, documented.
- **AC:** promoting writes a baseline artifact; `mlp registry show-baseline <version>` prints it; Pandera validates.
- **Depends on:** UP-29a.

## UP-32 — batch drift MVP against windowed events

- **Labels:** `phase:m4`, `type:feat`, `status:planned` — **Milestone:** M4
- **Scope:** Cloud Run Job reading a window through `BatchEventReader` port (DuckDB local, BQ hosted), comparing against UP-31 baseline, emitting `drift_report.json` into release evidence + a Prometheus gauge for UP-42.
- **Non-goals:** in-request drift; auto-promote/demote on drift.
- **AC:** synthetic shifted window produces KS > threshold; stable window shows no drift.
- **Depends on:** UP-29a, UP-31.

## UP-30 — offline replay harness

- **Labels:** `phase:m4`, `type:feat`, `status:planned` — **Milestone:** M4
- **Scope:** `mlp replay --from=<ts> --to=<ts> --candidate=<model@alias>` pulls events via `BatchEventReader`, reruns through candidate, writes `replay_report.json` (agreement rate, regression metrics, per-segment breakdown) into MLflow artifacts.
- **Non-goals:** live shadow replay (already available via serving shadow mode); distributed replay.
- **AC:** replay against known-equivalent candidate returns 100% agreement; known-worse candidate flags the gap.
- **Depends on:** UP-29a.

## UP-62 — tick feature contracts

- **Labels:** `phase:m6`, `type:feat`, `status:planned` — **Milestone:** M6
- **Scope:** new `src/ml_lifecycle_platform/contracts/tick_event.py` (Pydantic) for Binance depth / trade / kline payloads; [src/ml_lifecycle_platform/core/feature_contracts.py](src/ml_lifecycle_platform/core/feature_contracts.py) extended with rolling-window feature specs (mid, imbalance, microprice, realized vol at 1s/5s/15s); Pandera schema for offline tick tables.
- **Non-goals:** ingestion (UP-61), online store (UP-63).
- **AC:** round-trip Pydantic tests; Pandera green on a fixture; one `FeatureSpec` shared by offline + online paths.
- **Depends on:** UP-28.

---

# Wave 3 — feedback loop and release gating

## UP-33 — delayed-label ingestion contracts

- **Labels:** `phase:m4`, `type:feat`, `status:planned` — **Milestone:** M4
- **Scope:** Pydantic `LabelEvent` for ingestion/API; Pandera for batch `labels` table; join keys + freshness SLO + late-arrival policy.
- **AC:** Pandera catches bad join keys; freshness SLO published in [docs/reference/release-contract.md](docs/reference/release-contract.md).
- **Depends on:** UP-28.

## UP-34 — feedback capture and realized-performance table

- **Labels:** `phase:m4`, `type:feat`, `status:planned` — **Milestone:** M4
- **Scope:** Cloud Run Job joining `prediction_events_v1` ⋈ `labels`; Pandera on joined output; `realized_performance_v1` BQ table + DuckDB local equivalent.
- **AC:** local + staging e2e write a realized-performance row; UP-42 consumes it.
- **Depends on:** UP-29a, UP-33.

## UP-42 — model-quality dashboards and decay alerts

- **Labels:** `phase:m4`, `type:infra`, `status:planned` — **Milestone:** M4
- **Scope:** Grafana OSS panels for realized-accuracy / calibration / per-segment from UP-34; burn-rate alert on decay; routed via UP-25 alert-router.
- **AC:** synthetic accuracy drop produces a delivered alert.
- **Depends on:** UP-34, UP-25.

## UP-35 — env-aware promotion with replay/drift/health gates

- **Labels:** `phase:m4`, `type:feat`, `status:planned` — **Milestone:** M4
- **Scope:** replace alias-only promotion — `mlp promote --to=staging|prod` runs UP-30 replay + UP-32 drift + serving-health probe; emits `promotion_decision.json` with each gate's verdict; `prod` requires UP-26 approval; extend release evidence.
- **Non-goals:** canary traffic shifting (existing router feature).
- **AC:** failing gate blocks promotion; evidence records the failing gate; `prod` requires env approval.
- **Depends on:** UP-26, UP-30, UP-32, UP-34.

## UP-43 — continuous-training trigger

- **Labels:** `phase:m4`, `type:feat`, `status:planned` — **Milestone:** M4
- **Scope:** `RetrainTrigger` port — local cron+file watcher adapter, Cloud Scheduler + Eventarc filter over drift/decay adapter; Cloud Run Job that retrains → registers candidate → invokes UP-35 in staging.
- **Non-goals:** auto-promote to prod.
- **AC:** synthetic drift event kicks retrain; staging-only promotion visible in evidence.
- **Depends on:** UP-29b, UP-32, UP-34, UP-35.

## UP-44 — pipeline versioning and pipeline CD workflow

- **Labels:** `phase:m4`, `type:ci`, `status:planned` — **Milestone:** M4
- **Scope:** treat pipeline image as deployable artifact distinct from serving/jobs; pin pipeline image digest + `PipelineSpec` hash in every training run's tags; new `deploy-pipeline-staging.yml` publishes, runs synthetic end-to-end pipeline, promotes by digest; `promotion_decision.json` records pipeline digest.
- **AC:** breaking pipeline change caught by synthetic run; every training run carries pipeline-digest tag.
- **Depends on:** UP-26.

## UP-45 — ML metadata lineage over MLflow + BigQuery

- **Labels:** `phase:m4`, `type:feat`, `status:planned` — **Milestone:** M4
- **Scope:** BQ views over MLflow tags + `prediction_events_v1` + release evidence surfacing: dataset fingerprint → pipeline run → model version → release → prediction-event window. Queryable by UP-43.
- **Non-goals:** Vertex ML Metadata (revisit only if views insufficient).
- **AC:** one SQL view answers "which dataset produced the current prod model?" and "which events were scored by which version?".
- **Depends on:** UP-29a, UP-35.

## UP-36 — challenger automation

- **Labels:** `phase:m4`, `type:feat`, `status:planned` — **Milestone:** M4
- **Scope:** job generating challenger specs from staleness / UP-32 drift / UP-34 decay; trains + registers as `candidate`; no auto-prod.
- **AC:** synthetic trigger produces registered challenger; UP-35 gates run against it on next promotion.
- **Depends on:** UP-43.

---

# Wave 4 — HFT path wired end-to-end

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

## UP-61 — Binance WS ingestor

- **Labels:** `phase:m6`, `type:feat`, `status:planned` — **Milestone:** M6
- **Scope:** async WS client (uvloop) for depth + trades + klines; reconnect with jitter; NTP skew probe gauge; backpressure policy; publishes `TickEvent` to `EventStream` (UP-29b) + feature updates to `OnlineFeatureStore` (UP-63).
- **Non-goals:** execution, broker integration.
- **AC:** staging ingestor sustains Binance mainnet stream 1h, zero dropped sequence numbers; UP-60 waterfall shows ingest→feature-update p99 < 5ms.
- **Depends on:** UP-29b, UP-60, UP-62, UP-63.

## UP-65 — low-latency serving path (`serving/fast/`)

- **Labels:** `phase:m6`, `type:feat`, `status:planned` — **Milestone:** M6
- **Scope:** second serving surface: gRPC on uvloop, msgpack payloads, model warm at start, feature read via UP-63, fire-and-forget emit to `EventStream`; existing FastAPI path untouched.
- **Non-goals:** replace FastAPI; in-request drift.
- **AC:** predict p99 < 10ms under 1k rps locally; UP-60 budget enforced in CI.
- **Depends on:** UP-60, UP-63.

## UP-66 — first tick-level 15s-ahead forecasting model spec

- **Labels:** `phase:m6`, `type:feat`, `status:planned` — **Milestone:** M6
- **Scope:** new `configs/models/binance_btc_15s.yaml`; trained on replayed Binance history via UP-30; walk-forward CV; realized-PnL proxy metric; standard registration path.
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

---

# Wave 5 — scale-up and AWS parity

| Ticket | Labels / Milestone | One-liner | Depends on |
|---|---|---|---|
| **UP-37** `feat/vertex-job-runner` | `phase:m5`, `type:feat` / M5 | third `JobRunner` adapter for workloads outgrowing Cloud Run Jobs | UP-29a |
| **UP-46** `feat/feature-store-evaluate` | `phase:m5`, `type:docs` / M5 | evaluation PR: BQ views vs Feast vs Vertex FS; default to views | UP-63 |
| **UP-38** `infra/k8s-backend` | `phase:m5`, `type:infra` / M5 | `deployments/k8s/` + Helm + K8s `JobRunner` — only if Vertex/GCE can't carry the load | UP-68 |
| **UP-39** `feat/k8s-extensions` | `phase:m5`, `type:feat` / M5 | Argo / KServe / Knative — only when a second K8s consumer exists | UP-38 |
| **UP-40** `infra/aws-foundation` | `phase:m5`, `type:infra` / M5 | AWS adapter for every M4 port; mirrors GCP foundation | all M4 ports |
| **UP-70** `infra/aws-low-latency-parity` | `phase:m6`, `type:infra` / M6 | EC2 + ElastiCache mirror of UP-68 in Tokyo region | UP-40, UP-68 |

---

# Cross-cutting scope decisions

## UP-47 — production environment decision

- **Labels:** `phase:m5`, `type:docs`, `status:planned` — **Milestone:** M5
- **Scope:** decide — does the repo take on a prod GCP project, or stay staging-only? L2 formally needs prod. If yes, mirror staging foundation + UP-26 approvals in a new project. If no, UP-48 records the descope.
- **Depends on:** UP-26. **Blocks:** any real rollout claim.

## UP-48 — ADR on deliberate MLOps-L2 descopes

- **Labels:** `phase:m5`, `type:docs`, `status:planned` — **Milestone:** M5
- **Scope:** ADR listing L2 criteria intentionally not implemented (feature store, prod surface, etc.) and why. Keeps the simplification charter coherent.

## UP-71 — latency operability runbook

- **Labels:** `phase:m6`, `type:docs`, `status:planned` — **Milestone:** M6
- **Scope:** "how to diagnose a p99 regression, which dashboards in which order, how to replay a bad window". Lands with UP-69.

---

# Suggested execution order

1. **Now:** UP-26 (extend #175), UP-28 in parallel.
2. **Next:** UP-29a + UP-29b in the same window.
3. **Then:** UP-60 — do not start any M6 ticket before this.
4. **Analytics:** UP-31 → UP-32 → UP-30; UP-33 → UP-34 → UP-42 (two tracks in parallel).
5. **Release gates:** UP-35 → UP-43 → UP-44 → UP-36 → UP-45.
6. **Features + symmetry:** UP-62 → UP-63 → UP-64.
7. **HFT path:** UP-61 → UP-65 → UP-66 → UP-67 → UP-68 → UP-69.
8. **Scale + AWS:** UP-37, UP-46, UP-40 → UP-70; UP-38/39 only on demand.
9. **Always-on:** UP-47, UP-48, UP-71 — open as the corresponding scope questions come up.

---

# Appendix — tracking setup checklist

Do these once, then the day-to-day `gh` commands in [Tracking and overview workflow](#tracking-and-overview-workflow) give you a complete view.

- [ ] Create milestone `M5 — Scale-up and alternate backends` (Settings → Milestones)
- [ ] Create milestone `M6 — Low-latency trading path`
- [ ] Create label `phase:m6` (color `#B60205`, description "Low-latency trading path")
- [ ] Extend [#175](https://github.com/jellewillekes/ml-lifecycle-platform/issues/175) UP-26 scope with the additions in this roadmap, or close it and reopen with the extended scope
- [ ] Close [#53](https://github.com/jellewillekes/ml-lifecycle-platform/issues/53) once [#165](https://github.com/jellewillekes/ml-lifecycle-platform/issues/165) lands
- [ ] Optional: create a GitHub Project (v2) board, group by milestone, columns `Backlog → Ready → In progress → Review → Done`
- [ ] Open Wave 1 issues (UP-28, UP-29a, UP-29b, UP-60) from the drafts above
- [ ] Open Wave 2 issues after Wave 1 PRs are in review — dependencies resolve to real issue numbers
- [ ] Continue wave by wave — opening a ticket ahead of its dependency just creates noise in the backlog
