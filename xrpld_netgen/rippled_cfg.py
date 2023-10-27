#!/usr/bin/env python
# coding: utf-8

import sys
import logging
import os
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class RippledBuild:
    name: str
    path: str
    data: str


def generate_rippled_cfg(
    build_path: str,
    node_index: int,
    network: int,
    network_id: int,
    is_rpc_public: bool,
    rpc_public_port: int,
    is_rpc_admin: bool,
    rpc_admin_port: int,
    is_ws_public: bool,
    ws_public_port: int,
    is_ws_admin: bool,
    ws_admin_port: int,
    is_peer: bool,
    peer_port: int,
    ssl_verify: bool,
    is_ssl: bool,
    key_path: str,
    crt_path: str,
    size_node: str,
    nudb_path: str,
    db_path: str,
    num_ledgers: str,
    debug_path: str,
    log_level: str,
    private_peer: int,
    genesis: bool,
    v_seed: str = None,
    v_token: str = None,
    validators: List[str] = [],
    cluster_nodes: List[str] = [],
    validator_list_sites: List[str] = [],
    validator_list_keys: List[str] = [],
    import_vl_keys: List[str] = [],
    ips_fixed_urls: List[str] = [],
    ips_urls: List[str] = [],
    amendment_majority_time: str = None,
    amendments_dict: Dict[str, str] = {},
):
    try:
        node_config_path: str = build_path + "/config"

        cfg_out: str = ""

        server_cfg: str = "[server]" + "\n"
        cfg_out += server_cfg

        _rpc_public_ip: str = "0.0.0.0"
        _rpc_admin_ip: str = "0.0.0.0"
        _ws_public_ip: str = "0.0.0.0"
        _ws_admin_ip: str = "0.0.0.0"
        _peer_port_ip: int = "0.0.0.0"

        if is_rpc_public:
            cfg_out += "port_rpc_public" + "\n"

        if is_rpc_admin:
            cfg_out += "port_rpc_admin_local" + "\n"

        if is_ws_public:
            cfg_out += "port_ws_public" + "\n"

        if is_peer:
            cfg_out += "port_peer" + "\n"

        if is_ws_admin:
            cfg_out += "port_ws_admin_local" + "\n"

        if is_ssl and key_path and crt_path:
            cfg_out += "\n"
            cfg_out += f"ssl_key = {key_path}" + "\n"
            cfg_out += f"ssl_cert = {crt_path}" + "\n"

        http_protocol: str = "http"
        ws_protocol: str = "ws"
        if is_rpc_public:
            cfg_out += "\n"
            cfg_out += "[port_rpc_public]" + "\n"
            cfg_out += f"port = {rpc_public_port}" + "\n"
            cfg_out += f"ip = {_rpc_public_ip}" + "\n"
            cfg_out += f"admin = {_rpc_public_ip}" + "\n"
            cfg_out += f"protocol = {http_protocol}" + "\n"

        if is_rpc_admin:
            cfg_out += "\n"
            cfg_out += "[port_rpc_admin_local]" + "\n"
            cfg_out += f"port = {rpc_admin_port}" + "\n"
            cfg_out += f"ip = {_rpc_admin_ip}" + "\n"
            cfg_out += f"admin = {_rpc_admin_ip}" + "\n"
            cfg_out += f"protocol = {http_protocol}" + "\n"

        if is_ws_public:
            cfg_out += "\n"
            cfg_out += "[port_ws_public]" + "\n"
            cfg_out += f"port = {ws_public_port}" + "\n"
            cfg_out += f"ip = {_ws_public_ip}" + "\n"
            cfg_out += f"protocol = {ws_protocol}" + "\n"

        if is_ws_admin:
            cfg_out += "\n"
            cfg_out += "[port_ws_admin_local]" + "\n"
            cfg_out += f"port = {ws_admin_port}" + "\n"
            cfg_out += f"ip = {_ws_admin_ip}" + "\n"
            cfg_out += f"admin = {_ws_admin_ip}" + "\n"
            cfg_out += f"protocol = {ws_protocol}" + "\n"

        if is_peer:
            cfg_out += "\n"
            cfg_out += "[port_peer]" + "\n"
            cfg_out += f"port = {peer_port}" + "\n"
            cfg_out += f"ip = {_peer_port_ip}" + "\n"
            cfg_out += f"protocol = peer" + "\n"

        cfg_out += "\n"
        cfg_out += "[node_size]" + "\n"
        cfg_out += f"{size_node}" + "\n"
        cfg_out += "\n"

        cfg_out += "[node_db]" + "\n"
        cfg_out += "type=NuDB" + "\n"
        cfg_out += f"path={nudb_path}" + "\n"
        cfg_out += "advisory_delete=0" + "\n"
        # cfg_out += f"""online_delete={num_ledgers}""" + "\n"
        cfg_out += "\n"

        fee_account_reserve: int = 5000000
        cfg_out += "[fee_account_reserve]" + "\n"
        cfg_out += f"{fee_account_reserve}" + "\n"
        cfg_out += "\n"

        fee_owner_reserve: int = 1000000
        cfg_out += "[fee_owner_reserve]" + "\n"
        cfg_out += f"{fee_owner_reserve}" + "\n"
        cfg_out += "\n"

        cfg_out += "[ledger_history]" + "\n"
        cfg_out += f"{num_ledgers}" + "\n"
        cfg_out += "\n"

        cfg_out += "[database_path]" + "\n"
        cfg_out += f"{db_path}" + "\n"
        cfg_out += "\n"

        cfg_out += "[debug_logfile]" + "\n"
        cfg_out += f"{debug_path}" + "\n"
        cfg_out += "\n"

        cfg_out += "[sntp_servers]" + "\n"
        cfg_out += "time.windows.com" + "\n"
        cfg_out += "time.apple.com" + "\n"
        cfg_out += "time.nist.gov" + "\n"
        cfg_out += "pool.ntp.org" + "\n"
        cfg_out += "\n"

        if ips_urls and len(ips_urls) > 0:
            cfg_out += "[ips]" + "\n"
            for url in ips_urls:
                cfg_out += f"{url}" + "\n"
            cfg_out += "\n"

        if ips_fixed_urls and len(ips_fixed_urls) > 0:
            cfg_out += "[ips_fixed]" + "\n"
            for url in ips_fixed_urls:
                cfg_out += f"{url}" + "\n"
            cfg_out += "\n"

        if network_id:
            cfg_out += "[network_id]" + "\n"
            cfg_out += f"{network_id}" + "\n"
            cfg_out += "\n"

        cfg_out += "[peer_private]" + "\n"
        cfg_out += f"{private_peer}" + "\n"
        cfg_out += "\n"

        cfg_out += "[validators_file]" + "\n"
        cfg_out += "validators.txt" + "\n"
        cfg_out += "\n"

        if v_seed:
            cfg_out += "[validation_seed]" + "\n"
            cfg_out += f"{v_seed}" + "\n"
            cfg_out += "\n"

        if v_token:
            cfg_out += "[validator_token]" + "\n"
            cfg_out += f"{v_token}" + "\n"
            cfg_out += "\n"

        if len(cluster_nodes):
            cfg_out += "[cluster_nodes]" + "\n"
            for v in cluster_nodes:
                cfg_out += v + "\n"
            cfg_out += "\n"

        cfg_out += "[rpc_startup]" + "\n"
        if log_level == "trace":
            cfg_out += '{ "command": "log_level", "severity": "trace" }' + "\n"
        elif log_level == "debug":
            cfg_out += '{ "command": "log_level", "severity": "debug" }' + "\n"
        elif log_level == "info":
            cfg_out += '{ "command": "log_level", "severity": "info" }' + "\n"
        elif log_level == "warning":
            cfg_out += '{ "command": "log_level", "severity": "warning" }' + "\n"
        else:
            cfg_out += '{ "command": "log_level", "severity": "info" }' + "\n"

        cfg_out += "\n"
        cfg_out += "[ssl_verify]" + "\n"
        cfg_out += f"{ssl_verify}" + "\n"

        if amendment_majority_time:
            cfg_out += "\n"
            cfg_out += "[amendment_majority_time]" + "\n"
            cfg_out += amendment_majority_time + "\n"

        if amendments_dict and len(amendments_dict) > 0:
            cfg_out += "\n"
            cfg_out += "[amendments]" + "\n"
            for k, v in amendments_dict.items():
                cfg_out += f"{v}" + " " + f"{k}" + "\n"

        validators_out: str = ""
        if genesis:
            validators_out += "[validators]" + "\n"
            for kp in validators:
                validators_out += "    " + kp + "\n"
            validators_out += "\n"
        else:
            validators_out += "[validator_list_sites]" + "\n"
            for vs in validator_list_sites:
                validators_out += "    " + vs + "\n"
                validators_out += "\n"

            validators_out += "[validator_list_keys]" + "\n"
            for vk in validator_list_keys:
                validators_out += "    " + vk + "\n"

            if len(import_vl_keys) > 0:
                validators_out += "\n"
                validators_out += "[import_vl_keys]" + "\n"
                for vk in import_vl_keys:
                    validators_out += "    " + vk + "\n"

        return [
            RippledBuild("cfg", f"{node_config_path}/rippled.cfg", cfg_out),
            RippledBuild("vl", f"{node_config_path}/validators.txt", validators_out),
            RippledBuild(
                "docker", f"{node_config_path}/validators.txt", validators_out
            ),
        ]

    except Exception as e:
        print(f"line: {sys.exc_info()[-1].tb_lineno} error: {e}")
        print(build_path)
        print(node_index)
        print(network)
        print(network_id)
        print(is_rpc_public)
        print(rpc_public_port)
        print(is_rpc_admin)
        print(rpc_admin_port)
        print(is_ws_public)
        print(ws_public_port)
        print(is_ws_admin)
        print(ws_admin_port)
        print(is_peer)
        print(peer_port)
        print(ssl_verify)
        print(is_ssl)
        print(key_path)
        print(crt_path)
        print(size_node)
        print(nudb_path)
        print(db_path)
        print(num_ledgers)
        print(debug_path)
        print(log_level)
        print(private_peer)
        print(genesis)
        print(v_seed)
        print(v_token)
        print(validators)
        print(cluster_nodes)
        print(validator_list_sites)
        print(validator_list_keys)
        print(import_vl_keys)
        print(ips_fixed_urls)
        print(ips_urls)
        print(amendments_dict)
