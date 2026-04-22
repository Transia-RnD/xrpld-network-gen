# Changelog

## [3.0.0] - 2025-04-22

### Changed
- Complete architectural rewrite from `xrpld-netgen` to `xrpld-lab`
- Replaced 74-parameter functions with structured dataclasses
- Config generation via builder pattern instead of string concatenation
- Protocol differences consolidated into frozen ProtocolSpec dataclass
- CLI entry point is now `xrpld-lab` (was `xrpld-netgen`)

### Added
- Config-from-repo: download config from GitHub at specific commit, merge with local YAML overrides
- `--config_overrides` CLI argument for custom YAML/JSON config files
- Three-layer config merge: hardcoded defaults -> repo config -> local overrides
- Local network mode: run multi-node clusters as native processes without Docker
- 495 unit tests
