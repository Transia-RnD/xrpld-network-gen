#!/usr/bin/env python
# coding: utf-8

"""Tests for xrpld_lab.cli — the new thin CLI layer.

Covers:
- _build_parser: subcommand existence and default values
- build_lab_config: protocol-specific defaults and arg passthrough
- main(): dispatch to LabRunner and operational commands
"""

from unittest.mock import patch, MagicMock

import pytest

from xrpld_lab.cli import (
    _build_parser,
    build_lab_config,
    main,
    _DEFAULT_VL_KEY,
    _XAHAU_IMPORT_VL_KEY,
    _XRPL_RELEASE_FALLBACK,
    _XAHAU_RELEASE_FALLBACK,
)
from xrpld_lab.models import (
    BuildType,
    DeployMode,
    NodeDbType,
    Protocol,
)


# -------------------------------------------------------------------------
# _build_parser tests
# -------------------------------------------------------------------------


class TestBuildParser:
    """Test that _build_parser creates the expected subcommands and defaults."""

    def test_parser_creates_without_error(self):
        parser = _build_parser()
        assert parser is not None

    def test_up_standalone_defaults(self):
        parser = _build_parser()
        args = parser.parse_args(["up:standalone"])
        assert args.command == "up:standalone"
        assert args.log_level == "trace"
        assert args.build_type == "binary"
        assert args.public_key == _DEFAULT_VL_KEY
        assert args.import_key is None
        assert args.protocol == "xrpl"
        assert args.network_id == 21337
        assert args.network_type == "standalone"
        assert args.server is None
        assert args.version is None
        assert args.ipfs is False
        assert args.nodedb_type == "NuDB"

    def test_create_network_defaults(self):
        parser = _build_parser()
        args = parser.parse_args(["create:network"])
        assert args.command == "create:network"
        assert args.log_level == "trace"
        assert args.protocol == "xrpl"
        assert args.num_validators == 3
        assert args.num_peers == 1
        assert args.network_id == 21337
        assert args.build_server is None
        assert args.build_version is None
        assert args.genesis is False
        assert args.quorum is None
        assert args.nodedb_type == "NuDB"
        assert args.local is False
        assert args.binary_name == "xrpld"

    def test_operational_commands_exist(self):
        parser = _build_parser()
        # up
        args = parser.parse_args(["up", "--name", "my-net"])
        assert args.command == "up"
        assert args.name == "my-net"
        # down
        args = parser.parse_args(["down", "--name", "my-net"])
        assert args.command == "down"
        assert args.name == "my-net"
        # remove
        args = parser.parse_args(["remove", "--name", "my-net"])
        assert args.command == "remove"
        assert args.name == "my-net"

    # -- New operational subparsers --

    def test_down_standalone_defaults(self):
        parser = _build_parser()
        args = parser.parse_args(["down:standalone"])
        assert args.command == "down:standalone"
        assert args.name is None
        assert args.protocol == "xrpl"
        assert args.version is None

    def test_down_standalone_with_name(self):
        parser = _build_parser()
        args = parser.parse_args(["down:standalone", "--name", "my-standalone"])
        assert args.name == "my-standalone"

    def test_down_standalone_with_version(self):
        parser = _build_parser()
        args = parser.parse_args(["down:standalone", "--version", "1.0.0"])
        assert args.version == "1.0.0"
        assert args.protocol == "xrpl"

    def test_up_local_defaults(self):
        parser = _build_parser()
        args = parser.parse_args(["up:local"])
        assert args.command == "up:local"
        assert args.log_level == "trace"
        assert args.public_key == _DEFAULT_VL_KEY
        assert args.import_key is None
        assert args.protocol == "xrpl"
        assert args.network_type == "standalone"
        assert args.network_id == 21337
        assert args.nodedb_type == "NuDB"

    def test_down_local_exists(self):
        parser = _build_parser()
        args = parser.parse_args(["down:local"])
        assert args.command == "down:local"

    def test_update_node_args(self):
        parser = _build_parser()
        args = parser.parse_args([
            "update:node",
            "--name", "my-net",
            "--node_id", "2",
            "--node_type", "validator",
            "--build_server", "https://build.example.com",
            "--build_version", "2.0.0",
        ])
        assert args.command == "update:node"
        assert args.name == "my-net"
        assert args.node_id == 2
        assert args.node_type == "validator"
        assert args.build_server == "https://build.example.com"
        assert args.build_version == "2.0.0"

    def test_update_node_peer_type(self):
        parser = _build_parser()
        args = parser.parse_args([
            "update:node",
            "--name", "my-net",
            "--node_id", "1",
            "--node_type", "peer",
            "--build_server", "https://build.example.com",
            "--build_version", "1.0.0",
        ])
        assert args.node_type == "peer"

    def test_enable_amendment_args(self):
        parser = _build_parser()
        args = parser.parse_args([
            "enable:amendment",
            "--name", "my-net",
            "--amendment_name", "fixNFTokenRemint",
            "--node_id", "1",
            "--node_type", "validator",
        ])
        assert args.command == "enable:amendment"
        assert args.name == "my-net"
        assert args.amendment_name == "fixNFTokenRemint"
        assert args.node_id == 1
        assert args.node_type == "validator"

    def test_enable_amendment_peer_type(self):
        parser = _build_parser()
        args = parser.parse_args([
            "enable:amendment",
            "--name", "my-net",
            "--amendment_name", "SomeAmendment",
            "--node_id", "3",
            "--node_type", "peer",
        ])
        assert args.node_type == "peer"
        assert args.node_id == 3

    def test_logs_local_defaults(self):
        parser = _build_parser()
        args = parser.parse_args(["logs:local"])
        assert args.command == "logs:local"
        assert args.node is None

    def test_logs_local_with_node(self):
        parser = _build_parser()
        args = parser.parse_args(["logs:local", "--node", "vnode1"])
        assert args.node == "vnode1"

    def test_logs_standalone_defaults(self):
        parser = _build_parser()
        args = parser.parse_args(["logs:standalone"])
        assert args.command == "logs:standalone"
        assert args.protocol == "xrpl"

    def test_logs_standalone_with_protocol(self):
        parser = _build_parser()
        args = parser.parse_args(["logs:standalone", "--protocol", "xrpl"])
        assert args.protocol == "xrpl"

    def test_create_network_ansible_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["create:network", "--ansible",
                                  "--vips", "10.0.0.1", "10.0.0.2",
                                  "--pips", "10.0.0.3"])
        assert args.ansible is True
        assert args.vips == ["10.0.0.1", "10.0.0.2"]
        assert args.pips == ["10.0.0.3"]
        assert args.ssh_port == 20
        assert args.ssh_user == "ubuntu"

    def test_create_ansible_defaults(self):
        parser = _build_parser()
        args = parser.parse_args(["create:ansible",
                                  "--vips", "10.0.0.1",
                                  "--pips", "10.0.0.2"])
        assert args.command == "create:ansible"
        assert args.vips == ["10.0.0.1"]
        assert args.pips == ["10.0.0.2"]
        assert args.protocol == "xrpl"
        assert args.num_validators == 3

    def test_create_ansible_with_ssh_args(self):
        parser = _build_parser()
        args = parser.parse_args(["create:ansible",
                                  "--vips", "10.0.0.1",
                                  "--pips", "10.0.0.2",
                                  "--ssh_port", "22",
                                  "--ssh_user", "admin",
                                  "--ssh_key", "/root/.ssh/key"])
        assert args.ssh_port == 22
        assert args.ssh_user == "admin"
        assert args.ssh_key == "/root/.ssh/key"

    def test_deploy_ansible_args(self):
        parser = _build_parser()
        args = parser.parse_args(["deploy:ansible", "--name", "my-cluster"])
        assert args.command == "deploy:ansible"
        assert args.name == "my-cluster"

    def test_all_subcommands_present(self):
        """Verify all 15 subcommands are registered."""
        parser = _build_parser()
        expected_commands = [
            "up:standalone",
            "create:network",
            "create:ansible",
            "deploy:ansible",
            "up",
            "down",
            "remove",
            "down:standalone",
            "up:local",
            "down:local",
            "update:node",
            "enable:amendment",
            "logs:local",
            "logs:standalone",
        ]
        for cmd in expected_commands:
            # Should not raise SystemExit
            if cmd in (
                "up:standalone", "down:standalone",
                "up:local", "down:local", "logs:local", "logs:standalone",
            ):
                args = parser.parse_args([cmd])
            elif cmd == "create:network":
                args = parser.parse_args([cmd])
            elif cmd == "create:ansible":
                args = parser.parse_args([cmd, "--vips", "1.2.3.4", "--pips", "5.6.7.8"])
            elif cmd in ("up", "down", "remove", "deploy:ansible"):
                args = parser.parse_args([cmd, "--name", "test"])
            elif cmd == "update:node":
                args = parser.parse_args([
                    cmd, "--name", "test", "--node_id", "1",
                    "--node_type", "validator",
                    "--build_server", "s", "--build_version", "v",
                ])
            elif cmd == "enable:amendment":
                args = parser.parse_args([
                    cmd, "--name", "test", "--amendment_name", "x",
                    "--node_id", "1", "--node_type", "validator",
                ])
            assert args.command == cmd


