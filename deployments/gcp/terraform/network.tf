locals {
  staging_network_name                     = "${local.foundation_name_prefix}-staging-vpc"
  staging_subnetwork_name                  = "${local.foundation_name_prefix}-staging-subnet"
  staging_subnetwork_cidr                  = "10.42.0.0/24"
  staging_private_service_range_name       = "${local.foundation_name_prefix}-staging-private-services"
  staging_private_service_range_prefix_len = 16

  production_network_name                     = "${local.foundation_name_prefix}-production-vpc"
  production_subnetwork_name                  = "${local.foundation_name_prefix}-production-subnet"
  production_subnetwork_cidr                  = "10.43.0.0/24"
  production_private_service_range_name       = "${local.foundation_name_prefix}-production-private-services"
  production_private_service_range_prefix_len = 16
}

resource "google_compute_network" "staging" {
  project                 = data.google_project.current.project_id
  name                    = local.staging_network_name
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"

  depends_on = [google_project_service.required["compute.googleapis.com"]]
}

resource "google_compute_subnetwork" "staging" {
  project                  = data.google_project.current.project_id
  name                     = local.staging_subnetwork_name
  region                   = var.region
  network                  = google_compute_network.staging.id
  ip_cidr_range            = local.staging_subnetwork_cidr
  private_ip_google_access = true

  depends_on = [google_project_service.required["compute.googleapis.com"]]
}

resource "google_compute_global_address" "staging_private_services" {
  project       = data.google_project.current.project_id
  name          = local.staging_private_service_range_name
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = local.staging_private_service_range_prefix_len
  network       = google_compute_network.staging.id

  depends_on = [google_project_service.required["compute.googleapis.com"]]
}

resource "google_service_networking_connection" "staging_private_services" {
  network                 = google_compute_network.staging.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.staging_private_services.name]

  depends_on = [
    google_project_service.required["servicenetworking.googleapis.com"],
    google_compute_global_address.staging_private_services,
  ]
}

resource "google_compute_network" "production" {
  count = var.manage_production_foundation ? 1 : 0

  project                 = data.google_project.current.project_id
  name                    = local.production_network_name
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"

  depends_on = [google_project_service.required["compute.googleapis.com"]]
}

resource "google_compute_subnetwork" "production" {
  count = var.manage_production_foundation ? 1 : 0

  project                  = data.google_project.current.project_id
  name                     = local.production_subnetwork_name
  region                   = var.region
  network                  = google_compute_network.production[0].id
  ip_cidr_range            = local.production_subnetwork_cidr
  private_ip_google_access = true

  depends_on = [google_project_service.required["compute.googleapis.com"]]
}

resource "google_compute_global_address" "production_private_services" {
  count = var.manage_production_foundation ? 1 : 0

  project       = data.google_project.current.project_id
  name          = local.production_private_service_range_name
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = local.production_private_service_range_prefix_len
  network       = google_compute_network.production[0].id

  depends_on = [google_project_service.required["compute.googleapis.com"]]
}

resource "google_service_networking_connection" "production_private_services" {
  count = var.manage_production_foundation ? 1 : 0

  network                 = google_compute_network.production[0].id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.production_private_services[0].name]

  depends_on = [
    google_project_service.required["servicenetworking.googleapis.com"],
    google_compute_global_address.production_private_services,
  ]
}
