locals {
  platform_jobs_enabled = length(trimspace(var.platform_image)) > 0

  # Model identity is injected per job via env vars (MLP_ENV plus the
  # MODEL_NAME / MLP_MODEL_SPEC_PATH / EXPERIMENT_NAME runtime overrides), so a
  # single platform image can drive several model pipelines. The breast-cancer
  # demo is the default identity; the binance pipeline overrides it.
  staging_demo_model_env = {
    MLP_ENV             = "staging"
    MODEL_NAME          = "breast_cancer_clf"
    MLP_MODEL_SPEC_PATH = "configs/models/breast_cancer_demo.yaml"
  }

  platform_jobs = {
    pipeline = {
      name                 = "${local.foundation_name_prefix}-pipeline-staging"
      command              = ["python"]
      args                 = ["-m", "ml_lifecycle_platform.pipeline.orchestrate"]
      timeout              = "1800s"
      mutates_model_state  = true
      safe_validation_args = []
      model_env            = local.staging_demo_model_env
    }
    pipeline_binance = {
      name                 = "${local.foundation_name_prefix}-pipeline-binance-staging"
      command              = ["python"]
      args                 = ["-m", "ml_lifecycle_platform.pipeline.orchestrate"]
      timeout              = "1800s"
      mutates_model_state  = true
      safe_validation_args = []
      model_env = {
        MLP_ENV             = "staging"
        EXPERIMENT_NAME     = "binance-btc-1m"
        MODEL_NAME          = "binance_btc_1m"
        MLP_MODEL_SPEC_PATH = "configs/models/binance_btc_1m.yaml"
      }
    }
    promote = {
      name                 = "${local.foundation_name_prefix}-promote-staging"
      command              = ["python"]
      args                 = ["-m", "ml_lifecycle_platform.registry.promote", "--model-name", "breast_cancer_clf", "--format", "json"]
      timeout              = "900s"
      mutates_model_state  = true
      safe_validation_args = ["--model-name", "breast_cancer_clf", "--dry-run", "--format", "json"]
      model_env            = local.staging_demo_model_env
    }
    rollback = {
      name                 = "${local.foundation_name_prefix}-rollback-staging"
      command              = ["python"]
      args                 = ["-m", "ml_lifecycle_platform.registry.rollback", "--model-name", "breast_cancer_clf"]
      timeout              = "900s"
      mutates_model_state  = true
      safe_validation_args = ["--model-name", "breast_cancer_clf", "--dry-run", "--format", "json"]
      model_env            = local.staging_demo_model_env
    }
    reproduce = {
      name                 = "${local.foundation_name_prefix}-reproduce-staging"
      command              = ["python"]
      args                 = ["-m", "ml_lifecycle_platform.registry.reproduce", "--model-name", "breast_cancer_clf", "--alias", "prod", "--format", "json"]
      timeout              = "1800s"
      mutates_model_state  = false
      safe_validation_args = []
      model_env            = local.staging_demo_model_env
    }
    maintenance = {
      name                 = "${local.foundation_name_prefix}-maintenance-staging"
      command              = ["python"]
      args                 = ["-m", "ml_lifecycle_platform.jobs.maintenance", "--format", "json"]
      timeout              = "600s"
      mutates_model_state  = false
      safe_validation_args = []
      model_env            = local.staging_demo_model_env
    }
  }
}

resource "google_cloud_run_v2_job" "platform" {
  for_each = local.platform_jobs_enabled ? local.platform_jobs : {}

  project  = data.google_project.current.project_id
  name     = each.value.name
  location = var.region

  labels = merge(
    local.common_labels,
    {
      purpose = "platform_job"
      job     = each.key
    },
  )

  template {
    parallelism = 1
    task_count  = 1

    template {
      service_account = google_service_account.runtime.email
      timeout         = each.value.timeout
      max_retries     = 0

      vpc_access {
        egress = "PRIVATE_RANGES_ONLY"

        network_interfaces {
          network    = google_compute_network.staging.id
          subnetwork = google_compute_subnetwork.staging.id
        }
      }

      containers {
        image   = var.platform_image
        command = each.value.command
        args    = each.value.args

        resources {
          limits = {
            cpu    = "1"
            memory = "1Gi"
          }
        }

        dynamic "env" {
          for_each = each.value.model_env
          content {
            name  = env.key
            value = env.value
          }
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
      }
    }
  }

  depends_on = [
    google_project_service.required["run.googleapis.com"],
    google_cloud_run_v2_service.mlflow,
  ]
}

resource "google_cloud_run_v2_job_iam_member" "platform_ci_invoker" {
  for_each = google_cloud_run_v2_job.platform

  project  = each.value.project
  location = each.value.location
  name     = each.value.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.ci_staging.email}"
}

