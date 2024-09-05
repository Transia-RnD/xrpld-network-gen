#!/usr/bin/env python
# coding: utf-8

import os
import yaml
import shutil
import json
from typing import List, Any, Dict
from dotenv import load_dotenv

from xrpld_netgen.rippled_cfg import gen_config, RippledBuild
from xrpld_netgen.utils.deploy_kit import (
    create_dockerfile,
    copy_file,
    download_binary,
    update_dockerfile,
    DockerVars,
    create_ansible_vars_file,
)
from xrpld_netgen.libs.github import (
    get_commit_hash_from_server_version,
    download_file_at_commit_or_tag,
)
from xrpld_netgen.utils.misc import (
    download_json,
    run_command,
    generate_ports,
    save_local_config,
    get_node_port,
    sha512_half,
    run_stop,
    remove_directory,
    bcolors,
    write_file,
    read_json,
)

from xrpld_netgen.libs.rippled import (
    update_amendments,
    parse_rippled_amendments,
    get_feature_lines_from_content,
)

from xrpld_publisher.publisher import PublisherClient
from xrpld_publisher.validator import ValidatorClient

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))

deploykit_path: str = ""


def generate_validator_config(protocol: str, network: str):
    try:
        config = read_json(f"{basedir}/deploykit/config.json")
        return config[protocol][network]
    except Exception as e:
        print(e)
        return None


services: Dict[str, Dict] = {}


