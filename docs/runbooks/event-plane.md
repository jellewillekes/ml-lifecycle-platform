# Runbook: prediction event plane

The event plane is the durable record of what serving predicted. Drift, replay,
and feedback all read from it. It is the prediction-logging / data-capture
component of the platform: serving emits a `PredictionEvent` per row, off the
request path, to a configurable cold sink.

The contract lives in [`prediction_event.py`](../../src/ml_lifecycle_platform/contracts/prediction_event.py)
and its stability rules are in the
[release contract](../reference/release-contract.md). This runbook covers how to
operate the sink.

## Adapters

| Sink | When | Backed by |
| --- | --- | --- |
| `jsonl` | local / CI | append-only JSON Lines file |
| `bigquery` | hosted staging | `mlp_events.prediction_events_v1` table |
| `none` | default | emission disabled |

The sink is chosen by env var; serving and call sites only ever reference the
`PredictionEventSink` port, never a concrete adapter.

## Configuration

| Env var | Default | Meaning |
| --- | --- | --- |
| `MLP_EVENT_SINK` | `none` | `none` / `jsonl` / `bigquery` |
| `MLP_EVENT_JSONL_PATH` | `artifacts/prediction-events.jsonl` | JSONL output path |
| `MLP_EVENT_BQ_TABLE` | — | `project.dataset.table` (required for `bigquery`) |
| `MLP_EVENT_SAMPLE_PCT` | `100` | percent of predictions captured |
| `MLP_EVENT_QUEUE_MAX` | `10000` | bounded queue size; overflow is dropped |
| `MLP_EVENT_FSYNC` | `false` | fsync each JSONL append |
| `MLP_ENV`, `GIT_SHA` | `local`, `dev` | envelope `env` / `git_sha` |

Emission never blocks the predict path: events go through a bounded queue drained
by a background worker. On a full queue (or a sink write failure) the event is
dropped and counted on the `events_dropped_total{reason}` metric — protect p95
with `MLP_EVENT_SAMPLE_PCT` rather than by letting the queue saturate.

## Tail the local sink

```bash
MLP_EVENT_SINK=jsonl make serve   # serving now appends prediction events
tail -f artifacts/prediction-events.jsonl
tail -n 1 artifacts/prediction-events.jsonl | python -m json.tool
```

## Query the local sink with DuckDB

DuckDB over the JSONL file is the local parity for a BigQuery query — same
columns, no cloud needed:

```sql
-- duckdb
SELECT model_ref.model_name AS model_name,
       count(*)             AS n,
       avg(latency_ns)      AS avg_latency_ns
FROM read_json_auto('artifacts/prediction-events.jsonl')
GROUP BY 1
ORDER BY n DESC;
```

## Query BigQuery (and prove partition pruning)

The table is partitioned by `DATE(event_time)` and clustered on
`(model_name, env)`. A query that filters on the partition column scans only the
matching days — compare the bytes billed with and without the filter:

```sql
-- pruned: filters the partition column
SELECT model_name, count(*) AS n
FROM `PROJECT.mlp_events.prediction_events_v1`
WHERE event_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
  AND model_name = 'binance_btc_1m'
GROUP BY model_name;

-- full scan (no partition filter) — note the larger "bytes processed"
SELECT model_name, count(*) AS n
FROM `PROJECT.mlp_events.prediction_events_v1`
GROUP BY model_name;
```

Run both with `bq query --dry_run --use_legacy_sql=false '<sql>'` and confirm the
pruned query reports far fewer bytes.

## Schema evolution / add a column

The envelope uses bare-major versioning (`schema_version: "1"`). Follow the rule
in the [release contract](../reference/release-contract.md#event-plane-contracts):

- **additive, optional field** → no version bump. Add the field to
  `PredictionEvent`, add a `NULLABLE` column to `events.tf`, `terraform apply`.
  Old readers ignore it; old rows read back as null.
- **breaking change** (rename, type change, new required field) → bump the major
  (`"1"` → `"2"`), ship a new table `prediction_events_v2`, and migrate readers.
  A reader refuses an unknown major rather than guessing.

The BigQuery table schema is authored in
[`events.tf`](../../deployments/gcp/terraform/events.tf), not derived from the
Pydantic model — it stays fully Terraform-managed (no UI edits).

## Evolution paths

Both are adapter swaps behind the same `PredictionEventSink` port:

- **Throughput / cost:** replace the batched streaming insert with the BigQuery
  Storage Write API (cheaper, exactly-once via stream offsets).
- **Portability (AWS / lakehouse):** a Parquet-to-object-store adapter
  (`gs://` → `s3://`, local files for dev) with a BigLake/Athena external table
  as the query layer; DuckDB stays the local reader. The hot real-time path is
  separate (UP-29b: Pub/Sub → Kafka).
