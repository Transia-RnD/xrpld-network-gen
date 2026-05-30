"""Thin CLI layer for xrpld-lab.

Parses command-line arguments, converts them into a LabConfig dataclass,
and passes the config to LabRunner.run().
"""

from __future__ import annotations

import argparse
from typing import List, Optional

from xrpld_lab.config import load_ansible_config, load_overrides_file
from xrpld_lab.models import (
    AnsibleConfig,
    BuildSource,
    BuildType,
    CompilerConfig,
    DebugConfig,
    DeployMode,
    FaucetConfig,
    GcpConfig,
    LabConfig,
    NginxConfig,
    NodeDbType,
    Protocol,
    RedisConfig,
    ServicesHost,
    StreamConfig,
)
from xrpld_lab.models import _DEFAULT_PEER_ZONES, _DEFAULT_VALIDATOR_ZONES
from xrpld_lab.operations import (
    enable_amendment,
    node_stall,
    remove_network,
    restart_local_node,
    run_start_script,
    run_stop_script,
    start_local,
    stop_local,
    stop_standalone,
    update_node_binary,
    view_local_logs,
    view_standalone_logs,
)
from xrpld_lab.protocol import get_spec
from xrpld_lab.workspace import Workspace
from xrpld_lab.workflows import LabRunner

# ---------------------------------------------------------------------------
# Fallback versions (used when no --version / --build_version is provided)
# ---------------------------------------------------------------------------

_XRPL_RELEASE_FALLBACK: str = "3.2.0-rc2"
_XAHAU_RELEASE_FALLBACK: str = "2025.7.9-release+1951"

# ---------------------------------------------------------------------------
# Default VL keys
# ---------------------------------------------------------------------------

_DEFAULT_VL_KEY: str = (
    "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501"
)
_XAHAU_IMPORT_VL_KEY: str = (
    "ED74D4036C6591A4BDF9C54CEFA39B996A5DCE5F86D11FDA1874481CE9D5A1CDC1"
)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def _add_network_args(p: argparse.ArgumentParser) -> None:
    """Add arguments shared by create:network and create:ansible."""
    p.add_argument("--log_level", default="trace", choices=["warning", "debug", "trace"])
    p.add_argument("--protocol", default="xrpl")
    p.add_argument("--num_validators", type=int, default=3)
    p.add_argument("--num_peers", type=int, default=1)
    p.add_argument("--network_id", type=int, default=21337)
    p.add_argument("--build_server", default=None)
    p.add_argument("--build_version", default=None)
    p.add_argument("--genesis", type=bool, default=False)
    p.add_argument("--quorum", type=int, default=None)
    p.add_argument("--nodedb_type", default="NuDB", choices=["Memory", "NuDB", "rwdb"])
    p.add_argument("--config_overrides", type=str, default=None,
                   help="Path to YAML/JSON file with config overrides")
    p.add_argument("--datagram_monitor", type=str, default=None,
                   help="Perf-server XDGM sink as 'HOST PORT' (internal IP, e.g. "
                        "'10.128.0.2 9876'); adds [datagram_monitor] to every node cfg")
    p.add_argument("--binary_path", type=str, default=None,
                   help="Path to pre-built binary (skips download)")
    p.add_argument("--quantum", action="store_true",
                   help="Use dilithium (post-quantum) keys for validators and publisher")
    p.add_argument("--preload_accounts", type=int, default=0,
                   help="Prefund N accounts directly in genesis (perf-iac style)")
    p.add_argument("--preload_trustlines", type=int, default=0,
                   help="Create N trustlines from account 0 (issuer hub) in genesis")
    p.add_argument("--preload_balance", default="1000000000",
                   help="Drops per prefunded account (default 1000 XRP)")
    p.add_argument("--preload_currency", default="USD",
                   help="Currency code for preloaded trustlines")


