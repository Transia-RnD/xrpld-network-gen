from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Protocol(Enum):
    XRPL = "xrpl"
    XAHAU = "xahau"


class DeployMode(Enum):
    STANDALONE = "standalone"
    NETWORK = "network"
    LOCAL = "local"


class NodeRole(Enum):
    VALIDATOR = "validator"
    PEER = "peer"
    STANDALONE = "standalone"


class BuildType(Enum):
    IMAGE = "image"
    BINARY = "binary"


class NodeDbType(Enum):
    NUDB = "NuDB"
    MEMORY = "Memory"
    RWDB = "rwdb"


# ---------------------------------------------------------------------------
# Port calculation
# ---------------------------------------------------------------------------

# Base ports (from xrpld_netgen/utils/misc.py)
_RPC_PUBLIC: int = 5007
_RPC_ADMIN: int = 5005
_WS_PUBLIC: int = 6008
_WS_ADMIN: int = 6006
_PEER: int = 51235


@dataclass(frozen=True)
class PortSet:
    """Immutable set of network ports for a single node."""

    rpc_public: int
    rpc_admin: int
    ws_public: int
    ws_admin: int
    peer: int

    @classmethod
    def for_node(cls, index: int, role: NodeRole) -> PortSet:
        """Calculate ports for a node based on its role and index.

        - VALIDATOR: base + index * 100
        - PEER: base + index * 10
        - STANDALONE: base ports (index is ignored)
        """
        if role == NodeRole.VALIDATOR:
            offset = index * 100
        elif role == NodeRole.PEER:
            offset = index * 10
        elif role == NodeRole.STANDALONE:
            offset = 0
        else:
            raise ValueError(f"Unknown node role: {role}")

        return cls(
            rpc_public=_RPC_PUBLIC + offset,
            rpc_admin=_RPC_ADMIN + offset,
            ws_public=_WS_PUBLIC + offset,
            ws_admin=_WS_ADMIN + offset,
            peer=_PEER + offset,
        )


# ---------------------------------------------------------------------------
# Config sub-objects
# ---------------------------------------------------------------------------


@dataclass
class ServerConfig:
    rpc_public: bool = True
    rpc_admin: bool = True
    ws_public: bool = True
    ws_admin: bool = True
    peer: bool = True
    ssl_verify: bool = False
    ssl_key_path: Optional[str] = None
    ssl_cert_path: Optional[str] = None
    send_queue_limit: int = 65535


@dataclass
class NodeDbConfig:
    db_type: NodeDbType = NodeDbType.NUDB
    path: str = "db"
    num_ledgers: Optional[int] = 10000
    relational_db: Optional[str] = None

    @classmethod
    def for_mode(cls, db_type: NodeDbType, mode: DeployMode) -> NodeDbConfig:
        """Derive path and relational_db from the db type and deploy mode.

        Mirrors ``get_node_db_path`` / ``get_relational_db`` in misc.py.
        """
        # --- path ---
        if db_type == NodeDbType.NUDB:
            if mode == DeployMode.LOCAL:
                path = "db"
            elif mode == DeployMode.STANDALONE:
                path = "/opt/ripple/lib/db"
            elif mode == DeployMode.NETWORK:
                path = "/var/lib/xrpld/db"
            else:
                path = "db"
        elif db_type == NodeDbType.MEMORY:
            path = "./"
        elif db_type == NodeDbType.RWDB:
            if mode == DeployMode.NETWORK:
                path = "/var/lib/xrpld/db"
            else:
                path = "db"
        else:
            path = "db"

        # --- relational_db ---
        if db_type == NodeDbType.NUDB:
            relational_db = None
        elif db_type == NodeDbType.MEMORY:
            relational_db = "backend=memory"
        elif db_type == NodeDbType.RWDB:
            relational_db = "backend=rwdb"
        else:
            relational_db = None

        return cls(
            db_type=db_type,
            path=path,
            relational_db=relational_db,
        )


@dataclass
class TransactionQueueConfig:
    ledgers_in_queue: int = 20
    minimum_queue_size: int = 2000
    retry_sequence_percent: int = 25
    minimum_escalation_multiplier: int = 500
    minimum_txn_in_ledger: int = 5
    minimum_txn_in_ledger_standalone: int = 5
    target_txn_in_ledger: int = 100
    maximum_txn_in_ledger: int = 10000
    normal_consensus_increase_percent: int = 20
    slow_consensus_decrease_percent: int = 50
    maximum_txn_per_account: int = 100000
    minimum_last_ledger_buffer: int = 2
    zero_basefee_transaction_feelevel: int = 256000


