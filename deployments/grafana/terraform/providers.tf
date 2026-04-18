provider "grafana" {
  url  = var.grafana_stack_url
  auth = var.grafana_service_account_token
}
