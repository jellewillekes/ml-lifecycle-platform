moved {
  from = google_project_iam_member.ci_run_admin
  to   = google_project_iam_member.ci_run_admin["staging"]
}

moved {
  from = google_project_iam_member.ci_service_usage_admin
  to   = google_project_iam_member.ci_service_usage_admin["staging"]
}

moved {
  from = google_service_account_iam_member.ci_runtime_service_account_user
  to   = google_service_account_iam_member.ci_runtime_service_account_user["staging"]
}
