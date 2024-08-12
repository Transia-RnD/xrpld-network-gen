#!/usr/bin/env python
# coding: utf-8

import os
import yaml
import shutil
import json
from typing import List, Any, Dict

from xrpld_netgen.rippled_cfg import gen_config, RippledBuild
from xrpld_netgen.utils.deploy_kit import create_dockerfile, download_binary
from xrpld_netgen.libs.github import (
    get_commit_hash_from_server_version,
    download_file_at_commit_or_tag,
)
from xrpld_netgen.utils.misc import (
    generate_ports,
    save_local_config,
    bcolors,
    write_file,
    read_json,
)
from xrpld_netgen.libs.rippled import (
    update_amendments,
    parse_rippled_amendments,
    get_feature_lines_from_content,
    get_feature_lines_from_path,
)

basedir = os.path.abspath(os.path.dirname(__file__))


def generate_validator_config(protocol: str, network: str) -> str:
    try:
        config = read_json(f"{basedir}/deploykit/config.json")
        return config[protocol][network]
    except Exception as e:
        print(e)
        return None


deploykit_path: str = ""


services: Dict[str, Dict] = {}


def update_stop_sh(
    protocol: str,
    name: str,
    num_validators: int,
    num_peers: int,
    standalone: bool = False,
    local: bool = False,
) -> str:
    stop_sh_content = "#! /bin/bash\n"
    if num_validators > 0 and num_peers > 0:
        stop_sh_content += f"docker compose -f {basedir}/{protocol}-{name}/docker-compose.yml down --remove-orphans\n"  # noqa: E501

    for i in range(1, num_validators + 1):
        stop_sh_content += f"rm -r vnode{i}/lib\n"
        stop_sh_content += f"rm -r vnode{i}/log\n"

    for i in range(1, num_peers + 1):
        stop_sh_content += f"rm -r pnode{i}/lib\n"
        stop_sh_content += f"rm -r pnode{i}/log\n"

    if standalone:
        stop_sh_content += f"docker compose -f {basedir}/{protocol}-{name}/docker-compose.yml down --remove-orphans\n"  # noqa: E501
        stop_sh_content += f"rm -r {protocol}/config\n"
        stop_sh_content += f"rm -r {protocol}/lib\n"
        stop_sh_content += f"rm -r {protocol}/log\n"
        stop_sh_content += f"rm -r {protocol}\n"

    if local:
        stop_sh_content = (
            "#! /bin/bash\ndocker compose -f docker-compose.yml down --remove-orphans\n"
        )
        stop_sh_content += "rm -r db\n"
        stop_sh_content += "rm -r debug.log\n"

    return stop_sh_content


def create_standalone_folder(
    binary: bool,
    name: str,
    image: str,
    feature_content: str,
    network_id: int,
    vl_key: str,
    ivl_key: str,
    protocol: str,
    net_type: str,
    log_level: str,
):
    cfg_path = f"{basedir}/{protocol}-{name}/config"
    rpc_public, rpc_admin, ws_public, ws_admin, peer = generate_ports(0, "standalone")
    vl_config: Dict[str, Any] = generate_validator_config(protocol, net_type)

    if network_id:
        vl_config["network_id"] = network_id

    if vl_key:
        vl_config["validator_list_keys"] = [vl_key]

    if ivl_key:
        vl_config["import_vl_keys"] = [ivl_key]

    configs: List[RippledBuild] = gen_config(
        False,
        protocol,
        name,
        vl_config["network_id"],
        0,
        rpc_public,
        rpc_admin,
        ws_public,
        ws_admin,
        peer,
        "huge",
        10000,
        "/var/lib/rippled/db/nudb",
        "/var/lib/rippled/db",
        "/var/log/rippled/debug.log",
        log_level,
        None,
        vl_config["validator_list_sites"],
        vl_config["validator_list_keys"],
        vl_config["import_vl_keys"] if protocol == "xahau" else [],
        vl_config["ips"],
        vl_config["ips_fixed"],
    )
    os.makedirs(f"{basedir}/{protocol}-{name}/config", exist_ok=True)
    save_local_config(cfg_path, configs[0].data, configs[1].data)
    print(f"✅ {bcolors.CYAN}Creating config")

    lines: List[str] = get_feature_lines_from_content(feature_content)
    features_json: Dict[str, Any] = parse_rippled_amendments(lines)
    genesis_json: Any = update_amendments(features_json, protocol)
    write_file(
        f"{basedir}/{protocol}-{name}/genesis.json",
        json.dumps(genesis_json, indent=4, sort_keys=True),
    )
    print(f"✅ {bcolors.CYAN}Updating features")

    dockerfile: str = create_dockerfile(
        False,
        binary,
        name,
        image,
        rpc_public,
        rpc_admin,
        ws_public,
        ws_admin,
        peer,
        True,
        "",
        "-a",
    )
    with open(f"{basedir}/{protocol}-{name}/Dockerfile", "w") as file:
        file.write(dockerfile)

    shutil.copyfile(
        f"{basedir}/deploykit/{protocol}.entrypoint",
        f"{basedir}/{protocol}-{name}/entrypoint",
    )
    print(f"✅ {bcolors.CYAN}Building docker container...")
    pwd_str: str = "${PWD}"
    services[f"{protocol}"] = {
        "build": {
            "context": ".",
            "dockerfile": "Dockerfile",
        },
        "platform": "linux/x86_64",
        "container_name": f"{protocol}",
        "ports": [
            f"{rpc_public}:{rpc_public}",
            f"{rpc_admin}:{rpc_admin}",
            f"{ws_public}:{ws_public}",
            f"{ws_admin}:{ws_admin}",
            f"{peer}:{peer}",
        ],
        "volumes": [
            f"{pwd_str}/{protocol}/config:/etc/opt/ripple",
            f"{pwd_str}/{protocol}/log:/var/log/rippled",
            f"{pwd_str}/{protocol}/lib:/var/lib/rippled",
        ],
        "networks": ["standalone-network"],
    }


