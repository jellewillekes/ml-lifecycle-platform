resource "grafana_data_source" "prometheus" {
  type = "prometheus"
  name = "grafana-cloud-prometheus"
  url  = var.prometheus_url

  basic_auth_enabled  = true
  basic_auth_username = var.prometheus_user

  secure_json_data_encoded = jsonencode({
    basicAuthPassword = var.prometheus_token
  })
}

resource "grafana_data_source" "tempo" {
  type = "tempo"
  name = "grafana-cloud-tempo"
  url  = var.tempo_url

  basic_auth_enabled  = true
  basic_auth_username = var.tempo_user

  secure_json_data_encoded = jsonencode({
    basicAuthPassword = var.tempo_token
  })
}
