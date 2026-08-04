"""Builders that produce xrpld.cfg and validators.txt content strings.

Replaces the monolithic ``generate_xrpld_cfg()`` in ``xrpld_netgen/xrpld_cfg.py``
with composable, testable builder classes driven by :class:`NodeConfig`.
"""

from __future__ import annotations

from xrpld_lab.models import NodeConfig


# ---------------------------------------------------------------------------
# CfgSection helper
# ---------------------------------------------------------------------------


class CfgSection:
    """Small helper to build a single INI-style ``[section]``."""

    def __init__(self, name: str):
        self.name = name
        self.lines: list[str] = []

    def add(self, line: str) -> CfgSection:
        self.lines.append(line)
        return self

    def add_kv(self, key: str, value) -> CfgSection:
        self.lines.append(f"{key} = {value}")
        return self

    def render(self) -> str:
        header = f"[{self.name}]"
        body = "\n".join(self.lines)
        return f"{header}\n{body}\n" if self.lines else f"{header}\n"


# ---------------------------------------------------------------------------
# XrpldCfgBuilder
# ---------------------------------------------------------------------------

_KNOWN_LOG_LEVELS = {"trace", "debug", "info", "warning", "error"}

_SNTP_SERVERS = [
    "time.windows.com",
    "time.apple.com",
    "time.nist.gov",
    "pool.ntp.org",
]


