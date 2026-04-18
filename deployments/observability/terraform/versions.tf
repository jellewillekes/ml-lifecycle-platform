terraform {
  required_version = "~> 1.5.7"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "= 7.22.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "= 3.7.2"
    }
  }

  backend "gcs" {}
}
