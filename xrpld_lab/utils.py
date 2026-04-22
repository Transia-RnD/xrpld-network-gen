import os
import json
import hashlib
import subprocess
import shlex
import shutil
from typing import Dict, Any, List


class bcolors:
    RED = "\033[31m"
    GREEN = "\033[32m"
    BLUE = "\033[34m"
    PURPLE = "\033[35m"
    CYAN = "\033[36m"
    END = "\033[0m"


def write_file(path: str, data: str) -> None:
    with open(path, "w") as f:
        f.write(data)


def read_json(path: str) -> Dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def sha512_half(hex_string: str) -> str:
    hash_obj = hashlib.sha512()
    hash_obj.update(bytes.fromhex(hex_string))
    full_digest = hash_obj.hexdigest().upper()
    return full_digest[: len(full_digest) // 2]


def write_executable(path: str, content: str) -> None:
    """Write a file and make it executable."""
    write_file(path, content)
    os.chmod(path, 0o755)


def run_command(cwd: str, command: str) -> None:
    """Run a shell command in the given directory."""
    try:
        args = shlex.split(command)
        result = subprocess.run(
            args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd
        )
        if result.stdout:
            print(result.stdout.decode())
        if result.stderr:
            print(result.stderr.decode())
    except subprocess.CalledProcessError as e:
        print(f"{bcolors.RED}Command failed: {e}{bcolors.END}")
    except FileNotFoundError:
        print(f"{bcolors.RED}Command not found: {command}{bcolors.END}")
    except OSError as e:
        print(f"{bcolors.RED}OS error: {e}{bcolors.END}")


def run_subprocess(cmd: List[str], error_msg: str = "Command failed") -> bool:
    """Run a subprocess, return True on success."""
    try:
        result = subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
        return result.returncode == 0
    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as e:
        print(f"{bcolors.RED}{error_msg}: {e}{bcolors.END}")
        return False


def remove_directory(path: str) -> None:
    """Remove a directory tree, with error handling."""
    try:
        shutil.rmtree(path)
        name = os.path.basename(path)
        print(f"{bcolors.CYAN}Directory {name} removed.{bcolors.END}")
    except FileNotFoundError:
        print(f"{bcolors.RED}Not found: {path}{bcolors.END}")
    except PermissionError:
        print(f"{bcolors.RED}Permission denied: {path}{bcolors.END}")
    except OSError as e:
        print(f"{bcolors.RED}Error: {e}{bcolors.END}")


def save_config(
    protocol: str, cfg_path: str, cfg_out: str, validators_out: str
) -> None:
    """Write xrpld.cfg and validators.txt to the config directory."""
    with open(f"{cfg_path}/{protocol}d.cfg", "w") as f:
        f.write(cfg_out)
    with open(f"{cfg_path}/validators.txt", "w") as f:
        f.write(validators_out)