class XrpldCfgBuilder:
    """Produces the ``xrpld.cfg`` content string from a :class:`NodeConfig`."""

    def __init__(self, config: NodeConfig):
        self.config = config

    def build(self) -> str:
        c = self.config
        out = ""

        out += self._server_section()
        out += self._port_sections()
        out += self._node_size_section()
        out += self._tree_cache_ram_percent_section()
        out += self._tree_cache_target_entries_section()
        out += self._consensus_reserve_threads_section()
        out += self._node_db_section()
        out += self._relational_db_section()
        out += self._fee_reserves_section()
        out += self._ledger_history_section()
        out += self._database_path_section()
        out += self._debug_logfile_section()
        out += self._sntp_servers_section()
        out += self._ips_section()
        out += self._ips_fixed_section()
        out += self._datagram_monitor_section()
        out += self._network_id_section()
        out += self._peer_private_section()
        out += self._validators_file_section()
        out += self._validation_seed_section()
        out += self._validator_token_section()
        out += self._cluster_nodes_section()
        out += self._rpc_startup_section()
        out += self._ssl_verify_section()
        out += self._max_transactions_section()
        out += self._transaction_queue_section()
        out += self._workers_sections()
        out += self._amendment_majority_time_section()
        out += self._amendments_section()
        out += self._voting_section()
        out += self._dex_feed_section()

        return out

    # -- [server] + ssl -------------------------------------------------------

    def _server_section(self) -> str:
        c = self.config
        s = c.server
        out = "[server]\n"

        if s.rpc_public:
            out += "port_rpc_public\n"
        if s.rpc_admin:
            out += "port_rpc_admin_local\n"
        if s.ws_public:
            out += "port_ws_public\n"
        if s.peer:
            out += "port_peer\n"
        if s.ws_admin:
            out += "port_ws_admin_local\n"

        # SSL key/cert (only if both paths are set)
        if s.ssl_key_path and s.ssl_cert_path:
            out += "\n"
            out += f"ssl_key = {s.ssl_key_path}\n"
            out += f"ssl_cert = {s.ssl_cert_path}\n"

        return out

    # -- port sections --------------------------------------------------------

    def _port_sections(self) -> str:
        c = self.config
        s = c.server
        p = c.ports
        out = ""

        if s.rpc_public:
            out += "\n"
            out += f"[port_rpc_public]\n"
            out += f"port = {p.rpc_public}\n"
            out += f"ip = 0.0.0.0\n"
            out += f"admin = 0.0.0.0\n"
            out += f"protocol = http\n"
            out += f"send_queue_limit = {s.send_queue_limit}\n"

        if s.rpc_admin:
            out += "\n"
            out += f"[port_rpc_admin_local]\n"
            out += f"port = {p.rpc_admin}\n"
            out += f"ip = 0.0.0.0\n"
            out += f"admin = 0.0.0.0\n"
            out += f"protocol = http\n"
            out += f"send_queue_limit = {s.send_queue_limit}\n"

        if s.ws_public:
            out += "\n"
            out += f"[port_ws_public]\n"
            out += f"port = {p.ws_public}\n"
            out += f"ip = 0.0.0.0\n"
            out += f"protocol = ws\n"
            out += f"send_queue_limit = {s.send_queue_limit}\n"

        if s.ws_admin:
            out += "\n"
            out += f"[port_ws_admin_local]\n"
            out += f"port = {p.ws_admin}\n"
            out += f"ip = 0.0.0.0\n"
            out += f"admin = 0.0.0.0\n"
            out += f"protocol = ws\n"
            out += f"send_queue_limit = {s.send_queue_limit}\n"

        if s.peer:
            out += "\n"
            out += f"[port_peer]\n"
            out += f"port = {p.peer}\n"
            out += f"ip = 0.0.0.0\n"
            out += f"protocol = peer\n"
            out += f"send_queue_limit = {s.send_queue_limit}\n"

        return out

    # -- node_size / node_db / relational_db ----------------------------------

    def _node_size_section(self) -> str:
        return f"\n[node_size]\n{self.config.size_node}\n\n"

    def _tree_cache_ram_percent_section(self) -> str:
        return f"[tree_cache_ram_percent]\n{self.config.tree_cache_ram_percent}\n\n"

    def _tree_cache_target_entries_section(self) -> str:
        if self.config.tree_cache_target_entries > 0:
            return f"[tree_cache_target_entries]\n{self.config.tree_cache_target_entries}\n\n"
        return ""

    def _consensus_reserve_threads_section(self) -> str:
        return f"[consensus_reserve_threads]\n{self.config.consensus_reserve_threads}\n\n"

    def _node_db_section(self) -> str:
        from xrpld_lab.models import NodeDbType

        ndb = self.config.node_db
        out = f"[node_db]\n"
        out += f"type={ndb.db_type.value}\n"
        if ndb.db_type != NodeDbType.RWDB:
            out += f"path={ndb.path}\n"
            if ndb.num_ledgers:
                out += f"advisory_delete=0\n"
                out += f"online_delete={ndb.num_ledgers}\n"
        out += "\n"
        return out

    def _relational_db_section(self) -> str:
        rdb = self.config.node_db.relational_db
        if rdb:
            return f"[relational_db]\n{rdb}\n\n"
        return ""

    # -- fee reserves ---------------------------------------------------------

    def _fee_reserves_section(self) -> str:
        out = "[fee_account_reserve]\n5000000\n\n"
        out += "[fee_owner_reserve]\n1000000\n\n"
        return out

    # -- ledger_history -------------------------------------------------------

    def _ledger_history_section(self) -> str:
        nl = self.config.node_db.num_ledgers
        value = str(nl) if nl else "full"
        return f"[ledger_history]\n{value}\n\n"

    # -- paths ----------------------------------------------------------------

    def _database_path_section(self) -> str:
        return f"[database_path]\n{self.config.db_path}\n\n"

    def _debug_logfile_section(self) -> str:
        return f"[debug_logfile]\n{self.config.debug_path}\n\n"

    # -- sntp_servers ---------------------------------------------------------

    def _sntp_servers_section(self) -> str:
        out = "[sntp_servers]\n"
        for srv in _SNTP_SERVERS:
            out += f"{srv}\n"
        out += "\n"
        return out

    # -- ips / ips_fixed ------------------------------------------------------

    def _ips_section(self) -> str:
        urls = self.config.ips_urls
        if urls and len(urls) > 0:
            out = "[ips]\n"
            for url in urls:
                out += f"{url}\n"
            out += "\n"
            return out
        return ""

    def _ips_fixed_section(self) -> str:
        urls = self.config.ips_fixed_urls
        if urls and len(urls) > 0:
            out = "[ips_fixed]\n"
            for url in urls:
                out += f"{url}\n"
            out += "\n"
            return out
        return ""

    # -- datagram_monitor -----------------------------------------------------

    def _datagram_monitor_section(self) -> str:
        endpoints = self.config.datagram_monitor
        if endpoints and len(endpoints) > 0:
            out = "[datagram_monitor]\n"
            for ep in endpoints:
                out += f"{ep}\n"
            out += "\n"
            return out
        return ""

    # -- network_id -----------------------------------------------------------

    def _network_id_section(self) -> str:
        nid = self.config.network_id
        if nid:
            return f"[network_id]\n{nid}\n\n"
        return ""

    # -- peer_private ---------------------------------------------------------

    def _peer_private_section(self) -> str:
        val = 1 if self.config.private_peer else 0
        return f"[peer_private]\n{val}\n\n"

    # -- validators_file ------------------------------------------------------

    def _validators_file_section(self) -> str:
        return "[validators_file]\nvalidators.txt\n\n"

    # -- validation_seed / validator_token ------------------------------------

    def _validation_seed_section(self) -> str:
        v = self.config.validator
        if v and v.manifest:
            return f"[validation_seed]\n{v.manifest}\n\n"
        return ""

    def _validator_token_section(self) -> str:
        v = self.config.validator
        if v and v.token:
            return f"[validator_token]\n{v.token}\n\n"
        return ""

    # -- cluster_nodes --------------------------------------------------------

    def _cluster_nodes_section(self) -> str:
        cn = self.config.cluster_nodes
        if len(cn):
            out = "[cluster_nodes]\n"
            for node in cn:
                out += f"{node}\n"
            out += "\n"
            return out
        return ""

    # -- rpc_startup ----------------------------------------------------------

    def _rpc_startup_section(self) -> str:
        level = self.config.log_level
        if level not in _KNOWN_LOG_LEVELS:
            level = "info"
        out = "[rpc_startup]\n"
        out += f'{{ "command": "log_level", "severity": "{level}" }}\n'
        return out

    # -- ssl_verify -----------------------------------------------------------

    def _ssl_verify_section(self) -> str:
        val = 1 if self.config.server.ssl_verify else 0
        return f"\n[ssl_verify]\n{val}\n"

    # -- max_transactions -----------------------------------------------------

    def _max_transactions_section(self) -> str:
        return f"\n[max_transactions]\n{self.config.max_transactions}\n"

    # -- transaction_queue ----------------------------------------------------

    def _transaction_queue_section(self) -> str:
        tq = self.config.tx_queue
        out = "\n[transaction_queue]\n"
        out += f"ledgers_in_queue = {tq.ledgers_in_queue}\n"
        out += f"minimum_queue_size = {tq.minimum_queue_size}\n"
        out += f"retry_sequence_percent = {tq.retry_sequence_percent}\n"
        out += f"minimum_escalation_multiplier = {tq.minimum_escalation_multiplier}\n"
        out += f"minimum_txn_in_ledger = {tq.minimum_txn_in_ledger}\n"
        out += f"minimum_txn_in_ledger_standalone = {tq.minimum_txn_in_ledger_standalone}\n"
        out += f"target_txn_in_ledger = {tq.target_txn_in_ledger}\n"
        out += f"normal_consensus_increase_percent = {tq.normal_consensus_increase_percent}\n"
        out += f"slow_consensus_decrease_percent = {tq.slow_consensus_decrease_percent}\n"
        out += f"maximum_txn_in_ledger = {tq.maximum_txn_in_ledger}\n"
        out += f"maximum_txn_per_account = {tq.maximum_txn_per_account}\n"
        out += f"minimum_last_ledger_buffer = {tq.minimum_last_ledger_buffer}\n"
        out += f"zero_basefee_transaction_feelevel = {tq.zero_basefee_transaction_feelevel}\n"
        return out

    # -- workers --------------------------------------------------------------

    def _workers_sections(self) -> str:
        w = self.config.worker
        out = ""
        if w.workers:
            out += f"[workers] \n"
            out += f"{w.workers} \n"
        if w.io_workers:
            out += f"[io_workers] \n"
            out += f"{w.io_workers} \n"
        if w.prefetch_workers:
            out += f"[prefetch_workers] \n"
            out += f"{w.prefetch_workers} \n"
        return out

    # -- amendment_majority_time ----------------------------------------------

    def _amendment_majority_time_section(self) -> str:
        amt = self.config.amendment_majority_time
        if amt:
            return f"\n[amendment_majority_time]\n{amt}\n"
        return ""

    # -- amendments -----------------------------------------------------------

    def _amendments_section(self) -> str:
        amd = self.config.amendments
        if amd and len(amd) > 0:
            out = "\n[amendments]\n"
            for name, hash_val in amd.items():
                out += f"{hash_val} {name}\n"
            return out
        return ""

    # -- voting ---------------------------------------------------------------

    def _voting_section(self) -> str:
        v = self.config.voting
        out = "\n[voting]\n"
        out += f"account_reserve = {v.account_reserve}\n"
        out += f"owner_reserve = {v.owner_reserve}\n"
        out += f"reference_fee = {v.reference_fee}\n"
        return out

    # -- dex_feed -------------------------------------------------------------

    def _dex_feed_section(self) -> str:
        out = "\n[dex_feed]\n"
        out += "enabled=true\n"
        out += "socket_path=/tmp/dex_feed.sock\n"
        out += "include_amm_state=true\n"
        out += "db_path=./dex_timeseries\n"
        return out


# ---------------------------------------------------------------------------
# ValidatorsTxtBuilder
# ---------------------------------------------------------------------------


class ValidatorsTxtBuilder:
    """Produces the ``validators.txt`` content string from a :class:`NodeConfig`."""

    def __init__(self, config: NodeConfig, genesis: bool = False):
        self.config = config
        self.genesis = genesis

    def build(self) -> str:
        out = ""

        if self.genesis:
            out += self._genesis_validators()
        else:
            out += self._vl_sites_and_keys()

        out += self._import_vl_keys()

        return out

    def _genesis_validators(self) -> str:
        out = "[validators]\n"
        for key in self.config.validators:
            out += f"    {key}\n"
        out += "\n"
        return out

    def _vl_sites_and_keys(self) -> str:
        out = "[validator_list_sites]\n"
        for site in self.config.vl_sites:
            out += f"    {site}\n"
            out += "\n"

        out += "[validator_list_keys]\n"
        for key in self.config.vl_keys:
            out += f"    {key}\n"

        return out

    def _import_vl_keys(self) -> str:
        ivl = self.config.import_vl_keys
        if len(ivl) > 0:
            out = "\n[import_vl_keys]\n"
            for key in ivl:
                out += f"    {key}\n"
            return out
        return ""
