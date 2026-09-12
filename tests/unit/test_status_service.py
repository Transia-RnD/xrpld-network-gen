#!/usr/bin/env python
# coding: utf-8

import json
import socket
import threading
from types import SimpleNamespace
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from xrpld_lab.services.status import node_metrics as nm


def _latest(state, seq=100, ok=1, **extra):
    row = {
        "server_state": state,
        "validated_seq": seq,
        "xrpld_ok": ok,
        "peers": 4,
        "uptime": 3600,
        "build_version": "3.1.0",
    }
    row.update(extra)
    return row


def _fake_fetch(table):
    """urlopen stand-in keyed by node URL; a missing URL is a refused connection."""

    def fetch(url, timeout):
        if url not in table:
            raise urllib.error.URLError("connection refused")
        return table[url]

    return fetch


NODES = nm.parse_network_nodes(
    "vnode1=http://10.0.0.1:8687 role=validator,"
    "vnode2=http://10.0.0.2:8687 role=validator,"
    "pnode1=http://127.0.0.1:8687 role=peer"
)


class TestParseNetworkNodes:
    def test_roles_from_name_prefix(self):
        nodes = nm.parse_network_nodes("vnode1=http://a:1,pnode1=http://b:1/")
        assert nodes == [
            ("vnode1", "validator", "http://a:1"),
            ("pnode1", "peer", "http://b:1"),
        ]

    def test_explicit_role_token_overrides_the_prefix(self):
        nodes = nm.parse_network_nodes(
            "watcher=http://c:1 role=validator, other=http://d:1"
        )
        assert nodes[0] == ("watcher", "validator", "http://c:1")
        assert nodes[1][1] == "peer"

    def test_empty_spec(self):
        assert nm.parse_network_nodes("") == []

    def test_bad_entries_raise(self):
        with pytest.raises(ValueError):
            nm.parse_network_nodes("vnode1")
        with pytest.raises(ValueError):
            nm.parse_network_nodes("vnode1=http://a:1 role=king")
        with pytest.raises(ValueError):
            nm.parse_network_nodes("vnode1=http://a:1 colour=red")


class TestNetworkReport:
    def _network(self, table, tmp_path=None, network=None):
        path = ""
        if tmp_path is not None:
            path = str(tmp_path / "network.json")
            if network is not None:
                (tmp_path / "network.json").write_text(json.dumps(network))
        return nm.Network(
            NODES, network_file=path, name="alphanet", fetch=_fake_fetch(table)
        )

    def test_agreement_when_every_validator_reports_the_same_ledger(self):
        report = self._network(
            {
                "http://10.0.0.1:8687": _latest("proposing", 500),
                "http://10.0.0.2:8687": _latest("proposing", 500),
                "http://127.0.0.1:8687": _latest("full", 499),
            }
        ).report()
        assert report["agreement"] is True
        assert report["validated_ledger"] == 500
        assert report["name"] == "alphanet"
        assert [n["name"] for n in report["nodes"]] == ["vnode1", "vnode2", "pnode1"]
        vnode1 = report["nodes"][0]
        assert vnode1["role"] == "validator"
        assert vnode1["server_state"] == "proposing"
        assert vnode1["build_version"] == "3.1.0"
        assert vnode1["validated_ledger"] == 500
        assert vnode1["peers"] == 4
        assert vnode1["uptime"] == 3600
        assert vnode1["ok"] is True
        assert vnode1["error"] is None
        assert isinstance(report["generated_at"], int)

    def test_no_agreement_when_validators_differ(self):
        report = self._network(
            {
                "http://10.0.0.1:8687": _latest("proposing", 500),
                "http://10.0.0.2:8687": _latest("proposing", 498),
                "http://127.0.0.1:8687": _latest("full", 500),
            }
        ).report()
        assert report["agreement"] is False

    def test_no_agreement_when_a_validator_is_unreachable(self):
        report = self._network(
            {
                "http://10.0.0.1:8687": _latest("proposing", 500),
                "http://127.0.0.1:8687": _latest("full", 500),
            }
        ).report()
        assert report["agreement"] is False
        vnode2 = report["nodes"][1]
        assert vnode2["ok"] is False
        assert vnode2["server_state"] is None
        assert "refused" in vnode2["error"]

    def test_peer_only_network_has_no_agreement(self):
        net = nm.Network(
            nm.parse_network_nodes("pnode1=http://a:1"),
            fetch=_fake_fetch({"http://a:1": _latest("full")}),
        )
        assert net.report()["agreement"] is False

    def test_network_json_merged(self, tmp_path):
        info = {
            "last_deploy": {"sha": "abc123"},
            "branches": [{"repo": "XRPLF/rippled"}],
        }
        report = self._network({}, tmp_path, info).report()
        assert report["network"] == info

    def test_missing_network_json_is_empty(self, tmp_path):
        assert self._network({}, tmp_path).report()["network"] == {}

    def test_malformed_network_json_is_reported_not_raised(self, tmp_path):
        (tmp_path / "network.json").write_text("{not json")
        report = self._network({}, tmp_path).report()
        assert "network.json" in report["network"]["error"]