def _build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser with all subcommands."""
    parser = argparse.ArgumentParser(
        description="xrpld-lab: build xrpld networks and standalone ledgers.",
    )
    subparsers = parser.add_subparsers(dest="command")

    # -- up:standalone -------------------------------------------------------
    p = subparsers.add_parser("up:standalone", help="Create and start standalone ledger")
    p.add_argument("--log_level", default="trace", choices=["warning", "debug", "trace"])
    p.add_argument("--build_type", default="binary", choices=["image", "binary"])
    p.add_argument("--public_key", default=_DEFAULT_VL_KEY)
    p.add_argument("--import_key", default=None)
    p.add_argument("--protocol", default="xrpl")
    p.add_argument("--network_id", type=int, default=21337)
    p.add_argument("--network_type", default="standalone")
    p.add_argument("--server", default=None)
    p.add_argument("--version", default=None)
    p.add_argument("--ipfs", type=bool, default=False)
    p.add_argument("--nodedb_type", default="NuDB", choices=["Memory", "NuDB", "rwdb"])
    p.add_argument("--config_overrides", type=str, default=None,
                   help="Path to YAML/JSON file with config overrides")
    p.add_argument("--datagram_monitor", type=str, default=None,
                   help="Perf-server XDGM sink as 'HOST PORT' (e.g. '10.128.0.2 9876')")

    # -- create:network ------------------------------------------------------
    p = subparsers.add_parser("create:network", help="Create a multi-node network")
    _add_network_args(p)
    p.add_argument("--local", action="store_true")
    p.add_argument("--binary_name", default="xrpld")
    p.add_argument("--ansible", action="store_true",
                   help="Also generate ansible deployment files")
    p.add_argument("--vips", nargs="+", default=None,
                   help="Validator IP addresses (for ansible)")
    p.add_argument("--pips", nargs="+", default=None,
                   help="Peer IP addresses (for ansible)")
    p.add_argument("--ssh_port", type=int, default=20,
                   help="SSH port for ansible (default: 20)")
    p.add_argument("--ssh_user", default="ubuntu",
                   help="SSH user for ansible (default: ubuntu)")
    p.add_argument("--ssh_key", default="~/.ssh/id_rsa",
                   help="SSH key path for ansible")

    # -- create:ansible ------------------------------------------------------
    p = subparsers.add_parser("create:ansible",
                              help="Create network with ansible deployment")
    _add_network_args(p)
    p.add_argument("--binary_name", default="xrpld")
    p.add_argument("--vips", nargs="+", default=None,
                   help="Validator IP addresses")
    p.add_argument("--pips", nargs="+", default=None,
                   help="Peer IP addresses")
    p.add_argument("--ssh_port", type=int, default=20)
    p.add_argument("--ssh_user", default="ubuntu")
    p.add_argument("--ssh_key", default="~/.ssh/id_rsa")
    p.add_argument("--ansible_config", type=str, default=None,
                   help="Path to YAML file with full ansible config (services, etc.)")

    # -- create:gcp ----------------------------------------------------------
    p = subparsers.add_parser(
        "create:gcp",
        help="Provision GCP VMs (terraform), deploy via ansible, verify consensus",
    )
    _add_network_args(p)
    p.add_argument("--project", required=True, help="GCP project ID")
    p.add_argument("--cluster", default=None, help="Cluster name (default gcp-<protocol>)")
    p.add_argument("--machine_type", default="n2-standard-8")
    p.add_argument("--binary_name", default="xrpld")
    p.add_argument("--ssh_port", type=int, default=22)
    p.add_argument("--ssh_user", default="ubuntu")
    p.add_argument("--ssh_key", default="~/.ssh/id_rsa")
    p.add_argument("--ssh_pubkey", default="~/.ssh/id_rsa.pub")
    p.add_argument("--image", default=None,
                   help="Prebuilt node image to deploy (e.g. <region>-docker.pkg.dev/"
                        "<proj>/xrpld/xrpld:<tag>). Built elsewhere (loadtester build/).")
    p.add_argument("--no_apply", action="store_true",
                   help="Generate the terraform module only; don't apply or deploy")
    # perf-cluster defaults: 4 validators + 3 P2P peers
    p.set_defaults(num_validators=4, num_peers=3)

    # -- deploy:ansible ------------------------------------------------------
    p = subparsers.add_parser("deploy:ansible",
                              help="Run ansible deployment for an existing cluster")
    p.add_argument("--name", required=True, help="Cluster name")

    # -- Operational commands ------------------------------------------------
    p = subparsers.add_parser("up", help="Start network")
    p.add_argument("--name", required=True)

    p = subparsers.add_parser("down", help="Stop network")
    p.add_argument("--name", required=True)

    p = subparsers.add_parser("remove", help="Remove network")
    p.add_argument("--name", required=True)

    # -- down:standalone -----------------------------------------------------
    p = subparsers.add_parser("down:standalone", help="Stop and remove standalone ledger")
    p.add_argument("--name", default=None)
    p.add_argument("--protocol", default="xrpl")
    p.add_argument("--version", default=None)

    # -- up:local ------------------------------------------------------------
    p = subparsers.add_parser("up:local", help="Start local standalone")
    p.add_argument("--log_level", default="trace", choices=["warning", "debug", "trace"])
    p.add_argument("--public_key", default=_DEFAULT_VL_KEY)
    p.add_argument("--import_key", default=None)
    p.add_argument("--protocol", default="xrpl")
    p.add_argument("--network_type", default="standalone")
    p.add_argument("--network_id", type=int, default=21337)
    p.add_argument("--nodedb_type", default="NuDB", choices=["Memory", "NuDB", "rwdb"])

    # -- down:local ----------------------------------------------------------
    p = subparsers.add_parser("down:local", help="Stop local standalone")

    # -- update:node ---------------------------------------------------------
    p = subparsers.add_parser("update:node", help="Update a node binary")
    p.add_argument("--name", required=True)
    p.add_argument("--node_id", type=int, required=True)
    p.add_argument("--node_type", required=True, choices=["validator", "peer"])
    p.add_argument("--build_server", required=True)
    p.add_argument("--build_version", required=True)

    # -- enable:amendment ----------------------------------------------------
    p = subparsers.add_parser("enable:amendment", help="Enable amendment via RPC")
    p.add_argument("--name", required=True)
    p.add_argument("--amendment_name", required=True)
    p.add_argument("--node_id", type=int, required=True)
    p.add_argument("--node_type", required=True, choices=["validator", "peer"])

    # -- node:stall ----------------------------------------------------------
    p = subparsers.add_parser("node:stall", help="Stall a node (pause consensus)")
    p.add_argument("--name", required=True)
    p.add_argument("--node_id", type=int, required=True)
    p.add_argument("--node_type", required=True, choices=["validator", "peer"])
    p.add_argument("--duration_ms", type=int, default=30000,
                   help="Stall duration in ms (default: 30000)")
    p.add_argument("--clear", action="store_true",
                   help="Clear the stall immediately")

    # -- node:restart --------------------------------------------------------
    p = subparsers.add_parser(
        "node:restart",
        help="Restart a single local node (syncs from network)",
    )
    p.add_argument("node_name", help="Node directory name (e.g. vnode2)")
    p.add_argument("--genesis", action="store_true",
                   help="Start from genesis instead of syncing from network")

    # -- logs:local ----------------------------------------------------------
    p = subparsers.add_parser("logs:local", help="View local node logs")
    p.add_argument("--node", default=None)

    # -- logs:standalone -----------------------------------------------------
    p = subparsers.add_parser("logs:standalone", help="View standalone Docker logs")
    p.add_argument("--protocol", default="xrpl")

    return parser


# ---------------------------------------------------------------------------
# Ansible config helpers
# ---------------------------------------------------------------------------


def _resolve_service_dependencies(
    ansible: AnsibleConfig, log_level: str
) -> tuple:
    """Enforce service dependency constraints.

    - stream + debug are always paired (auto-create missing half)
    - stream/debug require redis on the same host
    - stream/debug require trace log level on nodes
    - debug.endpoint auto-derives from stream ip:port if not set
    """
    needs_trace = False

    for host in ansible.services:
        # stream and debug are a pair — auto-create the missing half
        if host.stream and not host.debug:
            host.debug = DebugConfig(
                endpoint=f"ws://{host.ip}:{host.stream.port}/",
            )
        elif host.debug and not host.stream:
            host.stream = StreamConfig()

        if host.stream or host.debug:
            needs_trace = True

            # debug/stream require redis
            if not host.redis:
                host.redis = RedisConfig()

            # auto-derive debug endpoint from stream
            if host.debug and host.stream and not host.debug.endpoint:
                host.debug.endpoint = f"ws://{host.ip}:{host.stream.port}/"

    if needs_trace and log_level != "trace":
        print(f"  [xrpld-lab] stream/debug services require trace logging, "
              f"overriding log_level from '{log_level}' to 'trace'")
        log_level = "trace"

    return ansible, log_level


def _build_ansible_config_from_args(args) -> AnsibleConfig:
    """Build AnsibleConfig from CLI args (--vips, --pips, --ssh_*)."""
    return AnsibleConfig(
        ssh_port=args.ssh_port,
        ssh_user=args.ssh_user,
        ssh_key_path=args.ssh_key,
        vips=args.vips or [],
        pips=args.pips or [],
    )


def _build_ansible_config_from_file(path: str, args) -> AnsibleConfig:
    """Build AnsibleConfig from a YAML file, with CLI args as fallback."""
    data = load_ansible_config(path)

    services: List[ServicesHost] = []
    for svc_data in data.get("services", []):
        host = ServicesHost(
            ip=svc_data["ip"],
            name=svc_data["name"],
            nginx=NginxConfig(**(svc_data["nginx"] or {})) if "nginx" in svc_data else None,
            redis=RedisConfig(**(svc_data["redis"] or {})) if "redis" in svc_data else None,
            faucet=FaucetConfig(**(svc_data["faucet"] or {})) if "faucet" in svc_data else None,
            stream=StreamConfig(**(svc_data["stream"] or {})) if "stream" in svc_data else None,
            debug=DebugConfig(**(svc_data["debug"] or {})) if "debug" in svc_data else None,
            compiler=CompilerConfig(**(svc_data["compiler"] or {})) if "compiler" in svc_data else None,
        )
        services.append(host)

    return AnsibleConfig(
        ssh_port=data.get("ssh_port", args.ssh_port),
        ssh_user=data.get("ssh_user", args.ssh_user),
        ssh_key_path=data.get("ssh_key_path", args.ssh_key),
        vips=data.get("vips", args.vips or []),
        pips=data.get("pips", args.pips or []),
        services=services,
    )


# ---------------------------------------------------------------------------
# Args -> LabConfig conversion
# ---------------------------------------------------------------------------


def build_lab_config(args: argparse.Namespace) -> LabConfig:
    """Convert parsed CLI args into a LabConfig.

    Applies protocol-specific defaults and constructs the proper BuildSource.
    """
    protocol = Protocol(args.protocol)
    spec = get_spec(protocol)

    if args.command == "up:standalone":
        return _build_standalone_config(args, protocol, spec)

    if args.command in ("create:network", "create:ansible"):
        return _build_network_config(args, protocol, spec)

    raise ValueError(f"Cannot build LabConfig for command: {args.command!r}")


def _build_standalone_config(args, protocol, spec):
    """Build LabConfig for the up:standalone command."""
    server = args.server
    version = args.version
    build_type = BuildType(args.build_type)
    import_key = args.import_key

    # Load config overrides from file if provided
    config_overrides = {}
    if args.config_overrides:
        config_overrides = load_overrides_file(args.config_overrides)

    if protocol == Protocol.XAHAU:
        server = server or spec.default_build_server
        version = version or _XAHAU_RELEASE_FALLBACK
        build_type = BuildType.BINARY
        import_key = import_key or _XAHAU_IMPORT_VL_KEY
    elif protocol == Protocol.XRPL:
        server = server or "rippleci"
        version = version or _XRPL_RELEASE_FALLBACK
        build_type = BuildType.IMAGE

    source = BuildSource(
        protocol=protocol,
        build_type=build_type,
        build_server=server,
        build_version=version,
        owner=spec.github_owner,
        repo=spec.github_repo,
        image=(
            f"{server}/xrpld:{version}"
            if build_type == BuildType.IMAGE
            else "ubuntu:jammy"
        ),
    )

    return LabConfig(
        protocol=protocol,
        mode=DeployMode.STANDALONE,
        build_source=source,
        network_id=args.network_id,
        log_level=args.log_level,
        node_db_type=NodeDbType(args.nodedb_type),
        add_ipfs=args.ipfs,
        public_vl_key=args.public_key,
        import_vl_key=import_key,
        config_overrides=config_overrides,
        datagram_monitor=getattr(args, "datagram_monitor", None),
    )


def _build_network_config(args, protocol, spec):
    """Build LabConfig for create:network, create:ansible, create:gcp commands."""
    is_ansible = args.command in ("create:ansible", "create:gcp")
    has_local = hasattr(args, "local") and args.local
    mode = DeployMode.LOCAL if has_local else DeployMode.NETWORK
    server = args.build_server
    version = args.build_version

    # Load config overrides from file if provided
    config_overrides = {}
    if args.config_overrides:
        config_overrides = load_overrides_file(args.config_overrides)

    cluster_name = ""
    commit_hash = ""
    binary_path = ""
    build_type = BuildType.IMAGE
    owner = spec.github_owner
    repo = spec.github_repo

    if protocol == Protocol.XAHAU:
        server = server or spec.default_build_server
        version = version or _XAHAU_RELEASE_FALLBACK
        build_type = BuildType.BINARY
    elif protocol == Protocol.XRPL:
        if server and server.startswith("https://github.com/"):
            owner = server.split("https://github.com/")[1].split("/")[0]
            tail = server.split(f"https://github.com/{owner}/")[1]
            branch = tail.split("/tree/")[1] if "/tree/" in tail else tail
            cluster_name = branch.replace("/", "-")
            commit_hash = version or ""
            binary_path = args.binary_path if args.binary_path else "./xrpld"
            build_type = BuildType.BINARY
            repo = "rippled"
        elif has_local:
            server = server or "https://github.com/XRPLF/xrpld/tree"
            version = version or _XRPL_RELEASE_FALLBACK
            build_type = BuildType.BINARY
        else:
            server = server or spec.default_build_server
            version = version or _XRPL_RELEASE_FALLBACK

    source = BuildSource(
        protocol=protocol,
        build_type=build_type,
        build_server=server or "",
        build_version=version or "",
        owner=owner,
        repo=repo,
        cluster_name=cluster_name,
        commit_hash=commit_hash,
        binary_path=binary_path,
    )

    # Ansible config
    ansible: Optional[AnsibleConfig] = None
    if is_ansible:
        if hasattr(args, "ansible_config") and args.ansible_config:
            ansible = _build_ansible_config_from_file(args.ansible_config, args)
        else:
            if not args.vips or not args.pips:
                raise SystemExit(
                    "error: create:ansible requires --vips and --pips "
                    "(or --ansible_config with vips/pips in the YAML file)"
                )
            ansible = _build_ansible_config_from_args(args)
    elif hasattr(args, "ansible") and args.ansible:
        ansible = _build_ansible_config_from_args(args)

    # Auto-derive debug endpoint from stream, enforce trace for stream/debug
    log_level = args.log_level
    if ansible:
        ansible, log_level = _resolve_service_dependencies(ansible, log_level)

    # For ansible, derive counts from the YAML if not explicitly overridden
    num_validators = args.num_validators
    num_peers = args.num_peers
    if is_ansible and ansible:
        if ansible.vips and num_validators == 3:
            num_validators = len(ansible.vips)
        if ansible.pips and num_peers == 1:
            num_peers = len(ansible.pips)

    key_algorithm = "dilithium" if getattr(args, "quantum", False) else "ed25519"

    return LabConfig(
        protocol=protocol,
        mode=mode,
        build_source=source,
        network_id=args.network_id or spec.default_network_id,
        log_level=log_level,
        num_validators=num_validators,
        num_peers=num_peers,
        genesis=args.genesis,
        quorum=args.quorum,
        node_db_type=NodeDbType(args.nodedb_type),
        binary_name=args.binary_name,
        import_vl_key=spec.default_import_vl_key,
        key_algorithm=key_algorithm,
        config_overrides=config_overrides,
        datagram_monitor=getattr(args, "datagram_monitor", None),
        ansible=ansible,
        preload_accounts=getattr(args, "preload_accounts", 0),
        preload_trustlines=getattr(args, "preload_trustlines", 0),
        preload_balance=getattr(args, "preload_balance", "1000000000"),
        preload_currency=getattr(args, "preload_currency", "USD"),
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point: parse args and dispatch."""
    parser = _build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # create:gcp orchestrates provision -> deploy -> health (its own flow)
    if args.command == "create:gcp":
        _create_gcp(args)
        return

    # Commands that need LabConfig -> LabRunner
    if args.command in ("up:standalone", "create:network", "create:ansible"):
        lab = build_lab_config(args)
        LabRunner(lab).run()
        return

    # Operational commands (scripts, logs, etc.)
    workspace = Workspace()

    if args.command == "deploy:ansible":
        _deploy_ansible(workspace, args.name)
    elif args.command == "up":
        run_start_script(workspace, args.name)
    elif args.command == "down":
        run_stop_script(workspace, args.name)
    elif args.command == "remove":
        remove_network(workspace, args.name)
    elif args.command == "down:standalone":
        stop_standalone(workspace, args.name, args.protocol, args.version)
    elif args.command == "up:local":
        start_local(
            protocol=args.protocol,
            network_type=args.network_type,
            network_id=args.network_id,
            log_level=args.log_level,
            nodedb_type=args.nodedb_type,
            public_key=args.public_key,
            import_key=args.import_key,
        )
    elif args.command == "down:local":
        stop_local()
    elif args.command == "update:node":
        update_node_binary(
            workspace,
            args.name,
            args.node_id,
            args.node_type,
            args.build_server,
            args.build_version,
        )
    elif args.command == "enable:amendment":
        enable_amendment(
            args.name,
            args.amendment_name,
            args.node_id,
            args.node_type,
            workspace,
        )
    elif args.command == "node:stall":
        node_stall(
            args.name,
            args.node_id,
            args.node_type,
            workspace,
            args.duration_ms,
            args.clear,
        )
    elif args.command == "node:restart":
        restart_local_node(args.node_name, genesis=args.genesis)
    elif args.command == "logs:local":
        view_local_logs(args.node)
    elif args.command == "logs:standalone":
        view_standalone_logs(args.protocol)


