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

# 2025.4.18-release+1718


class TestINetGenXahau(BaseTestConfig):
    def _test_create_xahau_network(cls):
        create_network(
            "trace",
            "ED74D4036C6591A4BDF9C54CEFA39B996A5DCE5F86D11FDA1874481CE9D5A1CDC1",
            "xahau",  # protocol
            7,  # num validators
            1,  # num peers
            21465,  # network id
            "https://build.xahau.tech",  # image host
            "2025.5.1-release+1762",  # image name
            True,
            3,
            "rwdb",  # database type
        )

    def _test_create_ansible(cls):
        create_ansible(
            "error",
            "ED74D4036C6591A4BDF9C54CEFA39B996A5DCE5F86D11FDA1874481CE9D5A1CDC1",
            "xahau",  # protocol
            6,  # num validators
            2,  # num peers
            21465,  # network id
            "https://build.xahau.tech",  # image host
            "2025.5.1-release+1762",  # image name
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
            "2025.2.6-release+1299-cluster",  # network name
            "1",  # node id
            "peer",  # node type: validator or peer
            "https://build.xahau.tech",  # build server
            "2025.4.18-release+1718",  # build version
        )

    def _test_enable_amendment(cls):
        network_name = "2025.2.6-release+1299-cluster"
        amendment_name = "Touch"
        validator_list = ["2", "3", "4", "5", "6", "7"]
        for id in validator_list:
            enable_node_amendment(
                network_name,  # network name
                amendment_name,  # amendment name
                id,  # node id
                "validator",  # node type
            )


class TestINetGenRippled(BaseTestConfig):
    def _test_create_network(cls):
        create_network(
            "trace",
            None,
            "xrpl",  # protocol
            3,  # num validators
            1,  # num peers
            21465,  # network id
            "https://github.com/Transia-RnD/rippled/tree/options",  # build server
            "d0120767e048ffc42ddd217f7118a6b49e79cab3",  # build version
            True,
            3,
            "NuDB",
        )

    def test_create_ansible(cls):
        # https://github.com/Transia-RnD/rippled/tree/develop
        # 9874d47d7fbfe81e4cd78afd5b60ec33124ee2e9
        create_ansible(
            "warn",
            None,
            "xrpl",  # protocol
            6,  # num validators
            2,  # num peers
            21465,  # network id
            "https://github.com/Transia-RnD/rippled/tree/firewall-v1",  # build server
            "3686ac3f3046a55fc6a6dbdb311b3eb52b88f217",  # build version
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
