#!/usr/bin/env python
# coding: utf-8
"""Generate a prefunded performance genesis: synthetic AccountRoot + RippleState
(trustline) ledger-state entries that the node loads via ``--ledgerfile``.

The node (xrpld) needs NO change — ``StartUpType::LoadFile`` already ingests
``accountState`` entries; each just needs its ``index`` (the SHAMap keylet).

Keylets are derived to match xrpld exactly:
  - account      = SHA512Half(0x0061 ‖ accountID)         [verified vs genesis root vector]
  - ripple_state = SHA512Half(0x0072 ‖ lo ‖ hi ‖ cur20)   [0x0072 namespace documented;
                   currency encoding verified vs xrpl-py codec; account order canonical]

Accounts are generated deterministically from an index so the loadtester can sign
with the same seeds (written to a wallets file in its ``wallets.sub.*.json`` format,
i.e. a JSON list of seeds). Because the accounts are prefunded in genesis, the
loadtester's funding step can be skipped.

Standalone:
    python -m xrpld_lab.ledger_generator --accounts 1000 --trustlines 200 \
        --out-state state.json --out-wallets wallets.sub.1.json
"""

import argparse
import hashlib
import json
from typing import List, Tuple

from xrpl.core.addresscodec import decode_classic_address
from xrpl.core.keypairs import generate_seed
from xrpl.wallet import Wallet

_NS_ACCOUNT = b"\x00\x61"  # 'a'
_NS_RIPPLE_STATE = b"\x00\x72"  # 'r'
_NS_OWNER_DIR = b"\x00\x4F"  # 'O'
_ZERO_TXN = "0" * 64
_ACCOUNT_ZERO = "rrrrrrrrrrrrrrrrrrrrBZbvji"  # RippleState Balance issuer (noAccount)

# RippleState flags
_LSF_LOW_RESERVE = 0x00010000
_LSF_HIGH_RESERVE = 0x00020000


def _sha512half(b: bytes) -> bytes:
    return hashlib.sha512(b).digest()[:32]


def account_index(address: str) -> str:
    return _sha512half(_NS_ACCOUNT + decode_classic_address(address)).hex().upper()


def currency_to_bytes(code: str) -> bytes:
    if len(code) == 40:
        return bytes.fromhex(code)
    if len(code) <= 3:
        return b"\x00" * 12 + code.encode("ascii").ljust(3, b"\x00") + b"\x00" * 5
    raise ValueError(f"currency must be 3-char ISO or 40-char hex, got {code!r}")


def ripple_state_index(addr_a: str, addr_b: str, currency: str) -> str:
    a, b = decode_classic_address(addr_a), decode_classic_address(addr_b)
    lo, hi = (a, b) if a < b else (b, a)
    return _sha512half(_NS_RIPPLE_STATE + lo + hi + currency_to_bytes(currency)).hex().upper()


def owner_dir_index(address: str) -> str:
    return _sha512half(_NS_OWNER_DIR + decode_classic_address(address)).hex().upper()


def make_wallet(index: int, prefix: bytes = b"perf-iac-") -> Wallet:
    """Deterministic wallet from an index (so lab + loadtester agree on the account set)."""
    entropy = hashlib.sha256(prefix + index.to_bytes(8, "big")).digest()[:16]
    return Wallet.from_seed(generate_seed(entropy.hex()))


def account_root_entry(address: str, balance_drops, sequence: int = 1, owner_count: int = 0) -> dict:
    return {
        "Account": address,
        "Balance": str(balance_drops),
        "Flags": 0,
        "LedgerEntryType": "AccountRoot",
        "OwnerCount": owner_count,
        "PreviousTxnID": _ZERO_TXN,
        "PreviousTxnLgrSeq": 0,
        "Sequence": sequence,
        "index": account_index(address),
    }


def ripple_state_entry(addr_a: str, addr_b: str, currency: str,
                       value: str = "0", limit: str = "1000000000") -> dict:
    a, b = decode_classic_address(addr_a), decode_classic_address(addr_b)
    low_addr, high_addr = (addr_a, addr_b) if a < b else (addr_b, addr_a)
    return {
        "LedgerEntryType": "RippleState",
        "Flags": _LSF_LOW_RESERVE | _LSF_HIGH_RESERVE,
        "Balance": {"currency": currency, "issuer": _ACCOUNT_ZERO, "value": value},
        "LowLimit": {"currency": currency, "issuer": low_addr, "value": limit},
        "HighLimit": {"currency": currency, "issuer": high_addr, "value": limit},
        "LowNode": "0",   # page 0 of the low account's owner directory
        "HighNode": "0",  # page 0 of the high account's owner directory
        "PreviousTxnID": _ZERO_TXN,
        "PreviousTxnLgrSeq": 0,
        "index": ripple_state_index(addr_a, addr_b, currency),
    }