def _deploy_ansible(workspace: Workspace, name: str) -> None:
    """Run the ansible deployment for an existing cluster."""
    import os
    import subprocess

    cluster_dir = workspace.cluster_dir(name)
    ansible_dir = os.path.join(cluster_dir, "ansible")
    run_sh = os.path.join(ansible_dir, "run.sh")

    if not os.path.exists(run_sh):
        print(f"No ansible deployment found at {ansible_dir}")
        print("Run 'xrpld-lab create:ansible' first to generate deployment files.")
        return

    subprocess.run(["bash", run_sh], cwd=ansible_dir, check=False)


# ---------------------------------------------------------------------------
# create:gcp  (terraform -> deploy -> health_check)
# ---------------------------------------------------------------------------


def _slice_zones(pool: List[str], n: int) -> List[str]:
    """Return n zones, cycling the default pool if n exceeds its length."""
    return [pool[i % len(pool)] for i in range(n)]


def _build_gcp_config(args) -> GcpConfig:
    return GcpConfig(
        project=args.project,
        validator_zones=_slice_zones(_DEFAULT_VALIDATOR_ZONES, args.num_validators),
        peer_zones=_slice_zones(_DEFAULT_PEER_ZONES, args.num_peers),
        machine_type=args.machine_type,
        ssh_user=args.ssh_user,
        ssh_key_path=args.ssh_key,
        ssh_pubkey_path=args.ssh_pubkey,
        ssh_port=args.ssh_port,
    )


