#!/usr/bin/env node

import * as path from 'path';

export interface RippledBuild {
  name: string;
  path: string;
  data: string;
}

function generateRippledCfg(
  buildPath: string,
  nodeIndex: number,
  network: string,
  networkId: number,
  isRpcPublic: boolean,
  rpcPublicPort: number,
  isRpcAdmin: boolean,
  rpcAdminPort: number,
  isWsPublic: boolean,
  wsPublicPort: number,
  isWsAdmin: boolean,
  wsAdminPort: number,
  isPeer: boolean,
  peerPort: number,
  sslVerify: number,
  isSsl: boolean,
  keyPath: string | null,
  crtPath: string | null,
  sizeNode: string,
  numLedgers: string,
  nudbPath: string,
  dbPath: string,
  debugPath: string,
  logLevel: string,
  privatePeer: number,
  genesis: boolean,
  vSeed: string | null = null,
  vToken: string | null = null,
  validators: string[] = [],
  clusterNodes: string[] = [],
  validatorListSites: string[] = [],
  validatorListKeys: string[] = [],
  importVlKeys: string[] = [],
  ipsFixedUrls: string[] = [],
  ipsUrls: string[] = [],
  amendmentMajorityTime: string | null = null,
  amendmentsDict: { [key: string]: string } = {},
  maxTransactions: number = 10000,
  ledgersInQueue: number = 20,
  minimumQueueSize: number = 2000,
  retrySequencePercent: number = 25,
  minimumEscalationMultiplier: number = 500,
  minimumTxnInLedger: number = 5,
  minimumTxnInLedgerStandalone: number = 5,
  targetTxnInLedger: number = 100,
  maximumTxnInLedger: number = 10000,
  normalConsensusIncreasePercent: number = 20,
  slowConsensusDecreasePercent: number = 50,
  maximumTxnPerAccount: number = 100000,
  minimumLastLedgerBuffer: number = 2,
  zeroBasefeeTransactionFeelevel: number = 256000,
  workers: number = 6,
  ioWorkers: number = 2,
  prefetchWorkers: number = 4,
  sendQueueLimit: number = 65535
): RippledBuild[] {
  try {
    const nodeConfigPath: string = path.join(buildPath, 'config');

    let cfgOut: string = '';

    const serverCfg: string = '[server]\n';
    cfgOut += serverCfg;

    const _rpcPublicIp: string = '0.0.0.0';
    const _rpcAdminIp: string = '0.0.0.0';
    const _wsPublicIp: string = '0.0.0.0';
    const _wsAdminIp: string = '0.0.0.0';
    const _peerPortIp: string = '0.0.0.0';

    if (isRpcPublic) {
      cfgOut += 'port_rpc_public\n';
    }

    if (isRpcAdmin) {
      cfgOut += 'port_rpc_admin_local\n';
    }

    if (isWsPublic) {
      cfgOut += 'port_ws_public\n';
    }

    if (isPeer) {
      cfgOut += 'port_peer\n';
    }

    if (isWsAdmin) {
      cfgOut += 'port_ws_admin_local\n';
    }

    if (isSsl && keyPath && crtPath) {
      cfgOut += '\n';
      cfgOut += `ssl_key = ${keyPath}\n`;
      cfgOut += `ssl_cert = ${crtPath}\n`;
    }

    const httpProtocol: string = 'http';
    const wsProtocol: string = 'ws';
    if (isRpcPublic) {
      cfgOut += '\n';
      cfgOut += '[port_rpc_public]\n';
      cfgOut += `port = ${rpcPublicPort}\n`;
      cfgOut += `ip = ${_rpcPublicIp}\n`;
      cfgOut += `admin = ${_rpcPublicIp}\n`;
      cfgOut += `protocol = ${httpProtocol}\n`;
      cfgOut += `send_queue_limit = ${sendQueueLimit}\n`;
    }

    if (isRpcAdmin) {
      cfgOut += '\n';
      cfgOut += '[port_rpc_admin_local]\n';
      cfgOut += `port = ${rpcAdminPort}\n`;
      cfgOut += `ip = ${_rpcAdminIp}\n`;
      cfgOut += `admin = ${_rpcAdminIp}\n`;
      cfgOut += `protocol = ${httpProtocol}\n`;
      cfgOut += `send_queue_limit = ${sendQueueLimit}\n`;
    }

    if (isWsPublic) {
      cfgOut += '\n';
      cfgOut += '[port_ws_public]\n';
      cfgOut += `port = ${wsPublicPort}\n`;
      cfgOut += `ip = ${_wsPublicIp}\n`;
      cfgOut += `protocol = ${wsProtocol}\n`;
      cfgOut += `send_queue_limit = ${sendQueueLimit}\n`;
    }

    if (isWsAdmin) {
      cfgOut += '\n';
      cfgOut += '[port_ws_admin_local]\n';
      cfgOut += `port = ${wsAdminPort}\n`;
      cfgOut += `ip = ${_wsAdminIp}\n`;
      cfgOut += `admin = ${_wsAdminIp}\n`;
      cfgOut += `protocol = ${wsProtocol}\n`;
      cfgOut += `send_queue_limit = ${sendQueueLimit}\n`;
    }

    if (isPeer) {
      cfgOut += '\n';
      cfgOut += '[port_peer]\n';
      cfgOut += `port = ${peerPort}\n`;
      cfgOut += `ip = ${_peerPortIp}\n`;
      cfgOut += 'protocol = peer\n';
      cfgOut += `send_queue_limit = ${sendQueueLimit}\n`;
    }

    cfgOut += '\n';
    cfgOut += '[node_size]\n';
    cfgOut += `${sizeNode}\n`;
    cfgOut += '\n';

    cfgOut += '[node_db]\n';
    cfgOut += 'type=NuDB\n';
    cfgOut += `path=${nudbPath}\n`;
    if (numLedgers) {
      cfgOut += 'advisory_delete=0\n';
      cfgOut += `online_delete=${numLedgers}\n`;
    }
    cfgOut += '\n';

    const feeAccountReserve: number = 5000000;
    cfgOut += '[fee_account_reserve]\n';
    cfgOut += `${feeAccountReserve}\n`;
    cfgOut += '\n';

    const feeOwnerReserve: number = 1000000;
    cfgOut += '[fee_owner_reserve]\n';
    cfgOut += `${feeOwnerReserve}\n`;
    cfgOut += '\n';

    cfgOut += '[ledger_history]\n';
    if (numLedgers) {
      cfgOut += `${numLedgers}\n`;
    } else {
      cfgOut += 'full\n';
    }
    cfgOut += '\n';

    cfgOut += '[database_path]\n';
    cfgOut += `${dbPath}\n`;
    cfgOut += '\n';

    cfgOut += '[debug_logfile]\n';
    cfgOut += `${debugPath}\n`;
    cfgOut += '\n';

    cfgOut += '[sntp_servers]\n';
    cfgOut += 'time.windows.com\n';
    cfgOut += 'time.apple.com\n';
    cfgOut += 'time.nist.gov\n';
    cfgOut += 'pool.ntp.org\n';
    cfgOut += '\n';

    if (ipsUrls && ipsUrls.length > 0) {
      cfgOut += '[ips]\n';
      for (const url of ipsUrls) {
        cfgOut += `${url}\n`;
      }
      cfgOut += '\n';
    }

    if (ipsFixedUrls && ipsFixedUrls.length > 0) {
      cfgOut += '[ips_fixed]\n';
      for (const url of ipsFixedUrls) {
        cfgOut += `${url}\n`;
      }
      cfgOut += '\n';
    }

    if (networkId) {
      cfgOut += '[network_id]\n';
      cfgOut += `${networkId}\n`;
      cfgOut += '\n';
    }

    cfgOut += '[peer_private]\n';
    cfgOut += `${privatePeer}\n`;
    cfgOut += '\n';

    cfgOut += '[validators_file]\n';
    cfgOut += 'validators.txt\n';
    cfgOut += '\n';

    if (vSeed) {
      cfgOut += '[validation_seed]\n';
      cfgOut += `${vSeed}\n`;
      cfgOut += '\n';
    }

    if (vToken) {
      cfgOut += '[validator_token]\n';
      cfgOut += `${vToken}\n`;
      cfgOut += '\n';
    }

    if (clusterNodes.length) {
      cfgOut += '[cluster_nodes]\n';
      for (const v of clusterNodes) {
        cfgOut += `${v}\n`;
      }
      cfgOut += '\n';
    }

    cfgOut += '[rpc_startup]\n';
    if (logLevel === 'trace') {
      cfgOut += '{ "command": "log_level", "severity": "trace" }\n';
    } else if (logLevel === 'debug') {
      cfgOut += '{ "command": "log_level", "severity": "debug" }\n';
    } else if (logLevel === 'info') {
      cfgOut += '{ "command": "log_level", "severity": "info" }\n';
    } else if (logLevel === 'warning') {
      cfgOut += '{ "command": "log_level", "severity": "warning" }\n';
    } else if (logLevel === 'error') {
      cfgOut += '{ "command": "log_level", "severity": "error" }\n';
    } else {
      cfgOut += '{ "command": "log_level", "severity": "info" }\n';
    }

    cfgOut += '\n';
    cfgOut += '[ssl_verify]\n';
    cfgOut += `${sslVerify}\n`;

    cfgOut += '\n';
    cfgOut += '[max_transactions]\n';
    cfgOut += `${maxTransactions}\n`;

    cfgOut += '\n';
    cfgOut += '[transaction_queue]\n';
    cfgOut += `ledgers_in_queue = ${ledgersInQueue}\n`;
    cfgOut += `minimum_queue_size = ${minimumQueueSize}\n`;
    cfgOut += `retry_sequence_percent = ${retrySequencePercent}\n`;
    cfgOut += `minimum_escalation_multiplier = ${minimumEscalationMultiplier}\n`;
    cfgOut += `minimum_txn_in_ledger = ${minimumTxnInLedger}\n`;
    cfgOut += `minimum_txn_in_ledger_standalone = ${minimumTxnInLedgerStandalone}\n`;
    cfgOut += `target_txn_in_ledger = ${targetTxnInLedger}\n`;
    cfgOut += `normal_consensus_increase_percent = ${normalConsensusIncreasePercent}\n`;
    cfgOut += `slow_consensus_decrease_percent = ${slowConsensusDecreasePercent}\n`;
    cfgOut += `maximum_txn_in_ledger = ${maximumTxnInLedger}\n`;
    cfgOut += `maximum_txn_per_account = ${maximumTxnPerAccount}\n`;
    cfgOut += `minimum_last_ledger_buffer = ${minimumLastLedgerBuffer}\n`;
    cfgOut += `zero_basefee_transaction_feelevel = ${zeroBasefeeTransactionFeelevel}\n`;

    if (workers) {
      cfgOut += '[workers]\n';
      cfgOut += `${workers}\n`;
    }

    if (ioWorkers) {
      cfgOut += '[io_workers]\n';
      cfgOut += `${ioWorkers}\n`;
    }

    if (prefetchWorkers) {
      cfgOut += '[prefetch_workers]\n';
      cfgOut += `${prefetchWorkers}\n`;
    }

    if (amendmentMajorityTime) {
      cfgOut += '\n';
      cfgOut += '[amendment_majority_time]\n';
      cfgOut += `${amendmentMajorityTime}\n`;
    }

    if (amendmentsDict && Object.keys(amendmentsDict).length > 0) {
      cfgOut += '\n';
      cfgOut += '[amendments]\n';
      for (const [k, v] of Object.entries(amendmentsDict)) {
        cfgOut += `${v} ${k}\n`;
      }
    }

    let validatorsOut: string = '';
    if (genesis) {
      validatorsOut += '[validators]\n';
      for (const kp of validators) {
        validatorsOut += `    ${kp}\n`;
      }
      validatorsOut += '\n';
    } else {
      validatorsOut += '[validator_list_sites]\n';
      for (const vs of validatorListSites) {
        validatorsOut += `    ${vs}\n`;
        validatorsOut += '\n';
      }

      validatorsOut += '[validator_list_keys]\n';
      for (const vk of validatorListKeys) {
        validatorsOut += `    ${vk}\n`;
      }
    }

    if (importVlKeys.length > 0) {
      validatorsOut += '\n';
      validatorsOut += '[import_vl_keys]\n';
      for (const vk of importVlKeys) {
        validatorsOut += `    ${vk}\n`;
      }
    }

    return [
      { name: 'cfg', path: `${nodeConfigPath}/rippled.cfg`, data: cfgOut },
      { name: 'vl', path: `${nodeConfigPath}/validators.txt`, data: validatorsOut },
      { name: 'docker', path: `${nodeConfigPath}/validators.txt`, data: validatorsOut }
    ];

  } catch (e) {
    console.error(`line: ${e.lineNumber} error: ${e.message}`);
    console.error(buildPath);
    console.error(nodeIndex);
    console.error(network);
    console.error(networkId);
    console.error(isRpcPublic);
    console.error(rpcPublicPort);
    console.error(isRpcAdmin);
    console.error(rpcAdminPort);
    console.error(isWsPublic);
    console.error(wsPublicPort);
    console.error(isWsAdmin);
    console.error(wsAdminPort);
    console.error(isPeer);
    console.error(peerPort);
    console.error(sslVerify);
    console.error(isSsl);
    console.error(keyPath);
    console.error(crtPath);
    console.error(sizeNode);
    console.error(nudbPath);
    console.error(dbPath);
    console.error(numLedgers);
    console.error(debugPath);
    console.error(logLevel);
    console.error(privatePeer);
    console.error(genesis);
    console.error(vSeed);
    console.error(vToken);
    console.error(validators);
    console.error(clusterNodes);
    console.error(validatorListSites);
    console.error(validatorListKeys);
    console.error(importVlKeys);
    console.error(ipsFixedUrls);
    console.error(ipsUrls);
    console.error(amendmentsDict);
    console.error(maxTransactions);
    console.error(ledgersInQueue);
    console.error(minimumTxnInLedger);
    console.error(targetTxnInLedger);
    console.error(normalConsensusIncreasePercent);
    console.error(slowConsensusDecreasePercent);
    console.error(maximumTxnInLedger);
    console.error(maximumTxnPerAccount);
    throw e;
  }
}

