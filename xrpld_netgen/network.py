#!/usr/bin/env python
# coding: utf-8

import os
import yaml
import shutil
import subprocess
from typing import List, Any, Dict, Tuple
from dotenv import load_dotenv

load_dotenv()

from xrpld_netgen.rippled_cfg import gen_config, RippledBuild
from xrpld_netgen.utils.deploy_kit import (
    create_dockerfile,
    download_binary,
    update_dockerfile,
)
from xrpld_netgen.libs.github import (
    get_commit_hash_from_server_version,
    download_file_at_commit,
)
from xrpld_netgen.utils.misc import (
    run_file,
    run_command,
    generate_ports,
    save_local_config,
    get_node_port,
)

from xrpl_helpers.common.utils import write_file, read_json
from xrpl_helpers.rippled.utils import (
    update_amendments,
    parse_rippled_amendments,
    get_feature_lines_from_content,
    get_feature_lines_from_path,
)

from xrpld_publisher.publisher import PublisherClient
from xrpld_publisher.validator import ValidatorClient

basedir = os.path.abspath(os.path.dirname(__file__))

RPC_PUBLIC: int = 5005
RPC_ADMIN: int = 5015
WS_PUBLIC: int = 6016
WS_ADMIN: int = 6018
PEER: int = 51235

deploykit_path: str = ""


def generate_validator_config(protocol: str, network: str):
    try:
        config = read_json(f"{basedir}/deploykit/config.json")
        return config[protocol][network]
    except Exception as e:
        return None


import requests
import os
import json


services: Dict[str, Dict] = {}


