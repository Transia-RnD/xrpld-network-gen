#!/usr/bin/env python3
# coding: utf-8

# ./cli/create_network.py --protocol "xahau" --name "test" --num_validators 3 --num_peers 1 --network_id 21337 --image_name "dangell7-devnet-binary:2.0.0-b2"

import argparse
from xrpld_netgen.main import create_network

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A python script to create a network.")
    parser.add_argument("--protocol", required=True, help="The protocol of the network")
    parser.add_argument("--name", required=True, help="The name of the network")
    parser.add_argument(
        "--num_validators",
        type=int,
        required=True,
        help="The number of validators in the network",
    )
    parser.add_argument(
        "--num_peers",
        type=int,
        required=True,
        help="The number of peers in the network",
    )
    parser.add_argument("--network_id", type=int, required=True, help="The network id")
    parser.add_argument(
        "--image_name", required=True, help="The image name for the network"
    )
    args = parser.parse_args()

    PROTOCOL = args.protocol
    NAME = args.name
    NUM_VALIDATORS = args.num_validators
    NUM_PEERS = args.num_peers
    NETWORK_ID = args.network_id
    IMAGE_NAME = args.image_name

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
