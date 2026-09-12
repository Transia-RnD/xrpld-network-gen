#!/usr/bin/env python
# coding: utf-8

"""Tests for xrpld_lab.config -- INI-style config parsing and merging."""

import json
import os

import pytest
import yaml
from unittest.mock import patch, Mock

import requests

from xrpld_lab.config import (
    parse_xrpld_cfg,
    load_overrides_file,
    merge_config,
    _deep_merge,
)
from xrpld_lab.source_resolver import SourceResolver
from xrpld_lab.models import BuildSource, Protocol, BuildType
from xrpld_lab.protocol import ProtocolSpec


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def resolver():
    return SourceResolver()


@pytest.fixture
def xahau_spec():
    return ProtocolSpec(
        name="xahau",
        daemon_name="xahaud",
        config_filename="xahaud.cfg",
        github_owner="Xahau",
        github_repo="xahaud",
        feature_paths=[
            "src/ripple/protocol/impl/Feature.cpp",
            "include/xrpl/protocol/detail/features.macro",
        ],
        config_paths=[
            "cfg/xahaud-example.cfg",
            "cfg/rippled-example.cfg",
        ],
        entrypoint_file="xahau.entrypoint",
        network_entrypoint_file="network.entrypoint",
        amendment_majority_time="5 minutes",
        default_build_server="https://build.xahau.tech",
        default_build_version="2025.7.9-release+1951",
        default_network_id=21339,
        default_standalone_network_id=21339,
        default_vl_key="ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501",
        default_import_vl_key="ED74D4036C6591A4BDF9C54CEFA39B996A5DCE5F86D11FDA1874481CE9D5A1CDC1",
    )


@pytest.fixture
def xrpl_spec():
    return ProtocolSpec(
        name="xrpl",
        daemon_name="xrpld",
        config_filename="xrpld.cfg",
        github_owner="XRPLF",
        github_repo="rippled",
        feature_paths=[
            "include/xrpl/protocol/detail/features.macro",
            "src/libxrpl/protocol/Feature.cpp",
        ],
        config_paths=[
            "cfg/rippled-example.cfg",
            "cfg/xrpld-example.cfg",
        ],
        entrypoint_file="xrpl.entrypoint",
        network_entrypoint_file="network.entrypoint",
        amendment_majority_time="15 minutes",
        default_build_server="rippleci",
        default_build_version="3.1.1",
        default_network_id=21337,
        default_standalone_network_id=1,
        default_vl_key="ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501",
        default_import_vl_key=None,
    )


@pytest.fixture
def xahau_source():
    return BuildSource(
        protocol=Protocol.XAHAU,
        build_type=BuildType.BINARY,
        build_server="https://build.xahau.tech",
        build_version="2025.7.9-release+1951",
        owner="Xahau",
        repo="xahaud",
    )


# ===========================================================================
# parse_xrpld_cfg
# ===========================================================================


