#!/usr/bin/env node

import * as path from 'path';
import { Command } from 'commander';
import {
  createStandaloneBinary,
  createStandaloneImage,
  startLocal,
} from './main';
import {
  createNetwork,
  updateNodeBinary,
  enableNodeAmendment,
} from './network';
import {
  removeDirectory,
  bcolors,
  checkDeps,
  removeContainers,
  runStart,
  runStop,
  runLogs,
} from './utils/misc';

const basedir = process.cwd()

const XAHAU_RELEASE = "2024.4.21-release+858";
const XRPL_RELEASE = "2.0.0-b4";

const program = new Command();

program
  .description('A CLI to build xrpld networks and standalone ledgers.')
  .version('1.0.0');

// LOGS
program
  .command('logs:hooks')
  .description('Log Hooks')
  .action(() => runLogs());

// LOCAL
program
  .command('start:local')
  .description('Start Local Network')
  .option('--log_level <level>', 'The log level', 'trace')
  .option('--public_key <key>', 'The public vl key', 'ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501')
  .option('--import_key <key>', 'The import vl key')
  .option('--protocol <protocol>', 'The protocol of the network', 'xahau')
  .option('--network_type <type>', 'The type of the network', 'standalone')
  .option('--network_id <id>', 'The network id', '21339')
  .action(async (options) => {
    const { log_level, public_key, import_key, protocol, network_type, network_id } = options;
    console.log(`${bcolors.BLUE}Starting Local Network with the following parameters:${bcolors.END}`);
    console.log(`    - Log Level: ${log_level}`);
    console.log(`    - Public Key: ${public_key}`);
    console.log(`    - Import Key: ${import_key}`);
    console.log(`    - Protocol: ${protocol}`);
    console.log(`    - Network Type: ${network_type}`);
    console.log(`    - Network ID: ${network_id}`);
    await startLocal(log_level, public_key, import_key, protocol, network_type, network_id);
  });

program
  .command('stop:local')
  .description('Stop Local Network')
  .action(() => {
    console.log(`${bcolors.BLUE}Stopping Local Network${bcolors.END}`);
    runStop(['./stop.sh']);
  });

// NETWORK
program
  .command('create:network')
  .description('Create Network')
  .option('--log_level <level>', 'The log level', 'trace')
  .option('--protocol <protocol>', 'The protocol of the network', 'xahau')
  .option('--num_validators <num>', 'The number of validators in the network', '3')
  .option('--num_peers <num>', 'The number of peers in the network', '1')
  .option('--network_id <id>', 'The id of the network', '21339')
  .option('--build_server <server>', 'The build server for the network')
  .option('--build_version <version>', 'The build version for the network')
  .option('--genesis', 'Is this a genesis network?', false)
  .option('--quorum <num>', 'The quorum required for the network')
  .action(async (options) => {
    const {
      log_level, protocol, num_validators, num_peers, network_id,
      build_server, build_version, genesis, quorum
    } = options;

    const import_vl_key = "ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501";
    const buildServer = build_server || "https://build.xahau.tech";
    const buildVersion = build_version || XAHAU_RELEASE;
    const networkQuorum = quorum || num_validators - 1;

    console.log(`${bcolors.BLUE}Creating Network with the following parameters:${bcolors.END}`);
    console.log(`    - Log Level: ${log_level}`);
    console.log(`    - Protocol: ${protocol}`);
    console.log(`    - Number of Validators: ${num_validators}`);
    console.log(`    - Number of Peers: ${num_peers}`);
    console.log(`    - Network ID: ${network_id}`);
    console.log(`    - Build Server: ${buildServer}`);
    console.log(`    - Build Version: ${buildVersion}`);
    console.log(`    - Genesis: ${genesis}`);
    console.log(`    - Quorum: ${networkQuorum}`);

    await createNetwork(
      log_level,
      import_vl_key,
      protocol,
      num_validators,
      num_peers,
      network_id,
      buildServer,
      buildVersion,
      genesis,
      networkQuorum
    );
  });

