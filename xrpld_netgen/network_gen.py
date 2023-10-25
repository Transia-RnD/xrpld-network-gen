import os
import yaml
import shutil
from typing import List, Any

from .rippled_cfg import generate_rippled_cfg, RippledBuild


"""
"""
"""
"""


def write_file(path: str, data: Any) -> str:
    """Write File

     # noqa: E501

    :param path: Path to file
    :type path: str

    :rtype: str
    """
    with open(path, "w") as f:
        return f.write(data)


"""
"""
"""
"""


def gen_config(
    name: str,
    network_id: int,
    index: int,
    rpc_admin: int,
    ws_public: int,
    ws_admin: int,
    peer: int,
    v_token: str,
    vl_site: str,
    vl_key: str,
    ips_fixed_urls: List[str] = [],
) -> List[RippledBuild]:
    configs: List[RippledBuild] = generate_rippled_cfg(
        # App
        build_path="/",
        node_index=index,
        network=name,
        network_id=network_id,
        # Rippled
        is_rpc_public=False,
        rpc_public_port=None,
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
        nudb_path="/var/lib/rippled/db/nudb",
        db_path="/var/lib/rippled/db",
        num_ledgers="full",
        debug_path="/var/log/rippled/debug.log",
        log_level="trace",
        # private_peer=1 if _node.private_peer and i == 1 else 0,
        private_peer=0,
        genesis=False,
        v_token=v_token,
        validator_list_sites=[vl_site],
        validator_list_keys=[vl_key],
        ips_urls=[],
        ips_fixed_urls=ips_fixed_urls,
        amendment_majority_time=None,
        amendments_dict={},
    )
    return configs


RPC_ADMIN: int = 5015
WS_PUBLIC: int = 6016
WS_ADMIN: int = 6018
PEER: int = 51235


def generate_ports(index, node_type):
    if node_type == "validator":
        rpc_admin = RPC_ADMIN + (index * 100)
        ws_public = WS_PUBLIC + (index * 100)
        ws_admin = WS_ADMIN + (index * 100)
        peer = PEER + (index * 100)
    elif node_type == "peer":
        rpc_admin = RPC_ADMIN + (index * 10)
        ws_public = WS_PUBLIC + (index * 10)
        ws_admin = WS_ADMIN + (index * 10)
        peer = PEER + (index * 10)
    else:
        raise ValueError("Invalid node type. Must be 'validator' or 'peer'.")

    return rpc_admin, ws_public, ws_admin, peer


deploykit_path: str = ""


def save_local_config(root_path: str, cfg_path: str, cfg_out: str, validators_out: str):
    with open(f"{cfg_path}/rippled.cfg", "w") as text_file:
        text_file.write(cfg_out)

    with open(f"{cfg_path}/validators.txt", "w") as text_file:
        text_file.write(validators_out)

    # # Copy Dockerfile
    # with open(deploykit_path + '/Dockerfile', 'rb') as src, open(root_path + '/Dockerfile', 'wb') as dst:
    #     dst.write(src.read())

    # # Copy Entrypoint
    # with open(deploykit_path + '/entrypoint', 'rb') as src, open(root_path + '/entrypoint', 'wb') as dst: dst.write(src.read())


def parse_image_name(image_name: str) -> str:
    # Split the image name into parts
    parts = image_name.split("/")
    # Get the project name
    project_name = parts[1].split("-")[0]
    # Get the image name
    image_name = parts[2].split(":")[0]
    # Get the version
    version = parts[2].split(":")[1]
    return project_name, image_name, version


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
        raise f"Failed to download file from {url}"


