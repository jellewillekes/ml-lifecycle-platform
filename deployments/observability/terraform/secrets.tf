resource "random_password" "grafana_admin" {
  length  = 24
  special = true
}

resource "google_secret_manager_secret" "grafana_admin_password" {
  project   = data.google_project.current.project_id
  secret_id = "${local.name_prefix}-grafana-admin-password"

  labels = merge(local.common_labels, { purpose = "grafana_admin" })

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "grafana_admin_password" {
  secret      = google_secret_manager_secret.grafana_admin_password.id
  secret_data = random_password.grafana_admin.result
}

resource "google_secret_manager_secret" "tempo_hmac_access" {
  project   = data.google_project.current.project_id
  secret_id = "${local.name_prefix}-tempo-hmac-access"

  labels = merge(local.common_labels, { purpose = "tempo_hmac" })

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "tempo_hmac_access" {
  secret      = google_secret_manager_secret.tempo_hmac_access.id
  secret_data = google_storage_hmac_key.tempo.access_id
}

resource "google_secret_manager_secret" "tempo_hmac_secret" {
  project   = data.google_project.current.project_id
  secret_id = "${local.name_prefix}-tempo-hmac-secret"

  labels = merge(local.common_labels, { purpose = "tempo_hmac" })

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "tempo_hmac_secret" {
  secret      = google_secret_manager_secret.tempo_hmac_secret.id
  secret_data = google_storage_hmac_key.tempo.secret
}

resource "google_secret_manager_secret_iam_member" "vm_grafana_admin_accessor" {
  project   = google_secret_manager_secret.grafana_admin_password.project
  secret_id = google_secret_manager_secret.grafana_admin_password.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.obs_vm.email}"
}

resource "google_secret_manager_secret_iam_member" "vm_tempo_hmac_access_accessor" {
  project   = google_secret_manager_secret.tempo_hmac_access.project
  secret_id = google_secret_manager_secret.tempo_hmac_access.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.obs_vm.email}"
}

resource "google_secret_manager_secret_iam_member" "vm_tempo_hmac_secret_accessor" {
  project   = google_secret_manager_secret.tempo_hmac_secret.project
  secret_id = google_secret_manager_secret.tempo_hmac_secret.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.obs_vm.email}"
}
