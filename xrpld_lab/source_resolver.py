"""Resolves build sources: downloads features from GitHub, handles binary downloads."""

from __future__ import annotations

import os
import re

import requests

from xrpld_lab.config import parse_xrpld_cfg
from xrpld_lab.models import BuildSource
from xrpld_lab.protocol import ProtocolSpec


class SourceResolver:
    """Resolves build sources: downloads features from GitHub, handles binary downloads."""

    def get_commit_hash(self, server: str, version: str) -> str:
        """Download release info from build server and extract commit hash.

        Fetches {server}/{version}.releaseinfo, parses "commit <hash>" line.

        :param server: The base URL of the build server
        :param version: The build version string
        :return: The commit hash
        :raises ValueError: If commit hash is not found in the release info
        :raises requests.HTTPError: If the HTTP request fails
        """
        response = requests.get(
            f"{server}/{version}.releaseinfo", timeout=30
        )

        if response.status_code == 200:
            match = re.search(r"commit (\w+)", response.text)
            if match:
                return match.group(1)
            else:
                raise ValueError("Commit hash not found in the release info.")
        else:
            response.raise_for_status()

    def download_file_at_commit(
        self,
        owner: str,
        repo: str,
        commit_or_tag: str,
        file_path: str,
        fallback_path: str = None,
    ) -> bytes:
        """Download a file from GitHub at a specific commit/tag.

        URL: https://raw.githubusercontent.com/{owner}/{repo}/{commit_or_tag}/{file_path}
        If 404 and fallback_path given, retry with fallback.

        :param owner: The repository owner (username or organization)
        :param repo: The repository name
        :param commit_or_tag: The commit hash or version tag
        :param file_path: The path to the file in the repository
        :param fallback_path: Optional fallback file path if primary returns 404
        :return: The content of the file as bytes
        :raises requests.HTTPError: If the HTTP request fails
        """
        url = (
            f"https://raw.githubusercontent.com/"
            f"{owner}/{repo}/{commit_or_tag}/{file_path}"
        )

        response = requests.get(url, timeout=30)

        if response.status_code == 404 and fallback_path:
            return self.download_file_at_commit(
                owner, repo, commit_or_tag, fallback_path
            )

        response.raise_for_status()
        return response.content

    def download_binary(self, url: str, save_path: str) -> None:
        """Download a binary file from URL to save_path.

        If file already exists, just chmod 755 and return.
        Streams download in 8192-byte chunks.
        Sets chmod 755 after download.

        :param url: The URL to download from
        :param save_path: Local file path to save the binary
        :raises ValueError: If an error occurs during download
        """
        if os.path.exists(save_path):
            os.chmod(save_path, 0o755)
            return

        try:
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()

            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            os.chmod(save_path, 0o755)
        except requests.exceptions.RequestException as e:
            raise ValueError(f"An error occurred: {e}")

    def resolve_features(
        self, source: BuildSource, spec: ProtocolSpec
    ) -> bytes:
        """Resolve feature content from the build source.

        Uses spec.feature_paths (ordered list) to try downloading feature files
        from the GitHub repo at the resolved commit. Returns the raw bytes content.

        If ``source.commit_hash`` is already set (e.g. GitHub-URL mode), uses it
        directly.  Otherwise resolves from the build server's ``.releaseinfo``.

        :param source: The build source configuration
        :param spec: The protocol specification with feature paths
        :return: The raw feature file content as bytes
        """
        commit_hash = (
            source.commit_hash
            or self.get_commit_hash(source.build_server, source.build_version)
        )

        primary_path = spec.feature_paths[0]
        fallback_path = (
            spec.feature_paths[1] if len(spec.feature_paths) > 1 else None
        )

        return self.download_file_at_commit(
            source.owner,
            source.repo,
            commit_hash,
            primary_path,
            fallback_path=fallback_path,
        )

    def resolve_repo_config(
        self, source: BuildSource, spec: ProtocolSpec
    ) -> dict:
        """Download and parse xrpld config from the repo at the resolved commit.

        Tries known config paths from ``spec.config_paths`` (ordered: primary,
        then fallback). Returns parsed config dict or empty dict if not found.

        :param source: The build source configuration
        :param spec: The protocol specification with config paths
        :return: Parsed config dict, or ``{}`` on failure
        """
        if not spec.config_paths:
            return {}

        try:
            commit_hash = (
                source.commit_hash
                or self.get_commit_hash(
                    source.build_server, source.build_version
                )
            )

            primary_path = spec.config_paths[0]
            fallback_path = (
                spec.config_paths[1] if len(spec.config_paths) > 1 else None
            )

            content = self.download_file_at_commit(
                source.owner,
                source.repo,
                commit_hash,
                primary_path,
                fallback_path=fallback_path,
            )

            return parse_xrpld_cfg(content.decode("utf-8", errors="replace"))
        except (requests.HTTPError, requests.RequestException, ValueError):
            return {}
