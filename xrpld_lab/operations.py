"""Operational helpers for the xrpld-lab CLI.

Functions for managing running networks/standalones:
- start/stop/remove networks
- update node binaries
- enable amendments via RPC
- view logs
"""

from __future__ import annotations

import glob
import json
import os
import subprocess
import sys

from xrpld_lab.models import NodeRole, PortSet
from xrpld_lab.utils import (
    bcolors,
    remove_directory,
    run_command,
    sha512_half,
)
from xrpld_lab.workspace import Workspace


# ---------------------------------------------------------------------------
# Script runners
# ---------------------------------------------------------------------------


def run_start_script(workspace: Workspace, name: str) -> None:
    """Run the start.sh script for a named network/cluster."""
    script = os.path.join(workspace.base, name, "start.sh")
    if not os.path.isfile(script):
        print(f"{bcolors.RED}start.sh not found: {script}{bcolors.END}")
        return
    run_command(os.path.join(workspace.base, name), "bash start.sh")


def run_stop_script(workspace: Workspace, name: str) -> None:
    """Run the stop.sh script for a named network/cluster."""
    script = os.path.join(workspace.base, name, "stop.sh")
    if not os.path.isfile(script):
        print(f"{bcolors.RED}stop.sh not found: {script}{bcolors.END}")
        return
    run_command(os.path.join(workspace.base, name), "bash stop.sh")


def remove_network(workspace: Workspace, name: str) -> None:
    """Remove a network directory from the workspace."""
    path = os.path.join(workspace.base, name)
    if not os.path.isdir(path):
        print(f"{bcolors.RED}Directory not found: {path}{bcolors.END}")
        return
    remove_directory(path)


# ---------------------------------------------------------------------------
# down:standalone
# ---------------------------------------------------------------------------


def stop_standalone(
    workspace: Workspace,
    name: str | None,
    protocol: str,
    version: str | None,
) -> None:
    """Stop and remove a standalone ledger.

    If *name* is given directly, use that as the directory name.
    Otherwise construct ``{protocol}-{version}`` from protocol and version.
    """
    if name:
        dir_name = name
    elif version:
        dir_name = f"{protocol}-{version}"
    else:
        print(f"{bcolors.RED}Either --name or --version is required.{bcolors.END}")
        return

    net_dir = os.path.join(workspace.base, dir_name)
    stop_script = os.path.join(net_dir, "stop.sh")

    if os.path.isfile(stop_script):
        run_command(net_dir, "bash stop.sh")

    if os.path.isdir(net_dir):
        remove_directory(net_dir)


# ---------------------------------------------------------------------------
# up:local / down:local
# ---------------------------------------------------------------------------


def start_local() -> None:
    """Start a local standalone by running ./start.sh in the current directory."""
    cwd = os.getcwd()
    script = os.path.join(cwd, "start.sh")
    if not os.path.isfile(script):
        print(f"{bcolors.RED}start.sh not found in {cwd}{bcolors.END}")
        return
    run_command(cwd, "bash start.sh")


def stop_local() -> None:
    """Stop a local standalone by running ./stop.sh in the current directory."""
    cwd = os.getcwd()
    script = os.path.join(cwd, "stop.sh")
    if not os.path.isfile(script):
        print(f"{bcolors.RED}stop.sh not found in {cwd}{bcolors.END}")
        return
    run_command(cwd, "bash stop.sh")


def restart_local_node(
    node_name: str,
    binary_name: str = "xrpld",
    genesis: bool = False,
) -> None:
    """Stop and restart a single local node.

    With ``genesis=False`` (default) the node syncs from the network —
    use this when restarting after a crash, stall, or attack simulation.
    With ``genesis=True`` it loads the genesis ledger and marks it valid.
    """
    cwd = os.getcwd()
    node_dir = os.path.join(cwd, node_name)
    if not os.path.isdir(node_dir):
        print(f"{bcolors.RED}Node directory not found: {node_dir}{bcolors.END}")
        return

    # Stop the node if running
    pid_file = os.path.join(node_dir, "xrpld.pid")
    if os.path.isfile(pid_file):
        with open(pid_file) as f:
            pid = f.read().strip()
        if pid:
            print(f"{bcolors.CYAN}Stopping {node_name} (PID {pid})...{bcolors.END}")
            subprocess.run(["kill", pid], capture_output=True)
            subprocess.run(["sleep", "2"], capture_output=True)
            subprocess.run(["kill", "-9", pid], capture_output=True)
        os.remove(pid_file)

    # Start the node
    from xrpld_lab.script_builder import ScriptBuilder

    cmd = ScriptBuilder.local_node_start_cmd(
        node_name, binary_name=binary_name, genesis=genesis
    )
    print(f"{bcolors.CYAN}Starting {node_name} (sync from network)...{bcolors.END}")
    run_command(cwd, cmd)
    print(f"{bcolors.GREEN}{node_name} started.{bcolors.END}")


