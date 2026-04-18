output "observability_vm_internal_ip" {
  description = "Static internal IP of the observability VM. Feed this (as <ip>:4317) into the GCP root's otlp_collector_endpoint."
  value       = google_compute_instance.observability.network_interface[0].network_ip
}

output "otlp_collector_endpoint" {
  description = "OTLP/gRPC endpoint for Cloud Run services and jobs."
  value       = "${google_compute_instance.observability.network_interface[0].network_ip}:4317"
}

output "grafana_url" {
  description = "Grafana URL (only reachable from grafana_admin_cidr)."
  value       = "http://${google_compute_instance.observability.network_interface[0].network_ip}:3000"
}

output "tempo_bucket" {
  description = "GCS bucket used as Tempo's S3-compatible backend."
  value       = google_storage_bucket.tempo.name
}

output "config_bucket" {
  description = "GCS bucket holding compose configs; updates land here via terraform apply and are synced to the VM on next boot."
  value       = google_storage_bucket.config.name
}

output "grafana_admin_password_secret" {
  description = "Secret Manager secret ID holding the generated Grafana admin password."
  value       = google_secret_manager_secret.grafana_admin_password.secret_id
}
