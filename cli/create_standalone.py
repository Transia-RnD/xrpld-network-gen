#!/usr/bin/env python3
# coding: utf-8

# ./cli/create_standalone.py --protocol "xahau" --network_id 21337 --binary_server https://build.xahau.tech  --build_version "2023.11.10-dev+549"

import argparse
from xrpld_netgen.main import create_standalone_binary

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="A python script to create a standalone."
    )
    parser.add_argument("--public_key", required=False, help="The public vl key")
    parser.add_argument("--import_key", required=False, help="The import vl key")
    parser.add_argument("--protocol", required=True, help="The protocol of the network")
    parser.add_argument("--network_id", type=int, required=True, help="The network id")
    parser.add_argument(
        "--binary_server", required=True, help="The build server for the network"
    )
    parser.add_argument(
        "--build_version", required=True, help="The build version for the network"
    )
    args = parser.parse_args()

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
    if not IMPORT_KEY:
        IMPORT_KEY: str = (
            "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501"
        )

    create_standalone_binary(
        PUBLIC_KEY,
        IMPORT_KEY,
        PROTOCOL,
        NETWORK_ID,
        BUILD_SERVER,
        BUILD_VERSION,
    )
