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


def start_local(
    protocol: str = "xrpl",
    network_type: str = "standalone",
    network_id: int = 21339,
    log_level: str = "trace",
    nodedb_type: str = "NuDB",
    public_key: str = None,
) -> None:
    """Set up and start a local standalone node from the current directory.

    Expects to be run from the build directory of a built xrpld repo.
    Generates config/, db/, log/ dirs, writes xrpld.cfg, validators.txt,
    genesis.json, start.sh, and stop.sh, then launches the node.
    """
    from xrpld_lab.amendments import (
        get_feature_lines_from_path,
        parse_amendments,
        update_genesis,
    )
    from xrpld_lab.config_builder import XrpldCfgBuilder, ValidatorsTxtBuilder
    from xrpld_lab.models import NodeDbType, Protocol
    from xrpld_lab.node_factory import NodeFactory
    from xrpld_lab.protocol import get_spec
    from xrpld_lab.utils import save_config, write_executable, write_file

    cwd = os.getcwd()
    protocol_enum = Protocol(protocol)
    spec = get_spec(protocol_enum)
    binary_name = spec.daemon_name
    config_filename = f"{binary_name}.cfg"

    # 1. Find binary in CWD
    binary_path = os.path.join(cwd, binary_name)
    if not os.path.isfile(binary_path):
        print(f"{bcolors.RED}{binary_name} not found in {cwd}{bcolors.END}")
        return

    # 2. Resolve features from source tree (CWD is build/, repo root is ../)
    feature_lines: list = []
    for fpath in spec.feature_paths:
        candidate = os.path.join(cwd, "..", fpath)
        if os.path.exists(candidate):
            feature_lines = get_feature_lines_from_path(candidate)
            print(f"{bcolors.CYAN}Resolved features from {candidate}{bcolors.END}")
            break

    if not feature_lines:
        print(f"{bcolors.RED}Could not resolve features from source tree{bcolors.END}")
        return

    # 3. Create directories
    config_dir = os.path.join(cwd, "config")
    os.makedirs(config_dir, exist_ok=True)
    os.makedirs(os.path.join(cwd, "db"), exist_ok=True)
    os.makedirs(os.path.join(cwd, "log"), exist_ok=True)

    # 4. Build NodeConfig for local standalone
    node = NodeFactory.create_local_standalone(
        protocol=protocol_enum,
        name="local",
        network_id=network_id,
        log_level=log_level,
        node_db_type=NodeDbType(nodedb_type),
        vl_keys=[public_key] if public_key else [],
    )

    # 5. Generate config files
    cfg_content = XrpldCfgBuilder(node).build()
    vl_content = ValidatorsTxtBuilder(node, genesis=True).build()
    save_config(protocol, config_dir, cfg_content, vl_content)

    # 6. Parse amendments and generate genesis
    features = parse_amendments(feature_lines)
    genesis = update_genesis(features, protocol)
    write_file(
        os.path.join(config_dir, "genesis.json"),
        json.dumps(genesis, indent=4, sort_keys=True),
    )

    # 7. Generate start.sh and stop.sh
    flag = "-a" if network_type == "standalone" else ""
    start_content = (
        "#!/bin/bash\n"
        f"exec ./{binary_name} {flag} --conf config/{config_filename}"
        " --ledgerfile config/genesis.json\n"
    )
    stop_content = (
        "#!/bin/bash\n"
        f"pkill -f './{binary_name}' && echo \"{binary_name} stopped\""
        f' || echo "No running {binary_name} found"\n'
    )
    write_executable(os.path.join(cwd, "start.sh"), start_content)
    write_executable(os.path.join(cwd, "stop.sh"), stop_content)

    print(f"{bcolors.CYAN}Generated config in {config_dir}{bcolors.END}")
    print(f"{bcolors.CYAN}Starting {binary_name} (Ctrl+C to stop)...{bcolors.END}")

    # 8. Launch in foreground — stdout/stderr stream to this terminal
    subprocess.run(["bash", "start.sh"], cwd=cwd)


def stop_local() -> None:
    """Stop a local standalone by running ./stop.sh in the current directory."""
    cwd = os.getcwd()
    script = os.path.join(cwd, "stop.sh")
    if not os.path.isfile(script):
        print(f"{bcolors.RED}stop.sh not found in {cwd}{bcolors.END}")
        return
    run_command(cwd, "bash stop.sh")


