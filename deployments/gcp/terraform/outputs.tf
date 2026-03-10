output "project_number" {
  description = "Numeric project identifier for the adopted GCP project."
  value       = data.google_project.current.number
}

output "project_id" {
  description = "GCP project targeted by this Terraform root."
  value       = data.google_project.current.project_id
}

output "required_services" {
  description = "Services that this Terraform root keeps enabled."
  value       = sort(tolist(local.managed_services))
}

output "artifact_registry_repository_id" {
  description = "Artifact Registry repository ID for platform images."
  value       = google_artifact_registry_repository.images.repository_id
}

output "artifact_registry_repository_name" {
  description = "Fully qualified Artifact Registry repository resource name."
  value       = google_artifact_registry_repository.images.id
}

output "artifact_registry_docker_repository" {
  description = "Docker push target prefix for platform images."
  value = format(
    "%s-docker.pkg.dev/%s/%s",
    google_artifact_registry_repository.images.location,
    data.google_project.current.project_id,
    google_artifact_registry_repository.images.repository_id,
  )
}

output "foundation_bucket_names" {
  description = "Named GCS buckets for hosted artifacts and data."
  value = {
    for key, bucket in google_storage_bucket.foundation : key => bucket.name
  }
}

output "foundation_bucket_urls" {
  description = "Named GCS bucket URLs for hosted artifacts and data."
  value = {
    for key, bucket in google_storage_bucket.foundation : key => bucket.url
  }
}

output "foundation_secret_ids" {
  description = "Secret Manager secret IDs reserved for hosted runtime configuration."
  value = {
    for key, secret in google_secret_manager_secret.foundation : key => secret.secret_id
  }
}

output "foundation_service_accounts" {
  description = "Service account emails for CI and hosted runtime identities."
  value = {
    ci      = google_service_account.ci.email
    runtime = google_service_account.runtime.email
  }
}

output "ci_service_account_email" {
  description = "CI service account email for GitHub Actions federation."
  value       = google_service_account.ci.email
}

output "runtime_service_account_email" {
  description = "Runtime service account email for hosted workloads."
  value       = google_service_account.runtime.email
}

output "github_repository_binding" {
  description = "GitHub repository allowed to federate into the CI service account."
  value       = local.github_repository_full_name
}

output "workload_identity_pool_name" {
  description = "Full workload identity pool resource name."
  value       = google_iam_workload_identity_pool.github.name
}

output "workload_identity_provider_name" {
  description = "Full workload identity provider name for GitHub Actions auth."
  value       = google_iam_workload_identity_pool_provider.github.name
}
