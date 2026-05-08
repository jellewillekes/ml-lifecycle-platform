locals {
  serving_service_name   = "${local.foundation_name_prefix}-serving-staging"
  serving_deploy_enabled = length(trimspace(var.serving_image)) > 0
  otlp_enabled           = length(trimspace(var.otlp_collector_endpoint)) > 0
}

resource "google_cloud_run_v2_service" "serving" {
  for_each = local.serving_deploy_enabled ? { staging = var.serving_image } : {}

  project             = data.google_project.current.project_id
  name                = local.serving_service_name
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = true

  labels = merge(local.common_labels, { purpose = "serving_staging" })

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
        container_port = 8000
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
      }

      env {
        name  = "MLP_ENV"
        value = "staging"
      }

      env {
        name  = "MLFLOW_TRACKING_URI"
        value = google_cloud_run_v2_service.mlflow["staging"].uri
      }

      env {
        name  = "MLFLOW_REGISTRY_URI"
        value = google_cloud_run_v2_service.mlflow["staging"].uri
      }

      env {
        name  = "MLFLOW_CLOUD_RUN_AUDIENCE"
        value = google_cloud_run_v2_service.mlflow["staging"].uri
      }

      env {
        name  = "MODEL_NAME"
        value = "breast_cancer_clf"
      }

      env {
        name  = "MLP_MODEL_SPEC_PATH"
        value = "configs/models/breast_cancer_demo.yaml"
      }

      env {
        name  = "PROD_ALIAS"
        value = "prod"
      }

      env {
        name  = "CANDIDATE_ALIAS"
        value = "candidate"
      }

      env {
        name  = "CANARY_PCT"
        value = "10"
      }

      env {
        name  = "MODEL_CACHE_TTL_SEC"
        value = "60"
      }

      env {
        name  = "LOG_LEVEL"
        value = "INFO"
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = data.google_project.current.project_id
      }

      dynamic "env" {
        for_each = local.otlp_enabled ? [1] : []
        content {
          name  = "OTEL_EXPORTER_OTLP_ENDPOINT"
          value = "http://${var.otlp_collector_endpoint}"
        }
      }

      dynamic "env" {
        for_each = local.otlp_enabled ? [1] : []
        content {
          name  = "OTEL_EXPORTER_OTLP_PROTOCOL"
          value = "grpc"
        }
      }

      dynamic "env" {
        for_each = local.otlp_enabled ? [1] : []
        content {
          name  = "OTEL_EXPORTER_OTLP_INSECURE"
          value = "true"
        }
      }

      startup_probe {
        failure_threshold = 30
        period_seconds    = 10
        timeout_seconds   = 5

        http_get {
          path = "/livez"
          port = 8000
        }
      }

      liveness_probe {
        failure_threshold = 3
        period_seconds    = 30
        timeout_seconds   = 5

        http_get {
          path = "/livez"
          port = 8000
        }
      }
    }
  }

  depends_on = [
    google_project_service.required["run.googleapis.com"],
    google_cloud_run_v2_service.mlflow,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "serving_ci_invoker" {
  for_each = google_cloud_run_v2_service.serving

  project  = each.value.project
  location = each.value.location
  name     = each.value.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.ci_staging.email}"
}

resource "google_cloud_run_v2_service_iam_member" "mlflow_runtime_invoker" {
  for_each = google_cloud_run_v2_service.mlflow

  project  = each.value.project
  location = each.value.location
  name     = each.value.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.runtime.email}"
}
