"""NodeFactory -- creates NodeConfig instances for each deployment scenario."""

from __future__ import annotations

from typing import List, Optional

from xrpld_lab.models import (
    NodeConfig,
    PortSet,
    NodeRole,
    Protocol,
    DeployMode,
    ServerConfig,
    NodeDbConfig,
    NodeDbType,
    ValidatorIdentity,
)
from xrpld_lab.protocol import get_spec


class NodeFactory:
    """Creates NodeConfig instances for network nodes."""

    @staticmethod
    def create_standalone(
        protocol: Protocol,
        name: str,
        network_id: int,
        log_level: str = "trace",
        node_db_type: NodeDbType = NodeDbType.NUDB,
        vl_sites: Optional[List[str]] = None,
        vl_keys: Optional[List[str]] = None,
        import_vl_keys: Optional[List[str]] = None,
        ips_urls: Optional[List[str]] = None,
        ips_fixed_urls: Optional[List[str]] = None,
    ) -> NodeConfig:
        """Create a NodeConfig for a standalone node."""
        spec = get_spec(protocol)
        ports = PortSet.for_node(0, NodeRole.STANDALONE)
        node_db = NodeDbConfig.for_mode(node_db_type, DeployMode.STANDALONE)
        node_db.num_ledgers = 10000

        return NodeConfig(
            name=name,
            index=0,
            role=NodeRole.STANDALONE,
            protocol=protocol,
            network_id=network_id,
            ports=ports,
            server=ServerConfig(),
            node_db=node_db,
            db_path="/opt/ripple/lib/db",
            debug_path="/opt/ripple/log/debug.log",
            size_node="huge",
            log_level=log_level,
            amendment_majority_time=spec.amendment_majority_time,
            vl_sites=vl_sites or [],
            vl_keys=vl_keys or [],
            import_vl_keys=import_vl_keys or [],
            ips_urls=ips_urls or [],
            ips_fixed_urls=ips_fixed_urls or [],
        )

    @staticmethod
    def create_validator(
        index: int,
        protocol: Protocol,
        name: str,
        network_id: int,
        token: str,
        all_validators: List[str],
        vl_key: str,
        ivl_key: Optional[str] = None,
        ips_fixed: Optional[List[str]] = None,
        log_level: str = "warning",
        node_db_type: NodeDbType = NodeDbType.NUDB,
        ports: Optional[PortSet] = None,
    ) -> NodeConfig:
        """Create a NodeConfig for a validator node in a network."""
        spec = get_spec(protocol)
        ports = ports or PortSet.for_node(index, NodeRole.VALIDATOR)
        node_db = NodeDbConfig.for_mode(node_db_type, DeployMode.NETWORK)
        node_db.num_ledgers = 10000

        # Validator identity: own public key from all_validators (1-based index)
        self_key = all_validators[index - 1]
        validator = ValidatorIdentity(
            public_key=self_key,
            token=token,
            manifest="",
        )

        # Exclude self from validators list
        validators = [v for v in all_validators if v != self_key]

        # Exclude self from ips_fixed
        all_ips = ips_fixed or []
        self_ips_entry = all_ips[index - 1] if index - 1 < len(all_ips) else None
        ips_fixed_urls = [ip for ip in all_ips if ip != self_ips_entry]

        return NodeConfig(
            name=name,
            index=index,
            role=NodeRole.VALIDATOR,
            protocol=protocol,
            network_id=network_id,
            ports=ports,
            server=ServerConfig(),
            node_db=node_db,
            db_path="/opt/ripple/lib/db",
            debug_path="/opt/ripple/log/debug.log",
            size_node="huge",
            log_level=log_level,
            validator=validator,
            validators=validators,
            vl_sites=["http://vl/vl.json"],
            vl_keys=[vl_key],
            import_vl_keys=[ivl_key] if ivl_key else [],
            ips_fixed_urls=ips_fixed_urls,
            amendment_majority_time=spec.amendment_majority_time,
        )

    @staticmethod
    def create_peer(
        index: int,
        protocol: Protocol,
        name: str,
        network_id: int,
        validators: List[str],
        vl_key: str,
        ivl_key: Optional[str] = None,
        ips_fixed: Optional[List[str]] = None,
        log_level: str = "warning",
        node_db_type: NodeDbType = NodeDbType.NUDB,
        ports: Optional[PortSet] = None,
    ) -> NodeConfig:
        """Create a NodeConfig for a peer node in a network."""
        spec = get_spec(protocol)
        ports = ports or PortSet.for_node(index, NodeRole.PEER)
        node_db = NodeDbConfig.for_mode(node_db_type, DeployMode.NETWORK)
        node_db.num_ledgers = 10000

        return NodeConfig(
            name=name,
            index=index,
            role=NodeRole.PEER,
            protocol=protocol,
            network_id=network_id,
            ports=ports,
            server=ServerConfig(),
            node_db=node_db,
            db_path="/opt/ripple/lib/db",
            debug_path="/opt/ripple/log/debug.log",
            size_node="huge",
            log_level=log_level,
            validators=list(validators),
            vl_sites=["http://vl/vl.json"],
            vl_keys=[vl_key],
            import_vl_keys=[ivl_key] if ivl_key else [],
            ips_fixed_urls=list(ips_fixed) if ips_fixed else [],
            amendment_majority_time=spec.amendment_majority_time,
        )

    @staticmethod
    def create_local_standalone(
        protocol: Protocol,
        name: str,
        network_id: int,
        log_level: str = "trace",
        node_db_type: NodeDbType = NodeDbType.NUDB,
        vl_keys: Optional[List[str]] = None,
        import_vl_keys: Optional[List[str]] = None,
    ) -> NodeConfig:
        """Create a NodeConfig for a local (native process) standalone node."""
        spec = get_spec(protocol)
        ports = PortSet.for_node(0, NodeRole.STANDALONE)
        node_db = NodeDbConfig.for_mode(node_db_type, DeployMode.LOCAL)
        node_db.num_ledgers = 10000

        return NodeConfig(
            name=name,
            index=0,
            role=NodeRole.STANDALONE,
            protocol=protocol,
            network_id=network_id,
            ports=ports,
            server=ServerConfig(),
            node_db=node_db,
            db_path="db",
            debug_path="log/debug.log",
            size_node="huge",
            log_level=log_level,
            amendment_majority_time=spec.amendment_majority_time,
            vl_keys=vl_keys or [],
            import_vl_keys=import_vl_keys or [],
        )

    @staticmethod
    def create_local_validator(
        index: int,
        protocol: Protocol,
        name: str,
        network_id: int,
        token: str,
        all_validators: List[str],
        vl_key: str,
        ivl_key: Optional[str] = None,
        ips_fixed: Optional[List[str]] = None,
        log_level: str = "trace",
        node_db_type: NodeDbType = NodeDbType.NUDB,
    ) -> NodeConfig:
        """Create a NodeConfig for a local (native process) validator."""
        spec = get_spec(protocol)
        ports = PortSet.for_node(index, NodeRole.VALIDATOR)
        node_db = NodeDbConfig.for_mode(node_db_type, DeployMode.LOCAL)
        node_db.num_ledgers = 10000

        # Validator identity: own public key from all_validators (1-based index)
        self_key = all_validators[index - 1]
        validator = ValidatorIdentity(
            public_key=self_key,
            token=token,
            manifest="",
        )

        # Exclude self from validators list
        validators = [v for v in all_validators if v != self_key]

        # Exclude self from ips_fixed
        all_ips = ips_fixed or []
        self_ips_entry = all_ips[index - 1] if index - 1 < len(all_ips) else None
        ips_fixed_urls = [ip for ip in all_ips if ip != self_ips_entry]

        return NodeConfig(
            name=name,
            index=index,
            role=NodeRole.VALIDATOR,
            protocol=protocol,
            network_id=network_id,
            ports=ports,
            server=ServerConfig(),
            node_db=node_db,
            db_path="db",
            debug_path="log/debug.log",
            size_node="huge",
            log_level=log_level,
            validator=validator,
            validators=validators,
            vl_sites=["http://vl/vl.json"],
            vl_keys=[vl_key],
            import_vl_keys=[ivl_key] if ivl_key else [],
            ips_fixed_urls=ips_fixed_urls,
            amendment_majority_time=spec.amendment_majority_time,
        )

    @staticmethod
    def create_local_peer(
        index: int,
        protocol: Protocol,
        name: str,
        network_id: int,
        validators: List[str],
        vl_key: str,
        ivl_key: Optional[str] = None,
        ips_fixed: Optional[List[str]] = None,
        log_level: str = "trace",
        node_db_type: NodeDbType = NodeDbType.NUDB,
    ) -> NodeConfig:
        """Create a NodeConfig for a local peer node."""
        spec = get_spec(protocol)
        ports = PortSet.for_node(index, NodeRole.PEER)
        node_db = NodeDbConfig.for_mode(node_db_type, DeployMode.LOCAL)
        node_db.num_ledgers = 10000

        return NodeConfig(
            name=name,
            index=index,
            role=NodeRole.PEER,
            protocol=protocol,
            network_id=network_id,
            ports=ports,
            server=ServerConfig(),
            node_db=node_db,
            db_path="db",
            debug_path="log/debug.log",
            size_node="huge",
            log_level=log_level,
            validators=list(validators),
            vl_sites=["http://vl/vl.json"],
            vl_keys=[vl_key],
            import_vl_keys=[ivl_key] if ivl_key else [],
            ips_fixed_urls=list(ips_fixed) if ips_fixed else [],
            amendment_majority_time=spec.amendment_majority_time,
        )
