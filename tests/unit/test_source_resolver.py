#!/usr/bin/env python
# coding: utf-8

import os
import pytest
import requests
from unittest.mock import Mock, patch, call

from xrpld_lab.source_resolver import SourceResolver
from xrpld_lab.models import BuildSource, Protocol, BuildType
from xrpld_lab.protocol import ProtocolSpec


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


class TestGetCommitHash:
    """Test extracting commit hash from server release info."""

    @patch("xrpld_lab.source_resolver.requests.get")
    def test_success(self, mock_get, resolver):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "commit abc123def456\nother info"
        mock_get.return_value = mock_response

        result = resolver.get_commit_hash(
            "https://build.xahau.tech", "2025.1.1-release+1000"
        )

        assert result == "abc123def456"
        mock_get.assert_called_once_with(
            "https://build.xahau.tech/2025.1.1-release+1000.releaseinfo",
            timeout=30,
        )

    @patch("xrpld_lab.source_resolver.requests.get")
    def test_no_match_raises_value_error(self, mock_get, resolver):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "release info without the expected pattern"
        mock_get.return_value = mock_response

        with pytest.raises(ValueError, match="Commit hash not found"):
            resolver.get_commit_hash(
                "https://build.xahau.tech", "2025.1.1-release+1000"
            )

    @patch("xrpld_lab.source_resolver.requests.get")
    def test_http_error_raises(self, mock_get, resolver):
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            "404 Not Found"
        )
        mock_get.return_value = mock_response

        with pytest.raises(requests.HTTPError):
            resolver.get_commit_hash(
                "https://build.xahau.tech", "invalid-version"
            )

    @patch("xrpld_lab.source_resolver.requests.get")
    def test_long_hash(self, mock_get, resolver):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = (
            "commit 1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b"
        )
        mock_get.return_value = mock_response

        result = resolver.get_commit_hash(
            "https://build.xahau.tech", "2025.1.1-release+1000"
        )

        assert result == "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b"


class TestDownloadFileAtCommit:
    """Test downloading files from GitHub at specific commits."""

    @patch("xrpld_lab.source_resolver.requests.get")
    def test_success(self, mock_get, resolver):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"file content here"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = resolver.download_file_at_commit(
            "XRPLF", "rippled", "abc123", "src/file.cpp"
        )

        assert result == b"file content here"
        mock_get.assert_called_once_with(
            "https://raw.githubusercontent.com/XRPLF/rippled/abc123/src/file.cpp",
            timeout=30,
        )

    @patch("xrpld_lab.source_resolver.requests.get")
    def test_http_error_raises(self, mock_get, resolver):
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            "500 Server Error"
        )
        mock_get.return_value = mock_response

        with pytest.raises(requests.HTTPError):
            resolver.download_file_at_commit(
                "XRPLF", "rippled", "abc123", "src/file.cpp"
            )

    @patch("xrpld_lab.source_resolver.requests.get")
    def test_fallback_on_404(self, mock_get, resolver):
        # First call returns 404, second call succeeds
        mock_404 = Mock()
        mock_404.status_code = 404

        mock_ok = Mock()
        mock_ok.status_code = 200
        mock_ok.content = b"fallback content"
        mock_ok.raise_for_status = Mock()

        mock_get.side_effect = [mock_404, mock_ok]

        result = resolver.download_file_at_commit(
            "XRPLF",
            "rippled",
            "abc123",
            "src/primary.cpp",
            fallback_path="src/fallback.cpp",
        )

        assert result == b"fallback content"
        assert mock_get.call_count == 2
        mock_get.assert_any_call(
            "https://raw.githubusercontent.com/XRPLF/rippled/abc123/src/primary.cpp",
            timeout=30,
        )
        mock_get.assert_any_call(
            "https://raw.githubusercontent.com/XRPLF/rippled/abc123/src/fallback.cpp",
            timeout=30,
        )

    @patch("xrpld_lab.source_resolver.requests.get")
    def test_404_without_fallback_raises(self, mock_get, resolver):
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            "404 Not Found"
        )
        mock_get.return_value = mock_response

        with pytest.raises(requests.HTTPError):
            resolver.download_file_at_commit(
                "XRPLF", "rippled", "abc123", "src/file.cpp"
            )

    @patch("xrpld_lab.source_resolver.requests.get")
    def test_different_owner_repo(self, mock_get, resolver):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"content"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        resolver.download_file_at_commit(
            "CustomOwner", "custom-repo", "main", "path/to/file.txt"
        )

        mock_get.assert_called_once_with(
            "https://raw.githubusercontent.com/CustomOwner/custom-repo/main/path/to/file.txt",
            timeout=30,
        )

    @patch("xrpld_lab.source_resolver.requests.get")
    def test_timeout_is_passed(self, mock_get, resolver):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"content"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        resolver.download_file_at_commit(
            "XRPLF", "rippled", "abc123", "src/file.cpp"
        )

        # Verify timeout=30 was passed
        _, kwargs = mock_get.call_args
        assert kwargs["timeout"] == 30


