locals {
  bootstrap_service = "serviceusage.googleapis.com"
  required_services = setsubtract(toset(var.required_services), toset([local.bootstrap_service]))
  managed_services  = setunion(toset([local.bootstrap_service]), local.required_services)
}

data "google_project" "current" {
  project_id = var.project_id
}

resource "google_project_service" "serviceusage" {
  project = data.google_project.current.project_id
  service = local.bootstrap_service

  disable_dependent_services = false
  disable_on_destroy         = false
}

resource "google_project_service" "required" {
  for_each = local.required_services

  project = data.google_project.current.project_id
  service = each.value

  disable_dependent_services = false
  disable_on_destroy         = false

  depends_on = [google_project_service.serviceusage]
}
