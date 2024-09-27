#!/usr/bin/env node

import * as fs from 'node:fs'
import * as path from 'node:path'
import * as util from 'node:util'
import * as yaml from 'js-yaml'
import { bcolors } from './misc'

const writeFile = util.promisify(fs.writeFile)
const chmod = util.promisify(fs.chmod)

export class DockerVars {
  ssh_port: number
  ws_port: number
  peer_port: number
  image_name: string
  container_name: string
  container_ports: number[]
  docker_volumes: string[]
  volumes: string[]

  constructor(
    ssh_port: number,
    ws_port: number,
    peer_port: number,
    image_name: string,
    container_name: string,
    container_ports: number[],
    docker_volumes: string[],
    volumes: string[],
  ) {
    this.ssh_port = ssh_port
    this.ws_port = ws_port
    this.peer_port = peer_port
    this.image_name = image_name
    this.container_name = container_name
    this.container_ports = container_ports
    this.docker_volumes = docker_volumes
    this.volumes = volumes
  }

  toDict(): object {
    return {
      ssh_port: this.ssh_port,
      ws_port: this.ws_port,
      peer_port: this.peer_port,
      docker_image_name: this.image_name,
      docker_container_name: this.container_name,
      docker_container_ports: this.container_ports,
      docker_volumes: this.docker_volumes,
      volumes: this.volumes,
    }
  }
}

export async function createAnsibleVarsFile(dirPath: string, ip: string, vars: DockerVars): Promise<DockerVars> {
  const filePath = path.join(dirPath, `${ip}.yml`)
  const yamlStr = yaml.dump(vars.toDict(), { indent: 4 })
  await writeFile(filePath, yamlStr, 'utf8')
  return vars
}

export function createDockerfile(
  binary: boolean,
  version: string,
  image_name: string,
  rpc_public_port: number,
  rpc_admin_port: number,
  ws_public_port: number,
  ws_admin_port: number,
  peer_port: number,
  include_genesis = false,
  quorum: number | null = null,
  standalone: string | null = null,
): string {
  let dockerfile = `
    FROM ${image_name} as base

    WORKDIR /app

    LABEL maintainer="dangell@transia.co"

    RUN export LANGUAGE=C.UTF-8; export LANG=C.UTF-8; export LC_ALL=C.UTF-8; export DEBIAN_FRONTEND=noninteractive

    COPY config /config
    COPY entrypoint /entrypoint.sh
    `

  if (include_genesis) {
    dockerfile += 'COPY genesis.json /genesis.json\n'
  }

  if (binary) {
    dockerfile += `COPY rippled.${version} /app/rippled\n`
  }

  dockerfile += `
    RUN chmod +x /entrypoint.sh && \
        echo '#!/bin/bash' > /usr/bin/server_info && \
        echo '/entrypoint.sh server_info' >> /usr/bin/server_info && \
        chmod +x /usr/bin/server_info

    EXPOSE ${rpc_public_port} ${rpc_admin_port} ${ws_public_port} ${ws_admin_port} ${peer_port} ${peer_port}/udp
    `

  if (include_genesis) {
    dockerfile += `ENTRYPOINT [ "/entrypoint.sh", "/genesis.json", "${quorum || ''}", "${standalone}" ]`
  } else {
    dockerfile += 'ENTRYPOINT [ "/entrypoint.sh" ]'
  }

  return dockerfile
}

export async function downloadBinary(url: string, savePath: string): Promise<void> {
  const version = url.split('/').pop()
  console.log(`${bcolors.END}Fetching versions of xahaud..`)
  if (fs.existsSync(savePath)) {
    console.log(`${bcolors.GREEN}version: ${bcolors.BLUE}${version} ${bcolors.END}already exists...`)
    await chmod(savePath, 0o755)
    return
  }

  try {
    console.log(`${bcolors.GREEN}Found latest version: ${bcolors.BLUE}${version}, downloading...`)

    const response = await fetch(url)
    if (!response.ok) {
      throw new Error(`Failed to download binary: ${response.status}`)
    }

    if (response.status !== 200) {
      throw new Error(`Failed to download binary: ${response.status}`)
    }
    const arrayBuffer = await response.arrayBuffer()
    const buffer = Buffer.from(arrayBuffer)
    await writeFile(savePath, buffer)
    await chmod(savePath, 0o755)
  } catch (error) {
    console.log(`${bcolors.GREEN}An error occurred: ${error}`)
  }
}

export async function updateDockerfile(buildVersion: string, savePath: string): Promise<void> {
  const data = await fs.promises.readFile(savePath, 'utf8')
  const lines = data.split('\n')
  const pattern = /^COPY rippled.* \/app\/rippled$/

  const updatedLines = lines.map((line) => (pattern.test(line) ? `COPY rippled.${buildVersion} /app/rippled` : line))

  await writeFile(savePath, updatedLines.join('\n'), 'utf8')
  console.log(`Dockerfile has been updated with the new rippled version: ${buildVersion}`)
}