program
  .command('update:node')
  .description('Update Node Version')
  .requiredOption('--name <name>', 'The name of the network')
  .requiredOption('--node_id <id>', 'The node id you want to update')
  .requiredOption('--node_type <type>', 'The node type you want to update', /^(validator|peer)$/i)
  .option('--build_server <server>', 'The build server for the node')
  .option('--build_version <version>', 'The build version for the node')
  .action(async (options) => {
    const { name, node_id, node_type, build_server, build_version } = options;
    console.log(`${bcolors.BLUE}Updating Node Version with the following parameters:${bcolors.END}`);
    console.log(`    - Network Name: ${name}`);
    console.log(`    - Node ID: ${node_id}`);
    console.log(`    - Node Type: ${node_type}`);
    console.log(`    - Build Server: ${build_server}`);
    console.log(`    - Build Version: ${build_version}`);
    await updateNodeBinary(name, node_id, node_type, build_server, build_version);
  });

program
  .command('enable:amendment')
  .description('Enable Amendment')
  .requiredOption('--name <name>', 'The name of the network')
  .requiredOption('--amendment_name <name>', 'The amendment you want to enable')
  .requiredOption('--node_id <id>', 'The node id you want to update')
  .requiredOption('--node_type <type>', 'The node type you want to update', /^(validator|peer)$/i)
  .action(async (options) => {
    const { name, amendment_name, node_id, node_type } = options;
    console.log(`${bcolors.BLUE}Enabling Amendment with the following parameters:${bcolors.END}`);
    console.log(`    - Network Name: ${name}`);
    console.log(`    - Amendment Name: ${amendment_name}`);
    console.log(`    - Node ID: ${node_id}`);
    console.log(`    - Node Type: ${node_type}`);
    await enableNodeAmendment(name, amendment_name, node_id, node_type);
  });

program
  .command('start')
  .description('Start Network')
  .requiredOption('--name <name>', 'The name of the network')
  .option('--protocol <protocol>', 'The protocol of the network', 'xahau')
  .option('--version <version>', 'The build version for the network')
  .action((options) => {
    const { name, protocol, version } = options;
    const buildVersion = protocol === 'xahau' && !version ? XAHAU_RELEASE : version;
    console.log(`${bcolors.BLUE}Starting Network: ${name}${bcolors.END}`);
    runStart([`${basedir}/${name}/start.sh`], protocol, buildVersion, 'network');
  });

program
  .command('stop')
  .description('Stop Network')
  .requiredOption('--name <name>', 'The name of the network')
  .action((options) => {
    const { name } = options;
    console.log(`${bcolors.BLUE}Stopping Network: ${name}${bcolors.END}`);
    runStop([`${basedir}/${name}/stop.sh`]);
  });

program
  .command('remove')
  .description('Remove Network')
  .requiredOption('--name <name>', 'The name of the network')
  .action((options) => {
    const { name } = options;
    console.log(`${bcolors.BLUE}Removing Network: ${name}${bcolors.END}`);
    removeDirectory(`${basedir}/${name}`);
  });

