locals {
  mlflow_sql_instance_name = "${local.foundation_name_prefix}-mlflow-staging"
  mlflow_database_name     = "mlflow"
  mlflow_database_user     = "mlflow"
  mlflow_sql_tier          = "db-custom-1-3840"
  mlflow_artifact_root = format(
    "%s/mlflow/",
    google_storage_bucket.foundation["artifacts"].url,
  )
  mlflow_sql_instance_name_production = "${local.foundation_name_prefix}-mlflow-production"
  mlflow_artifact_root_production = format(
    "%s/mlflow-production/",
    google_storage_bucket.foundation["artifacts"].url,
  )
}

resource "random_password" "mlflow_db_password" {
  length           = 32
  special          = false
  min_lower        = 1
  min_numeric      = 1
  min_upper        = 1
  override_special = ""
}

resource "google_sql_database_instance" "mlflow" {
  project             = data.google_project.current.project_id
  name                = local.mlflow_sql_instance_name
  region              = var.region
  database_version    = "POSTGRES_16"
  deletion_protection = true

  settings {
    edition           = "ENTERPRISE"
    tier              = local.mlflow_sql_tier
    availability_type = "ZONAL"
    disk_autoresize   = true
    disk_size         = 20
    disk_type         = "PD_SSD"

    backup_configuration {
      enabled = true
    }

    ip_configuration {
      ipv4_enabled                                  = false
      private_network                               = google_compute_network.staging.id
      enable_private_path_for_google_cloud_services = true
    }
  }

  depends_on = [
    google_project_service.required["sqladmin.googleapis.com"],
    google_service_networking_connection.staging_private_services,
  ]
}

resource "google_sql_database" "mlflow" {
  project  = data.google_project.current.project_id
  name     = local.mlflow_database_name
  instance = google_sql_database_instance.mlflow.name
}

resource "google_sql_user" "mlflow" {
  project  = data.google_project.current.project_id
  name     = local.mlflow_database_user
  instance = google_sql_database_instance.mlflow.name
  password = random_password.mlflow_db_password.result
}

resource "google_project_iam_member" "runtime_cloudsql_client" {
  project = data.google_project.current.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

resource "random_password" "mlflow_db_password_production" {
  length           = 32
  special          = false
  min_lower        = 1
  min_numeric      = 1
  min_upper        = 1
  override_special = ""
}

resource "google_sql_database_instance" "mlflow_production" {
  project             = data.google_project.current.project_id
  name                = local.mlflow_sql_instance_name_production
  region              = var.region
  database_version    = "POSTGRES_16"
  deletion_protection = true

  settings {
    edition           = "ENTERPRISE"
    tier              = local.mlflow_sql_tier
    availability_type = "ZONAL"
    disk_autoresize   = true
    disk_size         = 20
    disk_type         = "PD_SSD"

    backup_configuration {
      enabled = true
    }

    ip_configuration {
      ipv4_enabled                                  = false
      private_network                               = google_compute_network.production.id
      enable_private_path_for_google_cloud_services = true
    }
  }

  depends_on = [
    google_project_service.required["sqladmin.googleapis.com"],
    google_service_networking_connection.production_private_services,
  ]
}

resource "google_sql_database" "mlflow_production" {
  project  = data.google_project.current.project_id
  name     = local.mlflow_database_name
  instance = google_sql_database_instance.mlflow_production.name
}

resource "google_sql_user" "mlflow_production" {
  project  = data.google_project.current.project_id
  name     = local.mlflow_database_user
  instance = google_sql_database_instance.mlflow_production.name
  password = random_password.mlflow_db_password_production.result
}
