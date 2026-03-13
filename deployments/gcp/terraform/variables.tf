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
    "artifactregistry.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "compute.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "servicenetworking.googleapis.com",
    "sqladmin.googleapis.com",
    "storage.googleapis.com",
    "sts.googleapis.com",
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

variable "github_repository_owner" {
  description = "GitHub repository owner allowed to federate into the CI service account."
  type        = string
  default     = "jellewillekes"

  validation {
    condition     = length(trimspace(var.github_repository_owner)) > 0
    error_message = "github_repository_owner must not be empty."
  }
}

variable "github_repository" {
  description = "GitHub repository name allowed to federate into the CI service account."
  type        = string
  default     = "ml-lifecycle-platform"

  validation {
    condition     = length(trimspace(var.github_repository)) > 0
    error_message = "github_repository must not be empty."
  }
}

variable "github_repository_owner_id" {
  description = "Stable GitHub owner ID used in the WIF provider condition."
  type        = string
  default     = "94389770"

  validation {
    condition     = can(regex("^[0-9]+$", var.github_repository_owner_id))
    error_message = "github_repository_owner_id must contain only digits."
  }
}

variable "github_repository_id" {
  description = "Stable GitHub repository ID used in the WIF provider condition."
  type        = string
  default     = "1141930340"

  validation {
    condition     = can(regex("^[0-9]+$", var.github_repository_id))
    error_message = "github_repository_id must contain only digits."
  }
}

variable "mlflow_image" {
  description = "Hosted MLflow container image ref. Leave empty to bootstrap IAM and APIs before the first deploy workflow run."
  type        = string
  default     = ""
}

variable "serving_image" {
  description = "Hosted serving container image ref. Leave empty until the first serving deploy workflow run."
  type        = string
  default     = ""
}

variable "platform_image" {
  description = "Hosted platform jobs container image ref. Leave empty until the first platform-jobs deploy workflow run."
  type        = string
  default     = ""
}