export function genConfig(
  ansible: boolean,
  protocol: string,
  name: string,
  networkId: number,
  index: number,
  rpcPublic: number,
  rpcAdmin: number,
  wsPublic: number,
  wsAdmin: number,
  peer: number,
  sizeNode: string,
  numLedgers: number | null,
  nudbPath: string,
  dbPath: string,
  debugPath: string,
  logLevel: string,
  vToken: string | null,
  validators: string[],
  vlSites: string[],
  vlKeys: string[],
  ivlKeys: string[],
  ipsUrls: string[] = [],
  ipsFixedUrls: string[] = []
): RippledBuild[] {
  const configs: RippledBuild[] = generateRippledCfg(
    // App
    '/',
    index,
    name,
    networkId,
    // Rippled
    true,
    rpcPublic,
    true,
    rpcAdmin,
    true,
    wsPublic,
    true,
    wsAdmin,
    true,
    peer,
    // ssl_verify=1 if _node.ssl_verify else 0,
    0,
    true,
    null,
    null,
    sizeNode,
    (numLedgers || 0).toString(),
    nudbPath,
    dbPath,
    debugPath,
    logLevel,
    // private_peer=1 if _node.private_peer and i == 1 else 0,
    0,
    ansible,
    null,
    vToken,
    validators,
    [],
    vlSites,
    vlKeys,
    ivlKeys,
    ipsFixedUrls,
    ipsUrls,
    protocol === 'xahau' ? '5 minutes' : '15 minutes',
    {}
  );
  return configs;
}
