resource "google_compute_firewall" "allow_otlp_from_subnet" {
  project = data.google_project.current.project_id
  name    = "${local.name_prefix}-allow-otlp"
  network = data.google_compute_network.staging.name

  direction = "INGRESS"
  priority  = 1000

  source_ranges = [data.google_compute_subnetwork.staging.ip_cidr_range]
  target_tags   = [local.name_prefix]

  allow {
    protocol = "tcp"
    ports    = ["4317"]
  }
}

resource "google_compute_firewall" "allow_grafana_from_operator" {
  project = data.google_project.current.project_id
  name    = "${local.name_prefix}-allow-grafana"
  network = data.google_compute_network.staging.name

  direction = "INGRESS"
  priority  = 1000

  source_ranges = [var.grafana_admin_cidr]
  target_tags   = [local.name_prefix]

  allow {
    protocol = "tcp"
    ports    = ["3000"]
  }
}

resource "google_compute_firewall" "allow_iap_ssh" {
  project = data.google_project.current.project_id
  name    = "${local.name_prefix}-allow-iap-ssh"
  network = data.google_compute_network.staging.name

  direction = "INGRESS"
  priority  = 1000

  source_ranges = ["35.235.240.0/20"]
  target_tags   = [local.name_prefix]

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}
