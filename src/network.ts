import * as fs from 'fs';
import * as path from 'path';
import * as yaml from 'js-yaml';
import * as dotenv from 'dotenv';
import { DockerVars, createDockerfile, downloadBinary, updateDockerfile, createAnsibleVarsFile } from './utils/deployKit';
import { genConfig, RippledBuild } from './rippled_cfg';
import { getCommitHashFromServerVersion, downloadFileAtCommitOrTag } from './libs/github';
import { downloadJson, parseImageName, runCommand, generatePorts, saveLocalConfig, getNodePort, sha512Half, runStop, removeDirectory, bcolors } from './utils/misc';
import { updateAmendments, parseRippledAmendments, getFeatureLinesFromContent } from './libs/rippled';
import { PublisherClient, ValidatorClient } from '@transia/xrpld-publisher';

dotenv.config();

const basedir = path.resolve(__dirname);

let deploykitPath: string = '';

interface Services {
  [key: string]: any;
}

const services: Services = {};

async function generateValidatorConfig(protocol: string, network: string) {
  try {
    const config = JSON.parse(fs.readFileSync(`${basedir}/deploykit/config.json`,'utf-8'));
    return config[protocol][network];
  } catch (e) {
    console.error(e);
    return null;
  }
}

async function createNodeFolders(
  binary: boolean,
  name: string,
  image: string,
  featureContent: string,
  numValidators: number,
  numPeers: number,
  networkId: number,
  enableAll: boolean,
  quorum: number | null,
  vlKey: string,
  ivlKey: string,
  protocol: string,
  ansible: boolean = false,
  ips: string[] = [],
  logLevel: string = 'warning',
) {
  const ipsFixed: string[] = [];
  for (let i = 1; i <= numValidators; i++) {
    const ipsDir = ansible ? ips[i - 1] : `vnode${i}`;
    const [, , , , peer] = generatePorts(i, 'validator');
    ipsFixed.push(`${ipsDir} ${peer}`);
  }

  const manifests: string[] = [];
  const validators: string[] = [];
  const tokens: string[] = [];
  for (let i = 1; i <= numValidators; i++) {
    const nodeDir = `vnode${i}`;
    const client = new ValidatorClient(nodeDir);
    client.createKeys();
    client.setDomain(`xahau.${nodeDir}.transia.co`);
    client.createToken();
    const keys = client.getKeys();
    const token = client.readToken();
    const manifest = client.readManifest();
    manifests.push(manifest);
    validators.push(keys.publicKey);
    tokens.push(token);
  }

  console.log(`✅ ${bcolors.CYAN}Created validator keys`);

  for (let i = 1; i <= numValidators; i++) {
    const ipsDir = ansible ? ips[i - 1] : `vnode${i}`;
    const nodeDir = `vnode${i}`;
    const cfgPath = `${basedir}/${name}-cluster/${nodeDir}/config`;
    const [rpcPublic, rpcAdmin, wsPublic, wsAdmin, peer] = generatePorts(i, 'validator');
    const configs: RippledBuild[] = genConfig(
      ansible,
      protocol,
      name,
      networkId,
      i,
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
      tokens[i - 1],
      validators.filter(v => v !== validators[i - 1]),
      ['http://vl/vl.json'],
      [vlKey],
      ivlKey ? [ivlKey] : [],
      [],
      ipsFixed.filter(ips => ips !== `${ipsDir} ${peer}`),
    );

    fs.mkdirSync(`${basedir}/${name}-cluster/${nodeDir}`, { recursive: true });
    fs.mkdirSync(`${basedir}/${name}-cluster/${nodeDir}/config`, { recursive: true });
    saveLocalConfig(cfgPath, configs[0].data, configs[1].data);

    console.log(`✅ ${bcolors.CYAN}Created validator: ${i} config`);

    let featuresJson: any = JSON.parse(fs.readFileSync(`${basedir}/default.${protocol}.features.json`,'utf-8'));

    if (enableAll) {
      if (protocol === 'xahau') {
        const lines: string[] = getFeatureLinesFromContent(featureContent);
        featuresJson = parseRippledAmendments(lines);
      } else if (protocol === 'xrpl') {
        featuresJson = await downloadJson(featureContent, `${basedir}/${name}-cluster`);
      }
    }

    const genesisJson: any = await updateAmendments(featuresJson, protocol);
    fs.writeFileSync(
      `${basedir}/${name}-cluster/${nodeDir}/genesis.json`,
      JSON.stringify(genesisJson, null, 4),
    );

    fs.writeFileSync(
      `${basedir}/${name}-cluster/${nodeDir}/features.json`,
      JSON.stringify(featuresJson, null, 4),
    );

    console.log(`✅ ${bcolors.CYAN}Updated validator: ${i} features`);

    if (protocol === 'xahau') {
      fs.copyFileSync(
        `${basedir}/${name}-cluster/rippled.${name}`,
        `${basedir}/${name}-cluster/${nodeDir}/rippled.${name}`,
      );
      fs.chmodSync(`${basedir}/${name}-cluster/${nodeDir}/rippled.${name}`, 0o755);
    }

    const dockerfile: string = createDockerfile(
      binary && protocol === 'xahau',
      name,
      image,
      rpcPublic,
      rpcAdmin,
      wsPublic,
      wsAdmin,
      peer,
      true,
      quorum,
      '',
    );
    fs.writeFileSync(`${basedir}/${name}-cluster/${nodeDir}/Dockerfile`, dockerfile);

    fs.copyFileSync(
      `${basedir}/deploykit/${protocol}.entrypoint`,
      `${basedir}/${name}-cluster/${nodeDir}/entrypoint`,
    );

    console.log(`✅ ${bcolors.CYAN}Built validator: ${i} docker container...`);

    const pwdStr: string = basedir;
    services[`vnode${i}`] = {
      build: {
        context: `vnode${i}`,
        dockerfile: 'Dockerfile',
      },
      platform: 'linux/x86_64',
      container_name: `vnode${i}`,
      ports: [
        `${rpcPublic}:${rpcPublic}`,
        `${rpcAdmin}:${rpcAdmin}`,
        `${wsPublic}:${wsPublic}`,
        `${wsAdmin}:${wsAdmin}`,
        `${peer}:${peer}`,
      ],
      volumes: [
        `${pwdStr}/vnode${i}/log:/var/log/rippled`,
        `${pwdStr}/vnode${i}/lib:/var/lib/rippled`,
      ],
      networks: [`${name}-network`],
    };
  }

  for (let i = 1; i <= numPeers; i++) {
    const nodeDir = `pnode${i}`;
    const cfgPath = `${basedir}/${name}-cluster/${nodeDir}/config`;
    const [rpcPublic, rpcAdmin, wsPublic, wsAdmin, peer] = generatePorts(i, 'peer');
    const configs: RippledBuild[] = genConfig(
      ansible,
      protocol,
      name,
      networkId,
      i,
      rpcPublic,
      rpcAdmin,
      wsPublic,
      wsAdmin,
      peer,
      'huge',
      null,
      '/var/lib/rippled/db/nudb',
      '/var/lib/rippled/db',
      '/var/log/rippled/debug.log',
      logLevel,
      null,
      validators,
      ['http://vl/vl.json'],
      [vlKey],
      ivlKey ? [ivlKey] : [],
      [],
      ipsFixed,
    );

    fs.mkdirSync(`${basedir}/${name}-cluster/${nodeDir}`, { recursive: true });
    fs.mkdirSync(`${basedir}/${name}-cluster/${nodeDir}/config`, { recursive: true });
    saveLocalConfig(cfgPath, configs[0].data, configs[1].data);

    console.log(`✅ ${bcolors.CYAN}Created peer: ${i} config`);

    let featuresJson: any = JSON.parse(fs.readFileSync(`${basedir}/default.xahau.features.json`,'utf-8'));

    if (enableAll) {
      if (protocol === 'xahau') {
        const lines: string[] = getFeatureLinesFromContent(featureContent);
        featuresJson = parseRippledAmendments(lines);
      } else if (protocol === 'xrpl') {
        featuresJson = await downloadJson(featureContent, `${basedir}/${name}-cluster`);
      }
    }

    const genesisJson: any = await updateAmendments(featuresJson, protocol);
    fs.writeFileSync(
      `${basedir}/${name}-cluster/${nodeDir}/genesis.json`,
      JSON.stringify(genesisJson, null, 4),
    );

    fs.writeFileSync(
      `${basedir}/${name}-cluster/${nodeDir}/features.json`,
      JSON.stringify(featuresJson, null, 4),
    );

    console.log(`✅ ${bcolors.CYAN}Updated peer: ${i} features`);

    if (protocol === 'xahau') {
      fs.copyFileSync(
        `${basedir}/${name}-cluster/rippled.${name}`,
        `${basedir}/${name}-cluster/${nodeDir}/rippled.${name}`,
      );
      fs.chmodSync(`${basedir}/${name}-cluster/${nodeDir}/rippled.${name}`, 0o755);
    }

    const dockerfile: string = createDockerfile(
      binary && protocol === 'xahau',
      name,
      image,
      rpcPublic,
      rpcAdmin,
      wsPublic,
      wsAdmin,
      peer,
      true,
      quorum,
      '',
    );
    fs.writeFileSync(`${basedir}/${name}-cluster/${nodeDir}/Dockerfile`, dockerfile);

    fs.copyFileSync(
      `${basedir}/deploykit/${protocol}.entrypoint`,
      `${basedir}/${name}-cluster/${nodeDir}/entrypoint`,
    );

    console.log(`✅ ${bcolors.CYAN}Built peer: ${i} docker container...`);

    const pwdStr: string = basedir;
    services[`pnode${i}`] = {
      build: {
        context: `pnode${i}`,
        dockerfile: 'Dockerfile',
      },
      platform: 'linux/x86_64',
      container_name: `pnode${i}`,
      ports: [
        `${rpcPublic}:${rpcPublic}`,
        `${rpcAdmin}:${rpcAdmin}`,
        `${wsPublic}:${wsPublic}`,
        `${wsAdmin}:${wsAdmin}`,
        `${peer}:${peer}`,
      ],
      volumes: [
        `${pwdStr}/pnode${i}/log:/var/log/rippled`,
        `${pwdStr}/pnode${i}/lib:/var/lib/rippled`,
      ],
      networks: [`${name}-network`],
    };
  }

  return manifests;
}

