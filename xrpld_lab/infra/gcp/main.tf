# GCP multi-region xrpld perf cluster.
# One VM per node, each with an ephemeral external IP. Validators and P2P peers
# are spread across the zones supplied in terraform.tfvars (rendered by the lab
# from GcpConfig). The lab harvests `validator_ips` / `peer_ips` and feeds them
# into its existing ansible pipeline as vips/pips.

terraform {
  required_version = ">= 1.3"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
  }
}

provider "google" {
  project = var.project
  region  = var.region
}

locals {
  ssh_metadata = "${var.ssh_user}:${file(var.ssh_pubkey_path)}"
}

resource "google_compute_instance" "validator" {
  count        = length(var.validator_zones)
  name         = "${var.cluster}-vnode${count.index + 1}"
  machine_type = var.machine_type
  zone         = var.validator_zones[count.index]
  tags         = [var.network_tag]

  boot_disk {
    initialize_params {
      image = var.image
      size  = var.disk_gb
      type  = "pd-ssd"
    }
  }

  network_interface {
    network = "default"
    access_config {} # ephemeral external IP
  }

  metadata = {
    ssh-keys = local.ssh_metadata
  }
}

resource "google_compute_instance" "peer" {
  count        = length(var.peer_zones)
  name         = "${var.cluster}-pnode${count.index + 1}"
  machine_type = var.machine_type
  zone         = var.peer_zones[count.index]
  tags         = [var.network_tag]

  boot_disk {
    initialize_params {
      image = var.image
      size  = var.disk_gb
      type  = "pd-ssd"
    }
  }

  network_interface {
    network = "default"
    access_config {} # ephemeral external IP
  }

  metadata = {
    ssh-keys = local.ssh_metadata
  }
}

# Peer (51235+), public RPC/WS, and SSH. Admin ports are intentionally NOT
# opened — they stay node-local. Lock allowed_source_ranges down for anything
# longer-lived than a throwaway perf net.
resource "google_compute_firewall" "xrpld" {
  name    = "${var.cluster}-xrpld-fw"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = var.open_tcp_ports
  }

  source_ranges = var.allowed_source_ranges
  target_tags   = [var.network_tag]
}
