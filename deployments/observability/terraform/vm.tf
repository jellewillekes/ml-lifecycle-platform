resource "google_compute_disk" "prometheus" {
  project = data.google_project.current.project_id
  name    = "${local.name_prefix}-prometheus-tsdb"
  type    = "pd-balanced"
  size    = var.prometheus_disk_size_gb
  zone    = var.zone

  labels = merge(local.common_labels, { purpose = "prometheus_tsdb" })

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_iam_member" "vm_log_writer" {
  project = data.google_project.current.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.obs_vm.email}"
}

resource "google_project_iam_member" "vm_metric_writer" {
  project = data.google_project.current.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.obs_vm.email}"
}

locals {
  startup_script = <<-BASH
    #!/usr/bin/env bash
    set -euxo pipefail

    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y ca-certificates curl gnupg jq

    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/debian/gpg \
      | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
      > /etc/apt/sources.list.d/docker.list
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

    systemctl enable --now docker

    PROM_DISK_DEVICE=/dev/disk/by-id/google-prometheus-tsdb
    if ! blkid "$PROM_DISK_DEVICE"; then
      mkfs.ext4 -F "$PROM_DISK_DEVICE"
    fi
    mkdir -p /mnt/prometheus
    grep -q "$PROM_DISK_DEVICE" /etc/fstab \
      || echo "$PROM_DISK_DEVICE /mnt/prometheus ext4 defaults,nofail 0 2" >> /etc/fstab
    mount -a

    INSTALL_DIR=/opt/observability
    mkdir -p "$INSTALL_DIR"
    gcloud storage rsync -r "gs://${local.config_bucket_name}" "$INSTALL_DIR"

    fetch_secret() {
      local name="$1"
      gcloud secrets versions access latest --secret="$name" --project="${var.project_id}"
    }

    HMAC_ACCESS=$(fetch_secret "${google_secret_manager_secret.tempo_hmac_access.secret_id}")
    HMAC_SECRET=$(fetch_secret "${google_secret_manager_secret.tempo_hmac_secret.secret_id}")
    GRAFANA_PASSWORD=$(fetch_secret "${google_secret_manager_secret.grafana_admin_password.secret_id}")

    cat > "$INSTALL_DIR/tempo.env" <<ENV
    TEMPO_BUCKET=${google_storage_bucket.tempo.name}
    TEMPO_S3_ACCESS_KEY=$HMAC_ACCESS
    TEMPO_S3_SECRET_KEY=$HMAC_SECRET
    ENV

    cat > "$INSTALL_DIR/grafana.env" <<ENV
    GF_SECURITY_ADMIN_USER=admin
    GF_SECURITY_ADMIN_PASSWORD=$GRAFANA_PASSWORD
    ENV

    chmod 600 "$INSTALL_DIR/tempo.env" "$INSTALL_DIR/grafana.env"

    cd "$INSTALL_DIR"
    docker compose pull
    docker compose up -d
  BASH
}

resource "google_compute_instance" "observability" {
  project      = data.google_project.current.project_id
  name         = "${local.name_prefix}-vm"
  machine_type = var.vm_machine_type
  zone         = var.zone

  tags   = [local.name_prefix]
  labels = merge(local.common_labels, { purpose = "observability_stack" })

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
      size  = 20
      type  = "pd-balanced"
    }
  }

  attached_disk {
    source      = google_compute_disk.prometheus.id
    device_name = "prometheus-tsdb"
    mode        = "READ_WRITE"
  }

  network_interface {
    network    = data.google_compute_network.staging.id
    subnetwork = data.google_compute_subnetwork.staging.id
    network_ip = var.vm_static_internal_ip
  }

  service_account {
    email  = google_service_account.obs_vm.email
    scopes = ["cloud-platform"]
  }

  shielded_instance_config {
    enable_secure_boot          = true
    enable_vtpm                 = true
    enable_integrity_monitoring = true
  }

  metadata = {
    enable-oslogin = "TRUE"
  }

  metadata_startup_script = local.startup_script

  depends_on = [
    google_storage_bucket_object.config,
    google_secret_manager_secret_version.grafana_admin_password,
    google_secret_manager_secret_version.tempo_hmac_access,
    google_secret_manager_secret_version.tempo_hmac_secret,
    google_secret_manager_secret_iam_member.vm_grafana_admin_accessor,
    google_secret_manager_secret_iam_member.vm_tempo_hmac_access_accessor,
    google_secret_manager_secret_iam_member.vm_tempo_hmac_secret_accessor,
    google_storage_bucket_iam_member.vm_config_reader,
    google_storage_bucket_iam_member.vm_tempo_writer,
  ]
}
