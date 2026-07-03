locals {
  events_dataset_id          = "mlp_events"
  prediction_events_table_id = "prediction_events_v1"
}

# Cold event plane: the durable record of what serving predicted. Drift,
# replay, and feedback read from here. Staging-scoped; production parity is a
# one-block follow-up mirroring sql.tf when production rollout is in scope.
resource "google_bigquery_dataset" "events" {
  project     = data.google_project.current.project_id
  dataset_id  = local.events_dataset_id
  location    = var.region
  description = "Prediction event plane (cold sink) for drift, replay, and feedback."

  labels = merge(local.common_labels, { purpose = "events" })

  depends_on = [google_project_service.required["bigquery.googleapis.com"]]
}

# event_time is a derived TIMESTAMP partition column (BigQuery cannot partition
# on the INT64 event_time_ns); model_name and env are flattened top-level
# cluster keys (clustering cannot target nested STRUCT fields). The exact
# nanosecond timestamp is preserved in event_time_ns.
resource "google_bigquery_table" "prediction_events" {
  project             = data.google_project.current.project_id
  dataset_id          = google_bigquery_dataset.events.dataset_id
  table_id            = local.prediction_events_table_id
  deletion_protection = var.enable_deletion_protection

  labels = merge(local.common_labels, { purpose = "events" })

  time_partitioning {
    type  = "DAY"
    field = "event_time"
  }

  clustering = ["model_name", "env"]

  schema = jsonencode([
    { name = "event_id", type = "STRING", mode = "REQUIRED" },
    { name = "corr_id", type = "STRING", mode = "REQUIRED" },
    { name = "schema_version", type = "STRING", mode = "REQUIRED" },
    { name = "event_time", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "event_time_ns", type = "INT64", mode = "REQUIRED" },
    { name = "ingest_time_ns", type = "INT64", mode = "REQUIRED" },
    { name = "latency_ns", type = "INT64", mode = "REQUIRED" },
    { name = "model_name", type = "STRING", mode = "REQUIRED" },
    { name = "env", type = "STRING", mode = "REQUIRED" },
    { name = "service", type = "STRING", mode = "REQUIRED" },
    { name = "git_sha", type = "STRING", mode = "NULLABLE" },
    { name = "run_id", type = "STRING", mode = "NULLABLE" },
    { name = "model_ref", type = "JSON", mode = "NULLABLE" },
    { name = "features", type = "JSON", mode = "NULLABLE" },
    { name = "prediction", type = "JSON", mode = "NULLABLE" },
  ])
}

# CI (staging) manages data across the events dataset.
resource "google_bigquery_dataset_iam_member" "ci_staging_events_editor" {
  project    = data.google_project.current.project_id
  dataset_id = google_bigquery_dataset.events.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.ci_staging.email}"
}

# Serving runtime writes prediction events to the one table only.
resource "google_bigquery_table_iam_member" "runtime_prediction_events_editor" {
  project    = data.google_project.current.project_id
  dataset_id = google_bigquery_dataset.events.dataset_id
  table_id   = google_bigquery_table.prediction_events.table_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.runtime.email}"
}
