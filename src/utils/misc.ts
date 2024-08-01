import * as fs from 'fs';
import * as path from 'path';
import * as https from 'https';
import * as child_process from 'child_process';
import * as shlex from 'shlex';
import * as crypto from 'crypto';

export class bcolors {
  static RED = "\x1b[31m";
  static GREEN = "\x1b[32m";
  static BLUE = "\x1b[34m";
  static PURPLE = "\x1b[35m";
  static CYAN = "\x1b[36m";
  static END = "\x1b[0m";
}

export function removeDirectory(directoryPath: string): void {
  try {
    const name: string = path.basename(directoryPath);
    fs.rmdirSync(directoryPath, { recursive: true });
    console.log(`${bcolors.CYAN}Directory ${name} has been removed successfully. ${bcolors.END}`);
  } catch (error) {
    if (error.code === 'ENOENT') {
      console.log(`${bcolors.RED}❌ The file ${directoryPath} does not exist or cannot be found.${bcolors.END}`);
    } else if (error.code === 'EACCES') {
      console.log(`${bcolors.RED}❌ Permission denied: Unable to remove '${directoryPath}'.`);
    } else {
      console.log(`${bcolors.RED}❌ An OS error occurred: ${error.message}.${bcolors.END}`);
    }
  }
}

export function runStart(cmd: string[], protocol: string, version: string, type: string): void {
  try {
    const result = child_process.spawnSync(cmd[0], cmd.slice(1), { });
    if (result.status === 0) {
      console.log(`${bcolors.CYAN}${protocol.charAt(0).toUpperCase() + protocol.slice(1)} ${bcolors.GREEN}${version} ${type} running at: ${bcolors.PURPLE}6006 ${bcolors.END}`);
      console.log(`${bcolors.CYAN}Explorer running / starting container${bcolors.END}`);
      console.log(`Listening at: ${bcolors.PURPLE}http://localhost:4000${bcolors.END}`);
    } else {
      console.error(`${bcolors.RED}ERROR${bcolors.END}`);
      process.exit(1);
    }
  } catch (error) {
    if (error.code === 'ENOENT') {
      console.log(`${bcolors.RED}❌ The file ${cmd[0]} does not exist or cannot be found.`);
    } else {
      console.log(`${bcolors.RED}❌ An OS error occurred: ${error.message}`);
    }
    process.exit(1);
  }
}

export function runStop(cmd: string[]): void {
  try {
    const result = child_process.spawnSync(cmd[0], cmd.slice(1));
    if (result.status === 0) {
      console.log(`${bcolors.CYAN}shut down docker container ${bcolors.END}`);
    } else {
      console.error(`${bcolors.RED}ERROR${bcolors.END}`);
      process.exit(1);
    }
  } catch (error) {
    if (error.code === 'ENOENT') {
      console.log(`${bcolors.RED}❌ The file ${cmd[0]} does not exist or cannot be found.`);
    } else {
      console.log(`${bcolors.RED}❌ An OS error occurred: ${error.message}`);
    }
    process.exit(1);
  }
}

function isContainerRunning(containerName: string): boolean {
  const result = child_process.spawnSync('docker', ['inspect', containerName], { encoding: 'utf-8' });
  return result.stdout.includes('Hostname');
}

export function runLogs(): void {
  try {
    const containerName = "xahau";
    if (isContainerRunning(containerName)) {
      console.clear();
      console.log();
      console.log(`${bcolors.GREEN}Starting live log monitor, edit with ${bcolors.PURPLE}CTRL + C${bcolors.END}`);
      console.log();
      const logCommand = `docker logs --tail 20 -f ${containerName} 2>&1 | grep -E --color=always 'HookTrace|HookError|Publishing ledger [0-9]+'`;
      child_process.execSync(logCommand, { stdio: 'inherit' });
    } else {
      console.log();
      console.log(`${bcolors.RED}Cannot watch live logs, container not running. Run ${bcolors.PURPLE}./install${bcolors.RED} script${bcolors.END}`);
      console.log();
    }
  } catch (error) {
    return;
  }
}