function updateStopSh(
  protocol: string,
  name: string,
  numValidators: number,
  numPeers: number,
  standalone: boolean = false,
  local: boolean = false,
): string {
  let stopShContent = `#! /bin/bash\nREMOVE_FLAG=false \n`;
  stopShContent += `
for arg in "$@"; do
  if [ "$arg" == "--remove" ]; then
    REMOVE_FLAG=true
    break
  fi
done
`;
  stopShContent += '\nif [ "$REMOVE_FLAG" = true ]; then \n';
  if (numValidators > 0 && numPeers > 0) {
    stopShContent += `docker compose -f ${basedir}/${name}-cluster/docker-compose.yml down --remove-orphans\n`;
  }

  for (let i = 1; i <= numValidators; i++) {
    stopShContent += `rm -r ${basedir}/${name}-cluster/vnode${i}/lib\n`;
    stopShContent += `rm -r ${basedir}/${name}-cluster/vnode${i}/log\n`;
  }

  for (let i = 1; i <= numPeers; i++) {
    stopShContent += `rm -r ${basedir}/${name}-cluster/pnode${i}/lib\n`;
    stopShContent += `rm -r ${basedir}/${name}-cluster/pnode${i}/log\n`;
  }

  if (standalone) {
    stopShContent += `docker compose -f ${basedir}/${protocol}-${name}/docker-compose.yml down --remove-orphans\n`;
    stopShContent += `rm -r ${protocol}/config\n`;
    stopShContent += `rm -r ${protocol}/lib\n`;
    stopShContent += `rm -r ${protocol}/log\n`;
    stopShContent += `rm -r ${protocol}\n`;
  }

  if (local) {
    stopShContent = `#! /bin/bash\ndocker compose -f docker-compose.yml down --remove-orphans\n`;
    stopShContent += `rm -r db\n`;
    stopShContent += `rm -r debug.log\n`;
  }

  stopShContent += 'fi \n';
  return stopShContent;
}

