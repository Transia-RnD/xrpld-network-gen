#!/usr/bin/env python
# coding: utf-8

import requests
import re


def get_commit_hash_from_server_version(server: str, version: str):
    # Send a GET request to the URL to download the file
    response = requests.get(f"{server}/{version}.releaseinfo")

    # Check if the request was successful
    if response.status_code == 200:
        # Read the contents of the file
        release_info = response.text

        # Use a regular expression to find the commit hash
        match = re.search(r"commit (\w+)", release_info)

        # If a match is found, return the commit hash
        if match:
            return match.group(1)
        else:
            raise ValueError("Commit hash not found in the release info.")
    else:
        # If the request was not successful, raise an HTTPError
        response.raise_for_status()


def download_file_at_commit(owner: str, repo: str, commit_hash: str, file_path: str):
    """
    Download a specific file from a GitHub repository at a given commit hash.

    :param owner: The owner of the repository (username or organization)
    :param repo: The name of the repository
    :param commit_hash: The commit hash
    :param file_path: The path to the file in the repository
    :return: The content of the file
    """
    # Construct the raw content URL
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{commit_hash}/{file_path}"

    # Send a GET request to the URL
    response = requests.get(url)
    response.raise_for_status()  # Raise an exception for HTTP error responses

    # Return the content of the file
    return response.content
