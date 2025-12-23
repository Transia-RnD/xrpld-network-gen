#!/usr/bin/env python
# coding: utf-8

import requests
import re
import os
import yaml
import shutil

from .misc import bcolors


class DockerVars:
    def __init__(
        self,
        config_path: int,
        ssh_port: int,
        env_vars: int,
        ws_port: int,
        peer_port: int,
        image_name: str,
        network_name: str,
        container_name: str,
        container_ports: list,
        docker_volumes: list,
        volumes: list,
    ):
        self.config_path = config_path
        self.ssh_port = ssh_port
        self.env_vars = env_vars
        self.ws_port = ws_port
        self.peer_port = peer_port
        self.image_name = image_name
        self.network_name = network_name
        self.container_name = container_name
        self.container_ports = container_ports
        self.docker_volumes = docker_volumes
        self.volumes = volumes

    def to_dict(self) -> dict:
        env_dict = {var.split(": ")[0]: var.split(": ")[1] for var in self.env_vars}
        return {
            "config_path": self.config_path,
            "ssh_port": self.ssh_port,
            "docker_env_variables": env_dict,
            "ws_port": self.ws_port,
            "peer_port": self.peer_port,
            "docker_image_name": self.image_name,
            "docker_network_name": self.network_name,
            "docker_container_name": self.container_name,
            "docker_container_ports": self.container_ports,
            "docker_volumes": self.docker_volumes,
            "volumes": self.volumes,
        }


def create_ansible_vars_file(
    path: str,
    ip: str,
    vars: DockerVars,
) -> DockerVars:
    with open(os.path.join(path, f"{ip}.yml"), "w") as f:
        yaml.dump(vars.to_dict(), f, explicit_start=True, default_flow_style=False)
    return vars


def create_dockerfile(
    network: bool,
    binary: bool,
    version: str,
    image_name: str,
    rpc_public_port: int,
    rpc_admin_port: int,
    ws_public_port: int,
    ws_admin_port: int,
    peer_port: int,
    include_genesis: bool = False,
    quorum: int = None,
    standalone: str = None,
    data_port: int = 12345,
) -> str:
    dockerfile = f"""
    FROM {image_name} as base

    WORKDIR /app

    LABEL maintainer="dangell@transia.co"

    RUN export LANGUAGE=C.UTF-8; export LANG=C.UTF-8; export LC_ALL=C.UTF-8; export DEBIAN_FRONTEND=noninteractive

    COPY entrypoint /entrypoint.sh
    """  # noqa: E501

    if not network:
        dockerfile += "COPY config /config\n"

    if include_genesis:
        dockerfile += "COPY genesis.json /genesis.json\n"

    if binary:
        dockerfile += f"COPY xrpld.{version} /app/xrpld\n"

    if network:
        dockerfile += f"""
    ENV RPC_PUBLIC={rpc_public_port}
    ENV RPC_ADMIN={rpc_admin_port}
    ENV WS_PUBLIC={ws_public_port}
    ENV WS_ADMIN={ws_admin_port}
    ENV PEER={peer_port}
    ENV DATA={data_port}

    EXPOSE $RPC_PUBLIC $RPC_ADMIN $WS_PUBLIC $WS_ADMIN $PEER $PEER/udp $DATA $DATA/udp
        """

    dockerfile += f"""
    RUN chmod +x /entrypoint.sh && \
        echo '#!/bin/bash' > /usr/bin/server_info && \
        echo '/entrypoint.sh server_info' >> /usr/bin/server_info && \
        chmod +x /usr/bin/server_info
    """  # noqa: E501

    if not network:
        dockerfile += f"EXPOSE {rpc_public_port} {rpc_admin_port} {ws_public_port} {ws_admin_port} {peer_port} {peer_port}/udp\n"

    if include_genesis:
        dockerfile += f'ENTRYPOINT [ "/entrypoint.sh", "/genesis.json", "{quorum}", "{standalone}" ]'  # noqa: E501
    else:
        dockerfile += 'ENTRYPOINT [ "/entrypoint.sh" ]'

    return dockerfile


def copy_file(source_path: str, destination_path: str) -> None:
    """
    Copies a file from the source path to the destination path
    and sets the file permissions to be readable and executable by the owner.

    :param source_path: The path to the source file
    :param destination_path: The path to the destination file
    """
    if not os.path.exists(source_path):
        raise ValueError(f"{bcolors.RED}Source file {source_path} does not exist.")

    try:
        print(
            f"{bcolors.GREEN}Copying file from {source_path} to {destination_path}..."
        )
        shutil.copy2(source_path, destination_path)

        # Set the file permissions to be readable and executable by the owner
        os.chmod(destination_path, 0o755)
        print(f"{bcolors.BLUE}Copied and set permissions for {destination_path}.")

    except Exception as e:
        raise ValueError(f"{bcolors.RED}An error occurred while copying the file: {e}")


