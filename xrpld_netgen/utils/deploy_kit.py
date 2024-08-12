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
        dockerfile += f"COPY rippled.{version} /app/rippled\n"

    if network:
        dockerfile += f"""
    ENV RPC_PUBLIC={rpc_public_port}
    ENV RPC_ADMIN={rpc_admin_port}
    ENV WS_PUBLIC={ws_public_port}
    ENV WS_ADMIN={ws_admin_port}
    ENV PEER={peer_port}

    EXPOSE $RPC_PUBLIC $RPC_ADMIN $WS_PUBLIC $WS_ADMIN $PEER $PEER/udp
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
