locals {
  platform_schedules = {
    maintenance = {
      name             = "${local.foundation_name_prefix}-maintenance-staging-schedule"
      description      = "Conservative daily hosted maintenance cadence for staging."
      schedule         = "17 3 * * *"
      paused           = false
      attempt_deadline = "180s"
      retry_count      = 0
    }
    pipeline = {
      name             = "${local.foundation_name_prefix}-pipeline-staging-schedule"
      description      = "Optional weekly hosted candidate-generation cadence for staging. Paused by default."
      schedule         = "17 4 * * 1"
      paused           = true
      attempt_deadline = "180s"
      retry_count      = 0
    }
  }
}

resource "google_project_iam_member" "ci_cloud_scheduler_admin" {
  project = data.google_project.current.project_id
  role    = "roles/cloudscheduler.admin"
  member  = "serviceAccount:${google_service_account.ci.email}"
}

resource "google_service_account_iam_member" "ci_scheduler_service_account_user" {
  service_account_id = google_service_account.scheduler.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.ci.email}"
}

resource "google_cloud_scheduler_job" "platform" {
  for_each = local.platform_jobs_enabled ? local.platform_schedules : {}

  project          = data.google_project.current.project_id
  region           = var.region
  name             = each.value.name
  description      = each.value.description
  schedule         = each.value.schedule
  time_zone        = "UTC"
  paused           = each.value.paused
  attempt_deadline = each.value.attempt_deadline

  retry_config {
    retry_count = each.value.retry_count
  }

  http_target {
    http_method = "POST"
    uri = format(
      "https://%s-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/%s/jobs/%s:run",
      google_cloud_run_v2_job.platform[each.key].location,
      data.google_project.current.number,
      google_cloud_run_v2_job.platform[each.key].name,
    )

    headers = {
      "Content-Type" = "application/json"
    }

    body = base64encode(jsonencode({}))

    oauth_token {
      service_account_email = google_service_account.scheduler.email
      scope                 = "https://www.googleapis.com/auth/cloud-platform"
    }
  }

  depends_on = [
    google_project_service.required["cloudscheduler.googleapis.com"],
    google_cloud_run_v2_job.platform,
    google_project_iam_member.ci_cloud_scheduler_admin,
    google_service_account_iam_member.ci_scheduler_service_account_user,
  ]
}

resource "google_cloud_run_v2_job_iam_member" "platform_scheduler_invoker" {
  for_each = google_cloud_scheduler_job.platform

  project  = google_cloud_run_v2_job.platform[each.key].project
  location = google_cloud_run_v2_job.platform[each.key].location
  name     = google_cloud_run_v2_job.platform[each.key].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler.email}"
}