def download_binary(url: str, save_path: str) -> None:
    version: str = url.split("/")[-1]
    print(f"{bcolors.END}Fetching versions of xahaud..")
    if os.path.exists(save_path):
        print(
            f"{bcolors.GREEN}version: {bcolors.BLUE}{version} {bcolors.END}already exists..."
        )
        os.chmod(save_path, 0o755)
        return

    try:
        print(
            f"{bcolors.GREEN}Found latest version: {bcolors.BLUE}{version}, downloading..."
        )
        # Send a GET request to the URL
        response = requests.get(url, stream=True)

        # Raise an exception if the request was unsuccessful
        response.raise_for_status()

        # Open the file in binary write mode and save the content to the file
        with open(save_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)

        # Set the file permissions to be readable and executable by the owner
        os.chmod(save_path, 0o755)
    except requests.exceptions.RequestException as e:
        raise ValueError(f"{bcolors.RED}An error occurred: {e}")


def update_dockerfile(build_version: str, save_path: str) -> None:
    # Read the Dockerfile
    with open(save_path, "r") as file:
        lines = file.readlines()

    # Define the pattern to search for any xrpld COPY line
    pattern = re.compile(r"^COPY xrpld.* /app/xrpld$")

    # Replace the line with the new version
    with open(save_path, "w") as file:
        for line in lines:
            if pattern.match(line):
                # Replace the line with the new xrpld version
                file.write(f"COPY xrpld.{build_version} /app/xrpld\n")
            else:
                file.write(line)

    print(f"Dockerfile has been updated with the new xrpld version: {build_version}")


