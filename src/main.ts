#!/usr/bin/env node

import * as fs from 'fs';
import * as path from 'path';
import * as yaml from 'js-yaml';
import * as child_process from 'child_process';
import { genConfig, RippledBuild } from './rippled_cfg';
import { createDockerfile, downloadBinary } from './utils/deployKit';
import { getCommitHashFromServerVersion, downloadFileAtCommitOrTag } from './libs/github';
import { generatePorts, saveLocalConfig, bcolors } from './utils/misc';
import {
  updateAmendments,
  parseRippledAmendments,
  getFeatureLinesFromContent,
  getFeatureLinesFromPath,
} from './libs/rippled';

const basedir = process.cwd()
const srcDir = path.resolve(__dirname);

interface ValidatorConfig {
  ips: string[],
  ips_fixed: string[]
  network_id: number,
  validator_list_sites: string[]
  validator_list_keys: string[]
  import_vl_keys?: string[]
}

async function generateValidatorConfig(protocol: string, network: string): Promise<ValidatorConfig> {
  try {
    const config = JSON.parse(fs.readFileSync(`${srcDir}/deploykit/config.json`, 'utf-8'));
    return config[protocol][network];
  } catch (e) {
    console.error(e);
    throw e
  }
}

let deploykitPath = '';
let services: Record<string, any> = {};

function updateStopSh(
  protocol: string,
  name: string,
  numValidators: number,
  numPeers: number,
  standalone = false,
  local = false
): string {
  let stopShContent = '#! /bin/bash\n';
  if (numValidators > 0 && numPeers > 0) {
    stopShContent += `docker compose -f ${basedir}/${protocol}-${name}/docker-compose.yml down --remove-orphans\n`;
  }

  for (let i = 1; i <= numValidators; i++) {
    stopShContent += `rm -r vnode${i}/lib\n`;
    stopShContent += `rm -r vnode${i}/log\n`;
  }

  for (let i = 1; i <= numPeers; i++) {
    stopShContent += `rm -r pnode${i}/lib\n`;
    stopShContent += `rm -r pnode${i}/log\n`;
  }

  if (standalone) {
    stopShContent += `docker compose -f ${basedir}/${protocol}-${name}/docker-compose.yml down --remove-orphans\n`;
    stopShContent += `rm -r ${protocol}/config\n`;
    stopShContent += `rm -r ${protocol}/lib\n`;
    stopShContent += `rm -r ${protocol}/log\n`;
    stopShContent += `rm -r ${protocol}\n`;
  }

  if (local) {
    stopShContent = '#! /bin/bash\ndocker compose -f docker-compose.yml down --remove-orphans\n';
    stopShContent += 'rm -r db\n';
    stopShContent += 'rm -r debug.log\n';
  }

  return stopShContent;
}

async function createStandaloneFolder(
  binary: boolean,
  name: string,
  image: string,
  featureContent: string,
  networkId: number,
  vlKey: string,
  ivlKey: string,
  protocol: string,
  netType: string,
  logLevel: string
) {
  const cfgPath = `${basedir}/${protocol}-${name}/config`;
  const [rpcPublic, rpcAdmin, wsPublic, wsAdmin, peer] = generatePorts(0, 'standalone');
  const vlConfig = await generateValidatorConfig(protocol, netType);

  if (networkId) {
    vlConfig.network_id = networkId;
  }

  if (vlKey) {
    vlConfig.validator_list_keys = [vlKey];
  }

  if (ivlKey) {
    vlConfig.import_vl_keys = [ivlKey];
  }

  const configs: RippledBuild[] = genConfig(
    false,
    protocol,
    name,
    vlConfig.network_id,
    0,
    rpcPublic,
    rpcAdmin,
    wsPublic,
    wsAdmin,
    peer,
    'huge',
    10000,
    '/var/lib/rippled/db/nudb',
    '/var/lib/rippled/db',
    '/var/log/rippled/debug.log',
    logLevel,
    null,
    [],
    vlConfig.validator_list_sites,
    vlConfig.validator_list_keys,
    protocol === 'xahau' ? vlConfig.import_vl_keys! : [],
    vlConfig.ips,
    vlConfig.ips_fixed
  );
  fs.mkdirSync(`${basedir}/${protocol}-${name}/config`, { recursive: true });
  saveLocalConfig(cfgPath, configs[0].data, configs[1].data);
  console.log(`✅ ${bcolors.CYAN}Creating config`);

  const lines = getFeatureLinesFromContent(featureContent);
  const featuresJson = parseRippledAmendments(lines);
  const genesisJson = await updateAmendments(featuresJson, protocol);
  fs.writeFileSync(
    `${basedir}/${protocol}-${name}/genesis.json`,
    JSON.stringify(genesisJson, null, 4)
  );
  console.log(`✅ ${bcolors.CYAN}Updating features`);

  const dockerfile = createDockerfile(
    binary,
    name,
    image,
    rpcPublic,
    rpcAdmin,
    wsPublic,
    wsAdmin,
    peer,
    true,
    null,
    '-a'
  );
  fs.writeFileSync(`${basedir}/${protocol}-${name}/Dockerfile`, dockerfile);

  fs.copyFileSync(
    `${srcDir}/deploykit/${protocol}.entrypoint`,
    `${basedir}/${protocol}-${name}/entrypoint`
  );
  console.log(`✅ ${bcolors.CYAN}Building docker container...`);
  const pwdStr = '${PWD}';
  services[protocol] = {
    build: {
      context: '.',
      dockerfile: 'Dockerfile',
    },
    platform: 'linux/x86_64',
    container_name: protocol,
    ports: [
      `${rpcPublic}:${rpcPublic}`,
      `${rpcAdmin}:${rpcAdmin}`,
      `${wsPublic}:${wsPublic}`,
      `${wsAdmin}:${wsAdmin}`,
      `${peer}:${peer}`,
    ],
    volumes: [
      `${pwdStr}/${protocol}/config:/etc/opt/ripple`,
      `${pwdStr}/${protocol}/log:/var/log/rippled`,
      `${pwdStr}/${protocol}/lib:/var/lib/rippled`,
    ],
    networks: ['standalone-network'],
  };
}

