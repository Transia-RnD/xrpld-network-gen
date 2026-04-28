"""LabRunner -- orchestrates standalone, network, and local network workflows.

Ties together all the building blocks (NodeFactory, CfgBuilder, ComposeBuilder,
ScriptBuilder, SourceResolver, amendments) to execute the three main
deployment modes.
"""

from __future__ import annotations

import json
import os
import shutil
from typing import Dict, List

from xrpld_publisher.publisher import PublisherClient
from xrpld_publisher.validator import ValidatorClient

from xrpld_lab.models import (
    BuildType,
    DeployMode,
    LabConfig,
    NodeConfig,
    NodeRole,
    PortSet,
    Protocol,
)
from xrpld_lab.protocol import get_spec, ProtocolSpec
from xrpld_lab.workspace import Workspace
from xrpld_lab.node_factory import NodeFactory
from xrpld_lab.config_builder import XrpldCfgBuilder, ValidatorsTxtBuilder
from xrpld_lab.compose_builder import ComposeBuilder
from xrpld_lab.script_builder import DockerfileBuilder, ScriptBuilder
from xrpld_lab.source_resolver import SourceResolver
from xrpld_lab.amendments import (
    parse_amendments,
    update_genesis,
    get_feature_lines_from_content,
    get_feature_lines_from_path,
)
from xrpld_lab.config import merge_config
from xrpld_lab.ansible_builder import AnsibleBuilder
from xrpld_lab.utils import write_file, save_config, write_executable


