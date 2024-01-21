#!/usr/bin/env python
# coding: utf-8

import time
import logging
from typing import Dict, Any, List  # noqa: F401

from testing_config import BaseTestConfig

from xrpld_netgen.network import (
    create_network,
    update_node_binary,
    enable_node_amendment,
)

logger = logging.getLogger("app")


class TestINetGenXahau(BaseTestConfig):
    def test_create_xahau_network(cls):
        create_network(
            "ED74D4036C6591A4BDF9C54CEFA39B996A5DCE5F86D11FDA1874481CE9D5A1CDC1",
            "xahau",  # protocol
            6,  # num validators
            2,  # num peers
            21336,  # network id
            "https://build.xahau.tech",  # image host
            "2024.1.19-HEAD+702",  # image name
            True,
            3,
        )

    def _test_update_node(cls):
        update_node_binary(
            "2023.11.10-dev+549-cluster",  # network name
            "1",  # node id
            "validator",  # node type
            "https://build.xahau.tech",  # build server
            "2023.12.29-release+689",  # build version
        )

    def _test_enable_amendment(cls):
        enable_node_amendment(
            "2023.11.10-dev+549-cluster",  # network name
            "fixXahauV1",  # amendment name
            "5",  # node id
            "validator",  # node type
        )


class TestINetGenRippled(BaseTestConfig):
    def _test_create_rippled_network(cls):
        create_network(
            None,
            "ripple",  # protocol
            6,  # num validators
            2,  # num peers
            21336,  # network id
            "gcr.io/thelab-924f3",  # build server
            "dangell7-testnet-binary:2.0.0",  # build version
            True,
            3,
        )