# -------------------------------------------------------------------------
# build_lab_config tests — up:standalone
# -------------------------------------------------------------------------


class TestBuildLabConfigStandalone:
    """Test build_lab_config for the up:standalone command."""

    def _parse(self, *extra_args):
        parser = _build_parser()
        return parser.parse_args(["up:standalone", *extra_args])

    # -- xahau defaults --

    def test_xahau_defaults_build_server(self):
        args = self._parse("--protocol", "xahau")
        cfg = build_lab_config(args)
        assert cfg.build_source.build_server == "https://build.xahau.tech"

    def test_xahau_defaults_build_type_binary(self):
        args = self._parse("--protocol", "xahau")
        cfg = build_lab_config(args)
        assert cfg.build_source.build_type == BuildType.BINARY

    def test_xahau_defaults_import_key(self):
        args = self._parse("--protocol", "xahau")
        cfg = build_lab_config(args)
        assert cfg.import_vl_key == _XAHAU_IMPORT_VL_KEY

    def test_xahau_fallback_version(self):
        args = self._parse("--protocol", "xahau")
        cfg = build_lab_config(args)
        assert cfg.build_source.build_version == _XAHAU_RELEASE_FALLBACK

    # -- xrpl defaults --

    def test_xrpl_defaults_build_server(self):
        args = self._parse("--protocol", "xrpl")
        cfg = build_lab_config(args)
        assert cfg.build_source.build_server == "rippleci"

    def test_xrpl_defaults_build_type_image(self):
        args = self._parse("--protocol", "xrpl")
        cfg = build_lab_config(args)
        assert cfg.build_source.build_type == BuildType.IMAGE

    def test_xrpl_fallback_version(self):
        args = self._parse("--protocol", "xrpl")
        cfg = build_lab_config(args)
        assert cfg.build_source.build_version == _XRPL_RELEASE_FALLBACK

    # -- custom overrides --

    def test_custom_version_overrides_fallback(self):
        args = self._parse("--protocol", "xahau", "--version", "2099.1.1-custom")
        cfg = build_lab_config(args)
        assert cfg.build_source.build_version == "2099.1.1-custom"

    def test_custom_server_overrides_default(self):
        args = self._parse("--protocol", "xahau", "--server", "https://custom.build")
        cfg = build_lab_config(args)
        assert cfg.build_source.build_server == "https://custom.build"

    # -- passthrough fields --

    def test_mode_is_standalone(self):
        args = self._parse()
        cfg = build_lab_config(args)
        assert cfg.mode == DeployMode.STANDALONE

    def test_network_id_passed_through(self):
        args = self._parse("--network_id", "42")
        cfg = build_lab_config(args)
        assert cfg.network_id == 42

    def test_log_level_passed_through(self):
        args = self._parse("--log_level", "debug")
        cfg = build_lab_config(args)
        assert cfg.log_level == "debug"

    def test_nodedb_type_parsed_as_enum(self):
        args = self._parse("--nodedb_type", "Memory")
        cfg = build_lab_config(args)
        assert cfg.node_db_type == NodeDbType.MEMORY

    def test_nodedb_type_nudb(self):
        args = self._parse("--nodedb_type", "NuDB")
        cfg = build_lab_config(args)
        assert cfg.node_db_type == NodeDbType.NUDB

    def test_add_ipfs_flag(self):
        args = self._parse("--ipfs", "True")
        cfg = build_lab_config(args)
        assert cfg.add_ipfs is True

    # -- image string for xrpl --

    def test_xrpl_image_string(self):
        args = self._parse("--protocol", "xrpl")
        cfg = build_lab_config(args)
        assert cfg.build_source.image == f"rippleci/xrpld:{_XRPL_RELEASE_FALLBACK}"

    # -- github owner/repo from spec --

    def test_xahau_owner_repo(self):
        args = self._parse("--protocol", "xahau")
        cfg = build_lab_config(args)
        assert cfg.build_source.owner == "Xahau"
        assert cfg.build_source.repo == "xahaud"

    def test_xrpl_owner_repo(self):
        args = self._parse("--protocol", "xrpl")
        cfg = build_lab_config(args)
        assert cfg.build_source.owner == "XRPLF"
        assert cfg.build_source.repo == "rippled"