class TestParseXrpldCfg:
    """Parse INI-style xrpld.cfg content into a structured dict."""

    def test_simple_section_single_value(self):
        content = "[node_size]\nhuge\n"
        result = parse_xrpld_cfg(content)
        assert result == {"node_size": "huge"}

    def test_section_with_key_value_pairs(self):
        content = (
            "[transaction_queue]\nledgers_in_queue = 20\nminimum_queue_size = 2000\n"
        )
        result = parse_xrpld_cfg(content)
        assert result == {
            "transaction_queue": {
                "ledgers_in_queue": "20",
                "minimum_queue_size": "2000",
            }
        }

    def test_multiple_sections(self):
        content = (
            "[node_size]\nhuge\n\n"
            "[ledger_history]\nfull\n\n"
            "[transaction_queue]\nledgers_in_queue = 20\n"
        )
        result = parse_xrpld_cfg(content)
        assert result["node_size"] == "huge"
        assert result["ledger_history"] == "full"
        assert result["transaction_queue"] == {"ledgers_in_queue": "20"}

    def test_empty_content(self):
        result = parse_xrpld_cfg("")
        assert result == {}

    def test_comments_ignored(self):
        content = "# This is a comment\n" "[node_size]\n" "# Another comment\n" "huge\n"
        result = parse_xrpld_cfg(content)
        assert result == {"node_size": "huge"}

    def test_equals_in_value(self):
        """type=NuDB should parse as key=value."""
        content = "[node_db]\ntype=NuDB\npath=/var/lib/db\n"
        result = parse_xrpld_cfg(content)
        assert result == {
            "node_db": {
                "type": "NuDB",
                "path": "/var/lib/db",
            }
        }

    def test_key_space_equals_value(self):
        """key = value (space around =) should parse correctly."""
        content = "[voting]\naccount_reserve = 1000000\nowner_reserve = 200000\n"
        result = parse_xrpld_cfg(content)
        assert result == {
            "voting": {
                "account_reserve": "1000000",
                "owner_reserve": "200000",
            }
        }

    def test_multiline_list_section(self):
        """Section with multiple lines (no =) should produce a list."""
        content = (
            "[ips_fixed]\n192.168.1.1 51235\n192.168.1.2 51335\n192.168.1.3 51435\n"
        )
        result = parse_xrpld_cfg(content)
        assert result == {
            "ips_fixed": [
                "192.168.1.1 51235",
                "192.168.1.2 51335",
                "192.168.1.3 51435",
            ]
        }

    def test_section_with_only_whitespace_lines(self):
        """Section with only whitespace should be skipped."""
        content = "[empty_section]\n\n\n[node_size]\nhuge\n"
        result = parse_xrpld_cfg(content)
        assert result["node_size"] == "huge"

    def test_mixed_sections(self):
        """Mix of single value, kv pairs, and list in one config."""
        content = (
            "[node_size]\nhuge\n\n"
            "[node_db]\ntype=NuDB\npath=/var/lib/db\n\n"
            "[ips_fixed]\n10.0.0.1 51235\n10.0.0.2 51235\n"
        )
        result = parse_xrpld_cfg(content)
        assert result["node_size"] == "huge"
        assert result["node_db"] == {"type": "NuDB", "path": "/var/lib/db"}
        assert result["ips_fixed"] == ["10.0.0.1 51235", "10.0.0.2 51235"]


# ===========================================================================
# load_overrides_file
# ===========================================================================


class TestLoadOverridesFile:
    """Load config overrides from YAML or JSON files."""

    def test_load_yaml_file(self, tmp_path):
        path = str(tmp_path / "overrides.yaml")
        data = {"node_size": "medium", "voting": {"account_reserve": 500000}}
        with open(path, "w") as f:
            yaml.dump(data, f)
        result = load_overrides_file(path)
        assert result == data

    def test_load_json_file(self, tmp_path):
        path = str(tmp_path / "overrides.json")
        data = {"node_size": "small", "network_id": 12345}
        with open(path, "w") as f:
            json.dump(data, f)
        result = load_overrides_file(path)
        assert result == data

    def test_nonexistent_file_returns_empty(self):
        result = load_overrides_file("/tmp/does_not_exist_12345.yaml")
        assert result == {}

    def test_empty_file_returns_empty(self, tmp_path):
        path = str(tmp_path / "empty.yaml")
        with open(path, "w") as f:
            f.write("")
        result = load_overrides_file(path)
        assert result == {}

    def test_load_yml_extension(self, tmp_path):
        path = str(tmp_path / "overrides.yml")
        data = {"node_size": "tiny"}
        with open(path, "w") as f:
            yaml.dump(data, f)
        result = load_overrides_file(path)
        assert result == data


# ===========================================================================
# merge_config / _deep_merge
# ===========================================================================


