locals {
  mlflow_secret_ids = {
    db_user                  = "${local.foundation_name_prefix}-mlflow-db-user"
    db_password              = "${local.foundation_name_prefix}-mlflow-db-password"
    db_name                  = "${local.foundation_name_prefix}-mlflow-db-name"
    instance_connection_name = "${local.foundation_name_prefix}-mlflow-instance-connection-name"
    artifact_root            = "${local.foundation_name_prefix}-mlflow-artifact-root"
  }

  mlflow_secret_values = {
    db_user                  = google_sql_user.mlflow.name
    db_password              = random_password.mlflow_db_password.result
    db_name                  = google_sql_database.mlflow.name
    instance_connection_name = google_sql_database_instance.mlflow.connection_name
    artifact_root            = local.mlflow_artifact_root
  }
}

resource "google_secret_manager_secret" "mlflow" {
  for_each = local.mlflow_secret_ids

  project   = data.google_project.current.project_id
  secret_id = each.value

  labels = merge(local.common_labels, { purpose = "mlflow_${each.key}" })

  replication {
    auto {}
  }

  depends_on = [google_project_service.required["secretmanager.googleapis.com"]]
}

resource "google_secret_manager_secret_version" "mlflow" {
  for_each = local.mlflow_secret_values

  secret      = google_secret_manager_secret.mlflow[each.key].id
  secret_data = each.value
}

resource "google_secret_manager_secret_iam_member" "runtime_mlflow_secret_accessor" {
  for_each = google_secret_manager_secret.mlflow

  project   = each.value.project
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

locals {
  mlflow_secret_ids_production = var.manage_production_foundation ? {
    db_user                  = "${local.foundation_name_prefix}-mlflow-db-user-production"
    db_password              = "${local.foundation_name_prefix}-mlflow-db-password-production"
    db_name                  = "${local.foundation_name_prefix}-mlflow-db-name-production"
    instance_connection_name = "${local.foundation_name_prefix}-mlflow-instance-connection-name-production"
    artifact_root            = "${local.foundation_name_prefix}-mlflow-artifact-root-production"
  } : {}

  mlflow_secret_values_production = var.manage_production_foundation ? {
    db_user                  = google_sql_user.mlflow_production[0].name
    db_password              = random_password.mlflow_db_password_production[0].result
    db_name                  = google_sql_database.mlflow_production[0].name
    instance_connection_name = google_sql_database_instance.mlflow_production[0].connection_name
    artifact_root            = local.mlflow_artifact_root_production
  } : {}
}

resource "google_secret_manager_secret" "mlflow_production" {
  for_each = local.mlflow_secret_ids_production

  project   = data.google_project.current.project_id
  secret_id = each.value

  labels = merge(local.common_labels, { purpose = "mlflow_production_${each.key}" })

  replication {
    auto {}
  }

  depends_on = [google_project_service.required["secretmanager.googleapis.com"]]
}

resource "google_secret_manager_secret_version" "mlflow_production" {
  for_each = local.mlflow_secret_values_production

  secret      = google_secret_manager_secret.mlflow_production[each.key].id
  secret_data = each.value
}

resource "google_secret_manager_secret_iam_member" "runtime_mlflow_production_secret_accessor" {
  for_each = google_secret_manager_secret.mlflow_production

  project   = each.value.project
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}
