"""Config parsing and merging for xrpld/xahaud configuration files.

Reads INI-style .cfg files from the repo, parses them into structured dicts,
and merges them with hardcoded defaults and local YAML/JSON overrides.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict

import yaml


def parse_xrpld_cfg(content: str) -> Dict[str, Any]:
    """Parse INI-style xrpld.cfg content into a structured dict.

    Sections become keys. Sections can contain:
    - A single value: section_name -> "value"
    - Key-value pairs (with = or space =): section_name -> {key: value}
    - Multiple lines (IP addresses, etc.): section_name -> [line1, line2, ...]

    Lines starting with # are comments and ignored.
    Empty lines separate sections.
    """
    result: Dict[str, Any] = {}
    current_section: str | None = None
    section_lines: list[str] = []

    def _flush_section():
        nonlocal current_section, section_lines
        if current_section is None:
            return

        # Filter out empty lines
        lines = [line for line in section_lines if line.strip()]

        if not lines:
            # Empty section, skip
            current_section = None
            section_lines = []
            return

        # Check if any line contains '='
        has_kv = any("=" in line for line in lines)

        if has_kv:
            # Key-value pairs -> dict
            d: Dict[str, str] = {}
            for line in lines:
                if "=" in line:
                    key, _, value = line.partition("=")
                    d[key.strip()] = value.strip()
                # Lines without = in a kv section are ignored
            result[current_section] = d
        elif len(lines) == 1:
            # Single value -> string
            result[current_section] = lines[0].strip()
        else:
            # Multiple lines -> list
            result[current_section] = [line.strip() for line in lines]

        current_section = None
        section_lines = []

    for raw_line in content.splitlines():
        line = raw_line.strip()

        # Skip comments
        if line.startswith("#"):
            continue

        # Check for section header
        section_match = re.match(r"^\[([^\]]+)\]$", line)
        if section_match:
            _flush_section()
            current_section = section_match.group(1)
            section_lines = []
            continue

        # Accumulate lines within a section
        if current_section is not None:
            section_lines.append(line)

    # Flush the last section
    _flush_section()

    return result


def load_overrides_file(path: str) -> Dict[str, Any]:
    """Load config overrides from a YAML or JSON file.

    Returns empty dict if file doesn't exist or is empty.
    Supports .yaml, .yml, and .json extensions.
    """
    if not os.path.exists(path):
        return {}

    with open(path, "r") as f:
        content = f.read()

    if not content.strip():
        return {}

    if path.endswith(".json"):
        return json.loads(content)

    # Default: treat as YAML (.yaml, .yml, or anything else)
    result = yaml.safe_load(content)
    return result if result is not None else {}


def merge_config(
    hardcoded: Dict[str, Any],
    repo: Dict[str, Any],
    overrides: Dict[str, Any],
) -> Dict[str, Any]:
    """Merge config layers: hardcoded defaults -> repo config -> local overrides.

    Later layers override earlier ones. Nested dicts are deep-merged.
    """
    result = _deep_merge(hardcoded, repo)
    result = _deep_merge(result, overrides)
    return result


def _deep_merge(base: dict, overlay: dict) -> dict:
    """Deep merge overlay into base. Overlay values win."""
    result = base.copy()
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_ansible_config(path: str) -> Dict[str, Any]:
    """Load ansible deployment config from a YAML file.

    Expected structure::

        ssh_port: 20
        ssh_user: ubuntu
        ssh_key_path: ~/.ssh/id_rsa
        vips:
          - 10.0.0.1
          - 10.0.0.2
        pips:
          - 10.0.0.3
        services:
          - ip: 10.0.0.4
            name: infra
            nginx:
              domain: example.com
              ...
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Ansible config not found: {path}")

    with open(path, "r") as f:
        data = yaml.safe_load(f)

    if not data or not isinstance(data, dict):
        raise ValueError(f"Invalid ansible config: {path}")

    return data
