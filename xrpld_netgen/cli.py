#!/usr/bin/env python3
# coding: utf-8

# xrpld-netgen create:standalone --protocol "xahau" --build_version "2023.11.10-dev+549"

import os
import argparse
from xrpld_netgen.main import (
    create_network,
    create_standalone_binary,
    run_file,
    remove_directory,
)

basedir = os.path.abspath(os.path.dirname(__file__))


def main():
    parser = argparse.ArgumentParser(
        description="A python cli to build xrpld networks and standalone ledgers."
    )
    subparsers = parser.add_subparsers(dest="command")

    # start
    parser_st = subparsers.add_parser("start", help="Start Network")
    parser_st.add_argument("--name", required=True, help="The name of the network")
    # stop
    parser_s = subparsers.add_parser("stop", help="Start Network")
    parser_s.add_argument("--name", required=True, help="The name of the network")
    # remove
    parser_r = subparsers.add_parser("remove", help="Remove Network")
    parser_r.add_argument("--name", required=True, help="The name of the network")

    # create:network
    parser_cn = subparsers.add_parser("create:network", help="Create Network")
    parser_cn.add_argument(
        "--protocol", required=False, help="The protocol of the network"
    )
    parser_cn.add_argument("--name", required=True, help="The name of the network")
    parser_cn.add_argument(
        "--num_validators",
        type=int,
        required=False,
        help="The number of validators in the network",
    )
    parser_cn.add_argument(
        "--num_peers",
        type=int,
        required=False,
        help="The number of peers in the network",
    )
    parser_cn.add_argument(
        "--network_id", type=int, required=False, help="The network id"
    )
    parser_cn.add_argument(
        "--image_name", required=True, help="The image name for the network"
    )

    # create:standalone
    parser_cs = subparsers.add_parser("create:standalone", help="Create Standalone")
    parser_cs.add_argument("--public_key", required=False, help="The public vl key")
    parser_cs.add_argument("--import_key", required=False, help="The import vl key")
    parser_cs.add_argument(
        "--protocol", required=False, help="The protocol of the network"
    )
    parser_cs.add_argument(
        "--network_id", type=int, required=False, help="The network id"
    )
    parser_cs.add_argument(
        "--binary_server", required=False, help="The build server for the network"
    )
    parser_cs.add_argument(
        "--build_version", required=True, help="The build version for the network"
    )

    args = parser.parse_args()
    if args.command == "start":
        NAME = args.name
        run_file(f"{basedir}/{NAME}/start.sh")

    if args.command == "remove":
        NAME = args.name
        remove_directory(f"{basedir}/{NAME}")

    if args.command == "create:network":
        PROTOCOL = args.protocol
        NAME = args.name
        NUM_VALIDATORS = args.num_validators
        NUM_PEERS = args.num_peers
        NETWORK_ID = args.network_id
        IMAGE_NAME = args.image_name

        if not PROTOCOL:
            PROTOCOL: str = "rippled"
        if not NUM_VALIDATORS:
            NUM_VALIDATORS: int = 2
        if not NUM_PEERS:
            NUM_PEERS: int = 1
        if not NETWORK_ID:
            NETWORK_ID: int = 21337

        public_key: str = (
            "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501"
        )
        private_key: str = (
            "A232AD54A29466CDE4A3D99C651B332F89D25B5ACE3D8BD6ABD4748DA67159B2"
        )
        manifest: str = "JAAAAAFxIe2H4OqRqv+hMLeLddLMPlMgKqG9irPV57rFMMhEDjKFAXMh7eP2BCI6nc9g/k66bj7ksWmKuwZOKJeFx1emXip6dXxCdkB/0p6s8BzkgY7AXQxJh47pGP+vVtgcVJ44y2FK9H7xMsGOhdrbl0KUWY1Y15ZHd/R/QmvLhNC05psAX1+76YkNcBJAytrEazBhxQAEZSSLkfLwNTj3MewH1l1BjZhuIARiJNzh90dkV6AFqFW2m9VyVNLJX8EKl6yau/NET8KV2oFhAQ=="

        create_network(
            public_key,
            private_key,
            manifest,
            PROTOCOL,
            NAME,
            NUM_VALIDATORS,
            NUM_PEERS,
            NETWORK_ID,
            IMAGE_NAME,
        )

    if args.command == "create:standalone":
        PUBLIC_KEY = args.public_key
        IMPORT_KEY = args.import_key
        PROTOCOL = args.protocol
        NETWORK_ID = args.network_id
        BUILD_SERVER = args.binary_server
        BUILD_VERSION = args.build_version

        if not PUBLIC_KEY:
            PUBLIC_KEY: str = (
                "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501"
            )
        if not PROTOCOL:
            PROTOCOL: str = "rippled"
        if PROTOCOL == "xahau" and not IMPORT_KEY:
            IMPORT_KEY: str = (
                "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501"
            )
        if PROTOCOL == "xahau" and not BUILD_SERVER:
            BUILD_SERVER: str = "https://build.xahau.tech"
        if not NETWORK_ID:
            NETWORK_ID: int = 21337

        create_standalone_binary(
            PUBLIC_KEY,
            IMPORT_KEY,
            PROTOCOL,
            NETWORK_ID,
            BUILD_SERVER,
            BUILD_VERSION,
        )


if __name__ == "__main__":
    main()
