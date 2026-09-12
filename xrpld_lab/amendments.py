"""Amendment parsing and genesis-file helpers.

Parses C++ feature macro lines (XRPL_FEATURE, XRPL_FIX, REGISTER_FEATURE,
REGISTER_FIX) to extract amendment names and their SHA-512-half hashes,
then optionally writes them into a genesis JSON ledger.
"""

import hashlib
import os
import re
from typing import Dict, List

from xrpld_lab.utils import read_json

_PACKAGE_DIR = os.path.abspath(os.path.dirname(__file__))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _amendment_name_hash(name: str) -> str:
    """SHA-512 half of a UTF-8 amendment name (first 64 hex chars, uppercase)."""
    return hashlib.sha512(name.encode("utf-8")).digest().hex().upper()[:64]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_supported(value: str) -> bool:
    """Parse C++ Supported/DefaultVote value.  ``'no'`` -> False, else True."""
    return value.lower() != "no"


def get_feature_lines_from_path(path: str) -> list[str]:
    """Read a C++ feature file and return its lines."""
    with open(path, "r") as f:
        return f.readlines()


def get_feature_lines_from_content(content: bytes) -> list[str]:
    """Decode *bytes* content and split into lines."""
    return content.decode("utf-8").splitlines()


def parse_amendments(lines: list, include_unsupported: bool = False) -> Dict[str, str]:
    """Parse C++ macro lines into ``{amendment_name: sha512_half_hash}``.

    Handles four macro styles:

    * ``XRPL_FEATURE(Name, ...)``
    * ``XRPL_FIX(Name, ...)`` -- prepends ``"fix"`` to the name
    * ``REGISTER_FEATURE(Name, ...)``
    * ``REGISTER_FIX(Name, ...)``

    By default only amendments marked ``Supported::yes`` (or any value other
    than ``no``) are included.  Pass ``include_unsupported=True`` to include
    every amendment regardless of its ``Supported`` flag -- the amendment
    name -> hash mapping is identical either way, only the flag differs. This
    is used to pre-enable all amendments in a test genesis; the running binary
    must itself support them (built ``Supported::Yes``) or it amendment-blocks.
    The hash is the first 64 hex characters of the SHA-512 digest of the UTF-8
    encoded amendment name.
    """
    amendments: Dict[str, dict] = {}

    for line in lines:
        amendment_name: str = ""

        if re.match(r"XRPL_FIX", line):
            m = re.search(r"XRPL_FIX\)?.*?\((.*?),", line)
            if not m:
                continue
            amendment_name = f"fix{m.group(1)}"
        elif re.match(r"XRPL_FEATURE", line):
            m = re.search(r"XRPL_FEATURE\((.*?),", line)
            if not m:
                continue
            amendment_name = m.group(1)
        elif re.match(r"REGISTER_FIX", line):
            m = re.search(r"REGISTER_FIX\)?.*?\((.*?),", line)
            if not m:
                continue
            amendment_name = m.group(1)
        elif re.match(r"REGISTER_FEATURE", line):
            m = re.search(r"REGISTER_FEATURE\((.*?),", line)
            if not m:
                continue
            amendment_name = m.group(1)
        else:
            continue

        supported_match = re.findall(r"Supported::(yes|no)", line, re.IGNORECASE)
        default_vote_match = re.findall(
            r"(?:DefaultVote|VoteBehavior::Default)(yes|no)", line, re.IGNORECASE
        )

        amendments[amendment_name] = {
            "supported": parse_supported(
                supported_match[0] if supported_match else "no"
            ),
            "default_vote": parse_supported(
                default_vote_match[0] if default_vote_match else "no"
            ),
        }

    return {
        k: _amendment_name_hash(k)
        for k, v in amendments.items()
        if include_unsupported or v["supported"] is True
    }


def convert_to_list_of_hashes(features: Dict[str, str]) -> List[str]:
    """Return a flat list of hash strings from *features*."""
    return list(features.values())


def update_genesis(
    features: Dict[str, str],
    protocol_name: str,
    genesis_path: str = None,
    preload_entries: List[dict] = None,
) -> dict:
    """Update a genesis JSON file with amendment hashes.

    Parameters
    ----------
    features:
        ``{name: hash}`` mapping produced by :func:`parse_amendments`.
    protocol_name:
        ``"xrpl"`` or ``"xahau"``.
    genesis_path:
        Explicit path to a genesis JSON file.  When *None* the default
        package location ``xrpld_lab/genesis.<protocol>.json`` is used.

    Returns
    -------
    dict
        The full genesis dict with the ``Amendments`` list replaced.
    """
    if genesis_path is None:
        genesis_path = os.path.join(_PACKAGE_DIR, f"genesis.{protocol_name}.json")

    json_dict = read_json(genesis_path)
    new_amendments: List[str] = convert_to_list_of_hashes(features)

    if not new_amendments:
        raise RuntimeError(
            f"No features found for {protocol_name}. "
            "Cannot generate genesis without amendments."
        )

    for entry in json_dict["ledger"]["accountState"]:
        if entry.get("LedgerEntryType") == "Amendments":
            entry["Amendments"] = new_amendments
            break
    else:
        raise RuntimeError("Amendments entry not found in genesis template.")

    if preload_entries:
        from xrpld_lab.ledger_generator import merge_into_genesis

        merge_into_genesis(json_dict, preload_entries)

    return json_dict
