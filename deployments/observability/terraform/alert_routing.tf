resource "google_logging_metric" "grafana_alert_firing" {
  project = data.google_project.current.project_id
  name    = "${local.name_prefix}/grafana_alert_firing"

  description = "Counts firing Grafana alerts fanned out by the alert-router Cloud Run service."

  filter = <<-FILTER
    resource.type="cloud_run_revision"
    resource.labels.service_name="${google_cloud_run_v2_service.alert_router.name}"
    jsonPayload.message="grafana_alert"
    jsonPayload.status="firing"
  FILTER

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"

    labels {
      key         = "alertname"
      value_type  = "STRING"
      description = "Grafana alert rule name."
    }
  }

  label_extractors = {
    alertname = "EXTRACT(jsonPayload.alertname)"
  }
}

resource "google_monitoring_notification_channel" "alert_email" {
  project      = data.google_project.current.project_id
  display_name = "${local.name_prefix} alert email"
  type         = "email"

  labels = {
    email_address = var.alert_email
  }

  user_labels = local.common_labels
}

resource "google_monitoring_alert_policy" "grafana_alert_firing" {
  project      = data.google_project.current.project_id
  display_name = "Grafana alert firing (via alert-router)"
  combiner     = "OR"

  conditions {
    display_name = "Grafana alert firing"

    condition_threshold {
      filter          = "metric.type=\"logging.googleapis.com/user/${google_logging_metric.grafana_alert_firing.name}\" resource.type=\"cloud_run_revision\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      duration        = "0s"

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_DELTA"
        cross_series_reducer = "REDUCE_SUM"
        group_by_fields      = ["metric.label.alertname"]
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.alert_email.id]

  alert_strategy {
    auto_close = "1800s"
  }

  documentation {
    content   = <<-DOC
      A Grafana managed alert has fired and been delivered to the alert-router.

      Runbook: docs/runbooks/observability-alerts.md

      Investigate in Grafana (Alerting > Alert rules) and follow the alert-specific
      playbook in the runbook.
    DOC
    mime_type = "text/markdown"
  }

  user_labels = local.common_labels
}
