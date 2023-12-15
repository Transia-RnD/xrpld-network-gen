#!/usr/bin/env python
# coding: utf-8

import time
import logging
from typing import Dict, Any, List  # noqa: F401

from testing_config import BaseTestConfig
from xrpld_netgen.main import (
    create_standalone_image,
    create_standalone_binary,
)

logger = logging.getLogger("app")


class TestINetGen(BaseTestConfig):
    def test_standalone_image(cls):
        create_standalone_image(
            "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501",
            "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501",
            "xahau",  # protocol
            "standalone",  # net type
            21337,  # network id
            "gcr.io/thelab-924f3",  # build server
            "dangell7-devnet-binary:2.0.0-b2",  # build version
        )

    def test_standalone_binary(cls):
        create_standalone_binary(
            "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501",
            "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501",
            "xahau",  # protocol
            "standalone",  # net type
            21337,  # network id
            "https://build.xahau.tech",  # build server
            "2023.11.10-dev+549",  # build version
        )