class TestNetworkHealth:
    def _health(self, table):
        return nm.Network(NODES, fetch=_fake_fetch(table)).health()

    def test_200_when_validators_propose_and_peers_are_full(self):
        body, code = self._health(
            {
                "http://10.0.0.1:8687": _latest("proposing"),
                "http://10.0.0.2:8687": _latest("proposing"),
                "http://127.0.0.1:8687": _latest("full"),
            }
        )
        assert code == 200
        assert body["ok"] is True
        assert body["failing"] == []

    def test_503_lists_the_failing_nodes(self):
        body, code = self._health(
            {
                "http://10.0.0.1:8687": _latest("proposing"),
                "http://10.0.0.2:8687": _latest("full"),
            }
        )
        assert code == 503
        assert body["ok"] is False
        assert body["failing"] == [
            {"name": "vnode2", "role": "validator", "server_state": "full"},
            {"name": "pnode1", "role": "peer", "server_state": None},
        ]

    def test_a_full_validator_is_not_healthy(self):
        body, code = self._health(
            {
                "http://10.0.0.1:8687": _latest("full"),
                "http://10.0.0.2:8687": _latest("proposing"),
                "http://127.0.0.1:8687": _latest("full"),
            }
        )
        assert code == 503
        assert [f["name"] for f in body["failing"]] == ["vnode1"]


class TestNetworkRoutes:
    @pytest.fixture
    def server(self):
        table = {
            "http://10.0.0.1:8687": _latest("proposing"),
            "http://10.0.0.2:8687": _latest("proposing"),
            "http://127.0.0.1:8687": _latest("full"),
        }
        nm.Handler.network = nm.Network(
            NODES, name="alphanet", fetch=_fake_fetch(table)
        )
        srv = ThreadingHTTPServer(("127.0.0.1", 0), nm.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        yield srv, table
        srv.shutdown()
        nm.Handler.network = None

    def _get(self, srv, path):
        url = f"http://127.0.0.1:{srv.server_address[1]}{path}"
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def test_network_route(self, server):
        srv, _ = server
        code, body = self._get(srv, "/api/network")
        assert code == 200
        assert body["name"] == "alphanet"
        assert body["agreement"] is True

    def test_health_route_flips_to_503(self, server):
        srv, table = server
        assert self._get(srv, "/api/network/health")[0] == 200
        table["http://127.0.0.1:8687"] = _latest("syncing")
        code, body = self._get(srv, "/api/network/health")
        assert code == 503
        assert body["failing"][0]["name"] == "pnode1"

    def test_network_routes_absent_without_node_list(self, server):
        srv, _ = server
        nm.Handler.network = None
        assert self._get(srv, "/api/network")[0] == 404


class TestXdgmListener:
    def test_bind_failure_is_recorded_and_the_listener_exits(
        self, tmp_path, monkeypatch, capsys
    ):
        db = str(tmp_path / "metrics.db")
        conn = nm.connect(db)
        conn.executescript(nm.SCHEMA)
        conn.close()
        cfg = SimpleNamespace(db=db, xdgm_host="203.0.113.7", xdgm_port=9999)

        class FailingSocket:
            def __init__(self, *args):
                pass

            def setsockopt(self, *args):
                pass

            def bind(self, addr):
                raise OSError(49, "Can't assign requested address")

        monkeypatch.setattr(socket, "socket", FailingSocket)
        monkeypatch.setattr(nm, "read_proc_stat", lambda: (0, 0, 0))
        monkeypatch.setattr(nm, "read_diskstats", lambda: (0, 0))
        monkeypatch.setattr(nm, "read_netdev", lambda: (0, 0))

        nm.Sampler(cfg).listen_xdgm()

        rows = nm.connect(db).execute("SELECT kind, detail FROM events").fetchall()
        assert [r["kind"] for r in rows] == ["sampler_error"]
        assert "xdgm bind 203.0.113.7:9999" in rows[0]["detail"]
        assert "Can't assign requested address" in rows[0]["detail"]
        assert "xdgm bind 203.0.113.7:9999" in capsys.readouterr().err

    def test_default_host_is_every_interface(self, monkeypatch):
        monkeypatch.delenv("NODE_METRICS_XDGM_HOST", raising=False)
        monkeypatch.setattr("sys.argv", ["node_metrics.py"])
        assert nm.parse_args().xdgm_host == "0.0.0.0"
