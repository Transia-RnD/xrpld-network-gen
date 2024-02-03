#!/usr/bin/env python
# coding: utf-8

import requests
import re
import os
import yaml

from xrpl_helpers.common.utils import write_file


def build_entrypoint(root_path: str, genesis: False, quorum: int) -> None:
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
    exec: str = 'exec /app/rippled --conf /etc/opt/ripple/rippled.cfg "$@"'
    exec_quorum: str = (
        f'exec /app/rippled --conf /etc/opt/ripple/rippled.cfg --quorum={quorum} "$@"'
    )
    exec_genesis: str = (
        f'exec /app/rippled --ledgerfile /genesis.json --conf /etc/opt/ripple/rippled.cfg --quorum={quorum} "$@"'  # noqa: E501
    )

    entrypoint += "\n"
    if genesis:
        entrypoint += exec_genesis
    else:
        if quorum:
            entrypoint += exec_quorum
        else:
            entrypoint += exec

    write_file(f"{root_path}/entrypoint", entrypoint)


class DockerVars:
    def __init__(
        self,
        ssh_port: int,
        ws_port: int,
        peer_port: int,
        image_name: str,
        container_name: str,
        container_ports: list,
        docker_volumes: list,
        volumes: list,
    ):
        self.ssh_port = ssh_port
        self.ws_port = ws_port
        self.peer_port = peer_port
        self.image_name = image_name
        self.container_name = container_name
        self.container_ports = container_ports
        self.docker_volumes = docker_volumes
        self.volumes = volumes

    def to_dict(self) -> dict:
        return {
            "ssh_port": self.ssh_port,
            "ws_port": self.ws_port,
            "peer_port": self.peer_port,
            "docker_image_name": self.image_name,
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
        yaml.dump(vars.to_dict(), f, explicit_start=True)
    return vars


def create_dockerfile(
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
) -> str:
    dockerfile = f"""
    FROM {image_name} as base

    WORKDIR /app

    LABEL maintainer="dangell@transia.co"

    RUN export LANGUAGE=C.UTF-8; export LANG=C.UTF-8; export LC_ALL=C.UTF-8; export DEBIAN_FRONTEND=noninteractive

    COPY config /config
    COPY entrypoint /entrypoint.sh
    """  # noqa: E501

    if include_genesis:
        dockerfile += "COPY genesis.json /genesis.json\n"

    if binary:
        dockerfile += f"COPY rippled.{version} /app/rippled\n"

    dockerfile += f"""
    RUN chmod +x /entrypoint.sh && \
        echo '#!/bin/bash' > /usr/bin/server_info && \
        echo '/entrypoint.sh server_info' >> /usr/bin/server_info && \
        chmod +x /usr/bin/server_info

    EXPOSE {rpc_public_port} {rpc_admin_port} {ws_public_port} {ws_admin_port} {peer_port} {peer_port}/udp
    """  # noqa: E501

    if include_genesis:
        dockerfile += f'ENTRYPOINT [ "/entrypoint.sh", "/genesis.json", "{quorum}", "{standalone}" ]'  # noqa: E501
    else:
        dockerfile += 'ENTRYPOINT [ "/entrypoint.sh" ]'

    return dockerfile


def download_binary(url: str, save_path: str) -> None:
    # Check if the file already exists
    if os.path.exists(save_path):
        print(f"The file {save_path} already exists.")
        return

    try:
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
        print(f"Download complete. File saved as {save_path}")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")


def update_dockerfile(build_version: str, save_path: str) -> None:
    # Read the Dockerfile
    with open(save_path, "r") as file:
        lines = file.readlines()

    # Define the pattern to search for any rippled COPY line
    pattern = re.compile(r"^COPY rippled.* /app/rippled$")

    # Replace the line with the new version
    with open(save_path, "w") as file:
        for line in lines:
            if pattern.match(line):
                # Replace the line with the new rippled version
                file.write(f"COPY rippled.{build_version} /app/rippled\n")
            else:
                file.write(line)

    print(f"Dockerfile has been updated with the new rippled version: {build_version}")
