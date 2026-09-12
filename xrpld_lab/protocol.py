from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from xrpld_lab.models import Protocol


@dataclass(frozen=True)
class ProtocolSpec:
    """Immutable, protocol-specific constants and defaults.

    All protocol-divergent values live here so the rest of the codebase
    can be protocol-agnostic.
    """

    name: str
    daemon_name: str
    config_filename: str
    github_owner: str
    github_repo: str
    feature_paths: List[str]  # ordered: try first, then fallback
    config_paths: List[str]  # ordered: try first, then fallback (INI config)
    entrypoint_file: str
    network_entrypoint_file: str
    amendment_majority_time: str
    default_build_server: str
    default_build_version: str
    default_network_id: int
    default_standalone_network_id: int
    default_vl_key: str
    default_import_vl_key: Optional[str]


# ---------------------------------------------------------------------------
# Concrete specs — values extracted from the existing codebase
# ---------------------------------------------------------------------------

XRPL = ProtocolSpec(
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
    default_build_version="3.2.0-rc2",
    # 1025 is the lowest id that still requires the NetworkID field (<=1024 omits it,
    # losing cross-chain replay protection). Generic on purpose — every real network
    # must pass --network_id. Was 21337, which is Xahau Mainnet's id.
    default_network_id=1025,
    default_standalone_network_id=1,
    default_vl_key=(
        "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501"
    ),
    default_import_vl_key=None,
)

XAHAU = ProtocolSpec(
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
    default_vl_key=(
        "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501"
    ),
    default_import_vl_key=(
        "ED74D4036C6591A4BDF9C54CEFA39B996A5DCE5F86D11FDA1874481CE9D5A1CDC1"
    ),
)

_SPECS = {
    Protocol.XRPL: XRPL,
    Protocol.XAHAU: XAHAU,
}


def get_spec(protocol: Protocol) -> ProtocolSpec:
    """Look up the ``ProtocolSpec`` for a given protocol enum value."""
    try:
        return _SPECS[protocol]
    except KeyError:
        raise ValueError(f"No protocol spec for {protocol!r}")
