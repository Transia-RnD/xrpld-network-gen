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
)

logger = logging.getLogger("app")


class TestUNetGen(BaseTestConfig):
    def test_create_network(cls):
        print('done')
