#!/usr/bin/env python
# coding: utf-8

import os
import json
import requests
import shutil
import subprocess
import shlex

from xrpl_helpers.common.utils import read_json


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


def run_file(file_path: str):
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


def run_command(dir: str, command: str):
    try:
        # Split the command into a list of arguments
        # args = command.split()
        args = shlex.split(command)
        # Run the command as a subprocess
        result = subprocess.run(
            args,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=dir,
        )
        # Print the standard output and error (if any)
        print(result.stdout.decode())
        if result.stderr:
            print(result.stderr.decode())
        print(f"Command '{command}' executed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while trying to run the command: {e}")
    except FileNotFoundError:
        print(f"The command '{command}' does not exist or cannot be found.")
    except OSError as e:
        print(f"An error occurred while trying to run the command: {e}")


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


RPC_PUBLIC: int = 5005
RPC_ADMIN: int = 5015
WS_PUBLIC: int = 6016
WS_ADMIN: int = 6018
PEER: int = 51235


def get_node_port(index, node_type):
    if node_type == "validator":
        return RPC_ADMIN + (index * 100)
    elif node_type == "peer":
        return RPC_ADMIN + (index * 10)


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
