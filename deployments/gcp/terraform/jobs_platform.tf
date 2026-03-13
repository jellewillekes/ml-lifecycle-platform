locals {
  platform_jobs_enabled = length(trimspace(var.platform_image)) > 0
  platform_jobs = {
    pipeline = {
      name                 = "${local.foundation_name_prefix}-pipeline-staging"
      command              = ["python"]
      args                 = ["-m", "ml_lifecycle_platform.pipeline.orchestrate"]
      timeout              = "1800s"
      mutates_model_state  = true
      safe_validation_args = []
    }
    promote = {
      name                 = "${local.foundation_name_prefix}-promote-staging"
      command              = ["python"]
      args                 = ["-m", "ml_lifecycle_platform.registry.promote", "--model-name", "breast_cancer_clf", "--format", "json"]
      timeout              = "900s"
      mutates_model_state  = true
      safe_validation_args = ["--model-name", "breast_cancer_clf", "--dry-run", "--format", "json"]
    }
    rollback = {
      name                 = "${local.foundation_name_prefix}-rollback-staging"
      command              = ["python"]
      args                 = ["-m", "ml_lifecycle_platform.registry.rollback", "--model-name", "breast_cancer_clf"]
      timeout              = "900s"
      mutates_model_state  = true
      safe_validation_args = ["--model-name", "breast_cancer_clf", "--dry-run", "--format", "json"]
    }
    reproduce = {
      name                 = "${local.foundation_name_prefix}-reproduce-staging"
      command              = ["python"]
      args                 = ["-m", "ml_lifecycle_platform.registry.reproduce", "--model-name", "breast_cancer_clf", "--alias", "prod", "--format", "json"]
      timeout              = "1800s"
      mutates_model_state  = false
      safe_validation_args = []
    }
    maintenance = {
      name                 = "${local.foundation_name_prefix}-maintenance-staging"
      command              = ["python"]
      args                 = ["-m", "ml_lifecycle_platform.jobs.maintenance", "--format", "json"]
      timeout              = "600s"
      mutates_model_state  = false
      safe_validation_args = []
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
          name  = "LOG_LEVEL"
          value = "INFO"
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
  member   = "serviceAccount:${google_service_account.ci.email}"
}