def build_entrypoint(root_path: str, genesis: False, quorum: int):
    entrypoint: str = """
#!/bin/bash

rippledconfig=`/bin/cat /config/rippled.cfg 2>/dev/null | wc -l`
validatorstxt=`/bin/cat /config/validators.txt 2>/dev/null | wc -l`

mkdir -p /config

if [[ "$rippledconfig" -gt "0" && "$validatorstxt" -gt "0" ]]; then

    echo "Existing rippled config at host /config/, using them."
    mkdir -p /etc/opt/ripple

    /bin/cat /config/rippled.cfg > /etc/opt/ripple/rippled.cfg
    /bin/cat /config/validators.txt > /etc/opt/ripple/validators.txt

fi

# Start rippled, Passthrough other arguments
"""
    exec: str = f'exec /app/rippled --conf /etc/opt/ripple/rippled.cfg "$@"'
    exec_quorum: str = (
        f'exec /app/rippled --conf /etc/opt/ripple/rippled.cfg --quorum={quorum} "$@"'
    )
    exec_genesis: str = f'exec /app/rippled --ledgerfile /genesis.json --conf /etc/opt/ripple/rippled.cfg --quorum={quorum} "$@"'

    entrypoint += "\n"
    if genesis:
        entrypoint += exec_genesis
    else:
        if quorum:
            entrypoint += exec_quorum
        else:
            entrypoint += exec

    write_file(f"{root_path}/entrypoint", entrypoint)


services = {}
name: str = "xahau"


def create_node_folders(
    image: str,
    storage_url: str,
    num_validators: int,
    num_peers: int,
    network_id: int,
    genesis: bool,
    quorum: int,
):
    # Create directories for validator nodes
    ips_fixed: List[str] = []
    for i in range(1, num_validators + 1):
        node_dir = f"vnode{i}"
        _, _, _, peer = generate_ports(i, "validator")
        ips_fixed.append(f'{node_dir} {peer}')

    
    for i in range(1, num_validators + 1):
        node_dir = f"vnode{i}"
        root_path = f"{name}-cluster/{node_dir}"
        cfg_path = f"{name}-cluster/{node_dir}/config"
        print(f"DIR: {node_dir}")
        rpc_admin, ws_public, ws_admin, peer = generate_ports(i, "validator")
        configs: List[RippledBuild] = gen_config(
            name,
            network_id,
            i,
            rpc_admin,
            ws_public,
            ws_admin,
            peer,
            "vl_token",
            "https://vl.com",
            "vl_key",
            [ips for ips in ips_fixed if ips != f'{node_dir} {peer}']
        )
        # print(f'CONFIG: {configs}')
        os.makedirs(f"{name}-cluster/{node_dir}", exist_ok=True)
        os.makedirs(f"{name}-cluster/{node_dir}/config", exist_ok=True)
        save_local_config(root_path, cfg_path, configs[0].data, configs[1].data)
        features: Any = download_json(f"{storage_url}/features.json", "{name}-cluster")
        # build_entrypoint(root_path, genesis, quorum)
        shutil.copyfile("Dockerfile", f"{name}-cluster/{node_dir}/Dockerfile")
        shutil.copyfile("entrypoint", f"{name}-cluster/{node_dir}/entrypoint")
        pwd_str: str = "${PWD}"
        # args:
        # - IMAGE_NAME=transia/ripple-binary:1.12.0
        services[f"vnode{i}"] = {
            "build": {
                "context": f"vnode{i}", 
                "dockerfile": "Dockerfile",
                "args": [
                    f"IMAGE_NAME={image}",
                    f"RPC_ADMIN_PORT={rpc_admin}",
                    f"WS_PUBLIC_PORT={ws_public}",
                    f"WS_ADMIN_PORT={ws_admin}",
                    f"PEER_PORT={peer}",
                ],
            },
            "container_name": f"vnode{i}",
            "ports": [
                f"{rpc_admin}:{rpc_admin}",
                f"{ws_public}:{ws_public}",
                f"{ws_admin}:{ws_admin}",
                f"{peer}:{peer}",
            ],
            "volumes": [
                f"{pwd_str}/{name}_vnode{i}/config:/etc/opt/ripple",
                f"{pwd_str}/{name}_vnode{i}/log:/var/log/rippled",
                f"{pwd_str}/{name}_vnode{i}/lib:/var/lib/rippled",
            ],
            "networks": [f"{name}-network"],
        }

    # Create directories for peer nodes
    # https://storage.googleapis.com/thelab-builds/dangell7/devnet/2.0.0-b2/features.json
    # https://storage.cloud.google.com/thelab-builds/dangell/devnet/2.0.0-b2/features.json

    for i in range(1, num_peers + 1):
        node_dir = f"pnode{i}"
        root_path = f"{name}-cluster/{node_dir}"
        cfg_path = f"{name}-cluster/{node_dir}/config"
        print(f"IR: {node_dir}")
        rpc_admin, ws_public, ws_admin, peer = generate_ports(i, "peer")
        configs: List[RippledBuild] = gen_config(
            name,
            network_id,
            i,
            rpc_admin,
            ws_public,
            ws_admin,
            peer,
            "vl_token",
            "https://vl.com",
            "vl_key",
            ips_fixed
        )
        # print(f'CONFIG: {configs}')
        os.makedirs(f"{name}-cluster/{node_dir}", exist_ok=True)
        os.makedirs(f"{name}-cluster/{node_dir}/config", exist_ok=True)
        save_local_config(root_path, cfg_path, configs[0].data, configs[1].data)
        features: Any = download_json(f"{storage_url}/features.json", "{name}-cluster")
        # build_entrypoint(root_path, genesis, quorum)
        shutil.copyfile("Dockerfile", f"{name}-cluster/{node_dir}/Dockerfile")
        shutil.copyfile("entrypoint", f"{name}-cluster/{node_dir}/entrypoint")
        pwd_str: str = "${PWD}"
        services[f"pnode{i}"] = {
            "build": {
                "context": f"pnode{i}", 
                "dockerfile": "Dockerfile",
                "args": [
                    f"IMAGE_NAME={image}",
                    f"RPC_ADMIN_PORT={rpc_admin}",
                    f"WS_PUBLIC_PORT={ws_public}",
                    f"WS_ADMIN_PORT={ws_admin}",
                    f"PEER_PORT={peer}",
                ],
            },
            "container_name": f"pnode{i}",
            "ports": [
                f"{rpc_admin}:{rpc_admin}",
                f"{ws_public}:{ws_public}",
                f"{ws_admin}:{ws_admin}",
                f"{peer}:{peer}",
            ],
            "volumes": [
                f"{pwd_str}/{name}_pnode{i}/config:/etc/opt/ripple",
                f"{pwd_str}/{name}_pnode{i}/log:/var/log/rippled",
                f"{pwd_str}/{name}_pnode{i}/lib:/var/lib/rippled",
            ],
            "networks": [f"{name}-network"],
        }