# -------------------------------------------------------------------------
# build_lab_config tests — create:network
# -------------------------------------------------------------------------


class TestBuildLabConfigNetwork:
    """Test build_lab_config for the create:network command."""

    def _parse(self, *extra_args):
        parser = _build_parser()
        return parser.parse_args(["create:network", *extra_args])

    # -- deploy mode --

    def test_local_flag_sets_local_mode(self):
        args = self._parse("--local")
        cfg = build_lab_config(args)
        assert cfg.mode == DeployMode.LOCAL

    def test_no_local_flag_sets_network_mode(self):
        args = self._parse()
        cfg = build_lab_config(args)
        assert cfg.mode == DeployMode.NETWORK

    # -- passthrough fields --

    def test_num_validators_passed_through(self):
        args = self._parse("--num_validators", "5")
        cfg = build_lab_config(args)
        assert cfg.num_validators == 5

    def test_num_peers_passed_through(self):
        args = self._parse("--num_peers", "3")
        cfg = build_lab_config(args)
        assert cfg.num_peers == 3

    def test_genesis_flag(self):
        args = self._parse("--genesis", "True")
        cfg = build_lab_config(args)
        assert cfg.genesis is True

    def test_quorum_passed_through(self):
        args = self._parse("--quorum", "2")
        cfg = build_lab_config(args)
        assert cfg.quorum == 2

    def test_quorum_none_uses_effective(self):
        args = self._parse("--num_validators", "3")
        cfg = build_lab_config(args)
        assert cfg.quorum is None
        assert cfg.effective_quorum == 2

    # -- protocol defaults --

    def test_xahau_defaults(self):
        args = self._parse("--protocol", "xahau")
        cfg = build_lab_config(args)
        assert cfg.build_source.build_server == "https://build.xahau.tech"
        assert cfg.build_source.build_version == _XAHAU_RELEASE_FALLBACK
        assert cfg.build_source.build_type == BuildType.BINARY

    def test_xrpl_with_local_uses_github_url(self):
        args = self._parse("--protocol", "xrpl", "--local")
        cfg = build_lab_config(args)
        assert cfg.build_source.build_server == "https://github.com/XRPLF/xrpld/tree"
        assert cfg.mode == DeployMode.LOCAL

    def test_xrpl_without_local_uses_spec_default(self):
        args = self._parse("--protocol", "xrpl")
        cfg = build_lab_config(args)
        # spec.default_build_server for xrpl is "rippleci"
        assert cfg.build_source.build_server == "rippleci"

    def test_binary_name_passed_through(self):
        args = self._parse("--binary_name", "my-xrpld")
        cfg = build_lab_config(args)
        assert cfg.binary_name == "my-xrpld"

    def test_import_vl_key_none_for_xrpl(self):
        # XRPL spec has no import VL key; XRPL networks must emit no [import_vl_keys].
        args = self._parse()
        cfg = build_lab_config(args)
        assert cfg.import_vl_key is None

    def test_import_vl_key_for_xahau(self):
        args = self._parse("--protocol", "xahau")
        cfg = build_lab_config(args)
        assert cfg.import_vl_key == _XAHAU_IMPORT_VL_KEY

    def test_network_id_from_spec_when_default(self):
        """When network_id is the CLI default (21339) and protocol is xrpl,
        the spec default (21337) should be used via `args.network_id or spec.default_network_id`."""
        args = self._parse("--protocol", "xrpl", "--network_id", "0")
        cfg = build_lab_config(args)
        # 0 is falsy, so spec default should be used
        assert cfg.network_id == 21337

    # -- GitHub URL mode (custom XRPL builds) --

    def test_github_url_extracts_cluster_name(self):
        args = self._parse(
            "--protocol", "xrpl",
            "--build_server", "https://github.com/XRPLF/xrpld/tree/xrplf-smart-contracts",
            "--build_version", "abc123",
        )
        cfg = build_lab_config(args)
        assert cfg.build_source.cluster_name == "xrplf-smart-contracts"

    def test_github_url_sets_commit_hash(self):
        args = self._parse(
            "--protocol", "xrpl",
            "--build_server", "https://github.com/XRPLF/xrpld/tree/xrplf-smart-contracts",
            "--build_version", "abc123def456",
        )
        cfg = build_lab_config(args)
        assert cfg.build_source.commit_hash == "abc123def456"

    def test_github_url_sets_binary_path(self):
        args = self._parse(
            "--protocol", "xrpl",
            "--build_server", "https://github.com/XRPLF/xrpld/tree/xrplf-smart-contracts",
            "--build_version", "abc123",
        )
        cfg = build_lab_config(args)
        assert cfg.build_source.binary_path == "./xrpld"

    def test_github_url_custom_binary_path(self):
        args = self._parse(
            "--protocol", "xrpl",
            "--build_server", "https://github.com/XRPLF/xrpld/tree/xrplf-smart-contracts",
            "--build_version", "abc123",
            "--binary_path", "/opt/builds/xrpld",
        )
        cfg = build_lab_config(args)
        assert cfg.build_source.binary_path == "/opt/builds/xrpld"

    def test_github_url_sets_build_type_binary(self):
        args = self._parse(
            "--protocol", "xrpl",
            "--build_server", "https://github.com/XRPLF/xrpld/tree/feature-branch",
            "--build_version", "abc123",
        )
        cfg = build_lab_config(args)
        assert cfg.build_source.build_type == BuildType.BINARY

    def test_github_url_extracts_owner(self):
        args = self._parse(
            "--protocol", "xrpl",
            "--build_server", "https://github.com/Transia-RnD/rippled/tree/custom-branch",
            "--build_version", "abc123",
        )
        cfg = build_lab_config(args)
        assert cfg.build_source.owner == "Transia-RnD"

    def test_github_url_sets_repo_to_rippled(self):
        args = self._parse(
            "--protocol", "xrpl",
            "--build_server", "https://github.com/XRPLF/xrpld/tree/some-branch",
            "--build_version", "abc123",
        )
        cfg = build_lab_config(args)
        assert cfg.build_source.repo == "rippled"

    def test_github_url_branch_with_slashes(self):
        args = self._parse(
            "--protocol", "xrpl",
            "--build_server", "https://github.com/XRPLF/xrpld/tree/feature/my-branch",
            "--build_version", "abc123",
        )
        cfg = build_lab_config(args)
        assert cfg.build_source.cluster_name == "feature-my-branch"

    # -- ansible flag on create:network --

    def test_ansible_flag_creates_ansible_config(self):
        args = self._parse(
            "--ansible",
            "--vips", "10.0.0.1", "10.0.0.2", "10.0.0.3",
            "--pips", "10.0.0.4",
        )
        cfg = build_lab_config(args)
        assert cfg.ansible is not None
        assert cfg.ansible.vips == ["10.0.0.1", "10.0.0.2", "10.0.0.3"]
        assert cfg.ansible.pips == ["10.0.0.4"]

    def test_no_ansible_flag_leaves_ansible_none(self):
        args = self._parse()
        cfg = build_lab_config(args)
        assert cfg.ansible is None

    def test_ansible_ssh_args_passed_through(self):
        args = self._parse(
            "--ansible",
            "--vips", "10.0.0.1",
            "--pips", "10.0.0.2",
            "--ssh_port", "22",
            "--ssh_user", "admin",
            "--ssh_key", "/root/.ssh/key",
        )
        cfg = build_lab_config(args)
        assert cfg.ansible.ssh_port == 22
        assert cfg.ansible.ssh_user == "admin"
        assert cfg.ansible.ssh_key_path == "/root/.ssh/key"


