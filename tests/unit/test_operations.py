#!/usr/bin/env python
# coding: utf-8

"""Tests for xrpld_lab.operations — operational helpers for the CLI.

Covers:
- run_start_script / run_stop_script: script existence checks and delegation
- remove_network: directory removal
- stop_standalone: name vs. protocol+version resolution
- start_local / stop_local: CWD-based script running
- update_node_binary: node directory validation and subprocess calls
- enable_amendment: hash computation and RPC dispatch
- view_local_logs / view_standalone_logs: log file discovery
"""

import os
from unittest.mock import patch, MagicMock, call, mock_open

import pytest

from xrpld_lab.operations import (
    enable_amendment,
    remove_network,
    restart_local_node,
    run_start_script,
    run_stop_script,
    start_local,
    stop_local,
    stop_standalone,
    update_node_binary,
    view_local_logs,
    view_standalone_logs,
)


# -------------------------------------------------------------------------
# run_start_script / run_stop_script
# -------------------------------------------------------------------------


class TestRunScripts:
    """Test script runner helpers."""

    @patch("xrpld_lab.operations.run_command")
    @patch("os.path.isfile", return_value=True)
    def test_run_start_script_calls_bash(self, mock_isfile, mock_run):
        ws = MagicMock()
        ws.base = "/workspace"
        run_start_script(ws, "my-net")
        mock_run.assert_called_once_with("/workspace/my-net", "bash start.sh")

    @patch("xrpld_lab.operations.run_command")
    @patch("os.path.isfile", return_value=False)
    def test_run_start_script_missing_prints_error(self, mock_isfile, mock_run, capsys):
        ws = MagicMock()
        ws.base = "/workspace"
        run_start_script(ws, "my-net")
        mock_run.assert_not_called()
        captured = capsys.readouterr()
        assert "start.sh not found" in captured.out

    @patch("xrpld_lab.operations.run_command")
    @patch("os.path.isfile", return_value=True)
    def test_run_stop_script_calls_bash(self, mock_isfile, mock_run):
        ws = MagicMock()
        ws.base = "/workspace"
        run_stop_script(ws, "my-net")
        mock_run.assert_called_once_with("/workspace/my-net", "bash stop.sh")

    @patch("xrpld_lab.operations.run_command")
    @patch("os.path.isfile", return_value=False)
    def test_run_stop_script_missing_prints_error(self, mock_isfile, mock_run, capsys):
        ws = MagicMock()
        ws.base = "/workspace"
        run_stop_script(ws, "my-net")
        mock_run.assert_not_called()
        captured = capsys.readouterr()
        assert "stop.sh not found" in captured.out


# -------------------------------------------------------------------------
# remove_network
# -------------------------------------------------------------------------


class TestRemoveNetwork:
    """Test network directory removal."""

    @patch("xrpld_lab.operations.remove_directory")
    @patch("os.path.isdir", return_value=True)
    def test_removes_existing_directory(self, mock_isdir, mock_rm):
        ws = MagicMock()
        ws.base = "/workspace"
        remove_network(ws, "my-net")
        mock_rm.assert_called_once_with("/workspace/my-net")

    @patch("xrpld_lab.operations.remove_directory")
    @patch("os.path.isdir", return_value=False)
    def test_missing_directory_prints_error(self, mock_isdir, mock_rm, capsys):
        ws = MagicMock()
        ws.base = "/workspace"
        remove_network(ws, "my-net")
        mock_rm.assert_not_called()
        captured = capsys.readouterr()
        assert "not found" in captured.out


# -------------------------------------------------------------------------
# stop_standalone
# -------------------------------------------------------------------------