def create_node_folders(
    binary: bool,
    name: str,
    image: str,
    feature_content: str,
    num_validators: int,
    num_peers: int,
    network_id: int,
    genesis: bool,
    quorum: int,
    vl_key: str,
    ivl_key: str,
    protocol: str,
):
    # Create directories for validator nodes
    ips_fixed: List[str] = []
    for i in range(1, num_validators + 1):
        node_dir = f"vnode{i}"
        _, _, _, _, peer = generate_ports(i, "validator")
        ips_fixed.append(f"{node_dir} {peer}")

    manifests: List[str] = []
    for i in range(1, num_validators + 1):
        node_dir = f"vnode{i}"
        cfg_path = f"{basedir}/{name}-cluster/{node_dir}/config"
        # GENERATE VALIDATOR KEY
        client = ValidatorClient(node_dir)
        client.create_keys()
        client.set_domain(f"xahau.{node_dir}.transia.co")
        client.create_token()
        token = client.read_token()
        client.create_manifest()
        manifest = client.read_manifest()
        manifests.append(manifest)
        # GENERATE PORTS
        rpc_public, rpc_admin, ws_public, ws_admin, peer = generate_ports(
            i, "validator"
        )
        # GENERATE CONFIG
        configs: List[RippledBuild] = gen_config(
            name,
            network_id,
            i,
            rpc_public,
            rpc_admin,
            ws_public,
            ws_admin,
            peer,
            "/var/lib/rippled/db/nudb",
            "/var/lib/rippled/db",
            "/var/log/rippled/debug.log",
            token,
            [f"http://vl/vl.json"],
            [vl_key],
            [ivl_key] if ivl_key else [],
            [],
            [ips for ips in ips_fixed if ips != f"{node_dir} {peer}"],
        )

        os.makedirs(f"{basedir}/{name}-cluster/{node_dir}", exist_ok=True)
        os.makedirs(f"{basedir}/{name}-cluster/{node_dir}/config", exist_ok=True)
        save_local_config(cfg_path, configs[0].data, configs[1].data)

        lines: List[str] = get_feature_lines_from_content(feature_content)
        features_json: Dict[str, Any] = parse_rippled_amendments(lines)
        if genesis:
            genesis_json: Any = update_amendments(features_json, protocol)
            write_file(
                f"{basedir}/{name}-cluster/{node_dir}/genesis.json",
                json.dumps(genesis_json, indent=4, sort_keys=True),
            )

        write_file(
            f"{basedir}/{name}-cluster/{node_dir}/features.json",
            json.dumps(features_json, indent=4, sort_keys=True),
        )

        shutil.copyfile(
            f"{basedir}/{name}-cluster/rippled.{name}",
            f"{basedir}/{name}-cluster/{node_dir}/rippled.{name}",
        )
        os.chmod(f"{basedir}/{name}-cluster/{node_dir}/rippled.{name}", 0o755)

        dockerfile: str = create_dockerfile(
            binary,
            name,
            image,
            rpc_public,
            rpc_admin,
            ws_public,
            ws_admin,
            peer,
            genesis,
            quorum,
            "",
        )
        with open(f"{basedir}/{name}-cluster/{node_dir}/Dockerfile", "w") as file:
            file.write(dockerfile)

        shutil.copyfile(
            f"{basedir}/deploykit/entrypoint",
            f"{basedir}/{name}-cluster/{node_dir}/entrypoint",
        )

        pwd_str: str = "${PWD}"
        services[f"vnode{i}"] = {
            "build": {
                "context": f"vnode{i}",
                "dockerfile": "Dockerfile",
            },
            "platform": "linux/x86_64",
            "container_name": f"vnode{i}",
            "ports": [
                f"{rpc_public}:{rpc_public}",
                f"{rpc_admin}:{rpc_admin}",
                f"{ws_public}:{ws_public}",
                f"{ws_admin}:{ws_admin}",
                f"{peer}:{peer}",
            ],
            "volumes": [
                f"{pwd_str}/vnode{i}/log:/var/log/rippled",
                f"{pwd_str}/vnode{i}/lib:/var/lib/rippled",
            ],
            "networks": [f"{name}-network"],
        }
        services[f"vnode{i}-explorer"] = {
            "image": "transia/explorer:latest",
            "container_name": f"vnode{i}-explorer",
            "environment": [
                f"PORT=410{i}",
                f"VUE_APP_WSS_ENDPOINT=ws://0.0.0.0:{ws_admin}",
            ],
            "ports": [f"410{i}:410{i}"],
            "networks": [f"{name}-network"],
        }

    for i in range(1, num_peers + 1):
        node_dir = f"pnode{i}"
        cfg_path = f"{basedir}/{name}-cluster/{node_dir}/config"
        rpc_public, rpc_admin, ws_public, ws_admin, peer = generate_ports(i, "peer")
        configs: List[RippledBuild] = gen_config(
            name,
            network_id,
            i,
            rpc_public,
            rpc_admin,
            ws_public,
            ws_admin,
            peer,
            "/var/lib/rippled/db/nudb",
            "/var/lib/rippled/db",
            "/var/log/rippled/debug.log",
            None,
            [f"http://vl/vl.json"],
            [vl_key],
            [ivl_key] if ivl_key else [],
            [],
            ips_fixed,
        )
        # print(f'CONFIG: {configs}')
        os.makedirs(f"{basedir}/{name}-cluster/{node_dir}", exist_ok=True)
        os.makedirs(f"{basedir}/{name}-cluster/{node_dir}/config", exist_ok=True)
        save_local_config(cfg_path, configs[0].data, configs[1].data)

        lines: List[str] = get_feature_lines_from_content(feature_content)
        features_json: Dict[str, Any] = parse_rippled_amendments(lines)
        if genesis:
            genesis_json: Any = update_amendments(features_json, protocol)
            write_file(
                f"{basedir}/{name}-cluster/{node_dir}/genesis.json",
                json.dumps(genesis_json, indent=4, sort_keys=True),
            )

        write_file(
            f"{basedir}/{name}-cluster/{node_dir}/features.json",
            json.dumps(features_json, indent=4, sort_keys=True),
        )

        shutil.copyfile(
            f"{basedir}/{name}-cluster/rippled.{name}",
            f"{basedir}/{name}-cluster/{node_dir}/rippled.{name}",
        )
        os.chmod(f"{basedir}/{name}-cluster/{node_dir}/rippled.{name}", 0o755)

        dockerfile: str = create_dockerfile(
            binary,
            name,
            image,
            rpc_public,
            rpc_admin,
            ws_public,
            ws_admin,
            peer,
            genesis,
            quorum,
            "",
        )
        with open(f"{basedir}/{name}-cluster/{node_dir}/Dockerfile", "w") as file:
            file.write(dockerfile)

        shutil.copyfile(
            f"{basedir}/deploykit/entrypoint",
            f"{basedir}/{name}-cluster/{node_dir}/entrypoint",
        )
        pwd_str: str = "${PWD}"
        services[f"pnode{i}"] = {
            "build": {
                "context": f"pnode{i}",
                "dockerfile": "Dockerfile",
            },
            "platform": "linux/x86_64",
            "container_name": f"pnode{i}",
            "ports": [
                f"{rpc_public}:{rpc_public}",
                f"{rpc_admin}:{rpc_admin}",
                f"{ws_public}:{ws_public}",
                f"{ws_admin}:{ws_admin}",
                f"{peer}:{peer}",
            ],
            "volumes": [
                f"{pwd_str}/pnode{i}/log:/var/log/rippled",
                f"{pwd_str}/pnode{i}/lib:/var/lib/rippled",
            ],
            "networks": [f"{name}-network"],
        }
        services[f"pnode{i}-explorer"] = {
            "image": "transia/explorer:latest",
            "container_name": f"pnode{i}-explorer",
            "environment": [
                f"PORT=401{i}",
                f"VUE_APP_WSS_ENDPOINT=ws://0.0.0.0:{ws_admin}",
            ],
            "ports": [f"401{i}:401{i}"],
            "networks": [f"{name}-network"],
        }

    return manifests


