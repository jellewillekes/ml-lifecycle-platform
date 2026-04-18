resource "grafana_contact_point" "default_email" {
  name = "mlp-staging-default-email"

  email {
    addresses = [var.notification_email]
  }
}