def directory_node_entry(owner_address: str, indexes) -> dict:
    """Single-page owner directory (page 0 == root) listing the objects an account owns.

    Required for trustlines to appear in ``account_lines`` and count toward reserve;
    a RippleState object alone (no directory entry) is orphaned.
    """
    idx = owner_dir_index(owner_address)
    return {
        "LedgerEntryType": "DirectoryNode",
        "Flags": 0,
        "Owner": owner_address,
        "RootIndex": idx,
        "Indexes": list(indexes),
        "index": idx,
    }


def generate(num_accounts: int, balance_drops: str = "1000000000",
             num_trustlines: int = 0, currency: str = "USD",
             prefix: bytes = b"perf-iac-") -> Tuple[List[dict], List[str]]:
    """Return ``(accountState_entries, seeds)``.

    Trustlines link account 0 (a hub/issuer) with accounts 1..num_trustlines.
    """
    wallets = [make_wallet(i, prefix) for i in range(num_accounts)]
    owned: dict = {w.classic_address: [] for w in wallets}  # account -> [RippleState index]

    rs_entries: List[dict] = []
    if num_accounts and num_trustlines:
        hub = wallets[0]
        n = min(num_trustlines, num_accounts - 1)
        for i in range(1, n + 1):
            rs = ripple_state_entry(hub.classic_address, wallets[i].classic_address, currency)
            rs_entries.append(rs)
            owned[hub.classic_address].append(rs["index"])
            owned[wallets[i].classic_address].append(rs["index"])

    states: List[dict] = [
        account_root_entry(w.classic_address, balance_drops, owner_count=len(owned[w.classic_address]))
        for w in wallets
    ]
    states.extend(rs_entries)
    # Owner directory page per account that owns trustlines (so they show in
    # account_lines and count toward reserve). Single page suffices at small counts.
    for w in wallets:
        if owned[w.classic_address]:
            states.append(directory_node_entry(w.classic_address, owned[w.classic_address]))
    return states, [w.seed for w in wallets]


def merge_into_genesis(genesis: dict, entries: List[dict]) -> dict:
    """Append synthetic entries (dedup by index) and conserve XRP.

    Prefunded balances are deducted from the largest-balance (root) AccountRoot so
    total drops stay equal to ``total_coins`` — XRP is conserved, not minted.
    """
    state = genesis["ledger"]["accountState"]
    existing = {e.get("index") for e in state}
    added_balance = 0
    new: List[dict] = []
    for e in entries:
        if e.get("index") in existing:
            continue
        new.append(e)
        existing.add(e.get("index"))
        if e.get("LedgerEntryType") == "AccountRoot":
            added_balance += int(e["Balance"])

    if added_balance:
        roots = [e for e in state if e.get("LedgerEntryType") == "AccountRoot"]
        if roots:
            root = max(roots, key=lambda e: int(e.get("Balance", "0")))
            root["Balance"] = str(int(root["Balance"]) - added_balance)

    state.extend(new)
    return genesis


def _main(argv=None):
    p = argparse.ArgumentParser(description="Generate prefunded genesis state + wallets.")
    p.add_argument("--accounts", type=int, required=True)
    p.add_argument("--trustlines", type=int, default=0)
    p.add_argument("--balance", default="1000000000", help="drops per account (default 1000 XRP)")
    p.add_argument("--currency", default="USD")
    p.add_argument("--prefix", default="perf-iac-", help="deterministic seed namespace")
    p.add_argument("--out-state", required=True, help="JSON file: accountState entries array")
    p.add_argument("--out-wallets", required=True, help="JSON file: seed list (loadtester format)")
    args = p.parse_args(argv)

    states, seeds = generate(
        args.accounts, args.balance, args.trustlines, args.currency, args.prefix.encode()
    )
    with open(args.out_state, "w") as f:
        json.dump(states, f)
    with open(args.out_wallets, "w") as f:
        json.dump(seeds, f)
    n_acct = sum(1 for e in states if e["LedgerEntryType"] == "AccountRoot")
    n_rs = sum(1 for e in states if e["LedgerEntryType"] == "RippleState")
    print(f"wrote {n_acct} accounts + {n_rs} trustlines -> {args.out_state}")
    print(f"wrote {len(seeds)} seeds -> {args.out_wallets}")


if __name__ == "__main__":
    _main()
