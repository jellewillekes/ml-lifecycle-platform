variable "grafana_stack_url" {
  description = "Grafana Cloud stack URL, e.g. https://<org>.grafana.net."
  type        = string

  validation {
    condition     = can(regex("^https://", var.grafana_stack_url))
    error_message = "grafana_stack_url must be an https URL."
  }
}

variable "grafana_service_account_token" {
  description = "Stack-scoped Grafana Cloud service account token used by the provider to manage datasources and contact points."
  type        = string
  sensitive   = true

  validation {
    condition     = length(trimspace(var.grafana_service_account_token)) > 0
    error_message = "grafana_service_account_token must not be empty."
  }
}

variable "prometheus_url" {
  description = "Grafana Cloud hosted Prometheus base URL, e.g. https://prometheus-prod-XX-prod-eu-west-0.grafana.net/api/prom."
  type        = string

  validation {
    condition     = can(regex("^https://", var.prometheus_url))
    error_message = "prometheus_url must be an https URL."
  }
}

variable "prometheus_user" {
  description = "Grafana Cloud hosted Prometheus instance ID used as the Basic Auth username."
  type        = string

  validation {
    condition     = length(trimspace(var.prometheus_user)) > 0
    error_message = "prometheus_user must not be empty."
  }
}

variable "prometheus_token" {
  description = "Grafana Cloud hosted Prometheus access token used as the Basic Auth password."
  type        = string
  sensitive   = true

  validation {
    condition     = length(trimspace(var.prometheus_token)) > 0
    error_message = "prometheus_token must not be empty."
  }
}

variable "tempo_url" {
  description = "Grafana Cloud hosted Tempo base URL, e.g. https://tempo-prod-XX-prod-eu-west-0.grafana.net."
  type        = string

  validation {
    condition     = can(regex("^https://", var.tempo_url))
    error_message = "tempo_url must be an https URL."
  }
}

variable "tempo_user" {
  description = "Grafana Cloud hosted Tempo instance ID used as the Basic Auth username."
  type        = string

  validation {
    condition     = length(trimspace(var.tempo_user)) > 0
    error_message = "tempo_user must not be empty."
  }
}

variable "tempo_token" {
  description = "Grafana Cloud hosted Tempo access token used as the Basic Auth password."
  type        = string
  sensitive   = true

  validation {
    condition     = length(trimspace(var.tempo_token)) > 0
    error_message = "tempo_token must not be empty."
  }
}

variable "notification_email" {
  description = "Email address for the default contact point; UP-25 binds alert rules to it."
  type        = string
  default     = "jwillekes18@gmail.com"

  validation {
    condition     = can(regex("^[^@]+@[^@]+\\.[^@]+$", var.notification_email))
    error_message = "notification_email must look like an email address."
  }
}