class TestStopStandalone:
    """Test standalone stop and cleanup."""

    @patch("xrpld_lab.operations.remove_directory")
    @patch("xrpld_lab.operations.run_command")
    @patch("os.path.isdir", return_value=True)
    @patch("os.path.isfile", return_value=True)
    def test_with_name_uses_name_directly(self, mock_isfile, mock_isdir, mock_run, mock_rm):
        ws = MagicMock()
        ws.base = "/workspace"
        stop_standalone(ws, "custom-name", "xahau", None)
        mock_run.assert_called_once_with("/workspace/custom-name", "bash stop.sh")
        mock_rm.assert_called_once_with("/workspace/custom-name")

    @patch("xrpld_lab.operations.remove_directory")
    @patch("xrpld_lab.operations.run_command")
    @patch("os.path.isdir", return_value=True)
    @patch("os.path.isfile", return_value=True)
    def test_with_version_constructs_dir_name(self, mock_isfile, mock_isdir, mock_run, mock_rm):
        ws = MagicMock()
        ws.base = "/workspace"
        stop_standalone(ws, None, "xahau", "1.0.0")
        mock_run.assert_called_once_with("/workspace/xahau-1.0.0", "bash stop.sh")
        mock_rm.assert_called_once_with("/workspace/xahau-1.0.0")

    @patch("xrpld_lab.operations.remove_directory")
    @patch("xrpld_lab.operations.run_command")
    def test_no_name_or_version_prints_error(self, mock_run, mock_rm, capsys):
        ws = MagicMock()
        ws.base = "/workspace"
        stop_standalone(ws, None, "xahau", None)
        mock_run.assert_not_called()
        mock_rm.assert_not_called()
        captured = capsys.readouterr()
        assert "--name or --version is required" in captured.out


# -------------------------------------------------------------------------
# start_local / stop_local
# -------------------------------------------------------------------------


class TestLocalScripts:
    """Test local standalone start/stop."""

    @patch("xrpld_lab.operations.subprocess.run")
    @patch("os.path.isfile", return_value=False)
    @patch("os.getcwd", return_value="/my/project")
    def test_start_local_missing_binary(self, mock_cwd, mock_isfile, mock_run, capsys):
        start_local()
        mock_run.assert_not_called()
        captured = capsys.readouterr()
        assert "not found in /my/project" in captured.out

    @patch("xrpld_lab.operations.run_command")
    @patch("os.path.isfile", return_value=True)
    @patch("os.getcwd", return_value="/my/project")
    def test_stop_local_runs_stop_sh(self, mock_cwd, mock_isfile, mock_run):
        stop_local()
        mock_run.assert_called_once_with("/my/project", "bash stop.sh")


# -------------------------------------------------------------------------
# update_node_binary
# -------------------------------------------------------------------------