# -------------------------------------------------------------------------
# build_lab_config tests — create:ansible
# -------------------------------------------------------------------------


class TestBuildLabConfigAnsible:
    """Test build_lab_config for the create:ansible command."""

    def _parse(self, *extra_args):
        parser = _build_parser()
        return parser.parse_args(["create:ansible",
                                  "--vips", "10.0.0.1", "10.0.0.2",
                                  "--pips", "10.0.0.3",
                                  *extra_args])

    def test_creates_ansible_config(self):
        args = self._parse()
        cfg = build_lab_config(args)
        assert cfg.ansible is not None
        assert cfg.ansible.vips == ["10.0.0.1", "10.0.0.2"]
        assert cfg.ansible.pips == ["10.0.0.3"]

    def test_mode_is_network(self):
        args = self._parse()
        cfg = build_lab_config(args)
        assert cfg.mode == DeployMode.NETWORK

    def test_xahau_defaults_applied(self):
        args = self._parse("--protocol", "xahau")
        cfg = build_lab_config(args)
        assert cfg.build_source.build_server == "https://build.xahau.tech"
        assert cfg.build_source.build_type == BuildType.BINARY

    def test_xrpl_defaults_applied(self):
        args = self._parse("--protocol", "xrpl")
        cfg = build_lab_config(args)
        assert cfg.build_source.build_server == "rippleci"

    def test_nodedb_type_rwdb(self):
        args = self._parse("--nodedb_type", "rwdb")
        cfg = build_lab_config(args)
        assert cfg.node_db_type == NodeDbType.RWDB

    def test_ansible_config_from_file(self, tmp_path):
        config_file = tmp_path / "ansible.yml"
        config_file.write_text(
            "ssh_port: 22\n"
            "ssh_user: admin\n"
            "ssh_key_path: /root/.ssh/key\n"
            "vips:\n  - 192.168.1.1\n  - 192.168.1.2\n"
            "pips:\n  - 192.168.1.3\n"
        )
        parser = _build_parser()
        args = parser.parse_args([
            "create:ansible",
            "--vips", "ignored",
            "--pips", "ignored",
            "--ansible_config", str(config_file),
        ])
        cfg = build_lab_config(args)
        assert cfg.ansible.ssh_port == 22
        assert cfg.ansible.ssh_user == "admin"
        assert cfg.ansible.vips == ["192.168.1.1", "192.168.1.2"]
        assert cfg.ansible.pips == ["192.168.1.3"]

    def test_ansible_config_file_with_services(self, tmp_path):
        config_file = tmp_path / "ansible.yml"
        config_file.write_text(
            "vips:\n  - 10.0.0.1\n"
            "pips:\n  - 10.0.0.2\n"
            "services:\n"
            "  - ip: 10.0.0.3\n"
            "    name: infra\n"
            "    nginx:\n"
            "      domain: example.com\n"
            "    redis: {}\n"
        )
        parser = _build_parser()
        args = parser.parse_args([
            "create:ansible",
            "--vips", "ignored",
            "--pips", "ignored",
            "--ansible_config", str(config_file),
        ])
        cfg = build_lab_config(args)
        assert len(cfg.ansible.services) == 1
        assert cfg.ansible.services[0].ip == "10.0.0.3"
        assert cfg.ansible.services[0].name == "infra"
        assert cfg.ansible.services[0].nginx is not None
        assert cfg.ansible.services[0].nginx.domain == "example.com"
        assert cfg.ansible.services[0].redis is not None

    def test_stream_service_forces_trace_log_level(self, tmp_path):
        config_file = tmp_path / "ansible.yml"
        config_file.write_text(
            "vips:\n  - 10.0.0.1\n"
            "pips:\n  - 10.0.0.2\n"
            "services:\n"
            "  - ip: 10.0.0.3\n"
            "    name: infra\n"
            "    stream:\n"
            "      port: 1400\n"
            "      container_name: pnode1\n"
        )
        parser = _build_parser()
        args = parser.parse_args([
            "create:ansible",
            "--vips", "ignored", "--pips", "ignored",
            "--log_level", "warning",
            "--ansible_config", str(config_file),
        ])
        cfg = build_lab_config(args)
        assert cfg.log_level == "trace"

    def test_stream_auto_creates_debug(self, tmp_path):
        """stream and debug are always paired — stream alone creates debug."""
        config_file = tmp_path / "ansible.yml"
        config_file.write_text(
            "vips:\n  - 10.0.0.1\n"
            "pips:\n  - 10.0.0.2\n"
            "services:\n"
            "  - ip: 10.0.0.3\n"
            "    name: infra\n"
            "    stream:\n"
            "      port: 1400\n"
            "      container_name: pnode1\n"
        )
        parser = _build_parser()
        args = parser.parse_args([
            "create:ansible",
            "--vips", "ignored", "--pips", "ignored",
            "--ansible_config", str(config_file),
        ])
        cfg = build_lab_config(args)
        assert cfg.ansible.services[0].debug is not None
        assert cfg.ansible.services[0].debug.endpoint == "ws://10.0.0.3:1400/"

    def test_debug_auto_creates_stream(self, tmp_path):
        """stream and debug are always paired — debug alone creates stream."""
        config_file = tmp_path / "ansible.yml"
        config_file.write_text(
            "vips:\n  - 10.0.0.1\n"
            "pips:\n  - 10.0.0.2\n"
            "services:\n"
            "  - ip: 10.0.0.3\n"
            "    name: infra\n"
            "    debug:\n"
            "      port: 8081\n"
        )
        parser = _build_parser()
        args = parser.parse_args([
            "create:ansible",
            "--vips", "ignored", "--pips", "ignored",
            "--ansible_config", str(config_file),
        ])
        cfg = build_lab_config(args)
        assert cfg.ansible.services[0].stream is not None

    def test_stream_debug_auto_creates_redis(self, tmp_path):
        """stream/debug require redis — auto-created if missing."""
        config_file = tmp_path / "ansible.yml"
        config_file.write_text(
            "vips:\n  - 10.0.0.1\n"
            "pips:\n  - 10.0.0.2\n"
            "services:\n"
            "  - ip: 10.0.0.3\n"
            "    name: infra\n"
            "    stream:\n"
            "      port: 1400\n"
            "      container_name: pnode1\n"
        )
        parser = _build_parser()
        args = parser.parse_args([
            "create:ansible",
            "--vips", "ignored", "--pips", "ignored",
            "--ansible_config", str(config_file),
        ])
        cfg = build_lab_config(args)
        assert cfg.ansible.services[0].redis is not None

    def test_debug_endpoint_auto_derived_from_stream(self, tmp_path):
        config_file = tmp_path / "ansible.yml"
        config_file.write_text(
            "vips:\n  - 10.0.0.1\n"
            "pips:\n  - 10.0.0.2\n"
            "services:\n"
            "  - ip: 10.0.0.3\n"
            "    name: infra\n"
            "    stream:\n"
            "      port: 1400\n"
            "      container_name: pnode1\n"
            "    debug:\n"
            "      port: 8081\n"
        )
        parser = _build_parser()
        args = parser.parse_args([
            "create:ansible",
            "--vips", "ignored", "--pips", "ignored",
            "--ansible_config", str(config_file),
        ])
        cfg = build_lab_config(args)
        assert cfg.ansible.services[0].debug.endpoint == "ws://10.0.0.3:1400/"

    def test_debug_explicit_endpoint_not_overridden(self, tmp_path):
        config_file = tmp_path / "ansible.yml"
        config_file.write_text(
            "vips:\n  - 10.0.0.1\n"
            "pips:\n  - 10.0.0.2\n"
            "services:\n"
            "  - ip: 10.0.0.3\n"
            "    name: infra\n"
            "    stream:\n"
            "      port: 1400\n"
            "      container_name: pnode1\n"
            "    debug:\n"
            "      endpoint: ws://custom:9999/\n"
        )
        parser = _build_parser()
        args = parser.parse_args([
            "create:ansible",
            "--vips", "ignored", "--pips", "ignored",
            "--ansible_config", str(config_file),
        ])
        cfg = build_lab_config(args)
        assert cfg.ansible.services[0].debug.endpoint == "ws://custom:9999/"

    def test_no_services_keeps_log_level(self):
        parser = _build_parser()
        args = parser.parse_args([
            "create:ansible",
            "--vips", "10.0.0.1", "--pips", "10.0.0.2",
            "--log_level", "warning",
        ])
        cfg = build_lab_config(args)
        assert cfg.log_level == "warning"


