#!/usr/bin/env python3
# coding: utf-8

# NETWORK
# create:network
# xrpld-netgen create:network --protocol "xahau" --build_version "2023.11.10-dev+549"
# add:peer
# xrpld-netgen add:peer --network_name xrpld-2023.11.10-dev+549 --protocol "xahau" --version "2023.11.10-dev+549"  # noqa: E501
# remove:peer
# xrpld-netgen remove:peer --network_name xrpld-2023.11.10-dev+549 --protocol "xahau" --version "2023.11.10-dev+549"  # noqa: E501
# update:version
# xrpld-netgen update:version --node --version xrpld-2023.11.10-dev+549
# enable:amendment
# xrpld-netgen enable:amendment --peer 1 --amendment "name"
# start
# xrpld-netgen start --name xrpld-2023.11.10-dev+549
# stop
# xrpld-netgen stop --name xrpld-2023.11.10-dev+549
# remove
# xrpld-netgen remove --name xrpld-2023.11.10-dev+549


# LOCAL
# start:local
# xrpld-netgen start:local --protocol "xahau"
# stop:local
# xrpld-netgen stop:local --protocol "xahau"


# STANDALONE
# up:standalone
# xrpld-netgen up:standalone
# down:standalone
# xrpld-netgen down:standalone


import os
import argparse
from xrpld_netgen.main import (
    create_standalone_binary,
    create_standalone_image,
    start_local,
)
from xrpld_netgen.network import (
    create_network,
    update_node_binary,
    enable_node_amendment,
)
from xrpld_netgen.utils.misc import (
    remove_directory,
    bcolors,
    check_deps,
    remove_containers,
    run_start,
    run_stop,
    run_logs,
)

basedir = os.path.abspath(os.path.dirname(__file__))

XAHAU_RELEASE: str = "2024.4.21-release+858"
XRPL_RELEASE: str = "2.0.0-b4"