def update_stop_sh(
    protocol: str,
    name: str,
    num_validators: int,
    num_peers: int,
    standalone: bool = False,
    local: bool = False,
) -> str:
    stop_sh_content = f"#! /bin/bash\n"
    if num_validators > 0 and num_peers > 0:
        stop_sh_content += f"docker compose -f {basedir}/{name}-cluster/docker-compose.yml down --remove-orphans\n"

    for i in range(1, num_validators + 1):
        stop_sh_content += f"rm -r {basedir}/{name}-cluster/vnode{i}/lib\n"
        stop_sh_content += f"rm -r {basedir}/{name}-cluster/vnode{i}/log\n"

    for i in range(1, num_peers + 1):
        stop_sh_content += f"rm -r {basedir}/{name}-cluster/pnode{i}/lib\n"
        stop_sh_content += f"rm -r {basedir}/{name}-cluster/pnode{i}/log\n"

    if standalone:
        stop_sh_content += f"docker compose -f {basedir}/{protocol}-{name}/docker-compose.yml down --remove-orphans\n"
        stop_sh_content += f"rm -r {protocol}/config\n"
        stop_sh_content += f"rm -r {protocol}/lib\n"
        stop_sh_content += f"rm -r {protocol}/log\n"
        stop_sh_content += f"rm -r {protocol}\n"

    if local:
        stop_sh_content = f"#! /bin/bash\ndocker compose -f docker-compose.yml down --remove-orphans\n"
        stop_sh_content += f"rm -r db\n"
        stop_sh_content += f"rm -r debug.log\n"

    return stop_sh_content


