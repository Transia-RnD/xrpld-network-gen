from __future__ import annotations

from dataclasses import dataclass
from typing import List

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
    default_build_version="3.3.0",
    # 1025 is the lowest id that still requires the NetworkID field (<=1024 omits it,
    # losing cross-chain replay protection). Generic on purpose — every real network
    # must pass --network_id.
    default_network_id=1025,
    default_standalone_network_id=1,
    default_vl_key=(
        "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501"
    ),
)

_SPECS = {
    Protocol.XRPL: XRPL,
}


def get_spec(protocol: Protocol) -> ProtocolSpec:
    """Look up the ``ProtocolSpec`` for a given protocol enum value."""
    try:
        return _SPECS[protocol]
    except KeyError:
        raise ValueError(f"No protocol spec for {protocol!r}")
