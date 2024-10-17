#!/usr/bin/env python
# coding: utf-8

import time
import logging
from typing import Dict, Any, List  # noqa: F401

from testing_config import BaseTestConfig
from xrpld_netgen.main import create_standalone_image, create_standalone_binary, basedir
from tests.utils import is_folder_and_files

logger = logging.getLogger("app")


class TestINetGenStandalone(BaseTestConfig):
    def _test_standalone_image(cls):
        create_standalone_image(
            "trace",
            "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501",
            "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501",
            "xrpl",  # protocol
            "standalone",  # net type
            1,  # network id
            "rippleci",  # build server
            "2.0.0-b4",  # build version
        )
        folder = f"{basedir}/xrpl-2.0.0-b4"
        files = [
            "Dockerfile",
            "docker-compose.yml",
            # "features.json", // doesnt save for either
            "start.sh",
            # "config", // folder
            "entrypoint",
            "genesis.json",
            "stop.sh",
        ]
        folder_exists, files_exist = is_folder_and_files(folder, files)
        cls.assertTrue(folder_exists)
        for file in files_exist:
            cls.assertTrue(file)

    def test_standalone_binary(cls):
        create_standalone_binary(
            "trace",
            "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501",
            "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501",
            "xahau",  # protocol
            "standalone",  # net type
            21337,  # network id
            "https://build.xahau.tech",  # build server
            "2024.9.11-release+985",  # build version
        )
        folder = f"{basedir}/xahau-2024.9.11-release+985"
        files = [
            "Dockerfile",
            "docker-compose.yml",
            # "features.json", // doesnt save for xahau
            "start.sh",
            # "config", // folder
            "entrypoint",
            "genesis.json",
            "stop.sh",
        ]
        folder_exists, files_exist = is_folder_and_files(folder, files)
        cls.assertTrue(folder_exists)
        for file in files_exist:
            cls.assertTrue(file)