export async function createStandaloneImage(
  logLevel: string,
  publicKey: string,
  importKey: string,
  protocol: string,
  netType: string,
  networkId: number,
  buildSystem: string,
  buildName: string,
  addIpfs = false
) {
  const name = buildName;
  fs.mkdirSync(`${basedir}/${protocol}-${name}`, { recursive: true });
  const owner = 'XRPLF';
  const repo = 'rippled';
  const content = await downloadFileAtCommitOrTag(
    owner,
    repo,
    buildName,
    'src/ripple/protocol/impl/Feature.cpp'
  );
  const image = `${buildSystem}/rippled:${buildName}`;
  await createStandaloneFolder(
    false,
    name,
    image,
    content,
    networkId,
    publicKey,
    importKey,
    protocol,
    netType,
    logLevel
  );
  services['explorer'] = {
    image: 'transia/explorer:latest',
    container_name: 'explorer',
    environment: [
      'PORT=4000',
      `VUE_APP_WSS_ENDPOINT=ws://0.0.0.0:${6006}`,
    ],
    ports: ['4000:4000'],
    networks: ['standalone-network'],
  };

  if (addIpfs) {
    const pwdStr = '${PWD}';
    services['ipfs'] = {
      image: 'ipfs/go-ipfs:latest',
      container_name: 'ipfs',
      environment: [
        'IPFS_PROFILE=server',
      ],
      ports: ['4001:4001', '5001:5001', '8080:8080'],
      volumes: [
        `${pwdStr}/${protocol}/ipfs_staging:/export`,
        `${pwdStr}/${protocol}/ipfs_data:/data/ipfs`,
      ],
      networks: ['standalone-network'],
    };
  }

  const compose = {
    version: '3.9',
    services: services,
    networks: { 'standalone-network': { driver: 'bridge' } },
  };

  fs.writeFileSync(`${basedir}/${protocol}-${name}/docker-compose.yml`, yaml.dump(compose));

  fs.writeFileSync(
    `${basedir}/${protocol}-${name}/start.sh`,
    `\
#! /bin/bash
docker compose -f ${basedir}/${protocol}-${name}/docker-compose.yml up --build --force-recreate -d
`
  );
  fs.chmodSync(`${basedir}/${protocol}-${name}/start.sh`, 0o755);
  const stopShContent = updateStopSh(protocol, name, 0, 0, true);
  fs.writeFileSync(`${basedir}/${protocol}-${name}/stop.sh`, stopShContent);
  fs.chmodSync(`${basedir}/${protocol}-${name}/stop.sh`, 0o755);
}