def main():
    parser = argparse.ArgumentParser(
        description="A python cli to build xrpld networks and standalone ledgers."
    )
    subparsers = parser.add_subparsers(dest="command")

    # LOGS
    # logs:hooks
    subparsers.add_parser("logs:hooks", help="Log Hooks")

    # LOCAL
    # start:local
    parser_sl = subparsers.add_parser("start:local", help="Start Local Network")
    parser_sl.add_argument(
        "--log_level",
        required=False,
        help="The log level",
        choices=["warning", "debug", "trace"],
        default="trace",
    )
    parser_sl.add_argument(
        "--public_key",
        required=False,
        help="The public vl key",
        default="ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501",
    )
    parser_sl.add_argument("--import_key", required=False, help="The import vl key")
    parser_sl.add_argument(
        "--protocol",
        required=False,
        help="The protocol of the network",
        default="xahau",
    )
    parser_sl.add_argument(
        "--network_type",
        required=False,
        help="The type of the network",
        default="standalone",
    )
    parser_sl.add_argument(
        "--network_id", type=int, required=False, help="The network id", default=21339
    )
    # stop:local
    # parser_spl = subparsers.add_parser("stop:local", help="Stop Local Network")

    # NETWORK

    # create:network
    parser_cn = subparsers.add_parser("create:network", help="Create Network")
    parser_cn.add_argument(
        "--log_level",
        required=False,
        help="The log level",
        choices=["warning", "debug", "trace"],
        default="trace",
    )
    parser_cn.add_argument(
        "--protocol",
        type=str,
        required=False,
        help="The protocol of the network",
        default="xahau",
    )
    parser_cn.add_argument(
        "--num_validators",
        type=int,
        required=False,
        help="The number of validators in the network",
        default=3,
    )
    parser_cn.add_argument(
        "--num_peers",
        type=int,
        required=False,
        help="The number of peers in the network",
        default=1,
    )
    parser_cn.add_argument(
        "--network_id",
        type=int,
        required=False,
        help="The id of the network",
        default=21339,
    )
    parser_cn.add_argument(
        "--build_server",
        type=str,
        required=False,
        help="The build server for the network",
    )
    parser_cn.add_argument(
        "--build_version",
        type=str,
        required=False,
        help="The build version for the network",
    )
    parser_cn.add_argument(
        "--genesis",
        type=bool,
        required=False,
        help="Is this a genesis network?",
        default=False,
    )
    parser_cn.add_argument(
        "--quorum",
        type=int,
        required=False,
        help="The quorum required for the network",
    )
    # update:node
    parser_un = subparsers.add_parser("update:node", help="Update Node Version")
    parser_un.add_argument(
        "--name", type=str, required=True, help="The name of the network"
    )
    parser_un.add_argument(
        "--node_id",
        type=str,
        required=True,
        help="The node id you want to update",
    )
    parser_un.add_argument(
        "--node_type",
        type=str,
        required=True,
        help="The node type you want to update",
        choices=["validator", "peer"],
    )
    parser_un.add_argument(
        "--build_server", type=str, required=False, help="The build server for the node"
    )
    parser_un.add_argument(
        "--build_version",
        type=str,
        required=False,
        help="The build version for the node",
    )
    # enable:amendment
    parser_ea = subparsers.add_parser("enable:amendment", help="Enable Amendment")
    parser_ea.add_argument("--name", required=True, help="The name of the network")
    parser_ea.add_argument(
        "--amendment_name",
        required=True,
        help="The amendment you want to enable",
    )
    parser_ea.add_argument(
        "--node_id",
        required=True,
        help="The node id you want to update",
    )
    parser_ea.add_argument(
        "--node_type",
        required=True,
        help="The node type you want to update",
        choices=["validator", "peer"],
    )

    # start
    parser_st = subparsers.add_parser("start", help="Start Network")
    parser_st.add_argument("--name", required=True, help="The name of the network")
    # stop
    parser_sp = subparsers.add_parser("stop", help="Stop Network")
    parser_sp.add_argument("--name", required=True, help="The name of the network")

    # remove
    parser_r = subparsers.add_parser("remove", help="Remove Network")
    parser_r.add_argument("--name", required=True, help="The name of the network")

    # STANDALONE

    # up:standalone
    parser_us = subparsers.add_parser("up:standalone", help="Up Standalone")
    parser_us.add_argument(
        "--log_level",
        required=False,
        help="The log level",
        choices=["warning", "debug", "trace"],
        default="trace",
    )
    parser_us.add_argument(
        "--build_type",
        type=str,
        required=False,
        help="The build type",
        choices=["image", "binary"],
        default="binary",
    )
    parser_us.add_argument(
        "--public_key",
        type=str,
        required=False,
        help="The public vl key",
        default="ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501",
    )
    parser_us.add_argument(
        "--import_key",
        type=str,
        required=False,
        help="The import vl key",
    )
    parser_us.add_argument(
        "--protocol",
        type=str,
        required=False,
        help="The protocol of the network",
        default="xahau",
    )
    parser_us.add_argument(
        "--network_id", type=int, required=False, help="The network id", default=21339
    )
    parser_us.add_argument(
        "--network_type",
        type=str,
        required=False,
        help="The network type",
        default="standalone",
    )
    parser_us.add_argument(
        "--server",
        type=str,
        required=False,
        help="The build server for the network",
    )
    parser_us.add_argument(
        "--version",
        type=str,
        required=False,
        help="The build version for the network",
    )
    parser_us.add_argument(
        "--ipfs", type=bool, required=False, help="Add an IPFS server", default=False
    )
    # down:standalone
    parser_ds = subparsers.add_parser("down:standalone", help="Down Standalone")
    parser_ds.add_argument("--name", required=False, help="The name of the network")
    parser_ds.add_argument(
        "--protocol",
        type=str,
        required=False,
        help="The protocol of the network",
        default="xahau",
    )
    parser_ds.add_argument(
        "--version",
        type=str,
        required=False,
        help="The build version for the network",
    )

    args = parser.parse_args()

    # LOGS
    if args.command == "logs:hooks":
        return run_logs()

    if args.command == "stop":
        NAME = args.name
        print(f"{bcolors.BLUE}Stopping Network: {NAME}{bcolors.END}")
        return run_stop(f"{basedir}/{NAME}/stop.sh")

    if args.command == "remove":
        NAME = args.name
        print(f"{bcolors.BLUE}Removing Network: {NAME}{bcolors.END}")
        return remove_directory(f"{basedir}/{NAME}")

    # DOWN STANDALONE
    if args.command == "down:standalone":
        NAME = args.name
        print(
            f"{bcolors.BLUE}Taking Down Standalone Network with the following parameters:{bcolors.END}"
        )

        if NAME:
            print(f"    - Network Name: {NAME}")
            run_stop([f"{basedir}/{NAME}/stop.sh"])
            remove_directory(f"{basedir}/{NAME}")
            return

        PROTOCOL = args.protocol
        BUILD_VERSION = args.version

        if PROTOCOL == "xahau" and not BUILD_VERSION:
            BUILD_VERSION: str = XAHAU_RELEASE

        if PROTOCOL == "xrpl" and not BUILD_VERSION:
            BUILD_VERSION: str = XRPL_RELEASE

        print(f"    - Network Name: {NAME}")
        print(f"    - Protocol: {PROTOCOL}")
        print(f"    - Build Version: {BUILD_VERSION}")
        return run_stop([f"{basedir}/{PROTOCOL}-{BUILD_VERSION}/stop.sh"])

    # MANAGE NETWORK/STANDALONE
    if args.command == "start":
        NAME = args.name
        print(f"{bcolors.BLUE}Starting Network: {NAME}{bcolors.END}")
        return run_start(
            [f"{basedir}/{NAME}/start.sh"],
            None,
            None,
            "network",
        )

    print("")
    print("   _  __ ____  ____  __    ____     _   __     __  ______          ")
    print("  | |/ // __ \/ __ \/ /   / __ \   / | / /__  / /_/ ____/__  ____  ")
    print("  |   // /_/ / /_/ / /   / / / /  /  |/ / _ \/ __/ / __/ _ \/ __ \ ")
    print(" /   |/ _, _/ ____/ /___/ /_/ /  / /|  /  __/ /_/ /_/ /  __/ / / / ")
    print("/_/|_/_/ |_/_/   /_____/_____/  /_/ |_/\___/\__/\____/\___/_/ /_/  ")
    print("")

    check_deps([f"{basedir}/deploykit/prerequisites.sh"])

    print(f"{bcolors.BLUE}Removing existing containers: {bcolors.RED}")
    remove_containers("docker stop xahau")
    remove_containers("docker rm xahau")
    remove_containers("docker stop explorer")
    remove_containers("docker rm explorer")
    remove_containers("docker stop xrpl")
    remove_containers("docker rm xrpl")

    # LOCAL
    if args.command == "start:local":
        LOG_LEVEL = args.log_level
        PUBLIC_KEY = args.public_key
        IMPORT_KEY = args.import_key
        PROTOCOL = args.protocol
        NETWORK_TYPE = args.network_type
        NETWORK_ID = args.network_id

        print(
            f"{bcolors.BLUE}Starting Local Network with the following parameters:{bcolors.END}"
        )
        print(f"    - Log Level: {LOG_LEVEL}")
        print(f"    - Public Key: {PUBLIC_KEY}")
        print(f"    - Import Key: {IMPORT_KEY}")
        print(f"    - Protocol: {PROTOCOL}")
        print(f"    - Network Type: {NETWORK_TYPE}")
        print(f"    - Network ID: {NETWORK_ID}")

        start_local(
            LOG_LEVEL, PUBLIC_KEY, IMPORT_KEY, PROTOCOL, NETWORK_TYPE, NETWORK_ID
        )

    if args.command == "stop:local":
        print(f"{bcolors.BLUE}Stopping Local Network{bcolors.END}")
        run_stop(["./stop.sh"])

    # CREATE NETWORK
    if args.command == "create:network":
        LOG_LEVEL = args.log_level
        PROTOCOL = args.protocol
        NUM_VALIDATORS = args.num_validators
        NUM_PEERS = args.num_peers
        NETWORK_ID = args.network_id
        BUILD_SERVER = args.build_server
        BUILD_VERSION = args.build_version
        GENESIS = args.genesis
        QUORUM = args.quorum

        import_vl_key: str = (
            "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501"
        )

        if not BUILD_SERVER:
            BUILD_SERVER: str = "https://build.xahau.tech"

        if not BUILD_VERSION:
            BUILD_VERSION: str = XAHAU_RELEASE

        if not QUORUM:
            QUORUM = NUM_VALIDATORS - 1

        print(
            f"{bcolors.BLUE}Creating Network with the following parameters:{bcolors.END}"
        )
        print(f"    - Log Level: {LOG_LEVEL}")
        print(f"    - Protocol: {PROTOCOL}")
        print(f"    - Number of Validators: {NUM_VALIDATORS}")
        print(f"    - Number of Peers: {NUM_PEERS}")
        print(f"    - Network ID: {NETWORK_ID}")
        print(f"    - Build Server: {BUILD_SERVER}")
        print(f"    - Build Version: {BUILD_VERSION}")
        print(f"    - Genesis: {GENESIS}")
        print(f"    - Quorum: {QUORUM}")

        create_network(
            LOG_LEVEL,
            import_vl_key,
            PROTOCOL,
            NUM_VALIDATORS,
            NUM_PEERS,
            NETWORK_ID,
            BUILD_SERVER,
            BUILD_VERSION,
            GENESIS,
            QUORUM,
        )

    if args.command == "update:node":
        NAME = args.name
        NODE_ID = args.node_id
        NODE_VERSION = args.node_version
        BUILD_SERVER = args.build_server
        BUILD_VERSION = args.build_version
        print(
            f"{bcolors.BLUE}Updating Node Version with the following parameters:{bcolors.END}"
        )
        print(f"    - Network Name: {NAME}")
        print(f"    - Node ID: {NODE_ID}")
        print(f"    - Node Type: {NODE_VERSION}")
        print(f"    - Build Server: {BUILD_SERVER}")
        print(f"    - Build Version: {BUILD_VERSION}")
        update_node_binary(NAME, NODE_ID, NODE_VERSION, BUILD_SERVER, BUILD_VERSION)

    if args.command == "enable:amendment":
        NAME = args.name
        AMENDMENT_NAME = args.amendment_name
        NODE_ID = args.node_id
        NODE_VERSION = args.node_version
        print(
            f"{bcolors.BLUE}Enabling Amendment with the following parameters:{bcolors.END}"
        )
        print(f"    - Network Name: {NAME}")
        print(f"    - Amendment Name: {AMENDMENT_NAME}")
        print(f"    - Node ID: {NODE_ID}")
        print(f"    - Node Type: {NODE_VERSION}")
        enable_node_amendment(NAME, AMENDMENT_NAME, NODE_ID, NODE_VERSION)

    # UP STANDALONE
    if args.command == "up:standalone":
        LOG_LEVEL = args.log_level
        BUILD_TYPE = args.build_type
        PUBLIC_KEY = args.public_key
        IMPORT_KEY = args.import_key
        PROTOCOL = args.protocol
        NETWORK_TYPE = args.network_type
        NETWORK_ID = args.network_id
        BUILD_SERVER = args.server
        BUILD_VERSION = args.version
        IPFS_SERVER = args.ipfs

        if PROTOCOL == "xahau" and not IMPORT_KEY:
            IMPORT_KEY: str = (
                "ED74D4036C6591A4BDF9C54CEFA39B996A5DCE5F86D11FDA1874481CE9D5A1CDC1"
            )

        if PROTOCOL == "xahau":
            BUILD_SERVER: str = "https://build.xahau.tech"
            BUILD_TYPE: str = "binary"

        if PROTOCOL == "xahau" and not BUILD_VERSION:
            BUILD_VERSION: str = XAHAU_RELEASE

        if PROTOCOL == "xrpl":
            BUILD_SERVER: str = "rippleci"
            BUILD_TYPE: str = "image"
            NETWORK_ID: int = 1

        if PROTOCOL == "xrpl" and not BUILD_VERSION:
            BUILD_VERSION: str = XRPL_RELEASE

        print(
            f"{bcolors.BLUE}Setting Up Standalone Network with the following parameters:{bcolors.END}"
        )
        print(f"    - Log Level: {LOG_LEVEL}")
        print(f"    - Build Type: {BUILD_TYPE}")
        print(f"    - Public Key: {PUBLIC_KEY}")
        print(f"    - Import Key: {IMPORT_KEY}")
        print(f"    - Protocol: {PROTOCOL}")
        print(f"    - Network Type: {NETWORK_TYPE}")
        print(f"    - Network ID: {NETWORK_ID}")
        print(f"    - Build Server: {BUILD_SERVER}")
        print(f"    - Build Version: {BUILD_VERSION}")
        print(f"    - IPFS Server: {IPFS_SERVER}")

        if BUILD_TYPE == "image":
            create_standalone_image(
                LOG_LEVEL,
                PUBLIC_KEY,
                IMPORT_KEY,
                PROTOCOL,
                NETWORK_TYPE,
                NETWORK_ID,
                BUILD_SERVER,
                BUILD_VERSION,
                IPFS_SERVER,
            )
        else:
            create_standalone_binary(
                LOG_LEVEL,
                PUBLIC_KEY,
                IMPORT_KEY,
                PROTOCOL,
                NETWORK_TYPE,
                NETWORK_ID,
                BUILD_SERVER,
                BUILD_VERSION,
                IPFS_SERVER,
            )

        run_start(
            [f"{basedir}/{PROTOCOL}-{BUILD_VERSION}/start.sh"],
            PROTOCOL,
            BUILD_VERSION,
            "standalone",
        )


if __name__ == "__main__":
    main()