def create_network_binary(
    public_key: str,
    import_key: str,
    private_key: str,
    manifest: str,
    protocol: str,
    num_validators: int,
    num_peers: int,
    network_id: int,
    build_server: str,
    build_version: str,
    genesis: bool = False,
    quorum: int = None,
) -> None:
    name: str = build_version
    os.makedirs(f"{basedir}/{name}-cluster", exist_ok=True)
    # Usage
    owner = "Xahau"
    repo = "xahaud"
    commit_hash = get_commit_hash_from_server_version(build_server, build_version)
    content: str = download_file_at_commit(
        owner, repo, commit_hash, "src/ripple/protocol/impl/Feature.cpp"
    )
    url: str = f"{build_server}/{build_version}"
    download_binary(url, f"{basedir}/{name}-cluster/rippled.{build_version}")
    image: str = "ubuntu:jammy"
    manifests: List[str] = create_node_folders(
        True,
        name,
        image,
        content,
        num_validators,
        num_peers,
        network_id,
        genesis,
        quorum,
        public_key,
        import_key,
        protocol,
    )

    services["vl"] = {
        "build": {
            "context": "vl",
            "dockerfile": "Dockerfile",
        },
        "container_name": "vl",
        "ports": ["80:80"],
        "networks": [f"{name}-network"],
    }

    compose = {
        "version": "3.9",
        "services": services,
        "networks": {f"{name}-network": {"driver": "bridge"}},
    }
    with open(f"{basedir}/{name}-cluster/docker-compose.yml", "w") as f:
        yaml.dump(compose, f, default_flow_style=False)

    write_file(
        f"{basedir}/{name}-cluster/start.sh",
        f"""\
#! /bin/bash
docker compose -f {basedir}/{name}-cluster/docker-compose.yml up --build --force-recreate -d
""",
    )
    stop_sh_content: str = update_stop_sh(protocol, name, num_validators, num_peers)
    write_file(f"{basedir}/{name}-cluster/stop.sh", stop_sh_content)

    os.makedirs(f"{basedir}/{name}-cluster/vl", exist_ok=True)
    client = PublisherClient(manifest)
    for manifest in manifests:
        client.add_validator(manifest)
    print(private_key)
    print(f"{basedir}/{name}-cluster/vl/vl.json")
    print(os.getenv("BIN_PATH"))
    client.sign_unl(private_key, f"{basedir}/{name}-cluster/vl/vl.json")
    shutil.copyfile(
        f"{basedir}/deploykit/nginx.dockerfile",
        f"{basedir}/{name}-cluster/vl/Dockerfile",
    )

    os.chmod(f"{basedir}/{name}-cluster/start.sh", 0o755)
    os.chmod(f"{basedir}/{name}-cluster/stop.sh", 0o755)


def update_node_binary(
    name: str,
    node_id: str,
    node_type: str,
    build_server: str,
    new_version: str,
) -> None:
    node_dir: str = f"{'v' if node_type == 'validator' else 'p'}node{node_id}"
    run_command(f"{basedir}/{name}", f"docker-compose stop {node_dir}")
    url: str = f"{build_server}/{new_version}"
    download_binary(url, f"{basedir}/{name}/rippled.{new_version}")
    shutil.copyfile(
        f"{basedir}/{name}/rippled.{new_version}",
        f"{basedir}/{name}/{node_dir}/rippled.{new_version}",
    )
    os.chmod(f"{basedir}/{name}/{node_dir}/rippled.{new_version}", 0o755)
    update_dockerfile(new_version, f"{basedir}/{name}/{node_dir}/Dockerfile")
    run_command(
        f"{basedir}/{name}",
        f"docker compose up --build --force-recreate -d {node_dir}",
    )


def enable_node_amendment(
    name: str,
    amendment_name: str,
    node_id: str,
    node_type: str,
) -> None:
    node_dir: str = f"{'v' if node_type == 'validator' else 'p'}node{node_id}"
    features: Dict[str, Any] = read_json(f"{basedir}/{name}/{node_dir}/features.json")
    amendment_hash: str = features[amendment_name]
    command: Dict[str, Any] = {
        "method": "feature",
        "params": [
            {
                "feature": amendment_hash,
                "vetoed": False,
            }
        ],
    }
    port: int = get_node_port(int(node_id), node_type)
    json_str: str = json.dumps(command)
    escaped_str = json_str.replace('"', '\\"')
    command: str = f'curl -X POST -H "Content-Type: application/json" -d "{escaped_str}" http://localhost:{port}'
    run_command(f"{basedir}/{name}", command)
