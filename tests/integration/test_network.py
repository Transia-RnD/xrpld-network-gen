#!/usr/bin/env python
# coding: utf-8

import time
import logging
from typing import Dict, Any, List  # noqa: F401

from testing_config import BaseTestConfig

from xrpld_netgen.network import (
    create_ansible,
    create_network,
    update_node_binary,
    enable_node_amendment,
)

logger = logging.getLogger("app")


class TestINetGenXahau(BaseTestConfig):
    def _test_create_xahau_network(cls):
        create_network(
            "trace",
            "ED74D4036C6591A4BDF9C54CEFA39B996A5DCE5F86D11FDA1874481CE9D5A1CDC1",
            "xahau",  # protocol
            6,  # num validators
            2,  # num peers
            21336,  # network id
            "https://build.xahau.tech",  # image host
            "2024.6.3-jshooks+903",  # image name
            True,
            3,
        )

    def test_create_ansible(cls):
        create_ansible(
            "trace",
            "ED74D4036C6591A4BDF9C54CEFA39B996A5DCE5F86D11FDA1874481CE9D5A1CDC1",
            "xahau",  # protocol
            6,  # num validators
            2,  # num peers
            21339,  # network id
            "https://build.xahau.tech",  # image host
            "2024.12.2-HEAD+1182",  # image name
            True,
            3,
            "rwdb",
            [
                "79.110.60.99",
                "79.110.60.100",
                "79.110.60.101",
                "79.110.60.102",
                "79.110.60.103",
                "79.110.60.104",
            ],
            [
                "79.110.60.105",
                "79.110.60.106",
            ],
        )

    def _test_update_node(cls):
        update_node_binary(
            "2023.12.29-release+689-cluster",  # network name
            "1",  # node id
            "validator",  # node type
            "https://build.xahau.tech",  # build server
            "2024.1.25-release+738",  # build version
        )

    def _test_enable_amendment(cls):
        enable_node_amendment(
            "2023.11.10-dev+549-cluster",  # network name
            "fixXahauV2",  # amendment name
            "5",  # node id
            "validator",  # node type
        )


class TestINetGenRippled(BaseTestConfig):
    def _test_create_network(cls):
        create_network(
            "trace",
            None,
            "xrpl",  # protocol
            6,  # num validators
            2,  # num peers
            21336,  # network id
            "https://github.com/mvadari/rippled/tree/simulate",  # build server
            "01e568318811ff8bb667fe420e021a087fda1ee3",  # build version
            True,
            3,
        )

    def _test_create_ansible(cls):
        create_ansible(
            "trace",
            None,
            "xrpl",  # protocol
            6,  # num validators
            2,  # num peers
            21336,  # network id
            "https://github.com/Transia-RnD/rippled/tree/feature-batch",  # build server
            "70e993185c7bf5e77dc03729d6dc4e22d8607571",  # build version
            True,
            3,
            "NuDB",
            [
                "79.110.60.99",
                "79.110.60.100",
                "79.110.60.101",
                "79.110.60.102",
                "79.110.60.103",
                "79.110.60.104",
            ],
            [
                "79.110.60.105",
                "79.110.60.106",
            ],
        )