def create_node_folders(
    binary: bool,
    name: str,
    image: str,
    feature_content: str,
    num_validators: int,
    num_peers: int,
    network_id: int,
    enable_all: bool,
    quorum: int,
    vl_key: str,
    ivl_key: str,
    protocol: str,
    ansible: bool = False,
    ips: List[str] = [],
    log_level: str = "warning",
):
    # Create directories for validator nodes
    ips_fixed: List[str] = []
    for i in range(1, num_validators + 1):
        ips_dir = ips[i - 1] if ansible else f"vnode{i}"
        _, _, _, _, peer = generate_ports(i, "validator")
        ips_fixed.append(f"{ips_dir} {peer}")

    manifests: List[str] = []
    validators: List[str] = []
    tokens: List[str] = []
    for i in range(1, num_validators + 1):
        node_dir = f"vnode{i}"
        # GENERATE VALIDATOR KEY
        client = ValidatorClient(node_dir)
        client.create_keys()
        client.set_domain(f"xahau.{node_dir}.transia.co")
        client.create_token()
        keys = client.get_keys()
        token = client.read_token()
        manifest = client.read_manifest()
        manifests.append(manifest)
        validators.append(keys["public_key"])
        tokens.append(token)

    print(f"✅ {bcolors.CYAN}Created validator keys")

    for i in range(1, num_validators + 1):
        ips_dir = ips[i - 1] if ansible else f"vnode{i}"
        node_dir = f"vnode{i}"
        cfg_path = f"{basedir}/{name}-cluster/{node_dir}/config"
        # GENERATE PORTS
        rpc_public, rpc_admin, ws_public, ws_admin, peer = generate_ports(
            i, "validator"
        )
        # GENERATE CONFIG
        configs: List[RippledBuild] = gen_config(
            ansible,
            protocol,
            name,
            network_id,
            i,
            rpc_public,
            rpc_admin,
            ws_public,
            ws_admin,
            peer,
            "huge",
            10000,
            "/opt/ripple/lib/db/nudb",
            "/opt/ripple/lib/db",
            "/opt/ripple/log/debug.log",
            log_level,
            tokens[i - 1],
            [v for v in validators if v != validators[i - 1]],
            ["http://vl/vl.json"],
            [vl_key],
            [ivl_key] if ivl_key else [],
            [],
            [ips for ips in ips_fixed if ips != f"{ips_dir} {peer}"],
        )

        os.makedirs(f"{basedir}/{name}-cluster/{node_dir}", exist_ok=True)
        os.makedirs(f"{basedir}/{name}-cluster/{node_dir}/config", exist_ok=True)
        save_local_config(cfg_path, configs[0].data, configs[1].data)

        print(f"✅ {bcolors.CYAN}Created validator: {i} config")

        # default features
        features_json: Any = read_json(f"{basedir}/default.{protocol}.features.json")

        # genesis (enable all features)
        if enable_all:
            lines: List[str] = get_feature_lines_from_content(feature_content)
            features_json: Dict[str, Any] = parse_rippled_amendments(lines)

        genesis_json: Any = update_amendments(features_json, protocol)
        write_file(
            f"{basedir}/{name}-cluster/{node_dir}/genesis.json",
            json.dumps(genesis_json, indent=4, sort_keys=True),
        )

        write_file(
            f"{basedir}/{name}-cluster/{node_dir}/features.json",
            json.dumps(features_json, indent=4, sort_keys=True),
        )

        print(f"✅ {bcolors.CYAN}Updated validator: {i} features")

        shutil.copyfile(
            f"{basedir}/{name}-cluster/rippled.{name}",
            f"{basedir}/{name}-cluster/{node_dir}/rippled.{name}",
        )
        os.chmod(f"{basedir}/{name}-cluster/{node_dir}/rippled.{name}", 0o755)

        dockerfile: str = create_dockerfile(
            True,
            binary,
            name,
            image,
            rpc_public,
            rpc_admin,
            ws_public,
            ws_admin,
            peer,
            True,
            quorum,
            "",
        )
        with open(f"{basedir}/{name}-cluster/{node_dir}/Dockerfile", "w") as file:
            file.write(dockerfile)

        shutil.copyfile(
            f"{basedir}/deploykit/network.entrypoint",
            f"{basedir}/{name}-cluster/{node_dir}/entrypoint",
        )

        print(f"✅ {bcolors.CYAN}Built validator: {i} docker container...")

        pwd_str: str = basedir
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
                f"{pwd_str}/{name}-cluster/vnode{i}/config:/opt/ripple/config",
                f"{pwd_str}/{name}-cluster/vnode{i}/log:/opt/ripple/log",
                f"{pwd_str}/{name}-cluster/vnode{i}/lib:/opt/ripple/lib",
            ],
            "networks": [f"{name}-network"],
        }

    for i in range(1, num_peers + 1):
        node_dir = f"pnode{i}"
        cfg_path = f"{basedir}/{name}-cluster/{node_dir}/config"
        rpc_public, rpc_admin, ws_public, ws_admin, peer = generate_ports(i, "peer")
        configs: List[RippledBuild] = gen_config(
            ansible,
            protocol,
            name,
            network_id,
            i,
            rpc_public,
            rpc_admin,
            ws_public,
            ws_admin,
            peer,
            "huge",
            None,
            "/opt/ripple/lib/db/nudb",
            "/opt/ripple/lib/db",
            "/opt/ripple/log/debug.log",
            log_level,
            None,
            validators,
            ["http://vl/vl.json"],
            [vl_key],
            [ivl_key] if ivl_key else [],
            [],
            ips_fixed,
        )
        # print(f'CONFIG: {configs}')
        os.makedirs(f"{basedir}/{name}-cluster/{node_dir}", exist_ok=True)
        os.makedirs(f"{basedir}/{name}-cluster/{node_dir}/config", exist_ok=True)
        save_local_config(cfg_path, configs[0].data, configs[1].data)

        print(f"✅ {bcolors.CYAN}Created peer: {i} config")

        # default features
        features_json: Any = read_json(f"{basedir}/default.xahau.features.json")

        # genesis (enable all features)
        lines: List[str] = get_feature_lines_from_content(feature_content)
        features_json: Dict[str, Any] = parse_rippled_amendments(lines)

        genesis_json: Any = update_amendments(features_json, protocol)
        write_file(
            f"{basedir}/{name}-cluster/{node_dir}/genesis.json",
            json.dumps(genesis_json, indent=4, sort_keys=True),
        )

        write_file(
            f"{basedir}/{name}-cluster/{node_dir}/features.json",
            json.dumps(features_json, indent=4, sort_keys=True),
        )

        print(f"✅ {bcolors.CYAN}Updated peer: {i} features")

        shutil.copyfile(
            f"{basedir}/{name}-cluster/rippled.{name}",
            f"{basedir}/{name}-cluster/{node_dir}/rippled.{name}",
        )
        os.chmod(f"{basedir}/{name}-cluster/{node_dir}/rippled.{name}", 0o755)

        dockerfile: str = create_dockerfile(
            True,
            binary,
            name,
            image,
            rpc_public,
            rpc_admin,
            ws_public,
            ws_admin,
            peer,
            True,
            quorum,
            "",
        )
        with open(f"{basedir}/{name}-cluster/{node_dir}/Dockerfile", "w") as file:
            file.write(dockerfile)

        shutil.copyfile(
            f"{basedir}/deploykit/network.entrypoint",
            f"{basedir}/{name}-cluster/{node_dir}/entrypoint",
        )

        print(f"✅ {bcolors.CYAN}Built peer: {i} docker container...")

        pwd_str: str = basedir
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
                f"{pwd_str}/{name}-cluster/pnode{i}/config:/opt/ripple/config",
                f"{pwd_str}/{name}-cluster/pnode{i}/log:/opt/ripple/log",
                f"{pwd_str}/{name}-cluster/pnode{i}/lib:/opt/ripple/lib",
            ],
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
    stop_sh_content = "#! /bin/bash\n"
    stop_sh_content += "REMOVE_FLAG=false \n"
    stop_sh_content += """
for arg in "$@"; do
  if [ "$arg" == "--remove" ]; then
    REMOVE_FLAG=true
    break
  fi
done
"""
    stop_sh_content += "\n"
    stop_sh_content += 'if [ "$REMOVE_FLAG" = true ]; then \n'
    if num_validators > 0 and num_peers > 0:
        stop_sh_content += f"docker compose -f {basedir}/{name}-cluster/docker-compose.yml down --remove-orphans\n"  # noqa: E501

    for i in range(1, num_validators + 1):
        stop_sh_content += f"rm -r {basedir}/{name}-cluster/vnode{i}/lib\n"
        stop_sh_content += f"rm -r {basedir}/{name}-cluster/vnode{i}/log\n"

    for i in range(1, num_peers + 1):
        stop_sh_content += f"rm -r {basedir}/{name}-cluster/pnode{i}/lib\n"
        stop_sh_content += f"rm -r {basedir}/{name}-cluster/pnode{i}/log\n"

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

    stop_sh_content += "fi \n"
    return stop_sh_content


