terraform {
  required_version = "~> 1.5.7"

  required_providers {
    grafana = {
      source  = "grafana/grafana"
      version = "= 3.14.1"
    }
  }

  backend "gcs" {}
}
