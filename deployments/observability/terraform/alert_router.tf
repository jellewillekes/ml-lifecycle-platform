resource "random_password" "alert_router_token" {
  length  = 48
  special = false
}

resource "google_secret_manager_secret" "alert_router_token" {
  project   = data.google_project.current.project_id
  secret_id = "${local.name_prefix}-alert-router-token"

  labels = merge(local.common_labels, { purpose = "alert_router_token" })

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "alert_router_token" {
  secret      = google_secret_manager_secret.alert_router_token.id
  secret_data = random_password.alert_router_token.result
}

resource "google_service_account" "alert_router" {
  project      = data.google_project.current.project_id
  account_id   = "${local.name_prefix}-alert-router"
  display_name = "ML lifecycle platform alert router"
  description  = "Runtime identity for the Grafana webhook receiver on Cloud Run."
}

resource "google_secret_manager_secret_iam_member" "alert_router_token_accessor" {
  project   = google_secret_manager_secret.alert_router_token.project
  secret_id = google_secret_manager_secret.alert_router_token.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.alert_router.email}"
}

resource "google_secret_manager_secret_iam_member" "vm_alert_router_token_accessor" {
  project   = google_secret_manager_secret.alert_router_token.project
  secret_id = google_secret_manager_secret.alert_router_token.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.obs_vm.email}"
}

resource "google_cloud_run_v2_service" "alert_router" {
  project             = data.google_project.current.project_id
  name                = "${local.name_prefix}-alert-router"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  labels = merge(local.common_labels, { purpose = "alert_router" })

  template {
    service_account = google_service_account.alert_router.email

    scaling {
      max_instance_count = 2
    }

    containers {
      image = var.alert_router_image

      ports {
        container_port = 8080
      }

      env {
        name = "ALERT_ROUTER_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.alert_router_token.secret_id
            version = "latest"
          }
        }
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "256Mi"
        }
        cpu_idle          = true
        startup_cpu_boost = false
      }
    }
  }

  depends_on = [
    google_secret_manager_secret_iam_member.alert_router_token_accessor,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "alert_router_public_invoker" {
  project  = google_cloud_run_v2_service.alert_router.project
  location = google_cloud_run_v2_service.alert_router.location
  name     = google_cloud_run_v2_service.alert_router.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
