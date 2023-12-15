#!/usr/bin/env python3
# coding: utf-8

# NETWORK
# create:network
# xrpld-netgen create:network --protocol "xahau" --version "2023.11.10-dev+549"
# add:peer
# xrpld-netgen add:peer --network_name xrpld-2023.11.10-dev+549 --protocol "xahau" --version "2023.11.10-dev+549"
# remove:peer
# xrpld-netgen remove:peer --network_name xrpld-2023.11.10-dev+549 --protocol "xahau" --version "2023.11.10-dev+549"
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
    create_network_binary,
    update_node_binary,
    enable_node_amendment,
)
from xrpld_netgen.utils.misc import (
    run_file,
    remove_directory,
)

basedir = os.path.abspath(os.path.dirname(__file__))

XAHAU_RELEASE: str = "2023.11.10-dev+549"
XRPL_RELEASE: str = "1.12.0"


def main():
    parser = argparse.ArgumentParser(
        description="A python cli to build xrpld networks and standalone ledgers."
    )
    subparsers = parser.add_subparsers(dest="command")

    # LOCAL
    # start:local
    parser_sl = subparsers.add_parser("start:local", help="Start Local Network")
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
    parser_spl = subparsers.add_parser("stop:local", help="Stop Local Network")

    # NETWORK

    # create:network
    parser_cn = subparsers.add_parser("create:network", help="Create Network")
    parser_cn.add_argument(
        "--protocol",
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
        "--network_id", type=int, required=False, help="The network id", default=21339
    )
    parser_cn.add_argument(
        "--build_server", required=False, help="The build server for the network"
    )
    parser_cn.add_argument(
        "--build_version", required=False, help="The build version for the network"
    )
    # update:node
    parser_un = subparsers.add_parser("update:node", help="Update Node Version")
    parser_un.add_argument("--name", required=True, help="The name of the network")
    parser_un.add_argument(
        "--node_id",
        required=True,
        help="The node id you want to update",
    )
    parser_un.add_argument(
        "--node_type",
        required=True,
        help="The node type you want to update",
        choices=["validator", "peer"],
    )
    parser_un.add_argument(
        "--build_server", required=False, help="The build server for the node"
    )
    parser_un.add_argument(
        "--build_version", required=False, help="The build version for the node"
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

    # create:standalone
    parser_cs = subparsers.add_parser("create:standalone", help="Create Standalone")
    parser_cs.add_argument(
        "--build_type",
        required=True,
        help="The build type",
        choices=["image", "binary"],
        default="binary",
    )
    parser_cs.add_argument(
        "--public_key",
        required=False,
        help="The public vl key",
        default="ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501",
    )
    parser_cs.add_argument("--import_key", required=False, help="The import vl key")
    parser_cs.add_argument(
        "--protocol",
        required=False,
        help="The protocol of the network",
        default="xahau",
    )
    parser_cs.add_argument(
        "--network_id", type=int, required=False, help="The network id", default=21339
    )
    parser_cs.add_argument(
        "--network_type",
        type=int,
        required=False,
        help="The network type",
        default="standalone",
    )
    parser_cs.add_argument(
        "--server", required=False, help="The build server for the network"
    )
    parser_cs.add_argument(
        "--version", required=True, help="The build version for the network"
    )
    # up:standalone
    parser_us = subparsers.add_parser("up:standalone", help="Up Standalone")
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

    # LOCAL
    if args.command == "start:local":
        PUBLIC_KEY = args.public_key
        IMPORT_KEY = args.import_key
        PROTOCOL = args.protocol
        NETWORK_TYPE = args.network_type
        NETWORK_ID = args.network_id

        start_local(PUBLIC_KEY, IMPORT_KEY, PROTOCOL, NETWORK_TYPE, NETWORK_ID)

    if args.command == "stop:local":
        run_file("./stop.sh")

    # CREATE NETWORK
    if args.command == "create:network":
        PROTOCOL = args.protocol
        NUM_VALIDATORS = args.num_validators
        NUM_PEERS = args.num_peers
        NETWORK_ID = args.network_id
        BUILD_SERVER = args.build_server
        BUILD_VERSION = args.build_version

        public_key: str = (
            "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501"
        )
        import_vl_key: str = (
            "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501"
        )
        private_key: str = (
            "A232AD54A29466CDE4A3D99C651B332F89D25B5ACE3D8BD6ABD4748DA67159B2"
        )
        manifest: str = "JAAAAAFxIe2H4OqRqv+hMLeLddLMPlMgKqG9irPV57rFMMhEDjKFAXMh7eP2BCI6nc9g/k66bj7ksWmKuwZOKJeFx1emXip6dXxCdkB/0p6s8BzkgY7AXQxJh47pGP+vVtgcVJ44y2FK9H7xMsGOhdrbl0KUWY1Y15ZHd/R/QmvLhNC05psAX1+76YkNcBJAytrEazBhxQAEZSSLkfLwNTj3MewH1l1BjZhuIARiJNzh90dkV6AFqFW2m9VyVNLJX8EKl6yau/NET8KV2oFhAQ=="

        if not BUILD_SERVER:
            BUILD_SERVER: str = "https://build.xahau.tech"

        if not BUILD_VERSION:
            BUILD_VERSION: str = XAHAU_RELEASE

        create_network_binary(
            public_key,
            import_vl_key,
            private_key,
            manifest,
            PROTOCOL,
            NUM_VALIDATORS,
            NUM_PEERS,
            NETWORK_ID,
            BUILD_SERVER,
            BUILD_VERSION,
            True,
            3,
        )

    if args.command == "update:node":
        NAME = args.name
        NODE_ID = args.node_id
        NODE_VERSION = args.node_version
        BUILD_SERVER = args.build_server
        BUILD_VERSION = args.build_version
        update_node_binary(NAME, NODE_ID, NODE_VERSION, BUILD_SERVER, BUILD_VERSION)

    if args.command == "enable:amendment":
        NAME = args.name
        AMENDMENT_NAME = args.amendment_name
        NODE_ID = args.node_id
        NODE_VERSION = args.node_version
        enable_node_amendment(NAME, AMENDMENT_NAME, NODE_ID, NODE_VERSION)

    # MANAGE NETWORK/STANDALONE
    if args.command == "start":
        NAME = args.name
        run_file(f"{basedir}/{NAME}/start.sh")

    if args.command == "stop":
        NAME = args.name
        run_file(f"{basedir}/{NAME}/stop.sh")

    if args.command == "remove":
        NAME = args.name
        remove_directory(f"{basedir}/{NAME}")

    # UP STANDALONE
    if args.command == "up:standalone":
        BUILD_TYPE = args.build_type
        PUBLIC_KEY = args.public_key
        IMPORT_KEY = args.import_key
        PROTOCOL = args.protocol
        NETWORK_TYPE = args.network_type
        NETWORK_ID = args.network_id
        BUILD_SERVER = args.server
        BUILD_VERSION = args.version

        if PROTOCOL == "xahau" and not IMPORT_KEY:
            IMPORT_KEY: str = (
                "ED74D4036C6591A4BDF9C54CEFA39B996A5DCE5F86D11FDA1874481CE9D5A1CDC1"
            )

        if BUILD_TYPE == "binary" and not BUILD_SERVER:
            BUILD_SERVER: str = "https://build.xahau.tech"

        if BUILD_TYPE == "image" and not BUILD_SERVER:
            BUILD_SERVER: str = "gcr.io/thelab-924f3"

        if PROTOCOL == "xahau" and BUILD_TYPE == "binary" and not BUILD_VERSION:
            BUILD_VERSION: str = XAHAU_RELEASE

        if PROTOCOL == "xrpl" and BUILD_TYPE == "image" and not BUILD_VERSION:
            BUILD_VERSION: str = XRPL_RELEASE

        if BUILD_TYPE == "binary" and PROTOCOL == "xrpl":
            raise ValueError("Invalid `PROTOCOL`  and `BUILD_TYPE` mismatch")

        if BUILD_TYPE == "image":
            create_standalone_image(
                PUBLIC_KEY,
                IMPORT_KEY,
                PROTOCOL,
                NETWORK_TYPE,
                NETWORK_ID,
                BUILD_SERVER,
                BUILD_VERSION,
            )
        else:
            create_standalone_binary(
                PUBLIC_KEY,
                IMPORT_KEY,
                PROTOCOL,
                NETWORK_TYPE,
                NETWORK_ID,
                BUILD_SERVER,
                BUILD_VERSION,
            )

        run_file(f"{basedir}/{PROTOCOL}-{BUILD_VERSION}/start.sh")
        print(f"Run with: xrpld-netgen start --name {PROTOCOL}-{BUILD_VERSION}")

    # DOWN STANDALONE
    if args.command == "down:standalone":
        NAME = args.name
        if NAME:
            run_file(f"{basedir}/{NAME}/stop.sh")
            remove_directory(f"{basedir}/{NAME}")
            return

        PROTOCOL = args.protocol
        BUILD_VERSION = args.version

        if PROTOCOL == "xahau" and not BUILD_VERSION:
            BUILD_VERSION: str = XAHAU_RELEASE

        if PROTOCOL == "xrpl" and not BUILD_VERSION:
            BUILD_VERSION: str = XRPL_RELEASE

        run_file(f"{basedir}/{PROTOCOL}-{BUILD_VERSION}/stop.sh")
        # remove_directory(f"{basedir}/{PROTOCOL}-{BUILD_VERSION}")


if __name__ == "__main__":
    main()
