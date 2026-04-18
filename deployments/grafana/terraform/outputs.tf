output "prometheus_datasource_uid" {
  description = "Grafana UID of the hosted Prometheus datasource; referenced by UP-24 dashboard JSON."
  value       = grafana_data_source.prometheus.uid
}

output "tempo_datasource_uid" {
  description = "Grafana UID of the hosted Tempo datasource; referenced by UP-24 dashboard JSON."
  value       = grafana_data_source.tempo.uid
}

output "default_contact_point_name" {
  description = "Name of the default email contact point; referenced by UP-25 alert policies."
  value       = grafana_contact_point.default_email.name
}
