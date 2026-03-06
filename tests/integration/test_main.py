#!/usr/bin/env python
# coding: utf-8

import os
import logging
from typing import Dict, Any, List  # noqa: F401

from testing_config import BaseTestConfig
from xrpld_netgen.main import (
    start_local,
    create_standalone_image,
    create_standalone_binary,
    basedir
)
from tests.utils import is_folder_and_files

logger = logging.getLogger("app")

XAHAUD_BUILD_DIR = os.path.expanduser(
    "~/projects/ledger-works/xahaud/build"
)
XRPLD_BUILD_DIR = os.path.expanduser(
    "~/projects/ledger-works/xrpld/build"
)
XRPL_VERSION = "3.1.1"
XAHAU_VERSION = "2025.7.9-release+1951"


class TestINetGenMainLocal(BaseTestConfig):
    def setUp(self):
        super().setUp()
        self._orig_dir = os.getcwd()
        os.chdir(XAHAUD_BUILD_DIR)

    def tearDown(self):
        os.chdir(self._orig_dir)
        super().tearDown()

    def _test_start_local_xrpl(self):
        start_local(
            "trace",
            "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501",
            None,
            "xrpl",  # protocol
            "standalone",  # net type
            21337,  # network id
            "NuDB",
        )

    def _test_start_local_xahau(self):
        start_local(
            "trace",
            "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501",
            "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501",
            "xahau",  # protocol
            "standalone",  # net type
            21337,  # network id
            "NuDB",
        )

    def test_standalone_xrpl_image(cls):
        version: str = XRPL_VERSION
        create_standalone_image(
            "trace",
            "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501",
            None,
            "xrpl",  # protocol
            "standalone",  # net type
            1,  # network id
            "rippleci",  # build server
            version,  # build version
        )
        folder = f"{basedir}/xrpl-{version}"
        files = [
            "Dockerfile",
            "docker-compose.yml",
            "start.sh",
            "entrypoint",
            "genesis.json",
            "stop.sh",
        ]
        folder_exists, files_exist = is_folder_and_files(folder, files)
        cls.assertTrue(folder_exists)
        for file in files_exist:
            cls.assertTrue(file)

    # def test_standalone_xahau_image(cls):
    #     version: str = XAHAU_VERSION
    #     create_standalone_image(
    #         "trace",
    #         "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501",
    #         "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501",
    #         "xahau",  # protocol
    #         "standalone",  # net type
    #         1,  # network id
    #         "rippleci",  # build server
    #         version,  # build version
    #     )
    #     folder = f"{basedir}/xahau-{version}"
    #     files = [
    #         "Dockerfile",
    #         "docker-compose.yml",
    #         "start.sh",
    #         "entrypoint",
    #         "genesis.json",
    #         "stop.sh",
    #     ]
    #     folder_exists, files_exist = is_folder_and_files(folder, files)
    #     cls.assertTrue(folder_exists)
    #     for file in files_exist:
    #         cls.assertTrue(file)

    def _test_standalone_xahau_binary(cls):
        version: str = XAHAU_VERSION
        create_standalone_binary(
            "trace",
            "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501",
            "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501",
            "xahau",  # protocol
            "standalone",  # net type
            21337,  # network id
            "https://build.xahau.tech",  # build server
            version,  # build version
        )
        folder = f"{basedir}/xahau-{version}"
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