class TestMergeConfig:
    """Merge config layers: hardcoded -> repo -> local overrides."""

    def test_empty_layers(self):
        result = merge_config({}, {}, {})
        assert result == {}

    def test_hardcoded_used_as_base(self):
        hardcoded = {"node_size": "huge", "log_level": "trace"}
        result = merge_config(hardcoded, {}, {})
        assert result == hardcoded

    def test_repo_overrides_hardcoded(self):
        hardcoded = {"node_size": "huge", "log_level": "trace"}
        repo = {"node_size": "medium"}
        result = merge_config(hardcoded, repo, {})
        assert result["node_size"] == "medium"
        assert result["log_level"] == "trace"

    def test_local_overrides_repo(self):
        hardcoded = {"node_size": "huge"}
        repo = {"node_size": "medium"}
        overrides = {"node_size": "small"}
        result = merge_config(hardcoded, repo, overrides)
        assert result["node_size"] == "small"

    def test_nested_deep_merge(self):
        hardcoded = {
            "voting": {"account_reserve": 1000000, "owner_reserve": 200000},
        }
        repo = {
            "voting": {"account_reserve": 500000},
        }
        result = merge_config(hardcoded, repo, {})
        assert result["voting"]["account_reserve"] == 500000
        assert result["voting"]["owner_reserve"] == 200000

    def test_new_keys_from_repo_added(self):
        hardcoded = {"node_size": "huge"}
        repo = {"ledger_history": "full"}
        result = merge_config(hardcoded, repo, {})
        assert result["node_size"] == "huge"
        assert result["ledger_history"] == "full"

    def test_full_three_layer_merge(self):
        hardcoded = {
            "node_size": "huge",
            "voting": {"account_reserve": 1000000, "owner_reserve": 200000},
        }
        repo = {
            "node_size": "medium",
            "voting": {"account_reserve": 500000},
            "ledger_history": "full",
        }
        overrides = {
            "voting": {"owner_reserve": 100000},
            "debug_logfile": "/tmp/debug.log",
        }
        result = merge_config(hardcoded, repo, overrides)
        assert result["node_size"] == "medium"
        assert result["voting"]["account_reserve"] == 500000
        assert result["voting"]["owner_reserve"] == 100000
        assert result["ledger_history"] == "full"
        assert result["debug_logfile"] == "/tmp/debug.log"


class TestDeepMerge:
    """Unit tests for the _deep_merge helper."""

    def test_overlay_wins_for_flat_keys(self):
        result = _deep_merge({"a": 1}, {"a": 2})
        assert result == {"a": 2}

    def test_nested_dicts_are_merged(self):
        base = {"d": {"x": 1, "y": 2}}
        overlay = {"d": {"y": 3, "z": 4}}
        result = _deep_merge(base, overlay)
        assert result == {"d": {"x": 1, "y": 3, "z": 4}}

    def test_base_not_mutated(self):
        base = {"a": 1}
        overlay = {"a": 2}
        _deep_merge(base, overlay)
        assert base == {"a": 1}

    def test_overlay_replaces_non_dict_with_dict(self):
        result = _deep_merge({"a": "string"}, {"a": {"nested": True}})
        assert result == {"a": {"nested": True}}


# ===========================================================================
# SourceResolver.resolve_repo_config
# ===========================================================================