if __name__ == "__main__":
    # num_validators = int(input("Enter the number of validators: "))
    # num_peers = int(input("Enter the number of peer nodes: "))
    # network_id = int(input("Enter the network id: ")) # 21337
    genesis = False
    quorum = None
    num_validators = 3
    num_peers = 1
    network_id = 21337
    image = "gcr.io/thelab-924f3/dangell7-devnet-binary:2.0.0-b2"
    project_name, image_name, version = parse_image_name(image)
    storage_url = f"https://storage.googleapis.com/{project_name}-builds/{image_name.split('-')[0]}/{image_name.split('-')[1]}/{version}"
    create_node_folders(
        image, storage_url, num_validators, num_peers, network_id, genesis, quorum
    )
    services[f"{name}_explorer"] = {
        "image": "transia/explorer:latest",
        "container_name": f"{name}-explorer",
        "environment": [
            "PORT=4000",
            f"VUE_APP_WSS_ENDPOINT=ws://0.0.0.0:{6008 + (num_validators-1)*10}",
        ],
        "ports": ["4000:4000"],
        "networks": [f"{name}-network"],
    }

    compose = {
        "version": "3.4",
        "services": services,
        "networks": {f"{name}-network": {"driver": "bridge"}},
    }

    with open(f"{name}-cluster/docker-compose.yml", "w") as f:
        yaml.dump(compose, f, default_flow_style=False)
