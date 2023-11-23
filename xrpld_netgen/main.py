#!/usr/bin/env python
# coding: utf-8

import os
import yaml
import shutil
import subprocess
from typing import List, Any, Dict, Tuple

from xrpld_netgen.rippled_cfg import generate_rippled_cfg, RippledBuild
from xrpld_netgen.utils.deploy_kit import create_dockerfile, download_binary
from xrpld_netgen.libs.github import (
    get_commit_hash_from_server_version,
    download_file_at_commit,
)
from xrpl_helpers.common.utils import write_file
from xrpl_helpers.rippled.utils import (
    update_amendments,
    parse_rippled_amendments,
    get_feature_lines_from_content,
    get_feature_lines_from_path,
)

from xrpld_publisher.publisher import PublisherClient
from xrpld_publisher.validator import ValidatorClient

basedir = os.path.abspath(os.path.dirname(__file__))


def remove_directory(directory_path: str):
    try:
        shutil.rmtree(directory_path)
        print(f"Directory '{directory_path}' has been removed successfully.")
    except FileNotFoundError:
        print(f"The directory '{directory_path}' does not exist.")
    except PermissionError:
        print(f"Permission denied: Unable to remove '{directory_path}'.")
    except Exception as e:
        print(f"An error occurred: {e}")


def run_file(file_path):
    try:
        # Run the file as a subprocess
        result = subprocess.run(file_path, check=True)
        print(result)
        print(f"File {file_path} executed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while trying to run the file: {e}")
    except FileNotFoundError:
        print(f"The file {file_path} does not exist or cannot be found.")
    except OSError as e:
        print(f"An error occurred while trying to run the file: {e}")


def gen_config(
    name: str,
    network_id: int,
    index: int,
    rpc_public: int,
    rpc_admin: int,
    ws_public: int,
    ws_admin: int,
    peer: int,
    nudb_path: str,
    db_path: str,
    debug_path: str,
    v_token: str,
    vl_site: str,
    vl_key: str,
    ivl_key: str,
    ips_fixed_urls: List[str] = [],
) -> List[RippledBuild]:
    configs: List[RippledBuild] = generate_rippled_cfg(
        # App
        build_path="/",
        node_index=index,
        network=name,
        network_id=network_id,
        # Rippled
        is_rpc_public=True,
        rpc_public_port=rpc_public,
        is_rpc_admin=True,
        rpc_admin_port=rpc_admin,
        is_ws_public=True,
        ws_public_port=ws_public,
        is_ws_admin=True,
        ws_admin_port=ws_admin,
        is_peer=True,
        peer_port=peer,
        # ssl_verify=1 if _node.ssl_verify else 0,
        ssl_verify=0,
        is_ssl=True,
        key_path=None,
        crt_path=None,
        size_node="medium",
        nudb_path=nudb_path,
        db_path=db_path,
        num_ledgers=256,
        debug_path=debug_path,
        log_level="trace",
        # private_peer=1 if _node.private_peer and i == 1 else 0,
        private_peer=0,
        genesis=False,
        v_token=v_token,
        validator_list_sites=[vl_site],
        validator_list_keys=[vl_key],
        import_vl_keys=[ivl_key],
        ips_urls=[],
        ips_fixed_urls=ips_fixed_urls,
        amendment_majority_time=None,
        amendments_dict={},
    )
    return configs


RPC_PUBLIC: int = 5005
RPC_ADMIN: int = 5015
WS_PUBLIC: int = 6016
WS_ADMIN: int = 6018
PEER: int = 51235


def generate_ports(index, node_type):
    if node_type == "validator":
        rpc_public = RPC_PUBLIC + (index * 100)
        rpc_admin = RPC_ADMIN + (index * 100)
        ws_public = WS_PUBLIC + (index * 100)
        ws_admin = WS_ADMIN + (index * 100)
        peer = PEER + (index * 100)
    elif node_type == "peer":
        rpc_public = RPC_PUBLIC + (index * 10)
        rpc_admin = RPC_ADMIN + (index * 10)
        ws_public = WS_PUBLIC + (index * 10)
        ws_admin = WS_ADMIN + (index * 10)
        peer = PEER + (index * 10)
    elif node_type == "standalone":
        rpc_public = 5007
        rpc_admin = 5005
        ws_public = 6008
        ws_admin = 6006
        peer = PEER
    else:
        raise ValueError("Invalid node type. Must be 'validator' or 'peer'.")

    return rpc_public, rpc_admin, ws_public, ws_admin, peer


