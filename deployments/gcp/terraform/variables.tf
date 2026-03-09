variable "project_id" {
  description = "Existing GCP project ID to adopt as the bootstrap target."
  type        = string
  default     = "fpl-project-jelle"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "project_id must be a valid GCP project ID."
  }
}

variable "region" {
  description = "Default region for future regional GCP resources."
  type        = string
  default     = "europe-west1"

  validation {
    condition     = length(trimspace(var.region)) > 0
    error_message = "region must not be empty."
  }
}

variable "required_services" {
  description = "Project services enabled and maintained by this bootstrap root."
  type        = list(string)
  default = [
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
  ]

  validation {
    condition     = length(var.required_services) == length(distinct(var.required_services))
    error_message = "required_services must not contain duplicates."
  }

  validation {
    condition     = !contains(var.required_services, "serviceusage.googleapis.com")
    error_message = "required_services must not include serviceusage.googleapis.com; it is managed separately."
  }
}