def _docker_container_exists(name: str) -> bool:
    """True if a docker container with this exact name exists (running or not)."""
    try:
        r = subprocess.run(
            [
                "docker",
                "ps",
                "-a",
                "--filter",
                f"name=^{name}$",
                "--format",
                "{{.Names}}",
            ],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return False
    return name in r.stdout.split()


def restart_local_node(
    node_name: str,
    binary_name: str = "xrpld",
    genesis: bool = False,
) -> None:
    """Stop and restart a single local node.

    With ``genesis=False`` (default) the node resumes from its existing
    database — use this when restarting after a crash, stall, or attack
    simulation. With ``genesis=True`` it loads the genesis ledger and marks it
    valid, giving the node a fresh divergent history.

    Two node layouts are supported. A bare-process node has an ``xrpld.pid`` in
    its directory and is killed and re-launched from ``start.sh``. A docker node
    has no pidfile and a container named after the node: ``genesis=False``
    ``docker restart``\\s it (keeping its database layer), ``genesis=True``
    recreates it so the database is wiped and the entrypoint reloads genesis.
    """
    cwd = os.getcwd()
    node_dir = os.path.join(cwd, node_name)
    if not os.path.isdir(node_dir):
        print(f"{bcolors.RED}Node directory not found: {node_dir}{bcolors.END}")
        return

    pid_file = os.path.join(node_dir, "xrpld.pid")
    if not os.path.isfile(pid_file) and _docker_container_exists(node_name):
        if genesis:
            print(f"{bcolors.CYAN}Recreating {node_name} from genesis...{bcolors.END}")
            run_command(cwd, f"docker compose up --force-recreate -d {node_name}")
        else:
            print(
                f"{bcolors.CYAN}Restarting {node_name} (resume from db)...{bcolors.END}"
            )
            run_command(cwd, f"docker restart {node_name}")
        print(f"{bcolors.GREEN}{node_name} restarted.{bcolors.END}")
        return

    # Bare-process node: kill by pidfile and re-launch.
    if os.path.isfile(pid_file):
        with open(pid_file) as f:
            pid = f.read().strip()
        if pid:
            print(f"{bcolors.CYAN}Stopping {node_name} (PID {pid})...{bcolors.END}")
            subprocess.run(["kill", pid], capture_output=True)
            subprocess.run(["sleep", "2"], capture_output=True)
            subprocess.run(["kill", "-9", pid], capture_output=True)
        os.remove(pid_file)

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


# In-image binary locations across the layouts we build/consume: perf datagram
# images (/opt/xrpld/bin), stock rippleci images (/usr/bin), older ripple images.
_IMAGE_BINARY_PATHS = (
    "/opt/xrpld/bin/xrpld",
    "/usr/bin/xrpld",
    "/usr/local/bin/rippled",
    "/opt/ripple/bin/rippled",
    "/app/xrpld",
)


def _extract_binary_from_image(image: str, dest: str) -> bool:
    """Copy the xrpld/rippled binary out of a docker image to *dest*.

    The build pipeline publishes images (``-dg`` tags in GAR), not raw binaries,
    so an upgrade drill sources the target build from an image ref — local or, after
    a ``docker pull``, from the registry. The binary lives at a different path across
    image layouts, so each known location is tried. Returns True on success.
    """
    probe = f"xrpld-extract-{os.getpid()}"
    try:
        subprocess.run(["docker", "rm", "-f", probe], capture_output=True)
        r = subprocess.run(
            ["docker", "create", "--name", probe, image], capture_output=True, text=True
        )
        if r.returncode != 0:
            # Not present locally: pull then retry create.
            if subprocess.run(["docker", "pull", image]).returncode != 0:
                print(f"{bcolors.RED}Cannot pull image {image}{bcolors.END}")
                return False
            r = subprocess.run(
                ["docker", "create", "--name", probe, image],
                capture_output=True,
                text=True,
            )
            if r.returncode != 0:
                print(
                    f"{bcolors.RED}docker create failed: "
                    f"{r.stderr.strip()}{bcolors.END}"
                )
                return False
        for path in _IMAGE_BINARY_PATHS:
            cp = subprocess.run(
                ["docker", "cp", f"{probe}:{path}", dest],
                capture_output=True,
                text=True,
            )
            if cp.returncode == 0:
                return True
        print(
            f"{bcolors.RED}No xrpld/rippled binary found in {image} "
            f"(tried {', '.join(_IMAGE_BINARY_PATHS)}){bcolors.END}"
        )
        return False
    except FileNotFoundError:
        print(f"{bcolors.RED}docker not found{bcolors.END}")
        return False
    finally:
        subprocess.run(["docker", "rm", "-f", probe], capture_output=True)


def update_node_binary(
    workspace: Workspace,
    name: str,
    node_id: int,
    node_type: str,
    build_server: str,
    build_version: str,
    image: str = None,
) -> None:
    """Update the xrpld binary for a single node in a running network.

    Steps:
    1. docker-compose stop the node
    2. Source the new binary: extract it from *image* if given, else download it
       from ``build_server/build_version``. ``build_version`` is always the version
       label used for the on-disk filename and the Dockerfile COPY line.
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

    # 2. Source the new binary — from an image (what the build pipeline produces)
    #    or a raw-binary download.
    binary_dest = os.path.join(node_dir, f"xrpld.{build_version}")
    if image:
        print(f"{bcolors.CYAN}Extracting binary from image {image}...{bcolors.END}")
        if not _extract_binary_from_image(image, binary_dest):
            return
    else:
        binary_url = f"{build_server}/{build_version}"
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
            r"COPY xrpld\.\S+ /opt/xrpld/bin/xrpld",
            f"COPY xrpld.{build_version} /opt/xrpld/bin/xrpld",
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
    print(
        f"{bcolors.GREEN}Node {node_dir_name} updated to {build_version}.{bcolors.END}"
    )


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
    payload = json.dumps(
        {
            "method": "feature",
            "params": [{"feature": amendment_hash, "vetoed": False}],
        }
    )

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

    payload = json.dumps(
        {
            "method": "node_stall",
            "params": [params],
        }
    )

    url = f"http://localhost:{rpc_port}"
    action = "Clearing stall on" if clear else f"Stalling ({duration_ms}ms)"
    print(f"{bcolors.CYAN}{action} {node_type} {node_id} " f"at {url}...{bcolors.END}")

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


def view_standalone_logs(protocol: str = "xrpl") -> None:
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