class TestUpdateNodeBinary:
    """Test node binary update logic."""

    @patch("xrpld_lab.operations.run_command")
    @patch("subprocess.run")
    @patch("xrpld_lab.operations.remove_directory")
    @patch("os.chmod")
    @patch("os.path.isdir")
    @patch("os.path.isfile", return_value=False)
    def test_update_validator_node(
        self, mock_isfile, mock_isdir, mock_chmod, mock_rm, mock_subproc, mock_run
    ):
        # vnode2 dir exists, lib dir exists
        mock_isdir.side_effect = lambda p: True
        mock_subproc.return_value = MagicMock(returncode=0)

        ws = MagicMock()
        ws.base = "/workspace"

        update_node_binary(ws, "my-net", 2, "validator", "https://build.example.com", "2.0.0")

        # Should stop container
        mock_run.assert_any_call("/workspace/my-net", "docker compose stop vnode2")
        # Should download binary
        mock_subproc.assert_called_once()
        curl_args = mock_subproc.call_args[0][0]
        assert "curl" in curl_args
        assert "https://build.example.com/2.0.0" in curl_args
        # Should chmod the binary
        mock_chmod.assert_called_once()
        # Should remove lib dir
        mock_rm.assert_called_once_with("/workspace/my-net/vnode2/lib")
        # Should rebuild
        mock_run.assert_any_call(
            "/workspace/my-net",
            "docker compose up --build --force-recreate -d vnode2",
        )

    @patch("xrpld_lab.operations.run_command")
    @patch("os.path.isdir", return_value=False)
    def test_update_missing_node_dir(self, mock_isdir, mock_run, capsys):
        ws = MagicMock()
        ws.base = "/workspace"
        update_node_binary(ws, "my-net", 1, "peer", "https://build.example.com", "1.0.0")
        mock_run.assert_not_called()
        captured = capsys.readouterr()
        assert "not found" in captured.out

    @patch("xrpld_lab.operations.run_command")
    @patch("subprocess.run")
    @patch("xrpld_lab.operations.remove_directory")
    @patch("os.chmod")
    @patch("os.path.isdir", return_value=True)
    @patch("os.path.isfile", return_value=False)
    def test_update_peer_node_uses_pnode_prefix(
        self, mock_isfile, mock_isdir, mock_chmod, mock_rm, mock_subproc, mock_run
    ):
        mock_subproc.return_value = MagicMock(returncode=0)
        ws = MagicMock()
        ws.base = "/workspace"

        update_node_binary(ws, "my-net", 3, "peer", "https://build.example.com", "1.0.0")

        mock_run.assert_any_call("/workspace/my-net", "docker compose stop pnode3")

    @patch("xrpld_lab.operations.run_command")
    @patch("subprocess.run")
    @patch("xrpld_lab.operations.remove_directory")
    @patch("os.chmod")
    @patch("os.path.isdir", return_value=True)
    @patch("os.path.isfile", return_value=False)
    def test_update_from_image_extracts_not_downloads(
        self, mock_isfile, mock_isdir, mock_chmod, mock_rm, mock_subproc, mock_run
    ):
        # docker create/cp/rm all succeed
        mock_subproc.return_value = MagicMock(returncode=0)
        ws = MagicMock()
        ws.base = "/workspace"

        update_node_binary(
            ws, "my-net", 2, "validator", None, "3.3.0-rc1",
            image="rippleci/xrpld:3.3.0-rc1",
        )

        calls = [c.args[0] for c in mock_subproc.call_args_list]
        # no curl download when sourcing from an image
        assert not any("curl" in c for c in calls)
        # binary is copied out of the image
        assert any(c[:3] == ["docker", "create", "--name"] for c in calls)
        assert any(
            c[:2] == ["docker", "cp"]
            and c[2].endswith(":/opt/xrpld/bin/xrpld")
            and c[3].endswith("xrpld.3.3.0-rc1")
            for c in calls
        )
        # still rebuilds via compose
        mock_run.assert_any_call(
            "/workspace/my-net",
            "docker compose up --build --force-recreate -d vnode2",
        )


class TestRestartLocalNode:
    """Restart routing: docker container vs bare-process pidfile."""

    @patch("xrpld_lab.operations.run_command")
    @patch("xrpld_lab.operations._docker_container_exists", return_value=True)
    @patch("os.getcwd", return_value="/cluster")
    @patch("os.path.isdir", return_value=True)
    @patch("os.path.isfile", return_value=False)
    def test_docker_resume(
        self, mock_isfile, mock_isdir, mock_cwd, mock_docker, mock_run
    ):
        restart_local_node("vnode2")
        mock_run.assert_called_once_with("/cluster", "docker restart vnode2")

    @patch("xrpld_lab.operations.run_command")
    @patch("xrpld_lab.operations._docker_container_exists", return_value=True)
    @patch("os.getcwd", return_value="/cluster")
    @patch("os.path.isdir", return_value=True)
    @patch("os.path.isfile", return_value=False)
    def test_docker_genesis_recreates(
        self, mock_isfile, mock_isdir, mock_cwd, mock_docker, mock_run
    ):
        restart_local_node("vnode5", genesis=True)
        mock_run.assert_called_once_with(
            "/cluster", "docker compose up --force-recreate -d vnode5"
        )

    @patch("xrpld_lab.operations.run_command")
    @patch("xrpld_lab.script_builder.ScriptBuilder.local_node_start_cmd", return_value="./start")
    @patch("subprocess.run")
    @patch("xrpld_lab.operations._docker_container_exists", return_value=False)
    @patch("os.remove")
    @patch("os.getcwd", return_value="/cluster")
    @patch("os.path.isdir", return_value=True)
    @patch("os.path.isfile", return_value=True)
    def test_bare_process_pidfile_path(
        self, mock_isfile, mock_isdir, mock_cwd, mock_remove, mock_docker,
        mock_subproc, mock_startcmd, mock_run,
    ):
        with patch("builtins.open", mock_open(read_data="12345")):
            restart_local_node("vnode1")
        # killed by pid, not routed to docker
        assert any("kill" in c.args[0] for c in mock_subproc.call_args_list)
        mock_run.assert_called_once_with("/cluster", "./start")

    @patch("xrpld_lab.operations.run_command")
    @patch("os.path.isdir", return_value=False)
    def test_missing_node_dir(self, mock_isdir, mock_run, capsys):
        restart_local_node("vnode9")
        mock_run.assert_not_called()
        assert "not found" in capsys.readouterr().out


