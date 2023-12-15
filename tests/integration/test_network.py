#!/usr/bin/env python
# coding: utf-8

import time
import logging
from typing import Dict, Any, List  # noqa: F401

from testing_config import BaseTestConfig

from xrpld_netgen.network import (
    create_network_binary,
    update_node_binary,
    enable_node_amendment,
)

logger = logging.getLogger("app")


class TestINetGen(BaseTestConfig):
    def test_create_xahau_network(cls):
        create_network_binary(
            "ED6ACA9949FC56CB07574C5AC9D29C8E62EB9D0752954F4D8953380EDB3EC46DC3",
            "ED74D4036C6591A4BDF9C54CEFA39B996A5DCE5F86D11FDA1874481CE9D5A1CDC1",
            "87BAB1FB62F8F665F58DD1C8293B11A4E20DA1E5C1C41CE65FAEB3A1E110B6D8",
            "JAAAAAFxIe1qyplJ/FbLB1dMWsnSnI5i650HUpVPTYlTOA7bPsRtw3Mh7VyccqnOn1TaZC6UI1WMJD4sH3HqEzvJkPDoEVRWGdowdkArhkDIKzi+W4+/8ry4RyGnsSC7bMZzKw4/TM70esOQTr9TZKhF1FaePva/Aitt3l2KnORLIALBVmZ1x3yAYr4CcBJA67ISzEFSkOIoyNvLWPdetIdN/xEekPJNp2hyhodt2cu0sr46wdXPMjIFO/cFfxTndxTyTW/R/29U92Dcly8nAg==",
            "xahau",  # protocol
            4,  # num validators
            1,  # num peers
            21336,  # network id
            "https://build.xahau.tech",  # image host
            "2023.11.9-dev+540",  # image name
            True,
            3,
        )

    def _test_update_node(cls):
        update_node_binary(
            "2023.11.9-dev+540-cluster",  # network name
            "1",  # node id
            "validator",  # node type
            "https://build.xahau.tech",  # build server
            "2023.12.1-dev+610",  # build version
        )

    def _test_enable_amendment(cls):
        enable_node_amendment(
            "2023.11.9-dev+540-cluster",  # network name
            "fix1623",  # amendment name
            "2",  # node id
            "validator",  # node type
        )