def _write_endpoints(cluster_dir: str, vips: List[str], pips: List[str],
                     network_id: int) -> str:
    """Drop the raw endpoints the loadtester normalizes into its manifest."""
    import json
    import os
    from xrpld_lab.models import NodeRole, PortSet

    def _node(name, ip, role, idx):
        ports = PortSet.for_node(idx, role)
        return {"name": name, "ip": ip,
                "ws": f"ws://{ip}:{ports.ws_public}",
                "rpc": f"http://{ip}:{ports.rpc_public}",
                "peer": ports.peer}

    data = {
        "network_id": network_id,
        "validators": [_node(f"vnode{i+1}", ip, NodeRole.VALIDATOR, i + 1)
                       for i, ip in enumerate(vips)],
        "peers": [_node(f"pnode{i+1}", ip, NodeRole.PEER, i + 1)
                  for i, ip in enumerate(pips)],
    }
    path = os.path.join(cluster_dir, "endpoints.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path


def _create_gcp(args) -> None:
    """Provision GCP VMs, deploy xrpld via ansible, verify consensus."""
    import os

    from xrpld_lab.infra import GcpProvisioner, check_consensus

    protocol = Protocol(args.protocol)
    spec = get_spec(protocol)
    gcp = _build_gcp_config(args)
    cluster = args.cluster or f"gcp-{protocol.value}"
    workspace = Workspace()
    cluster_dir = workspace.cluster_dir(cluster)

    prov = GcpProvisioner(gcp, cluster, os.path.join(cluster_dir, "infra"))

    # 1. terraform
    if args.no_apply:
        work = prov.write()
        print(f"[gcp] terraform module written to {work}")
        print(f"[gcp] apply manually:  terraform -chdir={work} init && "
              f"terraform -chdir={work} apply")
        return

    print(f"[gcp] provisioning {gcp.num_validators} validators + "
          f"{gcp.num_peers} peers across {gcp.validator_zones + gcp.peer_zones}…")
    vips, pips = prov.provision()
    print(f"[gcp] validators={vips}")
    print(f"[gcp] peers={pips}")

    # 2. generate node configs + ansible (reuse the network workflow)
    args.vips, args.pips = vips, pips
    args.ssh_user, args.ssh_key, args.ssh_port = gcp.ssh_user, gcp.ssh_key_path, gcp.ssh_port
    args.ansible_config = None
    lab = _build_network_config(args, protocol, spec)
    lab.build_source.cluster_name = cluster  # pin the cluster dir name
    if getattr(args, "image", None):
        # Deploy a prebuilt image (Cloud Build output). The image IS the binary, so skip the
        # local-binary copy / download — but keep build_server+build_version so features/
        # amendments are still resolved from the source at that commit (sentinel's pattern).
        lab.build_source.image = args.image
        lab.build_source.binary_path = ""
        lab.build_source.build_type = BuildType.IMAGE
        print(f"[gcp] deploying supplied image {args.image}")
    LabRunner(lab, workspace).run()

    # 3. deploy (ansible run.sh) + 4. health
    _deploy_ansible(workspace, cluster)
    check_consensus(vips)

    # 5. endpoints for the loadtester
    path = _write_endpoints(cluster_dir, vips, pips, lab.network_id)
    print(f"[gcp] network running. endpoints → {path}")
