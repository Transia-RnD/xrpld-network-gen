#!/usr/bin/env python
# coding: utf-8

import time
import logging
from typing import Dict, Any, List  # noqa: F401

from testing_config import BaseTestConfig
from xrpld_netgen.main import (
    start_local,
)

logger = logging.getLogger("app")


class TestINetGenLocal(BaseTestConfig):
    def _test_start_local(cls):
        start_local(
            "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501",
            "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501",
            "xahau",  # protocol
            "standalone",  # net type
            21337,  # network id
        )