def create_standalone_image(
    log_level: str,
    public_key: str,
    import_key: str,
    protocol: str,
    net_type: str,
    network_id: int,
    build_system: str,
    build_name: str,
    add_ipfs: bool = False,
) -> None:
    name: str = build_name
    os.makedirs(f"{basedir}/{protocol}-{name}", exist_ok=True)
    owner = "XRPLF"
    repo = "rippled"
    content: str = download_file_at_commit_or_tag(
        owner, repo, build_name, "src/ripple/protocol/impl/Feature.cpp"
    )
    image: str = f"{build_system}/rippled:{build_name}"
    create_standalone_folder(
        False,
        name,
        image,
        content,
        network_id,
        public_key,
        import_key,
        protocol,
        net_type,
        log_level,
    )
    services["explorer"] = {
        "image": "transia/explorer:latest",
        "container_name": "explorer",
        "environment": [
            "PORT=4000",
            f"VUE_APP_WSS_ENDPOINT=ws://0.0.0.0:{6006}",
        ],
        "ports": ["4000:4000"],
        "networks": ["standalone-network"],
    }

    if add_ipfs:
        pwd_str: str = "${PWD}"
        services["ipfs"] = {
            "image": "ipfs/go-ipfs:latest",
            "container_name": "ipfs",
            "environment": [
                "IPFS_PROFILE=server",
            ],
            "ports": ["4001:4001", "5001:5001", "8080:8080"],
            "volumes": [
                f"{pwd_str}/{protocol}/ipfs_staging:/export",
                f"{pwd_str}/{protocol}/ipfs_data:/data/ipfs",
            ],
            "networks": ["standalone-network"],
        }

    compose = {
        "version": "3.9",
        "services": services,
        "networks": {"standalone-network": {"driver": "bridge"}},
    }

    with open(f"{basedir}/{protocol}-{name}/docker-compose.yml", "w") as f:
        yaml.dump(compose, f, default_flow_style=False)

    write_file(
        f"{basedir}/{protocol}-{name}/start.sh",
        f"""\
#! /bin/bash
docker compose -f {basedir}/{protocol}-{name}/docker-compose.yml up --build --force-recreate -d
""",  # noqa: E501
    )
    os.chmod(f"{basedir}/{protocol}-{name}/start.sh", 0o755)
    stop_sh_content: str = update_stop_sh(protocol, name, 0, 0, True)
    write_file(f"{basedir}/{protocol}-{name}/stop.sh", stop_sh_content)
    os.chmod(f"{basedir}/{protocol}-{name}/stop.sh", 0o755)


