#!/usr/bin/env python
# coding: utf-8

import os
import json
import requests
import shutil
import subprocess
import shlex
import hashlib
import sys

from typing import Dict, Any, Tuple, List


class bcolors:
    RED = "\033[31m"
    GREEN = "\033[32m"
    BLUE = "\033[34m"
    PURPLE = "\033[35m"
    CYAN = "\033[36m"
    END = "\033[0m"


def remove_directory(directory_path: str) -> None:
    try:
        name: str = directory_path.split("/")[-1]
        shutil.rmtree(directory_path)
        print(
            f"{bcolors.CYAN}Directory {name} has been removed successfully. {bcolors.END}"
        )
    except FileNotFoundError:
        print(
            f"{bcolors.RED}❌ The file {directory_path} does not exist or cannot be found.{bcolors.END}"
        )
    except PermissionError:
        print(
            f"{bcolors.RED}❌ Permission denied: Unable to remove '{directory_path}'."
        )
    except Exception as e:
        print(f"{bcolors.RED}❌ An OS error occurred: {e}.{bcolors.END}")


def run_start(cmd: List[str], protocol: str, version: str, type: str):
    try:
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            # stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            print(
                f"{bcolors.CYAN}{protocol.capitalize()} {bcolors.GREEN}{version} {type} running at: {bcolors.PURPLE}6006 {bcolors.END}"
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
    except FileNotFoundError:
        print(f"{bcolors.RED}❌ The file {cmd[0]} does not exist or cannot be found.")
        sys.exit(1)
    except OSError as e:
        print(f"{bcolors.RED}❌ An OS error occurred: {e}")
        sys.exit(1)


def run_stop(cmd: List[str]):
    try:
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            # stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            print(f"{bcolors.CYAN}shut down docker container {bcolors.END}")
        else:
            print(f"{bcolors.RED}ERROR{bcolors.END}", file=sys.stderr)
            sys.exit(1)
    except subprocess.CalledProcessError:
        print(
            f"{bcolors.RED}❌ Cannot connect to the Docker daemon at docker.sock. Is the docker daemon running?{bcolors.END}"
        )
        sys.exit(1)
    except FileNotFoundError:
        print(f"{bcolors.RED}❌ The file {cmd[0]} does not exist or cannot be found.")
        sys.exit(1)
    except OSError as e:
        print(f"{bcolors.RED}❌ An OS error occurred: {e}")
        sys.exit(1)


def is_container_running(container_name):
    result = subprocess.run(
        ["docker", "inspect", container_name], capture_output=True, text=True
    )
    return "Hostname" in result.stdout


def run_logs():
    try:
        container_name = "xahau"
        if is_container_running(container_name):
            os.system("clear")
            print()
            print(
                f"{bcolors.GREEN}Starting live log monitor, edit with {bcolors.PURPLE}CTRL + C{bcolors.END}"
            )
            print()
            log_command = f"docker logs --tail 20 -f {container_name} 2>&1 | grep -E --color=always 'HookTrace|HookError|Publishing ledger [0-9]+'"
            os.system(log_command)
        else:
            print()
            print(
                f"{bcolors.RED}Cannot watch live logs, container not running. Run {bcolors.PURPLE}./install{bcolors.RED} script{bcolors.END}"
            )
            print()
    except subprocess.CalledProcessError:
        return


def check_deps(cmd: List[str]) -> None:
    try:
        print(bcolors.BLUE + "Checking dependencies: \n")
        result = subprocess.run(cmd, check=True)
        if result.returncode == 0:
            print(f"{bcolors.GREEN}Dependencies OK{bcolors.END}")
        else:
            print(f"{bcolors.RED}Dependency ERROR{bcolors.END}")
            sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"{bcolors.RED}Dependency ERROR{bcolors.END}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"{bcolors.RED}Dependency ERROR{bcolors.END}")
        sys.exit(1)
    except OSError as e:
        print(f"{bcolors.RED}Dependency ERROR{bcolors.END}")
        sys.exit(1)


def remove_containers(cmd: str) -> None:
    try:
        args = shlex.split(cmd)
        result = subprocess.run(
            args,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if result.returncode == 0:
            print(f"{bcolors.GREEN}Docker Ready{bcolors.END}")
        else:
            print(f"{bcolors.RED}Docker ERROR{bcolors.END}")
            return
    except subprocess.CalledProcessError as e:
        return
    except FileNotFoundError:
        return
    except OSError as e:
        return


def run_command(dir: str, command: str) -> None:
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


def download_json(url: str, destination_dir: str) -> Dict[str, Any]:
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


def save_local_config(cfg_path: str, cfg_out: str, validators_out: str) -> None:
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


RPC_PUBLIC: int = 5007
RPC_ADMIN: int = 5005
WS_PUBLIC: int = 6008
WS_ADMIN: int = 6006
PEER: int = 51235


def get_node_port(index: int, node_type: str) -> int:
    if node_type == "validator":
        return RPC_ADMIN + (index * 100)
    elif node_type == "peer":
        return RPC_ADMIN + (index * 10)


def generate_ports(index: int, node_type: str) -> Tuple:
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


def sha512_half(hex_string: str) -> str:
    hash_obj = hashlib.sha512()
    hash_obj.update(bytes.fromhex(hex_string))
    full_digest = hash_obj.hexdigest().upper()
    hash_size = len(full_digest) // 2
    return full_digest[:hash_size]

def write_file(path: str, data: Any) -> str:
    """Write File

     # noqa: E501

    :param path: Path to file
    :type path: str

    :rtype: str
    """
    with open(path, "w") as f:
        return f.write(data)


def read_json(path: str) -> Dict[str, object]:
    """Read Json

     # noqa: E501

    :param path: Path to json
    :type path: str

    :rtype: Dict[str, object]
    """
    with open(path) as json_file:
        return json.load(json_file)