async function createBinaryFolder(
  binary: boolean,
  name: string,
  image: string,
  featureContent: string,
  networkId: number,
  vlKey: string,
  ivlKey: string,
  protocol: string,
  netType: string,
  logLevel: string
) {
  const cfgPath = `${basedir}/${protocol}-${name}/config`;
  const [rpcPublic, rpcAdmin, wsPublic, wsAdmin, peer] = generatePorts(0, 'standalone');
  const vlConfig = await generateValidatorConfig(protocol, netType);

  if (networkId) {
    vlConfig.network_id = networkId;
  }

  if (vlKey) {
    vlConfig.validator_list_keys = [vlKey];
  }

  if (ivlKey) {
    vlConfig.import_vl_keys = [ivlKey];
  }

  const configs: RippledBuild[] = genConfig(
    false,
    protocol,
    name,
    vlConfig.network_id,
    0,
    rpcPublic,
    rpcAdmin,
    wsPublic,
    wsAdmin,
    peer,
    'huge',
    10000,
    '/var/lib/rippled/db/nudb',
    '/var/lib/rippled/db',
    '/var/log/rippled/debug.log',
    logLevel,
    null,
    [],
    vlConfig.validator_list_sites,
    vlConfig.validator_list_keys,
    protocol === 'xahau' ? vlConfig.import_vl_keys! : [],
    vlConfig.ips,
    vlConfig.ips_fixed
  );
  fs.mkdirSync(`${basedir}/${protocol}-${name}/config`, { recursive: true });
  saveLocalConfig(cfgPath, configs[0].data, configs[1].data);
  console.log(`✅ ${bcolors.CYAN}Creating config`);

  const lines = getFeatureLinesFromContent(featureContent);
  const featuresJson = parseRippledAmendments(lines);
  const genesisJson = await updateAmendments(featuresJson, protocol);
  fs.writeFileSync(
    `${basedir}/${protocol}-${name}/genesis.json`,
    JSON.stringify(genesisJson, null, 4)
  );
  console.log(`✅ ${bcolors.CYAN}Updating features`);

  const dockerfile = createDockerfile(
    binary,
    name,
    image,
    rpcPublic,
    rpcAdmin,
    wsPublic,
    wsAdmin,
    peer,
    true,
    null,
    '-a'
  );
  fs.writeFileSync(`${basedir}/${protocol}-${name}/Dockerfile`, dockerfile);

  fs.copyFileSync(
    `${srcDir}/deploykit/${protocol}.entrypoint`,
    `${basedir}/${protocol}-${name}/entrypoint`
  );
  console.log(`✅ ${bcolors.CYAN}Building docker container...`);
  const pwdStr = '${PWD}';
  services[protocol] = {
    build: {
      context: '.',
      dockerfile: 'Dockerfile',
    },
    platform: 'linux/x86_64',
    container_name: protocol,
    ports: [
      `${rpcPublic}:${rpcPublic}`,
      `${rpcAdmin}:${rpcAdmin}`,
      `${wsPublic}:${wsPublic}`,
      `${wsAdmin}:${wsAdmin}`,
      `${peer}:${peer}`,
    ],
    volumes: [
      `${pwdStr}/${protocol}/config:/etc/opt/ripple`,
      `${pwdStr}/${protocol}/log:/var/log/rippled`,
      `${pwdStr}/${protocol}/lib:/var/lib/rippled`,
    ],
    networks: ['standalone-network'],
  };
}

export async function createStandaloneBinary(
  logLevel: string,
  publicKey: string,
  importKey: string,
  protocol: string,
  netType: string,
  networkId: number,
  buildServer: string,
  buildVersion: string,
  addIpfs = false
) {
  const name = buildVersion;
  fs.mkdirSync(`${basedir}/${protocol}-${name}`, { recursive: true });
  const owner = 'Xahau';
  const repo = 'xahaud';
  const commitHash = await getCommitHashFromServerVersion(buildServer, buildVersion);
  const content = await downloadFileAtCommitOrTag(
    owner,
    repo,
    commitHash,
    'src/ripple/protocol/impl/Feature.cpp'
  );
  const url = `${buildServer}/${buildVersion}`;
  await downloadBinary(url, `${basedir}/${protocol}-${name}/rippled.${name}`);
  const image = 'ubuntu:jammy';
  await createBinaryFolder(
    true,
    name,
    image,
    content,
    networkId,
    publicKey,
    importKey,
    protocol,
    netType,
    logLevel
  );
  services['explorer'] = {
    image: 'transia/explorer:latest',
    container_name: 'explorer',
    environment: [
      'PORT=4000',
      `VUE_APP_WSS_ENDPOINT=ws://0.0.0.0:${6006}`,
    ],
    ports: ['4000:4000'],
    networks: ['standalone-network'],
  };

  if (addIpfs) {
    const pwdStr = '${PWD}';
    services['ipfs'] = {
      image: 'ipfs/go-ipfs:latest',
      container_name: 'ipfs',
      environment: [
        'IPFS_PROFILE=server',
      ],
      ports: ['4001:4001', '5001:5001', '8080:8080'],
      volumes: [
        `${pwdStr}/${protocol}/ipfs_staging:/export`,
        `${pwdStr}/${protocol}/ipfs_data:/data/ipfs`,
      ],
      networks: ['standalone-network'],
    };
  }

  const compose = {
    version: '3.9',
    services: services,
    networks: { 'standalone-network': { driver: 'bridge' } },
  };

  fs.writeFileSync(`${basedir}/${protocol}-${name}/docker-compose.yml`, yaml.dump(compose));

  fs.writeFileSync(
    `${basedir}/${protocol}-${name}/start.sh`,
    `\
#! /bin/bash
docker compose -f ${basedir}/${protocol}-${name}/docker-compose.yml up --build --force-recreate -d
`
  );
  fs.chmodSync(`${basedir}/${protocol}-${name}/start.sh`, 0o755);
  const stopShContent = updateStopSh(protocol, name, 0, 0, true);
  fs.writeFileSync(`${basedir}/${protocol}-${name}/stop.sh`, stopShContent);
  fs.chmodSync(`${basedir}/${protocol}-${name}/stop.sh`, 0o755);
}

