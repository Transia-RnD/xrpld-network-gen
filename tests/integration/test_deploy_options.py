#!/usr/bin/env python
# coding: utf-8

from testing_config import BaseTestConfig

from xrpld_netgen.network import (
    create_ansible,
)


class TestINetGenXrpld(BaseTestConfig):
    def test_create_ansible(cls):
        create_ansible(
            "warn",
            None,
            "xrpl",  # protocol
            3,  # num validators
            1,  # num peers
            21565,  # network id
            "https://github.com/Transia-RnD/rippled/tree/options-sidechain",  # build server
            "204442f551db067526e0551f724f9a40cf8f5415",  # build version
            True,
            3,
            "NuDB",
            [
                "79.110.60.102",
                "79.110.60.103",
                "79.110.60.104",
            ],
            [
                "79.110.60.106",
            ],
        )