deploykit_path: str = ""


def save_local_config(cfg_path: str, cfg_out: str, validators_out: str):
    with open(f"{cfg_path}/rippled.cfg", "w") as text_file:
        text_file.write(cfg_out)

    with open(f"{cfg_path}/validators.txt", "w") as text_file:
        text_file.write(validators_out)


def parse_image_name(image_name: str) -> str:
    # Get the image name
    name = image_name.split(":")[0]
    # Get the version
    version = image_name.split(":")[1]
    return name, version


import requests
import os
import json


def download_json(url, destination_dir):
    # Make sure destination directory exists
    os.makedirs(destination_dir, exist_ok=True)

    # Get the file name from the url
    file_name = url.split("/")[-1]

    # Send a HTTP request to the URL
    response = requests.get(url)

    # Check if the request is successful
    if response.status_code == 200:
        # Parse the JSON data from the response
        data = response.json()

        # Open the destination file in write mode
        with open(os.path.join(destination_dir, file_name), "w") as f:
            # Write the JSON data to the file
            json.dump(data, f)
        return data
    else:
        raise ValueError(f"Failed to download file from {url}")


services: Dict[str, Dict] = {}


def create_node_folders(
    name: str,
    image: str,
    storage_url: str,
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
        root_path = f"{name}-cluster/{node_dir}"
        cfg_path = f"{name}-cluster/{node_dir}/config"
        # GENERATE VALIDATOR KEY
        client = ValidatorClient(node_dir)
        client.create_keys()
        client.set_domain(f"{name}.{node_dir}.transia.co")
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
            f"http://vl/vl.json",
            ivl_key,
            vl_key,
            [ips for ips in ips_fixed if ips != f"{node_dir} {peer}"],
        )

        os.makedirs(f"{name}-cluster/{node_dir}", exist_ok=True)
        os.makedirs(f"{name}-cluster/{node_dir}/config", exist_ok=True)
        save_local_config(cfg_path, configs[0].data, configs[1].data)
        features_json: Dict[str, Any] = download_json(
            f"{storage_url}/features.json", f"{name}-cluster"
        )
        if genesis:
            genesis_json: Any = update_amendments(features_json, protocol)
            write_file("genesis.json", genesis_json)

        dockerfile: str = create_dockerfile(
            image, rpc_public, rpc_admin, ws_public, ws_admin, peer, genesis, 0, False
        )
        with open(f"{name}-cluster/{node_dir}/Dockerfile", "w") as file:
            file.write(dockerfile)

        shutil.copyfile(
            f"{basedir}/deploykit/entrypoint", f"{name}-cluster/{node_dir}/entrypoint"
        )

        pwd_str: str = "${PWD}"
        services[f"vnode{i}"] = {
            "build": {
                "context": f"vnode{i}",
                "dockerfile": "Dockerfile",
            },
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

    for i in range(1, num_peers + 1):
        node_dir = f"pnode{i}"
        root_path = f"{name}-cluster/{node_dir}"
        cfg_path = f"{name}-cluster/{node_dir}/config"
        print(f"IR: {node_dir}")
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
            f"http://vl/vl.json",
            ivl_key,
            vl_key,
            ips_fixed,
        )
        # print(f'CONFIG: {configs}')
        os.makedirs(f"{name}-cluster/{node_dir}", exist_ok=True)
        os.makedirs(f"{name}-cluster/{node_dir}/config", exist_ok=True)
        save_local_config(cfg_path, configs[0].data, configs[1].data)
        dockerfile: str = create_dockerfile(
            image, rpc_public, rpc_admin, ws_public, ws_admin, peer, False, 0, False
        )
        with open(f"{name}-cluster/{node_dir}/Dockerfile", "w") as file:
            file.write(dockerfile)

        shutil.copyfile(
            f"{basedir}/deploykit/entrypoint", f"{name}-cluster/{node_dir}/entrypoint"
        )
        pwd_str: str = "${PWD}"
        services[f"pnode{i}"] = {
            "build": {
                "context": f"pnode{i}",
                "dockerfile": "Dockerfile",
            },
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

    return manifests


def update_stop_sh(
    name: str,
    num_validators: int,
    num_peers: int,
    standalone: bool = False,
    local: bool = False,
) -> str:
    if num_validators > 0 and num_peers > 0 or standalone:
        stop_sh_content = f"#! /bin/bash\ndocker compose -f {basedir}/xrpld-{name}/docker-compose.yml down --remove-orphans\n"

    for i in range(1, num_validators + 1):
        stop_sh_content += f"rm -r /vnode{i}/config\n"
        stop_sh_content += f"rm -r /vnode{i}/lib\n"
        stop_sh_content += f"rm -r vnode{i}/log\n"
        stop_sh_content += f"rm -r xrpld\n"

    for i in range(1, num_peers + 1):
        stop_sh_content += f"rm -r pnode{i}/config\n"
        stop_sh_content += f"rm -r pnode{i}/lib\n"
        stop_sh_content += f"rm -r pnode{i}/log\n"
        stop_sh_content += f"rm -r xrpld\n"

    if standalone:
        stop_sh_content += f"rm -r xrpld/config\n"
        stop_sh_content += f"rm -r xrpld/lib\n"
        stop_sh_content += f"rm -r xrpld/log\n"
        stop_sh_content += f"rm -r xrpld\n"

    if local:
        stop_sh_content = f"#! /bin/bash\ndocker compose -f docker-compose.yml down --remove-orphans\n"
        stop_sh_content += f"rm -r db\n"
        stop_sh_content += f"rm -r debug.log\n"

    return stop_sh_content


def create_network(
    public_key: str,
    import_key: str,
    private_key: str,
    manifest: str,
    protocol: str,
    name: str,
    num_validators: int,
    num_peers: int,
    network_id: int,
    build_name: str,
    genesis: bool = False,
    quorum: int = None,
) -> None:
    image_name, version = parse_image_name(build_name)
    root_url = f"https://storage.googleapis.com/thelab-builds/"
    storage_url: str = (
        root_url + f"{image_name.split('-')[0]}/{image_name.split('-')[1]}/{version}"
    )
    image: str = f"gcr.io/thelab-924f3/{build_name}"
    manifests: List[str] = create_node_folders(
        name,
        image,
        storage_url,
        num_validators,
        num_peers,
        network_id,
        genesis,
        quorum,
        public_key,
        import_key,
        protocol,
    )
    services["explorer"] = {
        "image": "transia/explorer:latest",
        "container_name": "explorer",
        "environment": [
            "PORT=4000",
            f"VUE_APP_WSS_ENDPOINT=ws://0.0.0.0:{6008 + (num_validators-1)*10}",
        ],
        "ports": ["4000:4000"],
        "networks": [f"{name}-network"],
    }

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
        f"{name}-cluster/start.sh",
        f"""\
#! /bin/bash
docker compose -f {basedir}/{name}-cluster/docker-compose.yml up --build --force-recreate -d
""",
    )
    stop_sh_content: str = update_stop_sh(name, num_validators, num_peers)
    write_file(f"{name}-cluster/stop.sh", stop_sh_content)

    os.makedirs(f"{name}-cluster/vl", exist_ok=True)
    client = PublisherClient(manifest)
    for manifest in manifests:
        client.add_validator(manifest)

    client.sign_unl(private_key, f"{name}-cluster/vl/vl.json")
    shutil.copyfile(
        f"{basedir}/deploykit/nginx.dockerfile", f"{name}-cluster/vl/Dockerfile"
    )