def create_binary_folder(
    binary: bool,
    name: str,
    image: str,
    feature_content: str,
    network_id: int,
    vl_key: str,
    ivl_key: str,
    protocol: str,
    net_type: str,
    log_level: str,
):
    cfg_path = f"{basedir}/{protocol}-{name}/config"
    rpc_public, rpc_admin, ws_public, ws_admin, peer = generate_ports(0, "standalone")
    vl_config: Dict[str, Any] = generate_validator_config(protocol, net_type)

    if network_id:
        vl_config["network_id"] = network_id

    if vl_key:
        vl_config["validator_list_keys"] = [vl_key]

    if ivl_key:
        vl_config["import_vl_keys"] = [ivl_key]

    configs: List[RippledBuild] = gen_config(
        False,
        protocol,
        name,
        vl_config["network_id"],
        0,
        rpc_public,
        rpc_admin,
        ws_public,
        ws_admin,
        peer,
        "huge",
        10000,
        "/var/lib/rippled/db/nudb",
        "/var/lib/rippled/db",
        "/var/log/rippled/debug.log",
        log_level,
        None,
        vl_config["validator_list_sites"],
        vl_config["validator_list_keys"],
        vl_config["import_vl_keys"] if protocol == "xahau" else [],
        vl_config["ips"],
        vl_config["ips_fixed"],
    )
    os.makedirs(f"{basedir}/{protocol}-{name}/config", exist_ok=True)
    save_local_config(cfg_path, configs[0].data, configs[1].data)
    print(f"✅ {bcolors.CYAN}Creating config")

    lines: List[str] = get_feature_lines_from_content(feature_content)
    features_json: Dict[str, Any] = parse_rippled_amendments(lines)
    genesis_json: Any = update_amendments(features_json, protocol)
    write_file(
        f"{basedir}/{protocol}-{name}/genesis.json",
        json.dumps(genesis_json, indent=4, sort_keys=True),
    )
    print(f"✅ {bcolors.CYAN}Updating features")
    # for k, v in features_json.items():
    #     print(f"{bcolors.GREEN}feature: {bcolors.BLUE}{k}")

    dockerfile: str = create_dockerfile(
        False,
        binary,
        name,
        image,
        rpc_public,
        rpc_admin,
        ws_public,
        ws_admin,
        peer,
        True,
        "",
        "-a",
    )
    with open(f"{basedir}/{protocol}-{name}/Dockerfile", "w") as file:
        file.write(dockerfile)

    shutil.copyfile(
        f"{basedir}/deploykit/{protocol}.entrypoint",
        f"{basedir}/{protocol}-{name}/entrypoint",
    )
    print(f"✅ {bcolors.CYAN}Building docker container...")
    pwd_str: str = "${PWD}"
    services[f"{protocol}"] = {
        "build": {
            "context": ".",
            "dockerfile": "Dockerfile",
        },
        "platform": "linux/x86_64",
        "container_name": f"{protocol}",
        "ports": [
            f"{rpc_public}:{rpc_public}",
            f"{rpc_admin}:{rpc_admin}",
            f"{ws_public}:{ws_public}",
            f"{ws_admin}:{ws_admin}",
            f"{peer}:{peer}",
        ],
        "volumes": [
            f"{pwd_str}/{protocol}/config:/etc/opt/ripple",
            f"{pwd_str}/{protocol}/log:/var/log/rippled",
            f"{pwd_str}/{protocol}/lib:/var/lib/rippled",
        ],
        "networks": ["standalone-network"],
    }


def create_standalone_binary(
    log_level: str,
    public_key: str,
    import_key: str,
    protocol: str,
    net_type: str,
    network_id: int,
    build_server: str,
    build_version: str,
    add_ipfs: bool = False,
) -> None:
    name: str = build_version
    os.makedirs(f"{basedir}/{protocol}-{name}", exist_ok=True)
    # Usage
    owner = "Xahau"
    repo = "xahaud"
    commit_hash = get_commit_hash_from_server_version(build_server, build_version)
    content: str = download_file_at_commit_or_tag(
        owner, repo, commit_hash, "src/ripple/protocol/impl/Feature.cpp"
    )
    url: str = f"{build_server}/{build_version}"
    download_binary(url, f"{basedir}/{protocol}-{name}/rippled.{name}")
    image: str = "ubuntu:jammy"
    create_binary_folder(
        True,
        name,
        image,
        content,
        network_id,
        public_key,
        import_key,
        protocol,
        net_type,
        log_level,
    )
    services["explorer"] = {
        "image": "transia/explorer:latest",
        "container_name": "explorer",
        "environment": [
            "PORT=4000",
            f"VUE_APP_WSS_ENDPOINT=ws://0.0.0.0:{6006}",
        ],
        "ports": ["4000:4000"],
        "networks": ["standalone-network"],
    }

    if add_ipfs:
        pwd_str: str = "${PWD}"
        services["ipfs"] = {
            "image": "ipfs/go-ipfs:latest",
            "container_name": "ipfs",
            "environment": [
                "IPFS_PROFILE=server",
            ],
            "ports": ["4001:4001", "5001:5001", "8080:8080"],
            "volumes": [
                f"{pwd_str}/{protocol}/ipfs_staging:/export",
                f"{pwd_str}/{protocol}/ipfs_data:/data/ipfs",
            ],
            "networks": ["standalone-network"],
        }

    compose = {
        "version": "3.9",
        "services": services,
        "networks": {"standalone-network": {"driver": "bridge"}},
    }

    with open(f"{basedir}/{protocol}-{name}/docker-compose.yml", "w") as f:
        yaml.dump(compose, f, default_flow_style=False)

    write_file(
        f"{basedir}/{protocol}-{name}/start.sh",
        f"""\
#! /bin/bash
docker compose -f {basedir}/{protocol}-{name}/docker-compose.yml up --build --force-recreate -d
""",  # noqa: E501
    )
    os.chmod(f"{basedir}/{protocol}-{name}/start.sh", 0o755)
    stop_sh_content: str = update_stop_sh(protocol, name, 0, 0, True)
    write_file(f"{basedir}/{protocol}-{name}/stop.sh", stop_sh_content)
    os.chmod(f"{basedir}/{protocol}-{name}/stop.sh", 0o755)