class LabRunner:
    """Orchestrates standalone, network, and local network deployments."""

    def __init__(self, lab: LabConfig, workspace: Workspace = None):
        self.lab = lab
        self.spec = get_spec(lab.protocol)
        self.workspace = workspace or Workspace()
        self.resolver = SourceResolver()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self):
        """Execute the workflow based on lab.mode."""
        if self.lab.mode == DeployMode.STANDALONE:
            self._run_standalone()
        elif self.lab.mode == DeployMode.NETWORK:
            self._run_network()
        elif self.lab.mode == DeployMode.LOCAL:
            self._run_local_network()

    # ------------------------------------------------------------------
    # Standalone workflow
    # ------------------------------------------------------------------

    def _run_standalone(self):
        """Execute standalone workflow:

        1. Resolve features from source
        2. Create NodeConfig via NodeFactory
        3. Build xrpld.cfg and validators.txt
        4. Parse amendments, update genesis
        5. Create Dockerfile
        6. Build docker-compose
        7. Generate start/stop scripts
        """
        lab = self.lab
        spec = self.spec
        source = lab.build_source

        # Determine build dir name
        name = source.build_version
        protocol_name = lab.protocol.value
        base_dir = self.workspace.standalone_dir(protocol_name, name)

        # 1. Resolve features
        feature_content = self.resolver.resolve_features(source, spec)
        feature_lines = get_feature_lines_from_content(feature_content)

        # 1b. Resolve repo config and merge with overrides
        repo_config = self.resolver.resolve_repo_config(source, spec)
        effective_config = merge_config({}, repo_config, lab.config_overrides)

        # 2. Create node config
        node = NodeFactory.create_standalone(
            protocol=lab.protocol,
            name=name,
            network_id=lab.network_id,
            log_level=lab.log_level,
            node_db_type=lab.node_db_type,
        )

        # 3. Build config files
        cfg_content = XrpldCfgBuilder(node).build()
        vl_content = ValidatorsTxtBuilder(node, genesis=False).build()

        cfg_path = os.path.join(base_dir, "config")
        os.makedirs(cfg_path, exist_ok=True)
        save_config(protocol_name, cfg_path, cfg_content, vl_content)

        # 4. Amendments + genesis
        features = parse_amendments(feature_lines)
        genesis = update_genesis(features, protocol_name)
        write_file(
            os.path.join(base_dir, "genesis.json"),
            json.dumps(genesis, indent=4, sort_keys=True),
        )

        # 5. Dockerfile
        dockerfile = DockerfileBuilder.build(
            protocol=protocol_name,
            ports=node.ports,
            image_name=source.image or "ubuntu:noble",
            binary=source.build_type == BuildType.BINARY,
            version=name,
            include_genesis=True,
            standalone="-a",
        )
        write_file(os.path.join(base_dir, "Dockerfile"), dockerfile)

        # Copy entrypoint
        entrypoint_src = os.path.join(
            self.workspace.package_dir, "deploykit", spec.entrypoint_file
        )
        if os.path.exists(entrypoint_src):
            shutil.copy2(entrypoint_src, os.path.join(base_dir, "entrypoint"))

        # 6. Docker compose
        compose = ComposeBuilder("standalone-network")
        compose.add_standalone_service(protocol_name, node.ports)
        compose.add_explorer_service(ws_port=node.ports.ws_admin, standalone=True)
        if lab.add_ipfs:
            compose.add_ipfs_service(protocol_name)
        compose.write(os.path.join(base_dir, "docker-compose.yml"))

        # 7. Scripts
        ws_base = os.path.dirname(base_dir)
        write_file(
            os.path.join(base_dir, "start.sh"),
            ScriptBuilder.standalone_start(ws_base, protocol_name, name),
        )
        os.chmod(os.path.join(base_dir, "start.sh"), 0o755)
        write_file(
            os.path.join(base_dir, "stop.sh"),
            ScriptBuilder.standalone_stop(ws_base, protocol_name, name),
        )
        os.chmod(os.path.join(base_dir, "stop.sh"), 0o755)

    # ------------------------------------------------------------------
    # Network workflow
    # ------------------------------------------------------------------

    def _run_network(self):
        """Execute network workflow:

        1. Resolve features from source
        2. Create VL (validator list) keys
        3. Create validator keys for each node
        4. Create NodeConfigs for validators and peers
        5. Build config files for each node
        6. Parse amendments, write genesis for each node
        7. Create Dockerfiles and copy entrypoints
        8. Build docker-compose with all services
        9. Sign UNL and write VL artifacts
        10. Generate start/stop scripts
        """
        lab = self.lab
        spec = self.spec
        source = lab.build_source

        name = source.cluster_name or source.build_version
        protocol_name = lab.protocol.value
        cluster_dir = self.workspace.cluster_dir(name)

        # 1. Resolve features
        feature_content = self.resolver.resolve_features(source, spec)
        feature_lines = get_feature_lines_from_content(feature_content)

        # 1b. Resolve repo config and merge with overrides
        repo_config = self.resolver.resolve_repo_config(source, spec)
        effective_config = merge_config({}, repo_config, lab.config_overrides)

        # 1c. Binary: copy local or download from build server
        binary_name = f"xrpld.{name}"
        binary_dest = os.path.join(cluster_dir, binary_name)
        if source.binary_path:
            shutil.copy2(source.binary_path, binary_dest)
            os.chmod(binary_dest, 0o755)
        elif source.build_type == BuildType.BINARY:
            url = f"{source.build_server}/{source.build_version}"
            self.resolver.download_binary(url, binary_dest)

        # 2. Create VL keys
        algo = lab.key_algorithm
        original_dir = os.getcwd()
        os.chdir(cluster_dir)
        try:
            publisher = PublisherClient()
            vl_keys = publisher.get_keys()
            if not vl_keys:
                publisher.create_keys()
                vl_keys = publisher.get_keys()

            vl_pub_key = vl_keys["publicKey"]

            # 3. Create validator keys
            manifests: List[str] = []
            validators: List[str] = []
            tokens: List[str] = []
            ips_fixed: List[str] = []
            use_ansible = lab.ansible is not None

            for i in range(1, lab.num_validators + 1):
                node_name = f"vnode{i}"
                vc = ValidatorClient(node_name)
                key_path = f"keystore/{node_name}/key.json"
                if not os.path.exists(key_path):
                    vc.create_keys()
                    vc.set_domain(f"xahau.{node_name}.transia.co")
                    vc.create_token()
                keys = vc.get_keys()
                token = vc.read_token()
                manifest = vc.read_manifest()
                manifests.append(manifest)
                validators.append(keys["public_key"])
                tokens.append(token)

                ports = PortSet.for_node(i, NodeRole.VALIDATOR)
                if use_ansible and i <= len(lab.ansible.vips):
                    ips_fixed.append(f"{lab.ansible.vips[i - 1]} {ports.peer}")
                else:
                    ips_fixed.append(f"vnode{i} {ports.peer}")

        finally:
            os.chdir(original_dir)

        # 4-7. Create nodes, configs, genesis, dockerfiles
        compose = ComposeBuilder(f"{name}-network")
        image_name = source.image or "ubuntu:noble"
        ansible_image = f"transia/cluster:{source.commit_hash or source.build_version}"

        for i in range(1, lab.num_validators + 1):
            node_name = f"vnode{i}"
            node = NodeFactory.create_validator(
                index=i,
                protocol=lab.protocol,
                name=name,
                network_id=lab.network_id,
                token=tokens[i - 1],
                all_validators=validators,
                vl_key=vl_pub_key,
                ivl_key=lab.import_vl_key,
                ips_fixed=ips_fixed,
                log_level=lab.log_level,
                node_db_type=lab.node_db_type,
            )

            node_dir = self.workspace.node_dir(cluster_dir, node_name)
            cfg_path = self.workspace.config_dir(node_dir)
            self.workspace.log_dir(node_dir)

            # Config
            cfg_content = XrpldCfgBuilder(node).build()
            vl_content = ValidatorsTxtBuilder(node, genesis=True).build()
            save_config(protocol_name, cfg_path, cfg_content, vl_content)

            # Amendments + genesis
            features = parse_amendments(feature_lines)
            if not lab.genesis:
                features = {}
            genesis = update_genesis(features, protocol_name)
            write_file(
                os.path.join(node_dir, "genesis.json"),
                json.dumps(genesis, indent=4, sort_keys=True),
            )

            # Dockerfile
            dockerfile = DockerfileBuilder.build(
                protocol=protocol_name,
                ports=node.ports,
                image_name=image_name,
                network=True,
                binary=source.build_type == BuildType.BINARY,
                version=name,
                include_genesis=True,
                quorum=lab.effective_quorum,
                standalone="--valid" if lab.genesis else None,
            )
            write_file(os.path.join(node_dir, "Dockerfile"), dockerfile)

            # Entrypoint
            entrypoint_src = os.path.join(
                self.workspace.package_dir, "deploykit",
                spec.network_entrypoint_file,
            )
            if os.path.exists(entrypoint_src):
                shutil.copy2(
                    entrypoint_src, os.path.join(node_dir, "entrypoint")
                )

            # Compose service
            compose.add_node_service(
                node_name, node.ports, node.role, network=True
            )

        for i in range(1, lab.num_peers + 1):
            node_name = f"pnode{i}"
            node = NodeFactory.create_peer(
                index=i,
                protocol=lab.protocol,
                name=name,
                network_id=lab.network_id,
                validators=validators,
                vl_key=vl_pub_key,
                ivl_key=lab.import_vl_key,
                ips_fixed=ips_fixed,
                log_level=lab.log_level,
                node_db_type=lab.node_db_type,
            )

            node_dir = self.workspace.node_dir(cluster_dir, node_name)
            cfg_path = self.workspace.config_dir(node_dir)
            self.workspace.log_dir(node_dir)

            # Config
            cfg_content = XrpldCfgBuilder(node).build()
            vl_content = ValidatorsTxtBuilder(node, genesis=True).build()
            save_config(protocol_name, cfg_path, cfg_content, vl_content)

            # Amendments + genesis (peers always get all amendments)
            features = parse_amendments(feature_lines)
            genesis = update_genesis(features, protocol_name)
            write_file(
                os.path.join(node_dir, "genesis.json"),
                json.dumps(genesis, indent=4, sort_keys=True),
            )

            # Dockerfile
            dockerfile = DockerfileBuilder.build(
                protocol=protocol_name,
                ports=node.ports,
                image_name=image_name,
                network=True,
                binary=source.build_type == BuildType.BINARY,
                version=name,
                include_genesis=True,
                quorum=lab.effective_quorum,
                standalone="--valid" if lab.genesis else None,
            )
            write_file(os.path.join(node_dir, "Dockerfile"), dockerfile)

            # Entrypoint
            entrypoint_src = os.path.join(
                self.workspace.package_dir, "deploykit",
                spec.network_entrypoint_file,
            )
            if os.path.exists(entrypoint_src):
                shutil.copy2(
                    entrypoint_src, os.path.join(node_dir, "entrypoint")
                )

            # Compose service
            compose.add_node_service(
                node_name, node.ports, node.role, network=True
            )

        # 8. VL + explorer services
        compose.add_vl_service()
        compose.add_explorer_service(ws_port=6016, standalone=False)
        compose.write(os.path.join(cluster_dir, "docker-compose.yml"))

        # 9. Sign UNL and write VL artifacts
        vl_dir = os.path.join(cluster_dir, "vl")
        os.makedirs(vl_dir, exist_ok=True)

        original_dir = os.getcwd()
        os.chdir(cluster_dir)
        try:
            for manifest in manifests:
                publisher.add_validator(manifest)
            publisher.sign_unl(os.path.join(vl_dir, "vl.json"))
        finally:
            os.chdir(original_dir)

        # Copy nginx dockerfile for VL
        nginx_src = os.path.join(
            self.workspace.package_dir, "deploykit", "nginx.dockerfile",
        )
        if os.path.exists(nginx_src):
            shutil.copyfile(nginx_src, os.path.join(vl_dir, "Dockerfile"))

        # 10. Scripts
        write_executable(
            os.path.join(cluster_dir, "start.sh"),
            ScriptBuilder.network_start(
                name, lab.num_validators, lab.num_peers
            ),
        )
        write_executable(
            os.path.join(cluster_dir, "stop.sh"),
            ScriptBuilder.network_stop(
                name, lab.num_validators, lab.num_peers
            ),
        )

        # 11. Ansible deployment (if configured)
        if lab.ansible:
            self._generate_ansible(lab, cluster_dir, name, ansible_image)

    # ------------------------------------------------------------------
    # Ansible generation
    # ------------------------------------------------------------------

    def _generate_ansible(
        self, lab: LabConfig, cluster_dir: str, name: str, image_name: str
    ):
        """Generate ansible deployment files for the cluster."""
        ansible_builder = AnsibleBuilder(
            cluster_dir=cluster_dir,
            config=lab.ansible,
            image_name=image_name,
        )

        for i in range(1, lab.num_validators + 1):
            node_name = f"vnode{i}"
            ip = lab.ansible.vips[i - 1] if i <= len(lab.ansible.vips) else ""
            node_dir = self.workspace.node_dir(cluster_dir, node_name)
            cfg_path = self.workspace.config_dir(node_dir)
            ports = PortSet.for_node(i, NodeRole.VALIDATOR)
            ansible_builder.add_node(
                name=node_name,
                ip=ip,
                ports=ports,
                config_path=cfg_path,
                role="validator",
            )

        for i in range(1, lab.num_peers + 1):
            node_name = f"pnode{i}"
            ip = lab.ansible.pips[i - 1] if i <= len(lab.ansible.pips) else ""
            node_dir = self.workspace.node_dir(cluster_dir, node_name)
            cfg_path = self.workspace.config_dir(node_dir)
            ports = PortSet.for_node(i, NodeRole.PEER)
            ansible_builder.add_node(
                name=node_name,
                ip=ip,
                ports=ports,
                config_path=cfg_path,
                role="peer",
            )

        ansible_builder.write()

    # ------------------------------------------------------------------
    # Local network workflow
    # ------------------------------------------------------------------

    def _run_local_network(self):
        """Execute local network workflow:

        1. Resolve features from local source files
        2. Create VL keys
        3. Create validator keys
        4. Create NodeConfigs for local validators and peers
        5. Build config files for each node
        6. Parse amendments, write genesis for each node
        7. Build docker-compose for Docker-only services (VL + Explorer)
        8. Generate native start/stop scripts
        9. Sign UNL and write VL artifacts
        """
        lab = self.lab
        spec = self.spec

        name = f"local-{lab.protocol.value}"
        protocol_name = lab.protocol.value
        cluster_dir = self.workspace.cluster_dir(name)

        # 1. Resolve features from local source
        feature_lines: list = []
        for fpath in spec.feature_paths:
            candidate = os.path.join("..", fpath)
            if os.path.exists(candidate):
                feature_lines = get_feature_lines_from_path(candidate)
                break

        # 2-3. Create VL + validator keys
        algo = lab.key_algorithm
        original_dir = os.getcwd()
        os.chdir(cluster_dir)
        try:
            publisher = PublisherClient()
            vl_keys = publisher.get_keys()
            if not vl_keys:
                publisher.create_keys()
                vl_keys = publisher.get_keys()

            vl_pub_key = vl_keys["publicKey"]

            manifests: List[str] = []
            validators: List[str] = []
            tokens: List[str] = []
            ips_fixed: List[str] = []

            for i in range(1, lab.num_validators + 1):
                node_name = f"vnode{i}"
                vc = ValidatorClient(node_name)
                key_path = f"keystore/{node_name}/key.json"
                if not os.path.exists(key_path):
                    vc.create_keys()
                    vc.set_domain(f"xahau.{node_name}.transia.co")
                    vc.create_token()
                keys = vc.get_keys()
                token = vc.read_token()
                manifest = vc.read_manifest()
                manifests.append(manifest)
                validators.append(keys["public_key"])
                tokens.append(token)

                ports = PortSet.for_node(i, NodeRole.VALIDATOR)
                ips_fixed.append(f"127.0.0.1 {ports.peer}")

        finally:
            os.chdir(original_dir)

        # 4-6. Create nodes, configs, genesis
        for i in range(1, lab.num_validators + 1):
            node_name = f"vnode{i}"
            node = NodeFactory.create_local_validator(
                index=i,
                protocol=lab.protocol,
                name=name,
                network_id=lab.network_id,
                token=tokens[i - 1],
                all_validators=validators,
                vl_key=vl_pub_key,
                ivl_key=lab.import_vl_key,
                ips_fixed=ips_fixed,
                log_level=lab.log_level,
                node_db_type=lab.node_db_type,
            )

            node_dir = self.workspace.node_dir(cluster_dir, node_name)
            cfg_path = self.workspace.config_dir(node_dir)
            self.workspace.log_dir(node_dir)

            cfg_content = XrpldCfgBuilder(node).build()
            vl_content = ValidatorsTxtBuilder(node, genesis=True).build()
            save_config(protocol_name, cfg_path, cfg_content, vl_content)

            features = parse_amendments(feature_lines)
            genesis = update_genesis(features, protocol_name)
            write_file(
                os.path.join(cfg_path, "genesis.json"),
                json.dumps(genesis, indent=4, sort_keys=True),
            )

        for i in range(1, lab.num_peers + 1):
            node_name = f"pnode{i}"
            node = NodeFactory.create_local_peer(
                index=i,
                protocol=lab.protocol,
                name=name,
                network_id=lab.network_id,
                validators=validators,
                vl_key=vl_pub_key,
                ivl_key=lab.import_vl_key,
                ips_fixed=ips_fixed,
                log_level=lab.log_level,
                node_db_type=lab.node_db_type,
            )

            node_dir = self.workspace.node_dir(cluster_dir, node_name)
            cfg_path = self.workspace.config_dir(node_dir)
            self.workspace.log_dir(node_dir)

            cfg_content = XrpldCfgBuilder(node).build()
            vl_content = ValidatorsTxtBuilder(node, genesis=True).build()
            save_config(protocol_name, cfg_path, cfg_content, vl_content)

            features = parse_amendments(feature_lines)
            genesis = update_genesis(features, protocol_name)
            write_file(
                os.path.join(cfg_path, "genesis.json"),
                json.dumps(genesis, indent=4, sort_keys=True),
            )

        # 7. Docker compose for Docker-only services (VL + Explorer)
        compose = ComposeBuilder(f"{name}-network")
        compose.add_vl_service()
        compose.add_explorer_service(ws_port=6016, standalone=False)
        compose.write(os.path.join(cluster_dir, "docker-compose.yml"))

        # 8. Native start/stop scripts
        write_executable(
            os.path.join(cluster_dir, "start.sh"),
            ScriptBuilder.local_network_start(
                name, lab.num_validators, lab.num_peers, lab.binary_name
            ),
        )
        write_executable(
            os.path.join(cluster_dir, "stop.sh"),
            ScriptBuilder.local_network_stop(
                name, lab.num_validators, lab.num_peers
            ),
        )

        # 9. Sign UNL and write VL artifacts
        vl_dir = os.path.join(cluster_dir, "vl")
        os.makedirs(vl_dir, exist_ok=True)

        original_dir = os.getcwd()
        os.chdir(cluster_dir)
        try:
            for manifest in manifests:
                publisher.add_validator(manifest)
            publisher.sign_unl(os.path.join(vl_dir, "vl.json"))
        finally:
            os.chdir(original_dir)

        # Copy nginx dockerfile for VL
        nginx_src = os.path.join(
            self.workspace.package_dir, "deploykit", "nginx.dockerfile",
        )
        if os.path.exists(nginx_src):
            shutil.copyfile(nginx_src, os.path.join(vl_dir, "Dockerfile"))
