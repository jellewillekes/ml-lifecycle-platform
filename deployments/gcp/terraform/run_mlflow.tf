locals {
  mlflow_service_name   = "${local.foundation_name_prefix}-mlflow-staging"
  mlflow_deploy_enabled = length(trimspace(var.mlflow_image)) > 0
}

resource "google_project_iam_member" "ci_run_admin" {
  project = data.google_project.current.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.ci_staging.email}"
}

resource "google_project_iam_member" "ci_service_usage_admin" {
  project = data.google_project.current.project_id
  role    = "roles/serviceusage.serviceUsageAdmin"
  member  = "serviceAccount:${google_service_account.ci_staging.email}"
}

resource "google_service_account_iam_member" "ci_runtime_service_account_user" {
  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.ci_staging.email}"
}

resource "google_cloud_run_v2_service" "mlflow" {
  for_each = local.mlflow_deploy_enabled ? { staging = var.mlflow_image } : {}

  project             = data.google_project.current.project_id
  name                = local.mlflow_service_name
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = true

  labels = merge(local.common_labels, { purpose = "mlflow_staging" })

  template {
    service_account                  = google_service_account.runtime.email
    timeout                          = "300s"
    max_instance_request_concurrency = 80

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    vpc_access {
      egress = "PRIVATE_RANGES_ONLY"

      network_interfaces {
        network    = google_compute_network.staging.id
        subnetwork = google_compute_subnetwork.staging.id
      }
    }

    containers {
      image = each.value

      ports {
        container_port = 5000
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
      }

      env {
        name  = "MLFLOW_HOST"
        value = "0.0.0.0"
      }

      env {
        name  = "MLFLOW_PORT"
        value = "5000"
      }

      env {
        name  = "DB_HOST"
        value = google_sql_database_instance.mlflow.private_ip_address
      }

      env {
        name  = "DB_PORT"
        value = "5432"
      }

      env {
        name = "DB_NAME"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.mlflow["db_name"].secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "DB_USER"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.mlflow["db_user"].secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "DB_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.mlflow["db_password"].secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "ARTIFACTS_DESTINATION"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.mlflow["artifact_root"].secret_id
            version = "latest"
          }
        }
      }

      startup_probe {
        failure_threshold = 30
        period_seconds    = 10
        timeout_seconds   = 5

        http_get {
          path = "/"
          port = 5000
        }
      }

      liveness_probe {
        failure_threshold = 3
        period_seconds    = 30
        timeout_seconds   = 5

        http_get {
          path = "/"
          port = 5000
        }
      }
    }
  }

  depends_on = [
    google_project_service.required["run.googleapis.com"],
    google_secret_manager_secret_iam_member.runtime_mlflow_secret_accessor,
    google_project_iam_member.runtime_cloudsql_client,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "mlflow_ci_invoker" {
  for_each = google_cloud_run_v2_service.mlflow

  project  = each.value.project
  location = each.value.location
  name     = each.value.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.ci_staging.email}"
}