def create_local_folder(
    name: str,
    network_id: int,
    vl_key: str,
    ivl_key: str,
    protocol: str,
    net_type: str,
    log_level: str,
):
    cfg_path = "config"
    rpc_public, rpc_admin, ws_public, ws_admin, peer = generate_ports(0, "standalone")
    vl_config: Dict[str, Any] = generate_validator_config(protocol, net_type)

    if network_id:
        vl_config["network_id"] = network_id

    if vl_key:
        vl_config["validator_list_keys"] = [vl_key]

    if ivl_key:
        vl_config["import_vl_keys"] = [ivl_key]

    configs: List[RippledBuild] = gen_config(
        False,
        protocol,
        name,
        vl_config["network_id"],
        0,
        rpc_public,
        rpc_admin,
        ws_public,
        ws_admin,
        peer,
        "huge",
        10000,
        "db/nudb",
        "db",
        "debug.log",
        log_level,
        None,
        vl_config["validator_list_sites"],
        vl_config["validator_list_keys"],
        vl_config["import_vl_keys"] if protocol == "xahau" else [],
        vl_config["ips"],
        vl_config["ips_fixed"],
    )
    os.makedirs(cfg_path, exist_ok=True)
    save_local_config(cfg_path, configs[0].data, configs[1].data)
    print(f"✅ {bcolors.CYAN}Creating config")

    if protocol == "xahaud":
        content: str = get_feature_lines_from_path(
            "../src/ripple/protocol/impl/Feature.cpp"
        )
    if protocol == "xrpl":
        content: str = get_feature_lines_from_path(
            "../src/libxrpl/protocol/Feature.cpp"
        )
    features_json: Dict[str, Any] = parse_rippled_amendments(content)
    genesis_json: Any = update_amendments(features_json, protocol)
    write_file(
        f"{cfg_path}/genesis.json",
        json.dumps(genesis_json, indent=4, sort_keys=True),
    )
    print(f"✅ {bcolors.CYAN}Updating features")


def start_local(
    log_level: str,
    public_key: str,
    import_key: str,
    protocol: str,
    net_type: str,
    network_id: int,
) -> None:
    name: str = "local"
    os.makedirs(f"{basedir}/{protocol}-{name}", exist_ok=True)
    create_local_folder(
        name,
        network_id,
        public_key,
        import_key,
        protocol,
        net_type,
        log_level,
    )
    services["explorer"] = {
        "image": "transia/explorer:latest",
        "container_name": "explorer",
        "environment": [
            "PORT=4000",
            f"VUE_APP_WSS_ENDPOINT=ws://0.0.0.0:{6006}",
        ],
        "ports": ["4000:4000"],
        "networks": ["standalone-network"],
    }

    compose = {
        "version": "3.9",
        "services": services,
        "networks": {"standalone-network": {"driver": "bridge"}},
    }

    with open("docker-compose.yml", "w") as f:
        yaml.dump(compose, f, default_flow_style=False)

    write_file(
        "start.sh",
        f"""\
#! /bin/bash
docker compose -f docker-compose.yml up --build --force-recreate -d
./rippled {'-a' if net_type == 'standalone' else ''} --conf config/rippled.cfg --ledgerfile config/genesis.json
""",  # noqa: E501
    )
    os.chmod("start.sh", 0o755)
    stop_sh_content: str = update_stop_sh(protocol, name, 0, 0, False, True)
    write_file("stop.sh", stop_sh_content)
    os.chmod("stop.sh", 0o755)
    import sys
    import subprocess

    try:
        result = subprocess.run(
            ["./start.sh"],
            check=True,
            stdout=subprocess.DEVNULL,
            # stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            print(
                f"{bcolors.CYAN}{protocol.capitalize()} local running at: {bcolors.PURPLE}6006 {bcolors.END}"
            )
            print(f"{bcolors.CYAN}Explorer running / starting container{bcolors.END}")
            print(f"Listening at: {bcolors.PURPLE}http://localhost:4000{bcolors.END}")
        else:
            print(f"{bcolors.RED}ERROR{bcolors.END}", file=sys.stderr)
            sys.exit(1)
    except subprocess.CalledProcessError:
        print(
            f"{bcolors.RED}❌ Cannot connect to the Docker daemon at docker.sock. Is the docker daemon running?{bcolors.END}"
        )
        sys.exit(1)