class TestResolveRepoConfig:
    """Test downloading and parsing config from the repo."""

    @patch.object(SourceResolver, "download_file_at_commit")
    @patch.object(SourceResolver, "get_commit_hash")
    def test_success_downloads_and_parses(
        self, mock_hash, mock_download, resolver, xahau_spec, xahau_source
    ):
        mock_hash.return_value = "abc123"
        cfg_content = b"[node_size]\nhuge\n\n[node_db]\ntype=NuDB\n"
        mock_download.return_value = cfg_content

        result = resolver.resolve_repo_config(xahau_source, xahau_spec)

        mock_hash.assert_called_once_with(
            "https://build.xahau.tech", "2025.7.9-release+1951"
        )
        mock_download.assert_called_once_with(
            "Xahau",
            "xahaud",
            "abc123",
            "cfg/xahaud-example.cfg",
            fallback_path="cfg/rippled-example.cfg",
        )
        assert result["node_size"] == "huge"
        assert result["node_db"]["type"] == "NuDB"

    @patch.object(SourceResolver, "download_file_at_commit")
    @patch.object(SourceResolver, "get_commit_hash")
    def test_returns_empty_on_http_error(
        self, mock_hash, mock_download, resolver, xahau_spec, xahau_source
    ):
        mock_hash.return_value = "abc123"
        mock_download.side_effect = requests.HTTPError("404 Not Found")

        result = resolver.resolve_repo_config(xahau_source, xahau_spec)
        assert result == {}

    @patch.object(SourceResolver, "download_file_at_commit")
    @patch.object(SourceResolver, "get_commit_hash")
    def test_uses_fallback_paths_from_spec(
        self, mock_hash, mock_download, resolver, xrpl_spec
    ):
        mock_download.return_value = b"[node_size]\nmedium\n"

        source = BuildSource(
            protocol=Protocol.XRPL,
            build_type=BuildType.BINARY,
            build_server="rippleci",
            build_version="3.1.1",
            owner="XRPLF",
            repo="rippled",
        )

        result = resolver.resolve_repo_config(source, xrpl_spec)

        mock_hash.assert_not_called()
        mock_download.assert_called_once_with(
            "XRPLF",
            "rippled",
            "3.1.1",
            "cfg/rippled-example.cfg",
            fallback_path="cfg/xrpld-example.cfg",
        )
        assert result["node_size"] == "medium"

    @patch.object(SourceResolver, "download_file_at_commit")
    @patch.object(SourceResolver, "get_commit_hash")
    def test_no_config_paths_returns_empty(
        self, mock_hash, mock_download, resolver, xahau_source
    ):
        """When spec has no config_paths, return empty dict."""
        spec_no_config = ProtocolSpec(
            name="test",
            daemon_name="testd",
            config_filename="test.cfg",
            github_owner="TestOwner",
            github_repo="test-repo",
            feature_paths=["src/features.cpp"],
            config_paths=[],
            entrypoint_file="test.entrypoint",
            network_entrypoint_file="network.entrypoint",
            amendment_majority_time="5 minutes",
            default_build_server="https://test.build",
            default_build_version="1.0.0",
            default_network_id=1,
            default_standalone_network_id=1,
            default_vl_key="TESTKEY",
            default_import_vl_key=None,
        )

        result = resolver.resolve_repo_config(xahau_source, spec_no_config)
        assert result == {}


# ===========================================================================
# CLI --config_overrides
# ===========================================================================


class TestCliConfigOverrides:
    """Test --config_overrides argument in CLI subparsers."""

    def test_standalone_accepts_config_overrides(self):
        from xrpld_lab.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(
            ["up:standalone", "--config_overrides", "/tmp/my.yaml"]
        )
        assert args.config_overrides == "/tmp/my.yaml"

    def test_network_accepts_config_overrides(self):
        from xrpld_lab.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(
            ["create:network", "--config_overrides", "/tmp/my.json"]
        )
        assert args.config_overrides == "/tmp/my.json"

    def test_standalone_default_is_none(self):
        from xrpld_lab.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["up:standalone"])
        assert args.config_overrides is None

    def test_network_default_is_none(self):
        from xrpld_lab.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["create:network"])
        assert args.config_overrides is None

    def test_overrides_loaded_into_lab_config(self, tmp_path):
        from xrpld_lab.cli import _build_parser, build_lab_config

        overrides_path = str(tmp_path / "overrides.yaml")
        data = {"node_size": "small", "voting": {"account_reserve": 500000}}
        with open(overrides_path, "w") as f:
            yaml.dump(data, f)

        parser = _build_parser()
        args = parser.parse_args(
            [
                "up:standalone",
                "--protocol",
                "xahau",
                "--config_overrides",
                overrides_path,
            ]
        )
        cfg = build_lab_config(args)
        assert cfg.config_overrides == data

    def test_no_overrides_gives_empty_dict(self):
        from xrpld_lab.cli import _build_parser, build_lab_config

        parser = _build_parser()
        args = parser.parse_args(["up:standalone", "--protocol", "xahau"])
        cfg = build_lab_config(args)
        assert cfg.config_overrides == {}
