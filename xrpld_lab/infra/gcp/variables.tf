variable "project" {
  type        = string
  description = "GCP project ID."
}

variable "region" {
  type        = string
  description = "Default provider region (instances pin their own zone)."
  default     = "us-central1"
}

variable "cluster" {
  type        = string
  description = "Cluster name prefix for instance + firewall names."
  default     = "xrpld-perf"
}

variable "validator_zones" {
  type        = list(string)
  description = "One zone per validator VM."
}

variable "peer_zones" {
  type        = list(string)
  description = "One zone per P2P peer VM."
}

variable "machine_type" {
  type    = string
  default = "n2-standard-8"
}

variable "image" {
  type    = string
  default = "ubuntu-os-cloud/ubuntu-2204-lts"
}

variable "disk_gb" {
  type    = number
  default = 100
}

variable "ssh_user" {
  type    = string
  default = "ubuntu"
}

variable "ssh_pubkey_path" {
  type        = string
  description = "Path to the SSH public key uploaded to instance metadata."
  default     = "~/.ssh/id_rsa.pub"
}

variable "network_tag" {
  type    = string
  default = "xrpld-perf"
}

variable "allowed_source_ranges" {
  type    = list(string)
  default = ["0.0.0.0/0"]
}

variable "open_tcp_ports" {
  type        = list(string)
  description = "TCP ports/ranges opened on the cluster (peer, public RPC/WS, ssh)."
  default     = ["22", "5007-5520", "6008-6520", "51235-51740"]
}
