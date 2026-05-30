output "validator_ips" {
  description = "Ephemeral external IPs of the validator VMs, in node order."
  value       = google_compute_instance.validator[*].network_interface[0].access_config[0].nat_ip
}

output "peer_ips" {
  description = "Ephemeral external IPs of the P2P peer VMs, in node order."
  value       = google_compute_instance.peer[*].network_interface[0].access_config[0].nat_ip
}