def create_network(
    log_level: str,
    import_key: str,
    protocol: str,
    num_validators: int,
    num_peers: int,
    network_id: int,
    build_server: str,
    build_version: str,
    genesis: bool = False,
    quorum: int = None,
) -> None:
    if protocol == "xahau":
        name: str = build_version
        os.makedirs(f"{basedir}/{name}-cluster", exist_ok=True)
        # Usage
        owner = "Xahau"
        repo = "xahaud"
        commit_hash = get_commit_hash_from_server_version(build_server, build_version)
        content: str = download_file_at_commit_or_tag(
            owner, repo, commit_hash, "src/ripple/protocol/impl/Feature.cpp"
        )
        url: str = f"{build_server}/{build_version}"
        download_binary(url, f"{basedir}/{name}-cluster/rippled.{build_version}")
        image: str = "ubuntu:jammy"

    if protocol == "xrpl":
        if build_server.startswith("https://github.com/"):
            name: str = build_server.split(
                "https://github.com/Transia-RnD/rippled/tree/"
            )[-1]
            os.makedirs(f"{basedir}/{name}-cluster", exist_ok=True)
            owner = "Transia-RnD"
            repo = "rippled"
            copy_file(f"./rippled", f"{basedir}/{name}-cluster/rippled.{name}")
            content: str = download_file_at_commit_or_tag(
                owner, repo, build_version, "src/libxrpl/protocol/Feature.cpp"
            )
            image: str = "ubuntu:jammy"
        else:
            name: str = build_version
            os.makedirs(f"{basedir}/{name}-cluster", exist_ok=True)
            owner = "XRPLF"
            repo = "rippled"
            content: str = download_file_at_commit_or_tag(
                owner, repo, build_version, "src/libxrpl/protocol/Feature.cpp"
            )
            image: str = f"{build_server}/{build_version}"

    client = PublisherClient()
    client.create_keys()
    keys = client.get_keys()
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
        keys["publicKey"],
        import_key,
        protocol,
        False,
        [],
        log_level,
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

    services["network-explorer"] = {
        "image": "transia/explorer-main:latest",
        "container_name": "network-explorer",
        "environment": [
            "PORT=4000",
            f"VUE_APP_WSS_ENDPOINT=ws://0.0.0.0:{6006}",
        ],
        "ports": ["4000:4000"],
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
""",  # noqa: E501
    )
    stop_sh_content: str = update_stop_sh(protocol, name, num_validators, num_peers)
    write_file(f"{basedir}/{name}-cluster/stop.sh", stop_sh_content)

    os.makedirs(f"{basedir}/{name}-cluster/vl", exist_ok=True)
    for manifest in manifests:
        client.add_validator(manifest)
    client.sign_unl(f"{basedir}/{name}-cluster/vl/vl.json")
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
    amendment_hash: str = sha512_half(amendment_name.encode("utf-8").hex())
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
    command: str = (
        f'curl -X POST -H "Content-Type: application/json" -d "{escaped_str}" http://localhost:{port}'  # noqa: E501
    )
    run_command(f"{basedir}/{name}", command)


def create_ansible(
    log_level: str,
    import_key: str,
    protocol: str,
    num_validators: int,
    num_peers: int,
    network_id: int,
    build_server: str,
    build_version: str,
    genesis: bool = False,
    quorum: int = None,
    vips: List[str] = [],
    pips: List[str] = [],
) -> None:
    if protocol == "xahau":
        name: str = build_version
        os.makedirs(f"{basedir}/{name}-cluster", exist_ok=True)
        # Usage
        owner = "Xahau"
        repo = "xahaud"
        commit_hash = get_commit_hash_from_server_version(build_server, build_version)
        content: str = download_file_at_commit_or_tag(
            owner, repo, commit_hash, "src/ripple/protocol/impl/Feature.cpp"
        )
        url: str = f"{build_server}/{build_version}"
        download_binary(url, f"{basedir}/{name}-cluster/rippled.{build_version}")
        image: str = "ubuntu:jammy"

    if protocol == "xrpl":
        if build_server.startswith("https://github.com/"):
            name: str = build_server.split(
                "https://github.com/Transia-RnD/rippled/tree/"
            )[-1]
            os.makedirs(f"{basedir}/{name}-cluster", exist_ok=True)
            owner = "Transia-RnD"
            repo = "rippled"
            copy_file(f"./rippled", f"{basedir}/{name}-cluster/rippled.{name}")
            content: str = download_file_at_commit_or_tag(
                owner, repo, build_version, "src/libxrpl/protocol/Feature.cpp"
            )
            image: str = "ubuntu:jammy"
        else:
            name: str = build_version
            os.makedirs(f"{basedir}/{name}-cluster", exist_ok=True)
            owner = "XRPLF"
            repo = "rippled"
            content: str = download_file_at_commit_or_tag(
                owner, repo, build_version, "src/libxrpl/protocol/Feature.cpp"
            )
            image: str = f"{build_server}/{build_version}"

    client = PublisherClient()
    client.create_keys()
    keys = client.get_keys()
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
        keys["publicKey"],
        import_key,
        protocol,
        True,
        vips,
        log_level,
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

    services["network-explorer"] = {
        "image": "transia/explorer-main:latest",
        "container_name": "network-explorer",
        "environment": [
            "PORT=4000",
        ],
        "ports": ["4000:4000"],
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
""",  # noqa: E501
    )
    stop_sh_content: str = update_stop_sh(protocol, name, num_validators, num_peers)
    write_file(f"{basedir}/{name}-cluster/stop.sh", stop_sh_content)

    os.makedirs(f"{basedir}/{name}-cluster/vl", exist_ok=True)
    for manifest in manifests:
        client.add_validator(manifest)
    client.sign_unl(f"{basedir}/{name}-cluster/vl/vl.json")
    shutil.copyfile(
        f"{basedir}/deploykit/nginx.dockerfile",
        f"{basedir}/{name}-cluster/vl/Dockerfile",
    )

    os.chmod(f"{basedir}/{name}-cluster/start.sh", 0o755)
    os.chmod(f"{basedir}/{name}-cluster/stop.sh", 0o755)

    os.makedirs(f"{basedir}/{name}-cluster/ansible", exist_ok=True)
    os.makedirs(f"{basedir}/{name}-cluster/ansible/host_vars", exist_ok=True)

    shutil.copytree(
        f"{basedir}/deploykit/ansible",
        f"{basedir}/{name}-cluster/ansible",
        dirs_exist_ok=True,
    )
    image_name: str = build_version.replace("-", ".")
    image_name: str = image_name.replace("+", ".")
    ssh_port: int = os.environ.get("SSH_PORT", 20)
    for k, v in services.items():
        if k[:5] == "vnode":
            index: int = int(k[5:])
            c_name: str = v["container_name"]
            ports: List[str] = v["ports"]
            vars = DockerVars(
                f"{basedir}/{name}-cluster/{c_name}/config/",
                ssh_port,
                [
                    f'RPC_PUBLIC: {ports[0].split(":")[0]}',
                    f'RPC_ADMIN: {ports[1].split(":")[0]}',
                    f'WS_PUBLIC: {ports[2].split(":")[0]}',
                    f'WS_ADMIN: {ports[3].split(":")[0]}',
                    f'PEER: {ports[4].split(":")[0]}',
                ],
                int(ports[2].split(":")[-1]),
                int(ports[4].split(":")[-1]),
                f"transia/cluster:{image_name}",
                c_name,
                ports,
                [
                    "/opt/ripple/config:/opt/ripple/config",
                    "/opt/ripple/log:/opt/ripple/log",
                    "/opt/ripple/lib:/opt/ripple/lib",
                ],
                ["/opt/ripple/log", "/opt/ripple/lib"],
            )
            create_ansible_vars_file(
                f"{basedir}/{name}-cluster/ansible/host_vars", vips[index - 1], vars
            )

        run_command(
            f"{basedir}/{name}-cluster/vnode1",
            f"docker build -f Dockerfile --platform linux/x86_64 --tag transia/cluster:{image_name} .",  # noqa: E501
        )
        run_command(
            f"{basedir}/{name}-cluster/vnode1",
            f"docker push transia/cluster:{image_name}",
        )
        if k[:5] == "pnode":
            index: int = int(k[5:])
            c_name: str = v["container_name"]
            ports: List[str] = v["ports"]
            vars = DockerVars(
                f"{basedir}/{name}-cluster/{c_name}/config/",
                ssh_port,
                [
                    f'RPC_PUBLIC: {ports[0].split(":")[0]}',
                    f'RPC_ADMIN: {ports[1].split(":")[0]}',
                    f'WS_PUBLIC: {ports[2].split(":")[0]}',
                    f'WS_ADMIN: {ports[3].split(":")[0]}',
                    f'PEER: {ports[4].split(":")[0]}',
                ],
                int(ports[2].split(":")[-1]),
                int(ports[4].split(":")[-1]),
                f"transia/cluster:{image_name}",
                c_name,
                ports,
                [
                    "/opt/ripple/config:/opt/ripple/config",
                    "/opt/ripple/log:/opt/ripple/log",
                    "/opt/ripple/lib:/opt/ripple/lib",
                ],
                ["/opt/ripple/log", "/opt/ripple/lib"],
            )
            create_ansible_vars_file(
                f"{basedir}/{name}-cluster/ansible/host_vars", pips[index - 1], vars
            )
    hosts_content: str = """
# this is a basic file putting different hosts into categories
# used by ansible to determine which actions to run on which hosts
[all]
    """
    hosts_content += "\n"
    ssh: str = os.environ.get("SSH_PORT", 20)
    user: str = os.environ.get("SSH_USER", "ubuntu")
    ssh_key: str = os.environ.get("SSH_PATH", "~/.ssh/id_rsa")
    for vip in vips:
        hosts_content += f"{vip} ansible_port={ssh} ansible_user={user} ansible_ssh_private_key_file={ssh_key} vars_file=host_vars/{vip}.yml \n"  # noqa: E501
    for pip in pips:
        hosts_content += f"{pip} ansible_port={ssh} ansible_user={user} ansible_ssh_private_key_file={ssh_key} vars_file=host_vars/{pip}.yml \n"  # noqa: E501
    write_file(f"{basedir}/{name}-cluster/ansible/hosts.txt", hosts_content)


def stop_network(name: str, remove: bool = False):
    cmd: List[str] = [f"{basedir}/{name}/stop.sh"]
    if remove:
        cmd.append("--remove")
    run_stop(cmd)


def remove_network(name: str):
    stop_network(name, True)
    remove_directory(f"{basedir}/{name}")
