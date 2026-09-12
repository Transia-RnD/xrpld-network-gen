# Changelog

## 3.5.0

### Added
- **`status` service** (`services: - status: {port: 8687}` in the ansible config) — every
  node runs `node_metrics.py` (the xrplf-devnet-node sampler, stdlib only) as the
  `xrpld-status` systemd unit; the services host aggregates them at `/api/network` and
  `/api/network/health` and its nginx vhost serves `/status/`, `/status/api/` and
  `/status/nodes/<name>/`. Node `[datagram_monitor]` stanzas default to the node's own
  address and the sampler's XDGM port. Operators fill `/opt/xrpld-status/network.json`
  for the deploy, branches, faucet, VL and amendment panels.

## 3.2.0

### Added
- **`create:gcp`** — provision a multi-region xrpld perf cluster on GCP (one VM per node,
  terraform), harvest IPs into the ansible pipeline, deploy and health-check consensus.
- **Prefunded genesis (perf-iac style)** — inject N AccountRoot + M RippleState entries
  directly into genesis (`--preload_accounts`, `--preload_trustlines`, `--preload_balance`,
  `--preload_currency`) so a network starts with realistic state.
- **`--datagram_monitor "HOST PORT"`** on `create:network` / `create:ansible` / `create:gcp`
  (and `up:standalone`) — writes a `[datagram_monitor]` stanza into every node's config so
  each node emits XDGM metrics to the given sink (e.g. a perf-results server). Endpoint is
  space-separated `"<ip> <port>"`, matching xrpld's `DatagramMonitor` `parseEndpoint`.
- `endpoints.json` manifest emitted by `create:gcp` (named validators/peers with `ws`/`rpc`
  URLs) for downstream load tooling.

### Changed
- Default protocol is now `xrpl`.

### Fixed
- `update_genesis` now fails loud on a genesis template with no amendments or no `Amendments`
  entry, instead of silently producing an empty/unchanged genesis.