def build_stop_sh(
    basedir: str,
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


def build_start_sh(
    basedir: str,
    protocol: str,
    name: str,
):
    return f"""\
#! /bin/bash
docker compose -f {basedir}/{protocol}-{name}/docker-compose.yml up --build --force-recreate -d
"""


def build_local_start_sh(
    net_type: str,
):
    return f"""\
#! /bin/bash
docker compose -f docker-compose.yml up --build --force-recreate -d
./xrpld {'-a' if net_type == 'standalone' else ''} --conf config/xrpld.cfg --ledgerfile config/genesis.json
"""


def build_network_start_sh(
    name: str,
    num_validators: int,
    num_peers: int,
):
    start_sh_content = "#! /bin/bash \n"
    for i in range(1, num_validators + 1):
        start_sh_content += f"cp xrpld.{name} vnode{i}/xrpld.{name}\n"

    for i in range(1, num_peers + 1):
        start_sh_content += f"cp xrpld.{name} pnode{i}/xrpld.{name}\n"
    start_sh_content += (
        f"docker compose -f docker-compose.yml up --build --force-recreate -d"
    )
    return start_sh_content


def build_network_stop_sh(
    name: str,
    num_validators: int,
    num_peers: int,
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
        stop_sh_content += f"docker compose -f docker-compose.yml down --remove-orphans\n"  # noqa: E501

    for i in range(1, num_validators + 1):
        stop_sh_content += f"rm -r vnode{i}/lib\n"
        stop_sh_content += f"rm -r vnode{i}/log\n"
        stop_sh_content += f"rm -r vnode{i}/xrpld.{name}\n"

    for i in range(1, num_peers + 1):
        stop_sh_content += f"rm -r pnode{i}/lib\n"
        stop_sh_content += f"rm -r pnode{i}/log\n"
        stop_sh_content += f"rm -r pnode{i}/xrpld.{name}\n"

    stop_sh_content += "else \n"
    if num_validators > 0 and num_peers > 0:
        stop_sh_content += f"docker compose -f docker-compose.yml down\n"  # noqa: E501
    stop_sh_content += "fi \n"
    return stop_sh_content


def build_local_network_start_sh(
    name: str,
    num_validators: int,
    num_peers: int,
    binary_name: str = "xrpld",
) -> str:
    """
    Generates a start.sh script for local multi-node network without Docker.
    Each xrpld node runs natively in its own Terminal window on macOS.
    """
    start_sh_content = "#! /bin/bash\n\n"
    start_sh_content += "# Start Explorer and VL services in Docker\n"
    start_sh_content += "echo 'Starting Docker services (Explorer & VL)...'\n"
    start_sh_content += "docker compose -f docker-compose.yml up --build --force-recreate -d\n\n"
    start_sh_content += "# Wait for services to be ready\n"
    start_sh_content += "sleep 2\n\n"

    # Get the absolute path to the cluster directory first
    start_sh_content += "# Get the absolute path to the cluster directory\n"
    start_sh_content += "CLUSTER_DIR=\"$(cd \"$(dirname \"$0\")\" && pwd)\"\n\n"

    # Find and copy binary to each node folder
    start_sh_content += "# Locate xrpld binary\n"
    start_sh_content += f"if [ -f \"$CLUSTER_DIR/../{binary_name}\" ]; then\n"
    start_sh_content += f"  BINARY_PATH=\"$CLUSTER_DIR/../{binary_name}\"\n"
    start_sh_content += f"elif command -v {binary_name} &> /dev/null; then\n"
    start_sh_content += f"  BINARY_PATH=$(command -v {binary_name})\n"
    start_sh_content += "else\n"
    start_sh_content += f"  echo 'Error: {binary_name} binary not found!'\n"
    start_sh_content += f"  echo 'Please ensure {binary_name} is either:'\n"
    start_sh_content += f"  echo '  1. In the parent directory: $CLUSTER_DIR/../{binary_name}'\n"
    start_sh_content += f"  echo '  2. In your PATH (e.g., /usr/local/bin/{binary_name})'\n"
    start_sh_content += "  exit 1\n"
    start_sh_content += "fi\n\n"
    start_sh_content += "echo \"Using binary: $BINARY_PATH\"\n\n"

    start_sh_content += "# Copy xrpld binary to each node (if not already present)\n"
    for i in range(1, num_validators + 1):
        start_sh_content += f"if [ ! -f \"vnode{i}/{binary_name}\" ] || [ \"$BINARY_PATH\" -nt \"vnode{i}/{binary_name}\" ]; then\n"
        start_sh_content += f"  cp \"$BINARY_PATH\" vnode{i}/{binary_name}\n"
        start_sh_content += f"  echo 'Copied binary to vnode{i}'\n"
        start_sh_content += "fi\n"
    for i in range(1, num_peers + 1):
        start_sh_content += f"if [ ! -f \"pnode{i}/{binary_name}\" ] || [ \"$BINARY_PATH\" -nt \"pnode{i}/{binary_name}\" ]; then\n"
        start_sh_content += f"  cp \"$BINARY_PATH\" pnode{i}/{binary_name}\n"
        start_sh_content += f"  echo 'Copied binary to pnode{i}'\n"
        start_sh_content += "fi\n"
    start_sh_content += "\n"

    start_sh_content += "# Start validator nodes in background\n"
    for i in range(1, num_validators + 1):
        start_sh_content += f"echo 'Starting vnode{i} in background...'\n"
        start_sh_content += f"cd \"$CLUSTER_DIR/vnode{i}\"\n"
        start_sh_content += f"nohup ./{binary_name} --conf config/xrpld.cfg --ledgerfile config/genesis.json > /dev/null 2>&1 &\n"
        start_sh_content += f"echo $! > \"$CLUSTER_DIR/vnode{i}/xrpld.pid\"\n"
        start_sh_content += f"cd \"$CLUSTER_DIR\"\n"

    start_sh_content += "\n# Start peer nodes in background\n"
    for i in range(1, num_peers + 1):
        start_sh_content += f"echo 'Starting pnode{i} in background...'\n"
        start_sh_content += f"cd \"$CLUSTER_DIR/pnode{i}\"\n"
        start_sh_content += f"nohup ./{binary_name} --conf config/xrpld.cfg --ledgerfile config/genesis.json > /dev/null 2>&1 &\n"
        start_sh_content += f"echo $! > \"$CLUSTER_DIR/pnode{i}/xrpld.pid\"\n"
        start_sh_content += f"cd \"$CLUSTER_DIR\"\n"

    start_sh_content += "\n# Wait for nodes to start\n"
    start_sh_content += "sleep 3\n\n"
    start_sh_content += "echo ''\n"
    start_sh_content += "echo '✅ Local network started!'\n"
    start_sh_content += "echo ''\n"
    start_sh_content += "echo 'Validator nodes: "
    start_sh_content += " ".join([f"vnode{i}" for i in range(1, num_validators + 1)])
    start_sh_content += "'\n"
    start_sh_content += "echo 'Peer nodes: "
    start_sh_content += " ".join([f"pnode{i}" for i in range(1, num_peers + 1)])
    start_sh_content += "'\n"
    start_sh_content += "echo ''\n"
    start_sh_content += "echo 'Each node is running in the background.'\n"
    start_sh_content += "echo 'Use \"xrpld-netgen logs:local --node <node_name>\" to view logs (e.g., --node vnode1).'\n"
    start_sh_content += "echo 'Use \"./stop.sh\" to stop all nodes.'\n"
    start_sh_content += "echo ''\n"
    start_sh_content += "echo 'Explorer UI: http://localhost:4000'\n"
    start_sh_content += "echo 'Validator 1 WebSocket: ws://127.0.0.1:6016'\n"

    return start_sh_content


def build_local_network_stop_sh(
    name: str,
    num_validators: int,
    num_peers: int,
) -> str:
    """
    Generates a stop.sh script for local multi-node network.
    Kills all running xrpld processes and cleans up.
    """
    stop_sh_content = "#! /bin/bash\n\n"
    stop_sh_content += "REMOVE_FLAG=false\n\n"
    stop_sh_content += """for arg in "$@"; do
  if [ "$arg" == "--remove" ]; then
    REMOVE_FLAG=true
    break
  fi
done

"""

    stop_sh_content += "echo 'Stopping all xrpld nodes...'\n\n"

    stop_sh_content += "# Get the absolute path to the cluster directory\n"
    stop_sh_content += "CLUSTER_DIR=\"$(cd \"$(dirname \"$0\")\" && pwd)\"\n\n"

    stop_sh_content += "# Stop validator nodes\n"
    for i in range(1, num_validators + 1):
        stop_sh_content += f"echo 'Stopping vnode{i}...'\n"
        stop_sh_content += f"if [ -f \"$CLUSTER_DIR/vnode{i}/xrpld.pid\" ]; then\n"
        stop_sh_content += f"  PID=$(cat \"$CLUSTER_DIR/vnode{i}/xrpld.pid\")\n"
        stop_sh_content += f"  if ps -p $PID > /dev/null 2>&1; then\n"
        stop_sh_content += f"    kill $PID 2>/dev/null || true\n"
        stop_sh_content += f"    sleep 1\n"
        stop_sh_content += f"    # Force kill if still running\n"
        stop_sh_content += f"    if ps -p $PID > /dev/null 2>&1; then\n"
        stop_sh_content += f"      kill -9 $PID 2>/dev/null || true\n"
        stop_sh_content += f"    fi\n"
        stop_sh_content += f"  fi\n"
        stop_sh_content += f"  rm -f \"$CLUSTER_DIR/vnode{i}/xrpld.pid\"\n"
        stop_sh_content += f"fi\n"
        stop_sh_content += f"# Fallback: Find and kill any xrpld process running in vnode{i} directory\n"
        stop_sh_content += f"pkill -9 -f \"vnode{i}/xrpld\" 2>/dev/null || true\n"

    stop_sh_content += "\n# Stop peer nodes\n"
    for i in range(1, num_peers + 1):
        stop_sh_content += f"echo 'Stopping pnode{i}...'\n"
        stop_sh_content += f"if [ -f \"$CLUSTER_DIR/pnode{i}/xrpld.pid\" ]; then\n"
        stop_sh_content += f"  PID=$(cat \"$CLUSTER_DIR/pnode{i}/xrpld.pid\")\n"
        stop_sh_content += f"  if ps -p $PID > /dev/null 2>&1; then\n"
        stop_sh_content += f"    kill $PID 2>/dev/null || true\n"
        stop_sh_content += f"    sleep 1\n"
        stop_sh_content += f"    # Force kill if still running\n"
        stop_sh_content += f"    if ps -p $PID > /dev/null 2>&1; then\n"
        stop_sh_content += f"      kill -9 $PID 2>/dev/null || true\n"
        stop_sh_content += f"    fi\n"
        stop_sh_content += f"  fi\n"
        stop_sh_content += f"  rm -f \"$CLUSTER_DIR/pnode{i}/xrpld.pid\"\n"
        stop_sh_content += f"fi\n"
        stop_sh_content += f"# Fallback: Find and kill any xrpld process running in pnode{i} directory\n"
        stop_sh_content += f"pkill -9 -f \"pnode{i}/xrpld\" 2>/dev/null || true\n"

    stop_sh_content += "\n# Wait for processes to terminate\n"
    stop_sh_content += "sleep 2\n\n"

    stop_sh_content += "# Stop Docker services\n"
    stop_sh_content += 'if [ "$REMOVE_FLAG" = true ]; then\n'
    stop_sh_content += "  echo 'Cleaning up Docker services and data...'\n"
    stop_sh_content += "  docker compose -f docker-compose.yml down --remove-orphans\n"

    # Clean up directories if --remove flag is used
    for i in range(1, num_validators + 1):
        stop_sh_content += f"  rm -rf vnode{i}/lib vnode{i}/log vnode{i}/xrpld vnode{i}/db\n"
    for i in range(1, num_peers + 1):
        stop_sh_content += f"  rm -rf pnode{i}/lib pnode{i}/log pnode{i}/xrpld pnode{i}/db\n"

    stop_sh_content += "else\n"
    stop_sh_content += "  echo 'Stopping Docker services...'\n"
    stop_sh_content += "  docker compose -f docker-compose.yml down\n"
    stop_sh_content += "fi\n\n"
    stop_sh_content += "echo ''\n"
    stop_sh_content += "echo '✅ Local network stopped.'\n"

    return stop_sh_content
