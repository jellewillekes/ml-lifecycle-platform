locals {
  config_bucket_name = "${var.project_id}-${var.config_bucket_suffix}"

  static_config_files = {
    "docker-compose.yml"                                = "${path.module}/../docker-compose.yml"
    "otel-collector.yaml"                               = "${path.module}/../otel-collector.yaml"
    "prometheus.yml"                                    = "${path.module}/../prometheus.yml"
    "tempo.yaml"                                        = "${path.module}/../tempo.yaml"
    "blackbox.yml"                                      = "${path.module}/../blackbox.yml"
    "grafana/provisioning/datasources/datasources.yaml" = "${path.module}/../grafana/provisioning/datasources/datasources.yaml"
    "grafana/provisioning/dashboards/dashboards.yaml"   = "${path.module}/../grafana/provisioning/dashboards/dashboards.yaml"
  }

  dashboard_files = {
    for f in fileset("${path.module}/../grafana/dashboards", "*.json") :
    "grafana/dashboards/${f}" => "${path.module}/../grafana/dashboards/${f}"
  }

  alerting_files = {
    for f in fileset("${path.module}/../grafana/provisioning/alerting", "*.yaml") :
    "grafana/provisioning/alerting/${f}" => "${path.module}/../grafana/provisioning/alerting/${f}"
  }

  prometheus_rule_files = {
    for f in fileset("${path.module}/../prometheus/rules", "*.yaml") :
    "prometheus/rules/${f}" => "${path.module}/../prometheus/rules/${f}"
  }

  config_files = merge(
    local.static_config_files,
    local.dashboard_files,
    local.alerting_files,
    local.prometheus_rule_files,
  )

  blackbox_targets = [
    for url in [var.serving_probe_url, var.mlflow_probe_url] : url if url != ""
  ]
}

resource "google_storage_bucket" "config" {
  project                     = data.google_project.current.project_id
  name                        = local.config_bucket_name
  location                    = upper(var.region)
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true

  labels = merge(local.common_labels, { purpose = "obs_config" })

  versioning {
    enabled = true
  }
}

resource "google_storage_bucket_iam_member" "vm_config_reader" {
  bucket = google_storage_bucket.config.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.obs_vm.email}"
}

resource "google_storage_bucket_object" "config" {
  for_each = local.config_files

  bucket = google_storage_bucket.config.name
  name   = each.key
  source = each.value
}

resource "google_storage_bucket_object" "blackbox_targets" {
  bucket       = google_storage_bucket.config.name
  name         = "blackbox-targets.json"
  content_type = "application/json"
  content = jsonencode([
    {
      targets = local.blackbox_targets
      labels  = { job = "blackbox" }
    }
  ])
}
