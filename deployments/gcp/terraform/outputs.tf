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
