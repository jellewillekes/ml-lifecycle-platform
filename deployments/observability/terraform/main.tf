locals {
  name_prefix = "mlp-obs"
  common_labels = {
    managed_by = "terraform"
    layer      = "observability"
    platform   = "mlp"
  }
}

data "google_project" "current" {
  project_id = var.project_id
}

data "google_compute_network" "staging" {
  name = var.staging_network_name
}

data "google_compute_subnetwork" "staging" {
  name   = var.staging_subnetwork_name
  region = var.region
}