export async function createNetwork(
  logLevel: string,
  importKey: string,
  protocol: string,
  numValidators: number,
  numPeers: number,
  networkId: number,
  buildServer: string,
  buildVersion: string,
  genesis: boolean = false,
  quorum: number | null = null,
): Promise<void> {
  let name: string;
  let image: string;
  let content: string;

  if (protocol === 'xahau') {
    name = buildVersion;
    fs.mkdirSync(`${basedir}/${name}-cluster`, { recursive: true });
    const owner = 'Xahau';
    const repo = 'xahaud';
    const commitHash = await getCommitHashFromServerVersion(buildServer, buildVersion);
    content = await downloadFileAtCommitOrTag(owner, repo, commitHash, 'src/ripple/protocol/impl/Feature.cpp');
    const url = `${buildServer}/${buildVersion}`;
    await downloadBinary(url, `${basedir}/${name}-cluster/rippled.${buildVersion}`);
    image = 'ubuntu:jammy';
  } else if (protocol === 'xrpl') {
    name = buildVersion.replace(':', '-');
    fs.mkdirSync(`${basedir}/${name}-cluster`, { recursive: true });
    const [imageName, version] = parseImageName(buildVersion);
    const rootUrl = 'https://storage.googleapis.com/thelab-builds/';
    content = `${rootUrl}${imageName.split('-')[0]}/${imageName.split('-')[1]}/${version}/features.json`;
    image = `${buildServer}/${buildVersion}`;
  } else {
    throw new Error('Invalid protocol');
  }

  const client = new PublisherClient();
  client.createKeys();
  const keys = client.getKeys();
  const manifests = await createNodeFolders(
    true,
    name,
    image,
    content,
    numValidators,
    numPeers,
    networkId,
    genesis,
    quorum,
    keys.publicKey,
    importKey,
    protocol,
    false,
    [],
    logLevel,
  );

  services['vl'] = {
    build: {
      context: 'vl',
      dockerfile: 'Dockerfile',
    },
    container_name: 'vl',
    ports: ['80:80'],
    networks: [`${name}-network`],
  };

  services['network-explorer'] = {
    image: 'transia/explorer-main:latest',
    container_name: 'network-explorer',
    environment: [
      'PORT=4000',
      `VUE_APP_WSS_ENDPOINT=ws://0.0.0.0:${6006}`,
    ],
    ports: ['4000:4000'],
    networks: [`${name}-network`],
  };

  const compose = {
    version: '3.9',
    services,
    networks: { [`${name}-network`]: { driver: 'bridge' } },
  };
  fs.writeFileSync(`${basedir}/${name}-cluster/docker-compose.yml`, yaml.dump(compose, { noRefs: true }));

  fs.writeFileSync(
    `${basedir}/${name}-cluster/start.sh`,
    `#! /bin/bash\ndocker compose -f ${basedir}/${name}-cluster/docker-compose.yml up --build --force-recreate -d\n`,
  );
  const stopShContent = updateStopSh(protocol, name, numValidators, numPeers);
  fs.writeFileSync(`${basedir}/${name}-cluster/stop.sh`, stopShContent);

  fs.mkdirSync(`${basedir}/${name}-cluster/vl`, { recursive: true });
  for (const manifest of manifests) {
    client.addValidator(manifest);
  }
  client.signUnl(`${basedir}/${name}-cluster/vl/vl.json`);
  fs.copyFileSync(
    `${basedir}/deploykit/nginx.dockerfile`,
    `${basedir}/${name}-cluster/vl/Dockerfile`,
  );

  fs.chmodSync(`${basedir}/${name}-cluster/start.sh`, 0o755);
  fs.chmodSync(`${basedir}/${name}-cluster/stop.sh`, 0o755);
}