@dataclass
class WorkerConfig:
    workers: int = 10
    io_workers: int = 10
    prefetch_workers: int = 10


@dataclass
class VotingConfig:
    account_reserve: int = 1000000
    owner_reserve: int = 200000
    reference_fee: int = 10


@dataclass
class ValidatorIdentity:
    public_key: str
    token: str
    manifest: str


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------


@dataclass
class NodeConfig:
    """Full configuration for a single xrpld node."""

    name: str
    index: int
    role: NodeRole
    protocol: Protocol
    network_id: int
    ports: PortSet
    server: ServerConfig = field(default_factory=ServerConfig)
    node_db: NodeDbConfig = field(default_factory=NodeDbConfig)
    tx_queue: TransactionQueueConfig = field(default_factory=TransactionQueueConfig)
    worker: WorkerConfig = field(default_factory=WorkerConfig)
    voting: VotingConfig = field(default_factory=VotingConfig)
    db_path: str = "/opt/ripple/lib/db"
    debug_path: str = "/opt/ripple/log/debug.log"
    size_node: str = "huge"
    log_level: str = "trace"
    private_peer: bool = False
    max_transactions: int = 10000
    validator: Optional[ValidatorIdentity] = None
    validators: List[str] = field(default_factory=list)
    cluster_nodes: List[str] = field(default_factory=list)
    ips_urls: List[str] = field(default_factory=list)
    ips_fixed_urls: List[str] = field(default_factory=list)
    # [datagram_monitor] endpoint lines ("<ip> <port>", space-separated to match the
    # node's parseEndpoint). Each measured node fires XDGM here — the perf-server sink.
    datagram_monitor: List[str] = field(default_factory=list)
    vl_sites: List[str] = field(default_factory=list)
    vl_keys: List[str] = field(default_factory=list)
    import_vl_keys: List[str] = field(default_factory=list)
    amendment_majority_time: Optional[str] = None
    amendments: Dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Build source
# ---------------------------------------------------------------------------


@dataclass
class BuildSource:
    protocol: Protocol
    build_type: BuildType
    build_server: str
    build_version: str
    owner: str = ""
    repo: str = ""
    image: str = ""
    binary_path: str = ""
    cluster_name: str = ""
    commit_hash: str = ""
    feature_content: list = field(default_factory=list)
    repo_config: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Ansible optional service configs
# ---------------------------------------------------------------------------


@dataclass
class NginxConfig:
    domain: str = ""
    ssl_org: str = ""
    ssl_ou: str = ""
    ws_port: str = ""
    rpc_port: str = ""
    faucet_port: str = "8080"
    debug_port: str = "8081"
    compiler_port: str = "9000"


@dataclass
class RedisConfig:
    image: str = "redis"
    container_name: str = "alpha-redis-main"
    network_name: str = "alpha"


@dataclass
class FaucetConfig:
    image: str = "transia/faucet"
    port: int = 8080
    ws_url: str = ""
    network_id: str = ""
    seed: str = ""


@dataclass
class StreamConfig:
    port: int = 1400
    container_name: str = "pnode1"
    log_path: str = "/opt/ripple/log/debug.log"


@dataclass
class DebugConfig:
    image: str = "transia/debugstream"
    port: int = 8081
    endpoint: str = ""
    redis_host: str = "alpha-redis-main"
    redis_port: str = "6379"
    network_name: str = "alpha"


@dataclass
class CompilerConfig:
    image: str = "transia/compiler-api:latest"
    port: int = 5002
    repo: str = "git@github.com:Transia-RnD/xrpl-hooks-compiler.git"
    branch: str = "dangell/smart-contracts"
    volumes: List[str] = field(default_factory=list)


@dataclass
class ServicesHost:
    """A host that runs optional infrastructure services.

    Each ServicesHost becomes its own ansible group and gets a dedicated
    directory under ``ansible/services/{name}/``.  Nginx is typically
    per-host (each domain points at one IP via Cloudflare), while
    faucet/redis/stream/debug/compiler usually live on a single host
    but can be spread across multiple if needed.
    """

    ip: str
    name: str
    nginx: Optional[NginxConfig] = None
    redis: Optional[RedisConfig] = None
    faucet: Optional[FaucetConfig] = None
    stream: Optional[StreamConfig] = None
    debug: Optional[DebugConfig] = None
    compiler: Optional[CompilerConfig] = None

    @property
    def enabled_services(self) -> List[str]:
        out: List[str] = []
        if self.nginx:
            out.append("nginx")
        if self.redis:
            out.append("redis")
        if self.faucet:
            out.append("faucet")
        if self.stream:
            out.append("stream")
        if self.debug:
            out.append("debug")
        if self.compiler:
            out.append("compiler")
        return out