class TestDownloadBinary:
    """Test binary file downloading."""

    def test_file_already_exists_skips_download(self, tmp_path, resolver):
        save_path = str(tmp_path / "xrpld")
        # Create existing file
        with open(save_path, "w") as f:
            f.write("existing binary")

        with patch("xrpld_lab.source_resolver.requests.get") as mock_get:
            resolver.download_binary("https://example.com/xrpld", save_path)
            mock_get.assert_not_called()

        # Verify chmod was applied
        assert os.access(save_path, os.X_OK)

    def test_new_download_streams_to_file(self, tmp_path, resolver):
        save_path = str(tmp_path / "xrpld")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.iter_content.return_value = [b"chunk1", b"chunk2", b"chunk3"]

        with patch("xrpld_lab.source_resolver.requests.get", return_value=mock_response) as mock_get:
            resolver.download_binary("https://example.com/xrpld", save_path)
            mock_get.assert_called_once_with(
                "https://example.com/xrpld", stream=True, timeout=60
            )

        # Verify file contents
        with open(save_path, "rb") as f:
            assert f.read() == b"chunk1chunk2chunk3"

        # Verify executable permission
        assert os.access(save_path, os.X_OK)

    def test_http_error_raises_value_error(self, tmp_path, resolver):
        save_path = str(tmp_path / "xrpld")

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.RequestException(
            "Connection failed"
        )

        with patch("xrpld_lab.source_resolver.requests.get", return_value=mock_response):
            with pytest.raises(ValueError, match="An error occurred"):
                resolver.download_binary("https://example.com/xrpld", save_path)


class TestResolveFeatures:
    """Test feature resolution from build source."""

    @patch.object(SourceResolver, "download_file_at_commit")
    @patch.object(SourceResolver, "get_commit_hash")
    def test_success(self, mock_hash, mock_download, resolver, xahau_spec):
        mock_hash.return_value = "abc123"
        mock_download.return_value = b"feature content lines"

        source = BuildSource(
            protocol=Protocol.XAHAU,
            build_type=BuildType.BINARY,
            build_server="https://build.xahau.tech",
            build_version="2025.7.9-release+1951",
            owner="Xahau",
            repo="xahaud",
        )

        result = resolver.resolve_features(source, xahau_spec)

        mock_hash.assert_called_once_with(
            "https://build.xahau.tech", "2025.7.9-release+1951"
        )
        mock_download.assert_called_once_with(
            "Xahau",
            "xahaud",
            "abc123",
            "src/ripple/protocol/impl/Feature.cpp",
            fallback_path="include/xrpl/protocol/detail/features.macro",
        )
        assert result == b"feature content lines"

    @patch.object(SourceResolver, "download_file_at_commit")
    @patch.object(SourceResolver, "get_commit_hash")
    def test_uses_spec_feature_paths(self, mock_hash, mock_download, resolver, xrpl_spec):
        mock_hash.return_value = "def456"
        mock_download.return_value = b"xrpl features"

        source = BuildSource(
            protocol=Protocol.XRPL,
            build_type=BuildType.BINARY,
            build_server="https://rippleci.example.com",
            build_version="3.1.1",
            owner="XRPLF",
            repo="rippled",
        )

        result = resolver.resolve_features(source, xrpl_spec)

        mock_hash.assert_called_once_with(
            "https://rippleci.example.com", "3.1.1"
        )
        # Should use xrpl_spec.feature_paths[0] as primary, [1] as fallback
        mock_download.assert_called_once_with(
            "XRPLF",
            "rippled",
            "def456",
            "include/xrpl/protocol/detail/features.macro",
            fallback_path="src/libxrpl/protocol/Feature.cpp",
        )
        assert result == b"xrpl features"

    @patch.object(SourceResolver, "download_file_at_commit")
    @patch.object(SourceResolver, "get_commit_hash")
    def test_fallback_path_used_when_primary_404s(
        self, mock_hash, mock_download, resolver, xahau_spec
    ):
        """Verify that download_file_at_commit is called with fallback_path,
        so the internal fallback mechanism can kick in on 404."""
        mock_hash.return_value = "abc123"
        mock_download.return_value = b"fallback feature content"

        source = BuildSource(
            protocol=Protocol.XAHAU,
            build_type=BuildType.BINARY,
            build_server="https://build.xahau.tech",
            build_version="2025.7.9-release+1951",
            owner="Xahau",
            repo="xahaud",
        )

        result = resolver.resolve_features(source, xahau_spec)

        # The key assertion: fallback_path is passed through
        _, kwargs = mock_download.call_args
        assert kwargs["fallback_path"] == "include/xrpl/protocol/detail/features.macro"
        assert result == b"fallback feature content"

    @patch.object(SourceResolver, "download_file_at_commit")
    @patch.object(SourceResolver, "get_commit_hash")
    def test_single_feature_path_no_fallback(
        self, mock_hash, mock_download, resolver
    ):
        """When spec has only one feature path, no fallback is provided."""
        mock_hash.return_value = "abc123"
        mock_download.return_value = b"single path content"

        single_path_spec = ProtocolSpec(
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

        source = BuildSource(
            protocol=Protocol.XRPL,
            build_type=BuildType.BINARY,
            build_server="https://test.build",
            build_version="1.0.0",
            owner="TestOwner",
            repo="test-repo",
        )

        result = resolver.resolve_features(source, single_path_spec)

        mock_download.assert_called_once_with(
            "TestOwner",
            "test-repo",
            "abc123",
            "src/features.cpp",
            fallback_path=None,
        )
        assert result == b"single path content"
