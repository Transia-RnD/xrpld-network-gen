#!/usr/bin/env python
# coding: utf-8

import time
import logging
from typing import Dict, Any, List  # noqa: F401

from testing_config import BaseTestConfig
from xrpld_netgen.main import (
    create_network,
    create_standalone_image,
    create_standalone_binary,
    start_local,
)

logger = logging.getLogger("app")


class TestINetGen(BaseTestConfig):
    def _test_create_ripple_network(cls):
        create_network(
            "ED74D4036C6591A4BDF9C54CEFA39B996A5DCE5F86D11FDA1874481CE9D5A1CDC1",
            None,
            "CC9E8B118E8E927DA82A66B9D931E1AB6309BA32F057F8B216600B347C552006",
            "JAAAAAFxIe101ANsZZGkvfnFTO+jm5lqXc5fhtEf2hh0SBzp1aHNwXMh7TN9+b62cZqTngaFYU5tbGpYHC8oYuI3G3vwj9OW2Z9gdkAnUjfY5zOEkhq31tU4338jcyUpVA5/VTsANFce7unDo+JeVoEhfuOb/Y8WA3Diu9XzuOD4U/ikfgf9SZOlOGcBcBJAw44PLjH+HUtEnwX45lIRmo0x5aINFMvZsBpE9QteSDBXKwYzLdnSW4e1bs21o+IILJIiIKU/+1Uxx0FRpQbMDA==",
            "ripple",  # protocol
            "test-ripple",  # name
            10,  # num validators
            1,  # num peers
            None,  # network id
            "transia",  # image host
            "ripple-binary:1.11.0",  # image name
            True,
            8,
        )

    def _test_create_xahau_network(cls):
        create_network(
            "ED6ACA9949FC56CB07574C5AC9D29C8E62EB9D0752954F4D8953380EDB3EC46DC3",
            "ED74D4036C6591A4BDF9C54CEFA39B996A5DCE5F86D11FDA1874481CE9D5A1CDC1",
            "87BAB1FB62F8F665F58DD1C8293B11A4E20DA1E5C1C41CE65FAEB3A1E110B6D8",
            "JAAAAAFxIe1qyplJ/FbLB1dMWsnSnI5i650HUpVPTYlTOA7bPsRtw3Mh7VyccqnOn1TaZC6UI1WMJD4sH3HqEzvJkPDoEVRWGdowdkArhkDIKzi+W4+/8ry4RyGnsSC7bMZzKw4/TM70esOQTr9TZKhF1FaePva/Aitt3l2KnORLIALBVmZ1x3yAYr4CcBJA67ISzEFSkOIoyNvLWPdetIdN/xEekPJNp2hyhodt2cu0sr46wdXPMjIFO/cFfxTndxTyTW/R/29U92Dcly8nAg==",
            "xahau",  # protocol
            "test-xahau",  # name
            3,  # num validators
            1,  # num peers
            21336,  # network id
            "transia",  # image host
            "xahau-binary:2023.11.8-507",  # image name
            True,
            3,
        )

    def _test_standalone_image(cls):
        create_standalone_image(
            "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501",
            "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501",
            "xahau",  # protocol
            "standalone",  # net type
            21337,  # network id
            "gcr.io/thelab-924f3",  # build server
            "dangell7-devnet-binary:2.0.0-b2",  # build version
        )

    def _test_standalone_binary(cls):
        create_standalone_binary(
            "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501",
            "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501",
            "xahau",  # protocol
            "standalone",  # net type
            21337,  # network id
            "https://build.xahau.tech",  # build server
            "2023.11.10-dev+549",  # build version
        )

    def _test_start_local(cls):
        start_local(
            "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501",
            "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501",
            "xahau",  # protocol
            "standalone",  # net type
            21337,  # network id
        )