export async function updateNodeBinary(
  name: string,
  nodeId: string,
  nodeType: string,
  buildServer: string,
  newVersion: string,
): Promise<void> {
  const nodeDir = `${nodeType === 'validator' ? 'v' : 'p'}node${nodeId}`;
  runCommand(`${basedir}/${name}`, `docker-compose stop ${nodeDir}`);
  const url = `${buildServer}/${newVersion}`;
  await downloadBinary(url, `${basedir}/${name}/rippled.${newVersion}`);
  fs.copyFileSync(
    `${basedir}/${name}/rippled.${newVersion}`,
    `${basedir}/${name}/${nodeDir}/rippled.${newVersion}`,
  );
  fs.chmodSync(`${basedir}/${name}/${nodeDir}/rippled.${newVersion}`, 0o755);
  await updateDockerfile(newVersion, `${basedir}/${name}/${nodeDir}/Dockerfile`);
  runCommand(
    `${basedir}/${name}`,
    `docker compose up --build --force-recreate -d ${nodeDir}`,
  );
}

export async function enableNodeAmendment(
  name: string,
  amendmentName: string,
  nodeId: string,
  nodeType: string,
): Promise<void> {
  const amendmentHash = sha512Half(Buffer.from(amendmentName, 'utf-8').toString('hex'));
  const command = {
    method: 'feature',
    params: [
      {
        feature: amendmentHash,
        vetoed: false,
      },
    ],
  };
  const port = getNodePort(parseInt(nodeId), nodeType);
  const jsonStr = JSON.stringify(command);
  const escapedStr = jsonStr.replace(/"/g, '\\"');
  const curlCommand = `curl -X POST -H "Content-Type: application/json" -d "${escapedStr}" http://localhost:${port}`;
  runCommand(`${basedir}/${name}`, curlCommand);
}

async function createAnsible(
  logLevel: string,
  importKey: string,
  protocol: string,
  numValidators: number,
  numPeers: number,
  networkId: number,
  buildServer: string,
  buildVersion: string,
  genesis: boolean = false,
  quorum: number | null = null,
  vips: string[] = [],
  pips: string[] = [],
): Promise<void> {
  let name: string = '';
  let image: string = '';
  let content: string = '';

  if (protocol === 'xahau') {
    name = buildVersion;
    fs.mkdirSync(`${basedir}/${name}-cluster`, { recursive: true });
    const owner = 'Xahau';
    const repo = 'xahaud';
    const commitHash = await getCommitHashFromServerVersion(buildServer, buildVersion);
    content = await downloadFileAtCommitOrTag(owner, repo, commitHash, 'src/ripple/protocol/impl/Feature.cpp');
    const url = `${buildServer}/${buildVersion}`;
    await downloadBinary(url, `${basedir}/${name}-cluster/rippled.${buildVersion}`);
    image = 'ubuntu:jammy';
  }

  const client = new PublisherClient();
  client.createKeys();
  const keys = client.getKeys();
  const manifests = await createNodeFolders(
    true,
    name,
    image,
    content,
    numValidators,
    numPeers,
    networkId,
    genesis,
    quorum,
    keys.publicKey,
    importKey,
    protocol,
    true,
    vips,
    logLevel,
  );

  services['vl'] = {
    build: {
      context: 'vl',
      dockerfile: 'Dockerfile',
    },
    container_name: 'vl',
    ports: ['80:80'],
    networks: [`${name}-network`],
  };

  services['network-explorer'] = {
    image: 'transia/explorer-main:latest',
    container_name: 'network-explorer',
    environment: [
      'PORT=4000',
    ],
    ports: ['4000:4000'],
    networks: [`${name}-network`],
  };

  const compose = {
    version: '3.9',
    services,
    networks: { [`${name}-network`]: { driver: 'bridge' } },
  };
  fs.writeFileSync(`${basedir}/${name}-cluster/docker-compose.yml`, yaml.dump(compose, { noRefs: true }));

  fs.writeFileSync(
    `${basedir}/${name}-cluster/start.sh`,
    `#! /bin/bash\ndocker compose -f ${basedir}/${name}-cluster/docker-compose.yml up --build --force-recreate -d\n`,
  );
  const stopShContent = updateStopSh(protocol, name, numValidators, numPeers);
  fs.writeFileSync(`${basedir}/${name}-cluster/stop.sh`, stopShContent);

  fs.mkdirSync(`${basedir}/${name}-cluster/vl`, { recursive: true });
  for (const manifest of manifests) {
    client.addValidator(manifest);
  }
  client.signUnl(`${basedir}/${name}-cluster/vl/vl.json`);
  fs.copyFileSync(
    `${basedir}/deploykit/nginx.dockerfile`,
    `${basedir}/${name}-cluster/vl/Dockerfile`,
  );

  fs.chmodSync(`${basedir}/${name}-cluster/start.sh`, 0o755);
  fs.chmodSync(`${basedir}/${name}-cluster/stop.sh`, 0o755);

  fs.mkdirSync(`${basedir}/${name}-cluster/ansible`, { recursive: true });
  fs.mkdirSync(`${basedir}/${name}-cluster/ansible/host_vars`, { recursive: true });
  fs.cpSync(
    `${basedir}/deploykit/ansible`,
    `${basedir}/${name}-cluster/ansible`,
    { recursive: true },
  );

  const imageName = buildVersion.replace(/[-+]/g, '.');
  const sshPort = parseInt(process.env.SSH_PORT || '20');
  for (const [key, value] of Object.entries(services)) {
    if (key.startsWith('vnode')) {
      const index = parseInt(key.slice(5));
      const cName = value.container_name;
      const ports = value.ports;
      const vars = new DockerVars(
        sshPort,
        parseInt(ports[2].split(':')[1]),
        parseInt(ports[4].split(':')[1]),
        `transia/cluster-${cName}:${imageName}`,
        cName,
        ports,
        [
          '/var/log/rippled:/var/log/rippled',
          '/var/lib/rippled:/var/lib/rippled',
        ],
        ['/var/log/rippled', '/var/lib/rippled'],
      );
      await createAnsibleVarsFile(
        `${basedir}/${name}-cluster/ansible/host_vars`, vips[index - 1], vars
      );
      runCommand(
        `${basedir}/${name}-cluster/${cName}`,
        `docker build -f Dockerfile --platform linux/x86_64 --tag transia/cluster-${cName}:${imageName} .`,
      );
      runCommand(
        `${basedir}/${name}-cluster/${cName}`,
        `docker push transia/cluster-${cName}:${imageName}`,
      );
    } else if (key.startsWith('pnode')) {
      const index = parseInt(key.slice(5));
      const cName = value.container_name;
      const ports = value.ports;
      const vars = new DockerVars(
        sshPort,
        parseInt(ports[2].split(':')[1]),
        parseInt(ports[4].split(':')[1]),
        `transia/cluster-${cName}:${imageName}`,
        cName,
        ports,
        [
          '/var/log/rippled:/var/log/rippled',
          '/var/lib/rippled:/var/lib/rippled',
        ],
        ['/var/log/rippled', '/var/lib/rippled'],
      );
      createAnsibleVarsFile(
        `${basedir}/${name}-cluster/ansible/host_vars`, pips[index - 1], vars
      );
      runCommand(
        `${basedir}/${name}-cluster/${cName}`,
        `docker build -f Dockerfile --platform linux/x86_64 --tag transia/cluster-${cName}:${imageName} .`,
      );
      runCommand(
        `${basedir}/${name}-cluster/${cName}`,
        `docker push transia/cluster-${cName}:${imageName}`,
      );
    }
  }

  let hostsContent = `
# this is a basic file putting different hosts into categories
# used by ansible to determine which actions to run on which hosts
[all]
    `;
  const ssh = process.env.SSH_PORT || '20';
  const user = process.env.SSH_USER || 'ubuntu';
  const sshKey = process.env.SSH_PATH || '~/.ssh/id_rsa';
  for (const vip of vips) {
    hostsContent += `${vip} ansible_port=${ssh} ansible_user=${user} ansible_ssh_private_key_file=${sshKey} vars_file=host_vars/${vip}.yml \n`;
  }
  for (const pip of pips) {
    hostsContent += `${pip} ansible_port=${ssh} ansible_user=${user} ansible_ssh_private_key_file=${sshKey} vars_file=host_vars/${pip}.yml \n`;
  }
  fs.writeFileSync(`${basedir}/${name}-cluster/ansible/hosts.txt`, hostsContent);
}

function stopNetwork(name: string, remove: boolean = false) {
  const cmd = [`${basedir}/${name}/stop.sh`];
  if (remove) {
    cmd.push('--remove');
  }
  runStop(cmd);
}

function removeNetwork(name: string) {
  stopNetwork(name, true);
  removeDirectory(`${basedir}/${name}`);
}
