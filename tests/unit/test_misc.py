#!/usr/bin/env python
# coding: utf-8

import pytest
from xrpld_netgen.utils.misc import (
    generate_ports,
    get_node_port,
    sha512_half,
    get_node_db_path,
    get_relational_db,
)


class TestGeneratePorts:
    """Test port generation for different node types"""

    def test_generate_ports_validator_first(self):
        rpc_public, rpc_admin, ws_public, ws_admin, peer = generate_ports(1, "validator")
        assert rpc_public == 5107
        assert rpc_admin == 5105
        assert ws_public == 6108
        assert ws_admin == 6106
        assert peer == 51335

    def test_generate_ports_validator_second(self):
        rpc_public, rpc_admin, ws_public, ws_admin, peer = generate_ports(2, "validator")
        assert rpc_public == 5207
        assert rpc_admin == 5205
        assert ws_public == 6208
        assert ws_admin == 6206
        assert peer == 51435

    def test_generate_ports_peer_first(self):
        rpc_public, rpc_admin, ws_public, ws_admin, peer = generate_ports(1, "peer")
        assert rpc_public == 5017
        assert rpc_admin == 5015
        assert ws_public == 6018
        assert ws_admin == 6016
        assert peer == 51245

    def test_generate_ports_peer_second(self):
        rpc_public, rpc_admin, ws_public, ws_admin, peer = generate_ports(2, "peer")
        assert rpc_public == 5027
        assert rpc_admin == 5025
        assert ws_public == 6028
        assert ws_admin == 6026
        assert peer == 51255

    def test_generate_ports_standalone(self):
        rpc_public, rpc_admin, ws_public, ws_admin, peer = generate_ports(0, "standalone")
        assert rpc_public == 5007
        assert rpc_admin == 5005
        assert ws_public == 6008
        assert ws_admin == 6006
        assert peer == 51235

    def test_generate_ports_invalid_type_raises_error(self):
        with pytest.raises(ValueError, match="Invalid node type"):
            generate_ports(1, "invalid_type")


class TestGetNodePort:
    """Test getting admin port for a node"""

    def test_get_node_port_validator(self):
        port = get_node_port(1, "validator")
        assert port == 5105

    def test_get_node_port_validator_multiple(self):
        assert get_node_port(1, "validator") == 5105
        assert get_node_port(2, "validator") == 5205
        assert get_node_port(3, "validator") == 5305

    def test_get_node_port_peer(self):
        port = get_node_port(1, "peer")
        assert port == 5015

    def test_get_node_port_peer_multiple(self):
        assert get_node_port(1, "peer") == 5015
        assert get_node_port(2, "peer") == 5025
        assert get_node_port(3, "peer") == 5035


class TestSha512Half:
    """Test SHA512 half hash generation"""

    def test_sha512_half_simple(self):
        result = sha512_half("48656c6c6f")  # "Hello" in hex
        assert len(result) == 64
        assert result.isupper()

    def test_sha512_half_deterministic(self):
        hex_string = "48656c6c6f"
        result1 = sha512_half(hex_string)
        result2 = sha512_half(hex_string)
        assert result1 == result2

    def test_sha512_half_different_inputs(self):
        result1 = sha512_half("48656c6c6f")
        result2 = sha512_half("48656c6c6f21")
        assert result1 != result2

    def test_sha512_half_empty_string(self):
        result = sha512_half("")
        assert len(result) == 64


class TestGetNodeDbPath:
    """Test getting node database path"""

    def test_get_node_db_path_nudb_local(self):
        path = get_node_db_path("NuDB", "local")
        assert path == "db"

    def test_get_node_db_path_nudb_standalone(self):
        path = get_node_db_path("NuDB", "standalone")
        assert path == "/opt/ripple/lib/db"

    def test_get_node_db_path_nudb_network(self):
        path = get_node_db_path("NuDB", "network")
        assert path == "/var/lib/xrpld/db"

    def test_get_node_db_path_memory(self):
        path = get_node_db_path("Memory")
        assert path == "./"

    def test_get_node_db_path_rwdb_network(self):
        path = get_node_db_path("rwdb", "network")
        assert path == "/var/lib/xrpld/db"


class TestGetRelationalDb:
    """Test getting relational database backend configuration"""

    def test_get_relational_db_nudb(self):
        result = get_relational_db("NuDB")
        assert result is None

    def test_get_relational_db_memory(self):
        result = get_relational_db("Memory")
        assert result == "backend=memory"

    def test_get_relational_db_rwdb(self):
        result = get_relational_db("rwdb")
        assert result == "backend=rwdb"
