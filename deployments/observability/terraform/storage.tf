resource "google_storage_bucket" "tempo" {
  project                     = data.google_project.current.project_id
  name                        = "${var.project_id}-mlp-tempo"
  location                    = upper(var.region)
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = !var.enable_deletion_protection

  labels = merge(local.common_labels, { purpose = "tempo_blocks" })

  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
    condition {
      age = var.tempo_bucket_retention_days
    }
  }
}

resource "google_service_account" "obs_vm" {
  project      = data.google_project.current.project_id
  account_id   = "${local.name_prefix}-vm"
  display_name = "ML lifecycle platform observability VM"
  description  = "Runtime identity for the self-hosted Grafana/Prometheus/Tempo VM."
}

resource "google_storage_bucket_iam_member" "vm_tempo_writer" {
  bucket = google_storage_bucket.tempo.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.obs_vm.email}"
}

resource "google_storage_hmac_key" "tempo" {
  project               = data.google_project.current.project_id
  service_account_email = google_service_account.obs_vm.email
}
