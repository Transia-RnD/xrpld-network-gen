#!/usr/bin/env python
# coding: utf-8

from xrpld_netgen.utils.deploy_kit import build_debugstream_service, build_stop_sh


class TestBuildDebugstreamService:
    """Test build_debugstream_service returns correct dict structure"""

    def test_default_port(self):
        result = build_debugstream_service("xahau", "xahau-net")
        assert result["container_name"] == "debugstream"
        assert result["ports"] == ["9999:9999"]
        assert result["build"] == {
            "context": "./debugstream",
            "dockerfile": "Dockerfile",
        }
        assert result["networks"] == ["xahau-net"]

    def test_custom_port(self):
        result = build_debugstream_service("xrpl", "xrpl-net", port=8888)
        assert result["ports"] == ["8888:8888"]

    def test_volume_readonly(self):
        result = build_debugstream_service("xahau", "xahau-net")
        volumes = result["volumes"]
        assert len(volumes) == 1
        assert volumes[0].endswith(":ro")

    def test_volume_uses_protocol_name(self):
        result = build_debugstream_service("xahau", "xahau-net")
        assert result["volumes"] == ["xahau-log:/opt/ripple/log:ro"]

    def test_depends_on_protocol(self):
        result = build_debugstream_service("xahau", "xahau-net")
        assert "xahau" in result["depends_on"]

    def test_depends_on_xrpl(self):
        result = build_debugstream_service("xrpl", "xrpl-net")
        assert "xrpl" in result["depends_on"]


class TestStopShStandalone:
    """Test build_stop_sh for standalone mode"""

    def test_has_volume_flag(self):
        result = build_stop_sh(
            basedir="/workspace",
            protocol="xahau",
            name="test",
            num_validators=0,
            num_peers=0,
            standalone=True,
        )
        assert "down -v" in result

    def test_no_log_rm(self):
        result = build_stop_sh(
            basedir="/workspace",
            protocol="xahau",
            name="test",
            num_validators=0,
            num_peers=0,
            standalone=True,
        )
        assert "rm -r xahau/log" not in result
