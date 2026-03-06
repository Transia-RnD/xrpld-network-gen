#!/usr/bin/env python
# coding: utf-8

import pytest
import requests
from unittest.mock import Mock, patch
from xrpld_netgen.libs.github import (
    get_commit_hash_from_server_version,
    download_file_at_commit_or_tag,
)


class TestGetCommitHashFromServerVersion:
    """Test extracting commit hash from server release info"""

    @patch("xrpld_netgen.libs.github.requests.get")
    def test_get_commit_hash_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "commit abc123def456\nother info"
        mock_get.return_value = mock_response

        result = get_commit_hash_from_server_version(
            "https://build.xahau.tech", "2025.1.1-release+1000"
        )

        assert result == "abc123def456"
        mock_get.assert_called_once_with(
            "https://build.xahau.tech/2025.1.1-release+1000.releaseinfo"
        )

    @patch("xrpld_netgen.libs.github.requests.get")
    def test_get_commit_hash_not_found(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        # Use text that doesn't match the "commit <word>" pattern
        mock_response.text = "release info without the expected pattern"
        mock_get.return_value = mock_response

        # The ValueError is raised when regex doesn't match
        with pytest.raises(ValueError, match="Commit hash not found"):
            result = get_commit_hash_from_server_version(
                "https://build.xahau.tech", "2025.1.1-release+1000"
            )

    @patch("xrpld_netgen.libs.github.requests.get")
    def test_get_commit_hash_http_error(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        with pytest.raises(requests.HTTPError):
            get_commit_hash_from_server_version(
                "https://build.xahau.tech", "invalid-version"
            )

    @patch("xrpld_netgen.libs.github.requests.get")
    def test_get_commit_hash_long_hash(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "commit 1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t"
        mock_get.return_value = mock_response

        result = get_commit_hash_from_server_version(
            "https://build.xahau.tech", "2025.1.1-release+1000"
        )

        assert result == "1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t"


class TestDownloadFileAtCommitOrTag:
    """Test downloading files from GitHub at specific commits"""

    @patch("xrpld_netgen.libs.github.requests.get")
    def test_download_file_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"file content here"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = download_file_at_commit_or_tag(
            "XRPLF", "xrpld", "abc123", "src/file.cpp"
        )

        assert result == b"file content here"
        mock_get.assert_called_once_with(
            "https://raw.githubusercontent.com/XRPLF/xrpld/abc123/src/file.cpp"
        )

    @patch("xrpld_netgen.libs.github.requests.get")
    def test_download_file_http_error(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        with pytest.raises(requests.HTTPError):
            download_file_at_commit_or_tag(
                "XRPLF", "xrpld", "invalid-commit", "src/file.cpp"
            )

    @patch("xrpld_netgen.libs.github.requests.get")
    def test_download_file_with_tag(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"tagged content"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = download_file_at_commit_or_tag(
            "Xahau", "xahaud", "v2.0.0", "src/feature.cpp"
        )

        assert result == b"tagged content"
        mock_get.assert_called_once_with(
            "https://raw.githubusercontent.com/Xahau/xahaud/v2.0.0/src/feature.cpp"
        )

    @patch("xrpld_netgen.libs.github.requests.get")
    def test_download_file_different_owner_repo(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"content"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        download_file_at_commit_or_tag(
            "CustomOwner", "custom-repo", "main", "path/to/file.txt"
        )

        mock_get.assert_called_once_with(
            "https://raw.githubusercontent.com/CustomOwner/custom-repo/main/path/to/file.txt"
        )
