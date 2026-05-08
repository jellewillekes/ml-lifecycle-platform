locals {
  foundation_name_prefix = "mlp"
  common_labels = {
    managed_by = "terraform"
    layer      = "foundation"
    platform   = local.foundation_name_prefix
  }

  artifact_registry_repository_id = "${local.foundation_name_prefix}-images"
  bucket_location                 = upper(var.region)
  github_repository_full_name     = "${var.github_repository_owner}/${var.github_repository}"
  workload_identity_pool_id       = "github-actions"
  workload_identity_provider_id   = "github-oidc"

  buckets = {
    artifacts = {
      name = "${var.project_id}-${local.foundation_name_prefix}-artifacts"
    }
    data = {
      name = "${var.project_id}-${local.foundation_name_prefix}-data"
    }
  }

  secret_ids = {
    mlflow_tracking_uri      = "${local.foundation_name_prefix}-mlflow-tracking-uri"
    mlflow_tracking_username = "${local.foundation_name_prefix}-mlflow-tracking-username"
    mlflow_tracking_password = "${local.foundation_name_prefix}-mlflow-tracking-password"
  }
}

resource "google_artifact_registry_repository" "images" {
  project       = data.google_project.current.project_id
  location      = var.region
  repository_id = local.artifact_registry_repository_id
  description   = "Docker images for ML lifecycle platform hosted workloads."
  format        = "DOCKER"

  labels = local.common_labels

  depends_on = [google_project_service.required["artifactregistry.googleapis.com"]]
}

resource "google_storage_bucket" "foundation" {
  for_each = local.buckets

  project                     = data.google_project.current.project_id
  name                        = each.value.name
  location                    = local.bucket_location
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  labels = merge(local.common_labels, { purpose = each.key })

  depends_on = [google_project_service.required["storage.googleapis.com"]]
}

resource "google_secret_manager_secret" "foundation" {
  for_each = local.secret_ids

  project   = data.google_project.current.project_id
  secret_id = each.value

  labels = merge(local.common_labels, { purpose = each.key })

  replication {
    auto {}
  }

  depends_on = [google_project_service.required["secretmanager.googleapis.com"]]
}

resource "google_service_account" "ci_staging" {
  project      = data.google_project.current.project_id
  account_id   = "${local.foundation_name_prefix}-ci-staging"
  display_name = "ML lifecycle platform CI / staging"
  description  = "GitHub Actions identity for staging deploys. Bound to environment:staging OIDC subject."

  depends_on = [google_project_service.required["iam.googleapis.com"]]
}

resource "google_service_account" "ci_prod" {
  project      = data.google_project.current.project_id
  account_id   = "${local.foundation_name_prefix}-ci-prod"
  display_name = "ML lifecycle platform CI / production"
  description  = "Reserved production CI identity. No WIF binding until UP-47."

  depends_on = [google_project_service.required["iam.googleapis.com"]]
}

resource "google_service_account" "runtime" {
  project      = data.google_project.current.project_id
  account_id   = "${local.foundation_name_prefix}-runtime"
  display_name = "ML lifecycle platform runtime"
  description  = "Hosted workload identity for serving and job runtimes."

  depends_on = [google_project_service.required["iam.googleapis.com"]]
}

resource "google_artifact_registry_repository_iam_member" "ci_staging_writer" {
  project    = google_artifact_registry_repository.images.project
  location   = google_artifact_registry_repository.images.location
  repository = google_artifact_registry_repository.images.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.ci_staging.email}"
}

resource "google_project_iam_member" "ci_staging_viewer" {
  project = data.google_project.current.project_id
  role    = "roles/viewer"
  member  = "serviceAccount:${google_service_account.ci_staging.email}"
}

resource "google_storage_bucket_iam_member" "runtime_bucket_admin" {
  for_each = google_storage_bucket.foundation

  bucket = each.value.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_secret_manager_secret_iam_member" "runtime_secret_accessor" {
  for_each = google_secret_manager_secret.foundation

  project   = each.value.project
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_iam_workload_identity_pool" "github" {
  project                   = data.google_project.current.project_id
  workload_identity_pool_id = local.workload_identity_pool_id
  display_name              = "GitHub Actions"
  description               = "Federated identities for GitHub Actions workflows."

  depends_on = [
    google_project_service.required["iam.googleapis.com"],
    google_project_service.required["iamcredentials.googleapis.com"],
    google_project_service.required["sts.googleapis.com"],
  ]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  project                            = data.google_project.current.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = local.workload_identity_provider_id
  display_name                       = "GitHub OIDC"
  description                        = "OIDC provider for GitHub Actions."

  attribute_condition = join(" && ", [
    "assertion.repository_owner_id == '${var.github_repository_owner_id}'",
    "assertion.repository_id == '${var.github_repository_id}'",
  ])

  attribute_mapping = {
    "google.subject"                = "assertion.sub"
    "attribute.actor"               = "assertion.actor"
    "attribute.aud"                 = "assertion.aud"
    "attribute.environment"         = "assertion.environment"
    "attribute.ref"                 = "assertion.ref"
    "attribute.ref_type"            = "assertion.ref_type"
    "attribute.repository"          = "assertion.repository"
    "attribute.repository_id"       = "assertion.repository_id"
    "attribute.repository_owner"    = "assertion.repository_owner"
    "attribute.repository_owner_id" = "assertion.repository_owner_id"
  }

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }

  depends_on = [
    google_project_service.required["iam.googleapis.com"],
    google_project_service.required["iamcredentials.googleapis.com"],
    google_project_service.required["sts.googleapis.com"],
  ]
}

resource "google_service_account_iam_member" "ci_staging_workload_identity_user" {
  service_account_id = google_service_account.ci_staging.name
  role               = "roles/iam.workloadIdentityUser"
  member = format(
    "principalSet://iam.googleapis.com/%s/attribute.environment/staging",
    google_iam_workload_identity_pool.github.name,
  )
}