export function checkDeps(cmd: string[]): void {
  try {
    console.log(bcolors.BLUE + "Checking dependencies: \n");
    const result = child_process.spawnSync(cmd[0], cmd.slice(1), { stdio: 'inherit' });
    if (result.status === 0) {
      console.log(`${bcolors.GREEN}Dependencies OK${bcolors.END}`);
    } else {
      console.log(`${bcolors.RED}Dependency ERROR${bcolors.END}`);
      process.exit(1);
    }
  } catch (error) {
    console.log(`${bcolors.RED}Dependency ERROR${bcolors.END}`);
    process.exit(1);
  }
}

export function removeContainers(cmd: string): void {
  try {
    const args = shlex.split(cmd);
    const result = child_process.spawnSync(args[0], args.slice(1), { stdio: 'pipe' });
    if (result.status === 0) {
      console.log(`${bcolors.GREEN}Docker Ready${bcolors.END}`);
    } else {
      console.log(`${bcolors.RED}Docker ERROR${bcolors.END}`);
    }
  } catch (error) {
    return;
  }
}

export function runCommand(dir: string, command: string): void {
  try {
    const args = shlex.split(command);
    const result = child_process.spawnSync(args[0], args.slice(1), { cwd: dir, stdio: 'pipe' });
    console.log(result.stdout.toString());
    if (result.stderr) {
      console.log(result.stderr.toString());
    }
    console.log(`Command '${command}' executed successfully.`);
  } catch (error) {
    console.log(`An error occurred while trying to run the command: ${error.message}`);
  }
}

export function downloadJson(url: string, destinationDir: string): Record<string, any> {
  fs.mkdirSync(destinationDir, { recursive: true });
  const fileName = path.basename(url);
  return new Promise((resolve, reject) => {
    https.get(url, (response) => {
      if (response.statusCode === 200) {
        let data = '';
        response.on('data', (chunk) => {
          data += chunk;
        });
        response.on('end', () => {
          const jsonData = JSON.parse(data);
          fs.writeFileSync(path.join(destinationDir, fileName), JSON.stringify(jsonData, null, 2));
          resolve(jsonData);
        });
      } else {
        reject(new Error(`Failed to download file from ${url}`));
      }
    }).on('error', (error) => {
      reject(error);
    });
  });
}

export function saveLocalConfig(cfgPath: string, cfgOut: string, validatorsOut: string): void {
  fs.writeFileSync(path.join(cfgPath, 'rippled.cfg'), cfgOut);
  fs.writeFileSync(path.join(cfgPath, 'validators.txt'), validatorsOut);
}

export function parseImageName(imageName: string): [string, string] {
  const [name, version] = imageName.split(':');
  return [name, version];
}

const RPC_PUBLIC = 5007;
const RPC_ADMIN = 5005;
const WS_PUBLIC = 6008;
const WS_ADMIN = 6006;
const PEER = 51235;

export function getNodePort(index: number, nodeType: string): number {
  if (nodeType === "validator") {
    return RPC_ADMIN + (index * 100);
  } else if (nodeType === "peer") {
    return RPC_ADMIN + (index * 10);
  }
  throw new Error("Invalid node type. Must be 'validator' or 'peer'.");
}

export function generatePorts(index: number, nodeType: string): [number, number, number, number, number] {
  let rpc_public, rpc_admin, ws_public, ws_admin, peer;
  if (nodeType === "validator") {
    rpc_public = RPC_PUBLIC + (index * 100);
    rpc_admin = RPC_ADMIN + (index * 100);
    ws_public = WS_PUBLIC + (index * 100);
    ws_admin = WS_ADMIN + (index * 100);
    peer = PEER + (index * 100);
  } else if (nodeType === "peer") {
    rpc_public = RPC_PUBLIC + (index * 10);
    rpc_admin = RPC_ADMIN + (index * 10);
    ws_public = WS_PUBLIC + (index * 10);
    ws_admin = WS_ADMIN + (index * 10);
    peer = PEER + (index * 10);
  } else if (nodeType === "standalone") {
    rpc_public = 5007;
    rpc_admin = 5005;
    ws_public = 6008;
    ws_admin = 6006;
    peer = PEER;
  } else {
    throw new Error("Invalid node type. Must be 'validator' or 'peer'.");
  }
  return [rpc_public, rpc_admin, ws_public, ws_admin, peer];
}

export function sha512Half(hexString: string): string {
  const hash = crypto.createHash('sha512');
  hash.update(Buffer.from(hexString, 'hex'));
  const fullDigest = hash.digest('hex').toUpperCase();
  const hashSize = fullDigest.length / 2;
  return fullDigest.slice(0, hashSize);
}