# ---------------------------------------------------------------------------
# update:node
# ---------------------------------------------------------------------------


def update_node_binary(
    workspace: Workspace,
    name: str,
    node_id: int,
    node_type: str,
    build_server: str,
    build_version: str,
) -> None:
    """Update the xrpld binary for a single node in a running network.

    Steps:
    1. docker-compose stop the node
    2. Download new binary from build_server/build_version
    3. Copy binary to node directory, chmod 755
    4. Remove node's lib directory (force re-sync)
    5. Update Dockerfile with new version
    6. docker compose up --build --force-recreate -d the node
    """
    node_dir_name = f"vnode{node_id}" if node_type == "validator" else f"pnode{node_id}"
    net_dir = os.path.join(workspace.base, name)
    node_dir = os.path.join(net_dir, node_dir_name)

    if not os.path.isdir(node_dir):
        print(f"{bcolors.RED}Node directory not found: {node_dir}{bcolors.END}")
        return

    # 1. Stop the node container
    print(f"{bcolors.CYAN}Stopping {node_dir_name}...{bcolors.END}")
    run_command(net_dir, f"docker compose stop {node_dir_name}")

    # 2. Download new binary
    binary_url = f"{build_server}/{build_version}"
    binary_dest = os.path.join(node_dir, f"xrpld.{build_version}")
    print(f"{bcolors.CYAN}Downloading binary from {binary_url}...{bcolors.END}")
    try:
        subprocess.run(
            ["curl", "-L", "-o", binary_dest, binary_url],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"{bcolors.RED}Failed to download binary: {e}{bcolors.END}")
        return

    # 3. chmod 755
    os.chmod(binary_dest, 0o755)

    # 4. Remove node lib dir (force re-sync)
    lib_dir = os.path.join(node_dir, "lib")
    if os.path.isdir(lib_dir):
        remove_directory(lib_dir)

    # 5. Update Dockerfile version reference
    dockerfile_path = os.path.join(node_dir, "Dockerfile")
    if os.path.isfile(dockerfile_path):
        with open(dockerfile_path) as f:
            content = f.read()
        # Replace old COPY xrpld.VERSION line with new version
        import re

        content = re.sub(
            r"COPY xrpld\.\S+ /app/xrpld",
            f"COPY xrpld.{build_version} /app/xrpld",
            content,
        )
        with open(dockerfile_path, "w") as f:
            f.write(content)

    # 6. Rebuild and start the node
    print(f"{bcolors.CYAN}Rebuilding {node_dir_name}...{bcolors.END}")
    run_command(
        net_dir,
        f"docker compose up --build --force-recreate -d {node_dir_name}",
    )
    print(f"{bcolors.GREEN}Node {node_dir_name} updated to {build_version}.{bcolors.END}")


# ---------------------------------------------------------------------------
# enable:amendment
# ---------------------------------------------------------------------------