// STANDALONE
program
  .command('up:standalone')
  .description('Up Standalone')
  .option('--log_level <level>', 'The log level', 'trace')
  .option('--build_type <type>', 'The build type', /^(image|binary)$/i, 'binary')
  .option('--public_key <key>', 'The public vl key', 'ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501')
  .option('--import_key <key>', 'The import vl key')
  .option('--protocol <protocol>', 'The protocol of the network', 'xahau')
  .option('--network_id <id>', 'The network id', '21339')
  .option('--network_type <type>', 'The network type', 'standalone')
  .option('--server <server>', 'The build server for the network')
  .option('--version <version>', 'The build version for the network')
  .option('--ipfs', 'Add an IPFS server', false)
  .action(async (options) => {
    const {
      log_level, build_type, public_key, import_key, protocol,
      network_id, network_type, server, version, ipfs
    } = options;

    const importKey = protocol === 'xahau' && !import_key ? "ED74D4036C6591A4BDF9C54CEFA39B996A5DCE5F86D11FDA1874481CE9D5A1CDC1" : import_key;
    const buildServer = protocol === 'xahau' ? "https://build.xahau.tech" : server;
    const buildType = protocol === 'xahau' ? "binary" : build_type;
    const buildVersion = protocol === 'xahau' && !version ? XAHAU_RELEASE : version;

    console.log(`${bcolors.BLUE}Setting Up Standalone Network with the following parameters:${bcolors.END}`);
    console.log(`    - Log Level: ${log_level}`);
    console.log(`    - Build Type: ${buildType}`);
    console.log(`    - Public Key: ${public_key}`);
    console.log(`    - Import Key: ${importKey}`);
    console.log(`    - Protocol: ${protocol}`);
    console.log(`    - Network Type: ${network_type}`);
    console.log(`    - Network ID: ${network_id}`);
    console.log(`    - Build Server: ${buildServer}`);
    console.log(`    - Build Version: ${buildVersion}`);
    console.log(`    - IPFS Server: ${ipfs}`);

    if (buildType === 'image') {
      await createStandaloneImage(
        log_level,
        public_key,
        importKey,
        protocol,
        network_type,
        network_id,
        buildServer,
        buildVersion,
        ipfs
      );
    } else {
      await createStandaloneBinary(
        log_level,
        public_key,
        importKey,
        protocol,
        network_type,
        network_id,
        buildServer,
        buildVersion,
        ipfs
      );
    }

    runStart([`${basedir}/${protocol}-${buildVersion}/start.sh`], protocol, buildVersion, 'standalone');
  });

program
  .command('down:standalone')
  .description('Down Standalone')
  .option('--name <name>', 'The name of the network')
  .option('--protocol <protocol>', 'The protocol of the network', 'xahau')
  .option('--version <version>', 'The build version for the network')
  .action((options) => {
    const { name, protocol, version } = options;
    console.log(`${bcolors.BLUE}Taking Down Standalone Network with the following parameters:${bcolors.END}`);

    if (name) {
      console.log(`    - Network Name: ${name}`);
      runStop([`${basedir}/${name}/stop.sh`]);
      removeDirectory(`${basedir}/${name}`);
      return;
    }

    const buildVersion = protocol === 'xahau' && !version ? XAHAU_RELEASE : version || XRPL_RELEASE;

    console.log(`    - Network Name: ${name}`);
    console.log(`    - Protocol: ${protocol}`);
    console.log(`    - Build Version: ${buildVersion}`);
    runStop([`${basedir}/${protocol}-${buildVersion}/stop.sh`]);
  });

program.parse(process.argv);

if (!process.argv.slice(2).length) {
  program.outputHelp();
  console.log("");
  console.log("   _  __ ____  ____  __    ____     _   __     __  ______          ");
  console.log("  | |/ // __ \\/ __ \\/ /   / __ \\   / | / /__  / /_/ ____/__  ____  ");
  console.log("  |   // /_/ / /_/ / /   / / / /  /  |/ / _ \\/ __/ / __/ _ \\/ __ \\ ");
  console.log(" /   |/ _, _/ ____/ /___/ /_/ /  / /|  /  __/ /_/ /_/ /  __/ / / / ");
  console.log("/_/|_/_/ |_/_/   /_____/_____/  /_/ |_|\\___/\\__/\\____/\\___/_/ /_/  ");
  console.log("");

  checkDeps([`${basedir}/deploykit/prerequisites.sh`]);

  console.log(`${bcolors.BLUE}Removing existing containers: ${bcolors.RED}`);
  removeContainers("docker stop xahau");
  removeContainers("docker rm xahau");
  removeContainers("docker stop explorer");
  removeContainers("docker rm explorer");
  removeContainers("docker stop xrpl");
  removeContainers("docker rm xrpl");
}