# -------------------------------------------------------------------------
# main() tests
# -------------------------------------------------------------------------


class TestMain:
    """Test main() dispatches correctly."""

    @patch("xrpld_lab.cli.LabRunner")
    @patch("xrpld_lab.cli.build_lab_config")
    def test_up_standalone_calls_runner(self, mock_build, mock_runner_cls):
        mock_config = MagicMock()
        mock_build.return_value = mock_config
        mock_runner = MagicMock()
        mock_runner_cls.return_value = mock_runner

        with patch("sys.argv", ["xrpld-lab", "up:standalone", "--protocol", "xahau"]):
            main()

        mock_build.assert_called_once()
        mock_runner_cls.assert_called_once_with(mock_config)
        mock_runner.run.assert_called_once()

    @patch("xrpld_lab.cli.LabRunner")
    @patch("xrpld_lab.cli.build_lab_config")
    def test_create_network_calls_runner(self, mock_build, mock_runner_cls):
        mock_config = MagicMock()
        mock_build.return_value = mock_config
        mock_runner = MagicMock()
        mock_runner_cls.return_value = mock_runner

        with patch("sys.argv", ["xrpld-lab", "create:network", "--protocol", "xrpl"]):
            main()

        mock_build.assert_called_once()
        mock_runner_cls.assert_called_once_with(mock_config)
        mock_runner.run.assert_called_once()

    @patch("xrpld_lab.cli._build_parser")
    def test_no_command_prints_help(self, mock_build_parser):
        mock_parser = MagicMock()
        mock_args = MagicMock()
        mock_args.command = None
        mock_parser.parse_args.return_value = mock_args
        mock_build_parser.return_value = mock_parser

        with patch("sys.argv", ["xrpld-lab"]):
            main()

        mock_parser.print_help.assert_called_once()

    # -- Operational command dispatch tests --

    @patch("xrpld_lab.cli.run_start_script")
    @patch("xrpld_lab.cli.Workspace")
    def test_up_dispatches_to_run_start_script(self, mock_ws_cls, mock_run):
        mock_ws = MagicMock()
        mock_ws_cls.return_value = mock_ws

        with patch("sys.argv", ["xrpld-lab", "up", "--name", "my-net"]):
            main()

        mock_run.assert_called_once_with(mock_ws, "my-net")

    @patch("xrpld_lab.cli.run_stop_script")
    @patch("xrpld_lab.cli.Workspace")
    def test_down_dispatches_to_run_stop_script(self, mock_ws_cls, mock_run):
        mock_ws = MagicMock()
        mock_ws_cls.return_value = mock_ws

        with patch("sys.argv", ["xrpld-lab", "down", "--name", "my-net"]):
            main()

        mock_run.assert_called_once_with(mock_ws, "my-net")

    @patch("xrpld_lab.cli.remove_network")
    @patch("xrpld_lab.cli.Workspace")
    def test_remove_dispatches_to_remove_network(self, mock_ws_cls, mock_run):
        mock_ws = MagicMock()
        mock_ws_cls.return_value = mock_ws

        with patch("sys.argv", ["xrpld-lab", "remove", "--name", "my-net"]):
            main()

        mock_run.assert_called_once_with(mock_ws, "my-net")

    @patch("xrpld_lab.cli.stop_standalone")
    @patch("xrpld_lab.cli.Workspace")
    def test_down_standalone_dispatches(self, mock_ws_cls, mock_run):
        mock_ws = MagicMock()
        mock_ws_cls.return_value = mock_ws

        with patch("sys.argv", ["xrpld-lab", "down:standalone",
                                  "--name", "my-standalone"]):
            main()

        mock_run.assert_called_once_with(mock_ws, "my-standalone", "xrpl", None)

    @patch("xrpld_lab.cli.stop_standalone")
    @patch("xrpld_lab.cli.Workspace")
    def test_down_standalone_with_version(self, mock_ws_cls, mock_run):
        mock_ws = MagicMock()
        mock_ws_cls.return_value = mock_ws

        with patch("sys.argv", ["xrpld-lab", "down:standalone",
                                  "--protocol", "xrpl", "--version", "3.1.1"]):
            main()

        mock_run.assert_called_once_with(mock_ws, None, "xrpl", "3.1.1")

    @patch("xrpld_lab.cli.start_local")
    @patch("xrpld_lab.cli.Workspace")
    def test_up_local_dispatches(self, mock_ws_cls, mock_run):
        with patch("sys.argv", ["xrpld-lab", "up:local"]):
            main()

        mock_run.assert_called_once()

    @patch("xrpld_lab.cli.stop_local")
    @patch("xrpld_lab.cli.Workspace")
    def test_down_local_dispatches(self, mock_ws_cls, mock_run):
        with patch("sys.argv", ["xrpld-lab", "down:local"]):
            main()

        mock_run.assert_called_once()

    @patch("xrpld_lab.cli.update_node_binary")
    @patch("xrpld_lab.cli.Workspace")
    def test_update_node_dispatches(self, mock_ws_cls, mock_run):
        mock_ws = MagicMock()
        mock_ws_cls.return_value = mock_ws

        with patch("sys.argv", ["xrpld-lab", "update:node",
                                  "--name", "my-net",
                                  "--node_id", "2",
                                  "--node_type", "validator",
                                  "--build_server", "https://build.example.com",
                                  "--build_version", "2.0.0"]):
            main()

        mock_run.assert_called_once_with(
            mock_ws, "my-net", 2, "validator",
            "https://build.example.com", "2.0.0",
        )

    @patch("xrpld_lab.cli.enable_amendment")
    @patch("xrpld_lab.cli.Workspace")
    def test_enable_amendment_dispatches(self, mock_ws_cls, mock_run):
        mock_ws = MagicMock()
        mock_ws_cls.return_value = mock_ws

        with patch("sys.argv", ["xrpld-lab", "enable:amendment",
                                  "--name", "my-net",
                                  "--amendment_name", "fixNFTokenRemint",
                                  "--node_id", "1",
                                  "--node_type", "validator"]):
            main()

        mock_run.assert_called_once_with(
            "my-net", "fixNFTokenRemint", 1, "validator", mock_ws,
        )

    @patch("xrpld_lab.cli.view_local_logs")
    @patch("xrpld_lab.cli.Workspace")
    def test_logs_local_dispatches(self, mock_ws_cls, mock_run):
        with patch("sys.argv", ["xrpld-lab", "logs:local", "--node", "vnode1"]):
            main()

        mock_run.assert_called_once_with("vnode1")

    @patch("xrpld_lab.cli.view_local_logs")
    @patch("xrpld_lab.cli.Workspace")
    def test_logs_local_no_node(self, mock_ws_cls, mock_run):
        with patch("sys.argv", ["xrpld-lab", "logs:local"]):
            main()

        mock_run.assert_called_once_with(None)

    @patch("xrpld_lab.cli.view_standalone_logs")
    @patch("xrpld_lab.cli.Workspace")
    def test_logs_standalone_dispatches(self, mock_ws_cls, mock_run):
        with patch("sys.argv", ["xrpld-lab", "logs:standalone"]):
            main()

        mock_run.assert_called_once_with("xrpl")

    @patch("xrpld_lab.cli.view_standalone_logs")
    @patch("xrpld_lab.cli.Workspace")
    def test_logs_standalone_with_protocol(self, mock_ws_cls, mock_run):
        with patch("sys.argv", ["xrpld-lab", "logs:standalone",
                                  "--protocol", "xrpl"]):
            main()

        mock_run.assert_called_once_with("xrpl")

    @patch("xrpld_lab.cli.LabRunner")
    @patch("xrpld_lab.cli.build_lab_config")
    def test_create_ansible_calls_runner(self, mock_build, mock_runner_cls):
        mock_config = MagicMock()
        mock_build.return_value = mock_config
        mock_runner = MagicMock()
        mock_runner_cls.return_value = mock_runner

        with patch("sys.argv", ["xrpld-lab", "create:ansible",
                                  "--vips", "10.0.0.1",
                                  "--pips", "10.0.0.2"]):
            main()

        mock_build.assert_called_once()
        mock_runner_cls.assert_called_once_with(mock_config)
        mock_runner.run.assert_called_once()

    @patch("xrpld_lab.cli._deploy_ansible")
    @patch("xrpld_lab.cli.Workspace")
    def test_deploy_ansible_dispatches(self, mock_ws_cls, mock_deploy):
        mock_ws = MagicMock()
        mock_ws_cls.return_value = mock_ws

        with patch("sys.argv", ["xrpld-lab", "deploy:ansible",
                                  "--name", "my-cluster"]):
            main()

        mock_deploy.assert_called_once_with(mock_ws, "my-cluster")