# -------------------------------------------------------------------------
# enable_amendment
# -------------------------------------------------------------------------


class TestEnableAmendment:
    """Test amendment enablement via RPC."""

    @patch("subprocess.run")
    def test_enable_amendment_sends_rpc(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        ws = MagicMock()
        ws.base = "/workspace"

        enable_amendment("my-net", "fixNFTokenRemint", 1, "validator", ws)

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "curl" in call_args
        # Validator 1: RPC admin port = 5005 + 1*100 = 5105
        assert "http://localhost:5105" in call_args

    @patch("subprocess.run")
    def test_enable_amendment_peer_port(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        ws = MagicMock()
        ws.base = "/workspace"

        enable_amendment("my-net", "SomeAmendment", 2, "peer", ws)

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        # Peer 2: RPC admin port = 5005 + 2*10 = 5025
        assert "http://localhost:5025" in call_args

    @patch("subprocess.run")
    def test_enable_amendment_hash_in_payload(self, mock_run):
        """Verify the amendment hash is computed and included in the RPC payload."""
        mock_run.return_value = MagicMock(returncode=0)
        ws = MagicMock()

        # Compute expected hash
        import hashlib
        expected = hashlib.sha512(
            "fixNFTokenRemint".encode("utf-8")
        ).hexdigest().upper()[:64]

        enable_amendment("my-net", "fixNFTokenRemint", 1, "validator", ws)

        # The hash should appear in the curl -d payload
        payload_arg = mock_run.call_args[0][0][-1]  # last arg is the JSON payload
        assert expected in payload_arg


# -------------------------------------------------------------------------
# view_local_logs / view_standalone_logs
# -------------------------------------------------------------------------


class TestLogs:
    """Test log viewing functions."""

    @patch("subprocess.run")
    @patch("os.path.isfile", return_value=True)
    @patch("os.getcwd", return_value="/my/project")
    def test_view_local_logs_with_node(self, mock_cwd, mock_isfile, mock_run):
        view_local_logs("vnode1")
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "tail" in call_args
        assert "/my/project/vnode1/log/debug.log" in call_args

    @patch("subprocess.run")
    @patch("os.path.isfile", return_value=False)
    @patch("os.getcwd", return_value="/my/project")
    @patch("glob.glob", return_value=[])
    def test_view_local_logs_no_file_prints_error(
        self, mock_glob, mock_cwd, mock_isfile, mock_run, capsys
    ):
        view_local_logs(None)
        mock_run.assert_not_called()
        captured = capsys.readouterr()
        assert "No debug.log found" in captured.out

    @patch("subprocess.run")
    def test_view_standalone_logs_tails_docker(self, mock_run):
        view_standalone_logs("xahau")
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "docker" in call_args
        assert "xahau" in call_args
