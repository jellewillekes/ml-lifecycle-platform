variable "project_id" {
  description = "GCP project hosting the staging VPC and observability VM."
  type        = string
  default     = "fpl-project-jelle"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "project_id must be a valid GCP project ID."
  }
}

variable "region" {
  description = "Region for the observability VM and Tempo bucket."
  type        = string
  default     = "europe-west1"
}

variable "zone" {
  description = "Zone for the observability VM."
  type        = string
  default     = "europe-west1-b"
}

variable "staging_network_name" {
  description = "Name of the existing staging VPC (managed by the GCP root)."
  type        = string
  default     = "mlp-staging-vpc"
}

variable "staging_subnetwork_name" {
  description = "Name of the existing staging subnet (managed by the GCP root)."
  type        = string
  default     = "mlp-staging-subnet"
}

variable "vm_machine_type" {
  description = "GCE machine type for the observability VM."
  type        = string
  default     = "e2-medium"
}

variable "vm_static_internal_ip" {
  description = "Reserved internal IP inside the staging subnet for the VM. Must sit in the staging subnet CIDR (10.42.0.0/24)."
  type        = string
  default     = "10.42.0.100"

  validation {
    condition     = can(regex("^10\\.42\\.0\\.[0-9]+$", var.vm_static_internal_ip))
    error_message = "vm_static_internal_ip must be an IPv4 in the staging subnet (10.42.0.0/24)."
  }
}

variable "prometheus_disk_size_gb" {
  description = "Persistent disk size for the Prometheus TSDB. Survives VM recreate."
  type        = number
  default     = 50

  validation {
    condition     = var.prometheus_disk_size_gb >= 20
    error_message = "prometheus_disk_size_gb must be at least 20."
  }
}

variable "grafana_admin_cidr" {
  description = "CIDR allowed to reach Grafana UI on :3000. Default is deny-all; override with an operator IP like 203.0.113.7/32."
  type        = string
  default     = "127.0.0.1/32"
}

variable "tempo_bucket_retention_days" {
  description = "Object lifecycle age after which trace blocks transition to NEARLINE."
  type        = number
  default     = 30
}

variable "config_bucket_suffix" {
  description = "Suffix for the GCS bucket holding compose configs synced to the VM."
  type        = string
  default     = "mlp-obs-config"
}

variable "serving_probe_url" {
  description = "Full URL for the serving /health endpoint probed by blackbox_exporter. Empty disables the probe."
  type        = string
  default     = ""
}

variable "mlflow_probe_url" {
  description = "Full URL for the MLflow /health endpoint probed by blackbox_exporter. Empty disables the probe."
  type        = string
  default     = ""
}
