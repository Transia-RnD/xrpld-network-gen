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
    import_vl_key: Optional[str] = None
    public_vl_key: Optional[str] = None
    add_ipfs: bool = False
    ansible: Optional[AnsibleConfig] = None
    config_overrides: dict = field(default_factory=dict)

    @property
    def effective_quorum(self) -> int:
        """Return the quorum: explicit value if set, else num_validators - 1 (min 1)."""
        if self.quorum is not None:
            return self.quorum
        return max(self.num_validators - 1, 1)