async function createLocalFolder(
  name: string,
  networkId: number,
  vlKey: string,
  ivlKey: string,
  protocol: string,
  netType: string,
  logLevel: string
) {
  const cfgPath = 'config';
  const [rpcPublic, rpcAdmin, wsPublic, wsAdmin, peer] = generatePorts(0, 'standalone');
  const vlConfig = await generateValidatorConfig(protocol, netType);

  if (networkId) {
    vlConfig.network_id = networkId;
  }

  if (vlKey) {
    vlConfig.validator_list_keys = [vlKey];
  }

  if (ivlKey) {
    vlConfig.import_vl_keys = [ivlKey];
  }

  const configs: RippledBuild[] = genConfig(
    false,
    protocol,
    name,
    vlConfig.network_id,
    0,
    rpcPublic,
    rpcAdmin,
    wsPublic,
    wsAdmin,
    peer,
    'huge',
    10000,
    'db/nudb',
    'db',
    'debug.log',
    logLevel,
    null,
    [],
    vlConfig.validator_list_sites,
    vlConfig.validator_list_keys,
    protocol === 'xahau' ? vlConfig.import_vl_keys! : [],
    vlConfig.ips,
    vlConfig.ips_fixed
  );
  fs.mkdirSync(cfgPath, { recursive: true });
  saveLocalConfig(cfgPath, configs[0].data, configs[1].data);
  console.log(`✅ ${bcolors.CYAN}Creating config`);

  const content = getFeatureLinesFromPath('../src/ripple/protocol/impl/Feature.cpp');
  const featuresJson = parseRippledAmendments(content);
  const genesisJson = await updateAmendments(featuresJson, protocol);
  fs.writeFileSync(
    `${cfgPath}/genesis.json`,
    JSON.stringify(genesisJson, null, 4)
  );
  console.log(`✅ ${bcolors.CYAN}Updating features`);
}

export async function startLocal(
  logLevel: string,
  publicKey: string,
  importKey: string,
  protocol: string,
  netType: string,
  networkId: number
) {
  const name = 'local';
  fs.mkdirSync(`${basedir}/${protocol}-${name}`, { recursive: true });
  await createLocalFolder(
    name,
    networkId,
    publicKey,
    importKey,
    protocol,
    netType,
    logLevel
  );
  services['explorer'] = {
    image: 'transia/explorer:latest',
    container_name: 'explorer',
    environment: [
      'PORT=4000',
      `VUE_APP_WSS_ENDPOINT=ws://0.0.0.0:${6006}`,
    ],
    ports: ['4000:4000'],
    networks: ['standalone-network'],
  };

  const compose = {
    version: '3.9',
    services: services,
    networks: { 'standalone-network': { driver: 'bridge' } },
  };

  fs.writeFileSync('docker-compose.yml', yaml.dump(compose));

  fs.writeFileSync(
    'start.sh',
    `\
#! /bin/bash
docker-compose.yml up --build --force-recreate -d
./rippled ${netType === 'standalone' ? '-a' : ''} --conf config/rippled.cfg --ledgerfile config/genesis.json
`
  );
  fs.chmodSync('start.sh', 0o755);
  const stopShContent = updateStopSh(protocol, name, 0, 0, false, true);
  fs.writeFileSync('stop.sh', stopShContent);
  fs.chmodSync('stop.sh', 0o755);
  try {
    const result = child_process.spawnSync('./start.sh', {});
    if (result.status === 0) {
      console.log(
        `${bcolors.CYAN}${protocol.charAt(0).toUpperCase() + protocol.slice(1)} local running at: ${bcolors.PURPLE}6006 ${bcolors.END}`
      );
      console.log(`${bcolors.CYAN}Explorer running / starting container${bcolors.END}`);
      console.log(`Listening at: ${bcolors.PURPLE}http://localhost:4000${bcolors.END}`);
    } else {
      console.error(`${bcolors.RED}ERROR${bcolors.END}`);
      process.exit(1);
    }
  } catch (error) {
    console.error(
      `${bcolors.RED}❌ Cannot connect to the Docker daemon at docker.sock.Is the docker daemon running ? ${bcolors.END}`
    );
    process.exit(1);
  }
}