locals {
  platform_production_jobs_enabled = length(trimspace(var.production_platform_image)) > 0 && var.manage_production_foundation

  platform_jobs_production = {
    pipeline = {
      name                 = "${local.foundation_name_prefix}-pipeline-production"
      command              = ["python"]
      args                 = ["-m", "ml_lifecycle_platform.pipeline.orchestrate"]
      timeout              = "1800s"
      mutates_model_state  = true
      safe_validation_args = []
    }
    promote = {
      name                 = "${local.foundation_name_prefix}-promote-production"
      command              = ["python"]
      args                 = ["-m", "ml_lifecycle_platform.registry.promote", "--model-name", "breast_cancer_clf", "--format", "json"]
      timeout              = "900s"
      mutates_model_state  = true
      safe_validation_args = ["--model-name", "breast_cancer_clf", "--dry-run", "--format", "json"]
    }
    rollback = {
      name                 = "${local.foundation_name_prefix}-rollback-production"
      command              = ["python"]
      args                 = ["-m", "ml_lifecycle_platform.registry.rollback", "--model-name", "breast_cancer_clf"]
      timeout              = "900s"
      mutates_model_state  = true
      safe_validation_args = ["--model-name", "breast_cancer_clf", "--dry-run", "--format", "json"]
    }
    reproduce = {
      name                 = "${local.foundation_name_prefix}-reproduce-production"
      command              = ["python"]
      args                 = ["-m", "ml_lifecycle_platform.registry.reproduce", "--model-name", "breast_cancer_clf", "--alias", "prod", "--format", "json"]
      timeout              = "1800s"
      mutates_model_state  = false
      safe_validation_args = []
    }
    maintenance = {
      name                 = "${local.foundation_name_prefix}-maintenance-production"
      command              = ["python"]
      args                 = ["-m", "ml_lifecycle_platform.jobs.maintenance", "--format", "json"]
      timeout              = "600s"
      mutates_model_state  = false
      safe_validation_args = []
    }
  }
}

resource "google_cloud_run_v2_job" "platform_production" {
  for_each = local.platform_production_jobs_enabled ? local.platform_jobs_production : {}

  project  = data.google_project.current.project_id
  name     = each.value.name
  location = var.region

  labels = merge(
    local.common_labels,
    {
      purpose = "platform_job"
      job     = each.key
    },
  )

  template {
    parallelism = 1
    task_count  = 1

    template {
      service_account = google_service_account.runtime.email
      timeout         = each.value.timeout
      max_retries     = 0

      vpc_access {
        egress = "PRIVATE_RANGES_ONLY"

        network_interfaces {
          network    = google_compute_network.production[0].id
          subnetwork = google_compute_subnetwork.production[0].id
        }
      }

      containers {
        image   = var.production_platform_image
        command = each.value.command
        args    = each.value.args

        resources {
          limits = {
            cpu    = "1"
            memory = "1Gi"
          }
        }

        env {
          name  = "MLP_ENV"
          value = "production"
        }

        env {
          name  = "MLFLOW_TRACKING_URI"
          value = google_cloud_run_v2_service.mlflow["production"].uri
        }

        env {
          name  = "MLFLOW_REGISTRY_URI"
          value = google_cloud_run_v2_service.mlflow["production"].uri
        }

        env {
          name  = "MLFLOW_CLOUD_RUN_AUDIENCE"
          value = google_cloud_run_v2_service.mlflow["production"].uri
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
      }
    }
  }

  depends_on = [
    google_project_service.required["run.googleapis.com"],
    google_cloud_run_v2_service.mlflow,
  ]
}

resource "google_cloud_run_v2_job_iam_member" "platform_production_ci_invoker" {
  for_each = google_cloud_run_v2_job.platform_production

  project  = each.value.project
  location = each.value.location
  name     = each.value.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.ci_prod[0].email}"
}
