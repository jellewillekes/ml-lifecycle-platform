locals {
  otlp_enabled = (
    length(trimspace(var.grafana_cloud_otlp_auth_header)) > 0
    && length(trimspace(var.grafana_cloud_otlp_endpoint)) > 0
  )
  otlp_auth_secret_id = "${local.foundation_name_prefix}-staging-otlp-auth-header"
}

resource "google_secret_manager_secret" "otlp_auth_header" {
  count = local.otlp_enabled ? 1 : 0

  project   = data.google_project.current.project_id
  secret_id = local.otlp_auth_secret_id

  labels = merge(local.common_labels, { purpose = "otlp_auth_header" })

  replication {
    auto {}
  }

  depends_on = [google_project_service.required["secretmanager.googleapis.com"]]
}

resource "google_secret_manager_secret_version" "otlp_auth_header" {
  count = local.otlp_enabled ? 1 : 0

  secret      = google_secret_manager_secret.otlp_auth_header[0].id
  secret_data = var.grafana_cloud_otlp_auth_header
}

resource "google_secret_manager_secret_iam_member" "runtime_otlp_auth_accessor" {
  count = local.otlp_enabled ? 1 : 0

  project   = google_secret_manager_secret.otlp_auth_header[0].project
  secret_id = google_secret_manager_secret.otlp_auth_header[0].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}