@dataclass
class AnsibleConfig:
    ssh_port: int = 20
    ssh_user: str = "ubuntu"
    ssh_key_path: str = "~/.ssh/id_rsa"
    vips: List[str] = field(default_factory=list)
    pips: List[str] = field(default_factory=list)
    services: List[ServicesHost] = field(default_factory=list)


# ---------------------------------------------------------------------------
# GCP provisioning (multi-region)
# ---------------------------------------------------------------------------

# Default zones spread the cluster across continents so the measured TPS knee
# reflects real cross-region consensus latency (method-comparable to perf-iac,
# not number-comparable to a single-region/LAN run). Validators land in 5
# regions, P2P nodes in 4 others — every node on its own ephemeral-IP VM.
_DEFAULT_VALIDATOR_ZONES: List[str] = [
    "us-central1-a",
    "europe-west1-b",
    "asia-east1-a",
    "us-east1-b",
    "australia-southeast1-a",
]
_DEFAULT_PEER_ZONES: List[str] = [
    "us-west1-a",
    "europe-west2-a",
    "asia-southeast1-a",
    "southamerica-east1-a",
]


@dataclass
class GcpConfig:
    """GCP multi-region provisioning for an xrpld perf cluster.

    Terraform stands up one VM per node (ephemeral external IP). The harvested
    IPs feed straight into the existing ansible pipeline as ``vips``/``pips`` —
    GCP is a provisioning front-end to NETWORK mode, not a separate deploy path.
    """

    project: str
    validator_zones: List[str] = field(default_factory=lambda: list(_DEFAULT_VALIDATOR_ZONES))
    peer_zones: List[str] = field(default_factory=lambda: list(_DEFAULT_PEER_ZONES))
    machine_type: str = "n2-standard-8"
    disk_gb: int = 100
    image: str = "ubuntu-os-cloud/ubuntu-2204-lts"
    ssh_user: str = "ubuntu"
    # Public key uploaded to instance metadata; private half is used by ansible.
    ssh_pubkey_path: str = "~/.ssh/id_rsa.pub"
    ssh_key_path: str = "~/.ssh/id_rsa"
    ssh_port: int = 22
    network_tag: str = "xrpld-perf"
    # Firewall source ranges. 0.0.0.0/0 is fine for a throwaway perf net; lock
    # this down to your load-gen / collector IPs for anything longer-lived.
    allowed_source_ranges: List[str] = field(default_factory=lambda: ["0.0.0.0/0"])
    # Peer (51235+), public RPC/WS, and ssh. Admin ports stay node-local.
    open_tcp_ports: List[str] = field(
        default_factory=lambda: ["22", "5007-5520", "6008-6520", "51235-51740"]
    )

    @property
    def region(self) -> str:
        """Provider region derived from the first validator zone (us-central1-a → us-central1)."""
        zone = self.validator_zones[0]
        return zone.rsplit("-", 1)[0]

    @property
    def num_validators(self) -> int:
        return len(self.validator_zones)

    @property
    def num_peers(self) -> int:
        return len(self.peer_zones)


# ---------------------------------------------------------------------------
# Top-level lab configuration
# ---------------------------------------------------------------------------


@dataclass
class LabConfig:
    protocol: Protocol
    mode: DeployMode
    build_source: BuildSource
    network_id: int
    log_level: str = "trace"
    num_validators: int = 1
    num_peers: int = 0
    genesis: bool = False
    quorum: Optional[int] = None
    node_db_type: NodeDbType = NodeDbType.NUDB
    binary_name: str = "xrpld"
    # Perf-server XDGM sink as "<ip> <port>" (e.g. "10.128.0.2 9876"); None disables the
    # [datagram_monitor] stanza. Must be the server's INTERNAL IP (firewall is VPC-only).
    datagram_monitor: Optional[str] = None
    import_vl_key: Optional[str] = None
    public_vl_key: Optional[str] = None
    add_ipfs: bool = False
    ansible: Optional[AnsibleConfig] = None
    gcp: Optional[GcpConfig] = None
    key_algorithm: str = "ed25519"
    config_overrides: dict = field(default_factory=dict)
    # Prefunded genesis (perf-iac style): inject N AccountRoot + M RippleState
    # entries directly into genesis so the network starts with realistic state.
    preload_accounts: int = 0
    preload_trustlines: int = 0
    preload_balance: str = "1000000000"
    preload_currency: str = "USD"

    @property
    def effective_quorum(self) -> int:
        """Return the quorum: explicit value if set, else num_validators - 1 (min 1)."""
        if self.quorum is not None:
            return self.quorum
        return max(self.num_validators - 1, 1)