def enable_amendment(
    name: str,
    amendment_name: str,
    node_id: int,
    node_type: str,
    workspace: Workspace,
) -> None:
    """Enable an amendment on a running node via its JSON-RPC interface.

    Computes the SHA-512-half of the amendment name, determines the node's
    RPC admin port, and sends a ``feature`` RPC command with ``vetoed: false``.
    """
    # Compute amendment hash: encode name to hex, then sha512_half
    amendment_hash = sha512_half(amendment_name.encode("utf-8").hex())

    # Compute RPC admin port
    if node_type == "validator":
        role = NodeRole.VALIDATOR
    else:
        role = NodeRole.PEER
    ports = PortSet.for_node(node_id, role)
    rpc_port = ports.rpc_admin

    # Build RPC request
    payload = json.dumps({
        "method": "feature",
        "params": [{"feature": amendment_hash, "vetoed": False}],
    })

    url = f"http://localhost:{rpc_port}"
    print(
        f"{bcolors.CYAN}Enabling amendment '{amendment_name}' "
        f"(hash: {amendment_hash}) on {node_type} {node_id} "
        f"at {url}...{bcolors.END}"
    )

    try:
        subprocess.run(
            [
                "curl",
                "-s",
                "-X",
                "POST",
                url,
                "-H",
                "Content-Type: application/json",
                "-d",
                payload,
            ],
            check=True,
        )
        print(f"\n{bcolors.GREEN}Amendment enabled.{bcolors.END}")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"{bcolors.RED}RPC request failed: {e}{bcolors.END}")


# ---------------------------------------------------------------------------
# node:stall
# ---------------------------------------------------------------------------


def node_stall(
    name: str,
    node_id: int,
    node_type: str,
    workspace: Workspace,
    duration_ms: int = 30000,
    clear: bool = False,
) -> None:
    """Stall or unstall a running node via the ``node_stall`` admin RPC.

    When stalled, the node stops participating in consensus (no proposals,
    no validations, no ledger closes).  After *duration_ms* the node
    automatically resumes.  Pass ``clear=True`` to lift the stall early.
    """
    if node_type == "validator":
        role = NodeRole.VALIDATOR
    else:
        role = NodeRole.PEER
    ports = PortSet.for_node(node_id, role)
    rpc_port = ports.rpc_admin

    if clear:
        params = {"clear": True}
    else:
        params = {"duration_ms": duration_ms}

    payload = json.dumps({
        "method": "node_stall",
        "params": [params],
    })

    url = f"http://localhost:{rpc_port}"
    action = "Clearing stall on" if clear else f"Stalling ({duration_ms}ms)"
    print(
        f"{bcolors.CYAN}{action} {node_type} {node_id} "
        f"at {url}...{bcolors.END}"
    )

    try:
        subprocess.run(
            [
                "curl",
                "-s",
                "-X",
                "POST",
                url,
                "-H",
                "Content-Type: application/json",
                "-d",
                payload,
            ],
            check=True,
        )
        print(f"\n{bcolors.GREEN}node_stall RPC sent.{bcolors.END}")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"{bcolors.RED}RPC request failed: {e}{bcolors.END}")


# ---------------------------------------------------------------------------
# logs:local
# ---------------------------------------------------------------------------


def view_local_logs(node: str | None) -> None:
    """Tail local node log files.

    If *node* is given (e.g. ``"vnode1"``), look for its ``log/debug.log``.
    Otherwise search the current directory for any ``debug.log`` files.
    """
    cwd = os.getcwd()

    if node:
        candidates = [
            os.path.join(cwd, node, "log", "debug.log"),
            os.path.join(cwd, node, "config", "debug.log"),
        ]
    else:
        candidates = glob.glob(os.path.join(cwd, "**/debug.log"), recursive=True)

    log_file = None
    for path in candidates:
        if os.path.isfile(path):
            log_file = path
            break

    if not log_file:
        search = node or "current directory"
        print(f"{bcolors.RED}No debug.log found for {search}.{bcolors.END}")
        return

    print(f"{bcolors.CYAN}Tailing {log_file} (Ctrl+C to stop)...{bcolors.END}")
    try:
        subprocess.run(["tail", "-f", log_file], check=False)
    except KeyboardInterrupt:
        pass


# ---------------------------------------------------------------------------
# logs:standalone
# ---------------------------------------------------------------------------


def view_standalone_logs(protocol: str = "xahau") -> None:
    """Tail Docker logs for the standalone container."""
    container_name = protocol
    print(
        f"{bcolors.CYAN}Tailing Docker logs for '{container_name}' "
        f"(Ctrl+C to stop)...{bcolors.END}"
    )
    try:
        subprocess.run(
            ["docker", "logs", "-f", container_name],
            check=False,
        )
    except KeyboardInterrupt:
        pass