def create_standalone_folder(
    binary: bool,
    name: str,
    image: str,
    features_url: str,
    network_id: int,
    vl_key: str,
    ivl_key: str,
    protocol: str,
):
    cfg_path = f"{basedir}/xrpld-{name}/config"
    rpc_public, rpc_admin, ws_public, ws_admin, peer = generate_ports(0, "standalone")
    configs: List[RippledBuild] = gen_config(
        name,
        network_id,
        0,
        rpc_public,
        rpc_admin,
        ws_public,
        ws_admin,
        peer,
        "/var/lib/rippled/db/nudb",
        "/var/lib/rippled/db",
        "/var/log/rippled/debug.log",
        None,
        f"http://vl/vl.json",
        vl_key,
        ivl_key,
        [f"0.0.0.0 {peer}"],
    )
    os.makedirs(f"{basedir}/xrpld-{name}/config", exist_ok=True)
    save_local_config(cfg_path, configs[0].data, configs[1].data)
    features_json: Dict[str, Any] = download_json(
        features_url, f"{basedir}/xrpld-{name}"
    )
    genesis_json: Any = update_amendments(features_json, protocol)
    write_file(
        f"{basedir}/xrpld-{name}/genesis.json",
        json.dumps(genesis_json, indent=4, sort_keys=True),
    )
    dockerfile: str = create_dockerfile(
        binary,
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
    with open(f"{basedir}/xrpld-{name}/Dockerfile", "w") as file:
        file.write(dockerfile)

    shutil.copyfile(
        f"{basedir}/deploykit/entrypoint", f"{basedir}/xrpld-{name}/entrypoint"
    )
    pwd_str: str = "${PWD}"
    services["xrpld"] = {
        "build": {
            "context": ".",
            "dockerfile": "Dockerfile",
        },
        "platform": "linux/x86_64",
        "container_name": "xrpld",
        "ports": [
            f"{rpc_public}:{rpc_public}",
            f"{rpc_admin}:{rpc_admin}",
            f"{ws_public}:{ws_public}",
            f"{ws_admin}:{ws_admin}",
            f"{peer}:{peer}",
        ],
        "volumes": [
            f"{pwd_str}/xrpld/config:/etc/opt/ripple",
            f"{pwd_str}/xrpld/log:/var/log/rippled",
            f"{pwd_str}/xrpld/lib:/var/lib/rippled",
        ],
        "networks": ["standalone-network"],
    }


def create_standalone_image(
    public_key: str,
    import_key: str,
    protocol: str,
    network_id: int,
    build_system: str,
    build_name: str,
) -> None:
    name: str = "standalone"
    image_name, version = parse_image_name(build_name)
    root_url = f"https://storage.googleapis.com/thelab-builds/"
    storage_url: str = (
        root_url + f"{image_name.split('-')[0]}/{image_name.split('-')[1]}/{version}"
    )
    image: str = f"{build_system}/{build_name}"
    create_standalone_folder(
        False,
        name,
        image,
        f"{storage_url}/features.json",
        network_id,
        public_key,
        import_key,
        protocol,
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

    with open(f"{basedir}/xrpld-{name}/docker-compose.yml", "w") as f:
        yaml.dump(compose, f, default_flow_style=False)

    write_file(
        f"{basedir}/xrpld-{name}/start.sh",
        f"""\
#! /bin/bash
docker compose -f {basedir}/xrpld-{name}/docker-compose.yml up --build --force-recreate -d
""",
    )
    stop_sh_content: str = update_stop_sh(name, 0, 0, True)
    write_file(f"{basedir}/xrpld-{name}/stop.sh", stop_sh_content)


def create_binary_folder(
    binary: bool,
    name: str,
    image: str,
    feature_content: str,
    network_id: int,
    vl_key: str,
    ivl_key: str,
    protocol: str,
):
    cfg_path = f"{basedir}/{protocol}-{name}/config"
    rpc_public, rpc_admin, ws_public, ws_admin, peer = generate_ports(0, "standalone")
    configs: List[RippledBuild] = gen_config(
        name,
        network_id,
        0,
        rpc_public,
        rpc_admin,
        ws_public,
        ws_admin,
        peer,
        "/var/lib/rippled/db/nudb",
        "/var/lib/rippled/db",
        "/var/log/rippled/debug.log",
        None,
        f"http://vl/vl.json",
        vl_key,
        ivl_key,
        [f"0.0.0.0 {peer}"],
    )
    os.makedirs(f"{basedir}/{protocol}-{name}/config", exist_ok=True)
    save_local_config(cfg_path, configs[0].data, configs[1].data)

    lines: List[str] = get_feature_lines_from_content(feature_content)
    features_json: Dict[str, Any] = parse_rippled_amendments(lines)
    genesis_json: Any = update_amendments(features_json, protocol)
    write_file(
        f"{basedir}/{protocol}-{name}/genesis.json",
        json.dumps(genesis_json, indent=4, sort_keys=True),
    )
    dockerfile: str = create_dockerfile(
        binary,
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
        f"{basedir}/deploykit/entrypoint", f"{basedir}/{protocol}-{name}/entrypoint"
    )
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
    public_key: str,
    import_key: str,
    protocol: str,
    network_id: int,
    build_server: str,
    build_version: str,
) -> None:
    name: str = build_version
    os.makedirs(f"{basedir}/{protocol}-{name}", exist_ok=True)
    # Usage
    owner = "Xahau"
    repo = "xahaud"
    commit_hash = get_commit_hash_from_server_version(build_server, build_version)
    content: str = download_file_at_commit(
        owner, repo, commit_hash, "src/ripple/protocol/impl/Feature.cpp"
    )
    url: str = f"{build_server}/{build_version}"
    download_binary(url, f"{basedir}/{protocol}-{name}/rippled")
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
    )
    services["explorer"] = {
        "image": "transia/explorer:latest",
        "container_name": "explorer",
        "environment": [
            "PORT=4000",
            f"VUE_APP_WSS_ENDPOINT=ws://0.0.0.0:{6018}",
        ],
        "ports": ["4000:4000"],
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
""",
    )
    os.chmod(f"{basedir}/{protocol}-{name}/start.sh", 0o755)
    stop_sh_content: str = update_stop_sh(name, 0, 0, True)
    write_file(f"{basedir}/{protocol}-{name}/stop.sh", stop_sh_content)
    os.chmod(f"{basedir}/{protocol}-{name}/stop.sh", 0o755)


def create_local_folder(
    name: str,
    network_id: int,
    vl_key: str,
    ivl_key: str,
    protocol: str,
):
    cfg_path = f"config"
    rpc_public, rpc_admin, ws_public, ws_admin, peer = generate_ports(0, "standalone")
    configs: List[RippledBuild] = gen_config(
        name,
        network_id,
        0,
        rpc_public,
        rpc_admin,
        ws_public,
        ws_admin,
        peer,
        "db/nudb",
        "db",
        "debug.log",
        None,
        f"http://vl/vl.json",
        vl_key,
        ivl_key,
        [f"0.0.0.0 {peer}"],
    )
    os.makedirs(f"config", exist_ok=True)
    save_local_config(cfg_path, configs[0].data, configs[1].data)
    content: str = get_feature_lines_from_path(
        "../src/ripple/protocol/impl/Feature.cpp"
    )
    features_json: Dict[str, Any] = parse_rippled_amendments(content)
    genesis_json: Any = update_amendments(features_json, protocol)
    write_file(
        f"config/genesis.json",
        json.dumps(genesis_json, indent=4, sort_keys=True),
    )


def start_local(
    public_key: str,
    import_key: str,
    protocol: str,
    network_id: int,
) -> None:
    name: str = "local"
    os.makedirs(f"{basedir}/xrpld-{name}", exist_ok=True)
    create_local_folder(
        name,
        network_id,
        public_key,
        import_key,
        protocol,
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

    with open(f"docker-compose.yml", "w") as f:
        yaml.dump(compose, f, default_flow_style=False)

    write_file(
        "start.sh",
        f"""\
#! /bin/bash
docker compose -f docker-compose.yml up --build --force-recreate -d
./rippled -a --conf config/rippled.cfg --ledgerfile config/genesis.json
""",
    )
    os.chmod("start.sh", 0o755)
    stop_sh_content: str = update_stop_sh(name, 0, 0, False, True)
    write_file("stop.sh", stop_sh_content)
    os.chmod("stop.sh", 0o755)
    run_file("./start.sh")
