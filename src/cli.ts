#!/usr/bin/env node

import * as path from 'node:path'
import { Command } from 'commander'
import { createStandaloneBinary, createStandaloneImage } from './main'
import { bcolors, checkDeps, removeContainers, removeDirectory, runLogs, runStart, runStop } from './utils/misc'

const basedir = process.cwd()
const srcdir = path.resolve(__dirname)

const XAHAU_RELEASE = '2024.4.21-release+858'
const XRPL_RELEASE = '2.0.0-b4'

const program = new Command()

program.description('A CLI to build xrpld standalone ledgers.').version('1.0.0')

// LOGS
program
  .command('logs:hooks')
  .description('Log Hooks')
  .action(() => runLogs())

// STANDALONE
program
  .command('up')
  .description('Up Standalone')
  .option('--log_level <level>', 'The log level', 'trace')
  .option('--build_type <type>', 'The build type', /^(image|binary)$/i, 'binary')
  .option(
    '--public_key <key>',
    'The public vl key',
    'ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501',
  )
  .option('--import_key <key>', 'The import vl key')
  .option('--protocol <protocol>', 'The protocol of the network', 'xahau')
  .option('--network_id <id>', 'The network id', '21339')
  .option('--server <server>', 'The build server for the network')
  .option('--build-version <version>', 'The build version for the network')
  .option('--ipfs', 'Add an IPFS server', false)
  .action(async (options) => {

    console.log('')
    console.log('   _  __ ____  ____  __    ____     _   __     __  ______          ')
    console.log('  | |/ // __ \\/ __ \\/ /   / __ \\   / | / /__  / /_/ ____/__  ____  ')
    console.log('  |   // /_/ / /_/ / /   / / / /  /  |/ / _ \\/ __/ / __/ _ \\/ __ \\ ')
    console.log(' /   |/ _, _/ ____/ /___/ /_/ /  / /|  /  __/ /_/ /_/ /  __/ / / / ')
    console.log('/_/|_/_/ |_/_/   /_____/_____/  /_/ |_|\\___/\\__/\\____/\\___/_/ /_/  ')
    console.log('')

    checkDeps([`${srcdir}/deploykit/prerequisites.sh`])

    console.log(`${bcolors.BLUE}Removing existing containers: ${bcolors.RED}`)
    removeContainers('docker stop xahau')
    removeContainers('docker rm xahau')
    removeContainers('docker stop explorer')
    removeContainers('docker rm explorer')
    removeContainers('docker stop xrpl')
    removeContainers('docker rm xrpl')

    const {
      log_level,
      build_type,
      public_key,
      import_key,
      protocol,
      network_id,
      server,
      buildVersion: version,
      ipfs,
    } = options

    let importKey: string = import_key
    let buildServer: string = server
    let buildType: string = build_type
    let buildVersion: string = version
    if (protocol === 'xahau') {
      importKey = import_key || 'ED74D4036C6591A4BDF9C54CEFA39B996A5DCE5F86D11FDA1874481CE9D5A1CDC1'
      buildServer = 'https://build.xahau.tech'
      buildType = 'binary'
      buildVersion = buildVersion || XAHAU_RELEASE
    }

    if (protocol === 'xrpl') {
      buildServer = 'rippleci'
      buildType = 'image'
      buildVersion = buildVersion || XRPL_RELEASE
    }

    console.log(`${bcolors.BLUE}Setting Up Standalone Network with the following parameters:${bcolors.END}`)
    console.log(`    - Log Level: ${log_level}`)
    console.log(`    - Build Type: ${buildType}`)
    console.log(`    - Public Key: ${public_key}`)
    console.log(`    - Import Key: ${importKey}`)
    console.log(`    - Protocol: ${protocol}`)
    console.log(`    - Network ID: ${network_id}`)
    console.log(`    - Build Server: ${buildServer}`)
    console.log(`    - Build Version: ${buildVersion}`)
    console.log(`    - IPFS Server: ${ipfs}`)

    if (buildType === 'image') {
      await createStandaloneImage(
        log_level,
        public_key,
        importKey,
        protocol,
        network_id,
        buildServer,
        buildVersion,
        ipfs,
      )
    } else if (buildType === 'binary') {
      await createStandaloneBinary(
        log_level,
        public_key,
        importKey,
        protocol,
        network_id,
        buildServer,
        buildVersion,
        ipfs,
      )
    } else {
      throw new Error('Invalid build type')
    }

    runStart([`${basedir}/${protocol}-${buildVersion}/start.sh`], protocol, buildVersion, 'standalone')
  })

program
  .command('down')
  .description('Down Standalone')
  .option('--name <name>', 'The name of the network')
  .option('--protocol <protocol>', 'The protocol of the network', 'xahau')
  .option('--build-version <version>', 'The build version for the network')
  .action((options) => {
    const { name, protocol, buildVersion: version } = options
    console.log(`${bcolors.BLUE}Taking Down Standalone Network with the following parameters:${bcolors.END}`)

    if (name) {
      console.log(`    - Network Name: ${name}`)
      runStop([`${basedir}/${name}/stop.sh`])
      removeDirectory(`${basedir}/${name}`)
      return
    }

    const buildVersion = protocol === 'xahau' && !version ? XAHAU_RELEASE : version || XRPL_RELEASE

    console.log(`    - Network Name: ${name}`)
    console.log(`    - Protocol: ${protocol}`)
    console.log(`    - Build Version: ${buildVersion}`)
    runStop([`${basedir}/${protocol}-${buildVersion}/stop.sh`])
  })

program.parse(process.argv)
