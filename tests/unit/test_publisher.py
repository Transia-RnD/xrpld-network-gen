#!/usr/bin/env python
# coding: utf-8

import time
import logging
from typing import Dict, Any, List  # noqa: F401

from testing_config import BaseTestConfig
from xrpld_publisher.publisher import (
    PublisherClient,
)
from xrpld_publisher.utils import from_days_to_expiration

logger = logging.getLogger("app")


class TestPublisher(BaseTestConfig):
    name: str = "test"
    pk: str = "CC9E8B118E8E927DA82A66B9D931E1AB6309BA32F057F8B216600B347C552006"
    manifest: str = "JAAAAAFxIe101ANsZZGkvfnFTO+jm5lqXc5fhtEf2hh0SBzp1aHNwXMh7TN9+b62cZqTngaFYU5tbGpYHC8oYuI3G3vwj9OW2Z9gdkAnUjfY5zOEkhq31tU4338jcyUpVA5/VTsANFce7unDo+JeVoEhfuOb/Y8WA3Diu9XzuOD4U/ikfgf9SZOlOGcBcBJAw44PLjH+HUtEnwX45lIRmo0x5aINFMvZsBpE9QteSDBXKwYzLdnSW4e1bs21o+IILJIiIKU/+1Uxx0FRpQbMDA=="
    vl_path: str = "tests/fixtures/test.json"

    def test_init(cls):
        client: PublisherClient = PublisherClient(vl_path=cls.vl_path)
        cls.assertIsNotNone(client.vl)
        cls.assertEqual(client.vl.blob.sequence, 2)
        cls.assertEqual(len(client.vl.blob.validators), 1)

    def test_init_new_vl(cls):
        client: PublisherClient = PublisherClient(manifest=cls.manifest)
        cls.assertIsNotNone(client.vl)
        cls.assertEqual(client.vl.blob.sequence, 1)
        cls.assertEqual(len(client.vl.blob.validators), 0)

    def test_add_validator(cls):
        client: PublisherClient = PublisherClient(vl_path=cls.vl_path)
        cls.assertEqual(client.vl.blob.sequence, 2)
        add_manifest: str = "JAAAAAFxIe3kW20uKHcjYwGFkZ7+Ax8FIorTwvHqmY8kvePtYG4nSHMhAjIn+/pQWK/OU9ln8Rux6wnQGY1yMFeaGR5gEcFSGxa1dkYwRAIgSAGa6gWCa2C9XxIMSoAB1qCZjjJMXGpl5Tb+81U5RDwCIG3GQHXPUjFkTMwEcuM8G6dwcWzEfB1nYa5MqxFAhOXscBJApcamLcUBNxmABeKigy+ZYTYLqMKuGtV9HgjXKA5oI9CNH0xA6R52NchP3rZyXWOWS0tan25o0rwQBNIY78k6Cg=="
        client.add_validator(add_manifest)
        cls.assertEqual(len(client.vl.blob.validators), 2)
        cls.assertEqual(
            client.vl.blob.validators[1].pk,
            "EDE45B6D2E287723630185919EFE031F05228AD3C2F1EA998F24BDE3ED606E2748",
        )
        cls.assertEqual(
            client.vl.blob.validators[1].manifest,
            add_manifest,
        )

    def test_remove_validator(cls):
        client: PublisherClient = PublisherClient(vl_path=cls.vl_path)
        cls.assertEqual(client.vl.blob.sequence, 2)
        remove_pk: str = (
            "EDA164F4B36C2D730462D5F762BFA2808AA5092ABCECEBB27089525D1D054BE33B"
        )
        client.remove_validator(remove_pk)
        cls.assertEqual(len(client.vl.blob.validators), 0)

    def test_sign_vl(cls):
        client: PublisherClient = PublisherClient(vl_path=cls.vl_path)
        cls.assertEqual(client.vl.blob.sequence, 2)
        add_manifest: str = "JAAAAAFxIe3kW20uKHcjYwGFkZ7+Ax8FIorTwvHqmY8kvePtYG4nSHMhAjIn+/pQWK/OU9ln8Rux6wnQGY1yMFeaGR5gEcFSGxa1dkYwRAIgSAGa6gWCa2C9XxIMSoAB1qCZjjJMXGpl5Tb+81U5RDwCIG3GQHXPUjFkTMwEcuM8G6dwcWzEfB1nYa5MqxFAhOXscBJApcamLcUBNxmABeKigy+ZYTYLqMKuGtV9HgjXKA5oI9CNH0xA6R52NchP3rZyXWOWS0tan25o0rwQBNIY78k6Cg=="
        client.add_validator(add_manifest)
        expiration: int = from_days_to_expiration(int(time.time()), 30)
        client.sign_unl(cls.pk, expiration=expiration)
        cls.assertEqual(len(client.vl.blob.validators), 2)
