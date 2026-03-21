# XRPLD Network Generator CLI Documentation

## Overview

The XRPLD Network Generator CLI is a command-line interface tool designed to facilitate the creation, management, and interaction with XRPLD networks and standalone ledgers.

### What Does This Tool Do?

This tool creates **local Docker-based XRPLD networks** for testing and development purposes. Instead of spending hours building rippled from source inside Docker containers (which is slow), this tool:

1. Uses pre-built rippled binaries (downloaded or built locally on your Mac)
2. Creates a multi-node network with validators and peer nodes
3. Generates all necessary configuration files, validator keys, and UNL (Unique Node List)
4. Provides a docker-compose setup for easy network management
5. Includes a network explorer UI for monitoring your local network

This dramatically speeds up local development - you can build rippled natively on your Mac (which is fast), then deploy it to a Docker network in seconds.

### Key Features

- **Multi-Validator Networks**: Create Docker-based networks with configurable validators and peer nodes
- **Local Native Networks**: Run networks as native processes without Docker for faster development
- **Standalone Ledgers**: Quick single-node setup for testing and development
- **Version Management**: Update individual nodes to different versions for upgrade testing
- **Amendment Control**: Enable/disable amendments on specific nodes for feature testing
- **Protocol Support**: Full support for both XRPL and Xahau protocols
- **Database Options**: Choose between NuDB (persistent) and Memory (fast testing) databases
- **Network Explorer**: Built-in web UI for monitoring your local networks (port 4000)
- **IPFS Integration**: Optional IPFS server deployment with standalone ledgers
- **Custom Binaries**: Use locally built binaries instead of building in Docker
- **Genesis Mode**: Create genesis networks with custom amendment initialization
- **Flexible Configuration**: Configure quorum, network IDs, log levels, and more

### Current Versions

- XRPL: `3.1.1`
- Xahau: `2025.7.9-release+1951`

## Prerequisites

Before using the XRPLD Network Generator CLI, ensure that you have the following prerequisites installed:

- Python ^3.9.6
- Docker
- Git (for cloning the repository)

## Installation

To install the XRPLD Network Generator CLI, use pypi to install the package.

```bash
pip3 install xrpld-netgen --break-system-packages
```

Add/Make sure the path is in your profile

```bash
export PATH="/usr/local/bin:$PATH"
```

## Usage

The CLI provides several commands to manage XRPLD networks and standalone ledgers.

### Available Protocols

- `xrpl` - XRP Ledger protocol
- `xahau` - Xahau ledger protocol

## Commands

### Network Management Commands

#### Create a Multi-Validator Network

Create a Docker-based multi-validator network with custom configuration:

```bash
xrpld-netgen create:network [OPTIONS]
```

**Options:**
- `--protocol` - Protocol to use: "xrpl" or "xahau" (default: "xahau")
- `--num_validators` - Number of validator nodes (default: 3)
- `--num_peers` - Number of peer nodes (default: 1)
- `--build_version` - Specific version to deploy (optional)
- `--network_id` - Network identifier (default: 21339 for xahau, 21337 for xrpl)
- `--log_level` - Log level: "warning", "debug", "trace" (default: "trace")
- `--genesis` - Enable genesis mode (default: false)
- `--quorum` - Consensus quorum requirement (default: num_validators - 1)
- `--nodedb_type` - Database type: "Memory" or "NuDB" or "rwdb" (default: "NuDB")
- `--local` - Create local network without Docker (runs natively)
- `--binary_name` - Custom xrpld binary name (default: "xrpld")
- `--build_server` - Build server URL (auto-detected by protocol)

**Examples:**
```bash
# Create a 5-validator XRPL network
xrpld-netgen create:network --protocol xrpl --num_validators 5 --num_peers 2

# Create a Xahau network with specific version
xrpld-netgen create:network --protocol xahau --build_version 2025.7.9-release+1951

# Create a local network (no Docker, native processes)
xrpld-netgen create:network --protocol xahau --local

# Create with Memory database for faster testing
xrpld-netgen create:network --nodedb_type Memory
```

#### Start a Network

Start a previously created network:

```bash
xrpld-netgen up --name [NETWORK_NAME]
```

**Example:**
```bash
xrpld-netgen up --name xahau-2025.7.9-release+1951
```

#### Stop a Network

Stop a running network:

```bash
xrpld-netgen down --name [NETWORK_NAME]
```

#### Remove a Network

Completely remove a network and all its data:

```bash
xrpld-netgen remove --name [NETWORK_NAME]
```

#### Update a Node

Update a specific node to a different version:

```bash
xrpld-netgen update:node --name [NETWORK_NAME] --node_id [NODE_ID] --node_type [NODE_TYPE] --build_version [VERSION]
```

**Options:**
- `--name` - Network name (required)
- `--node_id` - Node identifier, e.g., "vnode1", "pnode1" (required)
- `--node_type` - "validator" or "peer" (required)
- `--build_version` - New version to update to (optional)
- `--build_server` - Build server URL (optional)

**Example:**
```bash
xrpld-netgen update:node --name xahau-2025.7.9 --node_id vnode1 --node_type validator --build_version 2025.7.10
```

#### Enable Amendment

Enable a specific amendment on a node:

```bash
xrpld-netgen enable:amendment --name [NETWORK_NAME] --amendment_name [AMENDMENT] --node_id [NODE_ID] --node_type [NODE_TYPE]
```

**Supported Amendments:**
Hooks, URIToken, Import, Remit, ZeroB2M, Clawback, fixXahauV1, fixNFTokenRemint, and 40+ more.

**Example:**
```bash
xrpld-netgen enable:amendment --name xahau-2025.7.9 --amendment_name Hooks --node_id vnode1 --node_type validator
```

---

### Local Network Commands

#### Start a Local Network

Create and start a network using native processes (no Docker):

```bash
xrpld-netgen up:local [OPTIONS]
```

**Options:**
- `--protocol` - Protocol: "xrpl" or "xahau" (default: "xahau")
- `--log_level` - Log level: "warning", "debug", "trace" (default: "trace")
- `--network_id` - Network identifier (default: 21339)
- `--nodedb_type` - Database type: "Memory" or "NuDB" or "rwdb" (default: "NuDB")
- `--public_key` - Validator list public key
- `--import_key` - Import validator list key

**Example:**
```bash
xrpld-netgen up:local --protocol xahau --nodedb_type Memory
```

#### View Local Network Logs

View logs from a local network:

```bash
xrpld-netgen logs:local [--node NODE_ID]
```

**Example:**
```bash
# View all logs
xrpld-netgen logs:local

# View specific node logs
xrpld-netgen logs:local --node vnode1
```

---

### Standalone Ledger Commands

#### Create a Standalone Ledger

Create and start a single-node standalone ledger:

```bash
xrpld-netgen up:standalone [OPTIONS]
```

**Options:**
- `--protocol` - Protocol: "xrpl" or "xahau" (default: "xahau")
- `--version` - Build version (optional, uses current release if omitted)
- `--build_type` - Build type: "image" or "binary" (default: "binary")
- `--log_level` - Log level: "warning", "debug", "trace" (default: "trace")
- `--network_id` - Network identifier (default: 21339 for xahau, 1 for xrpl)
- `--nodedb_type` - Database type: "Memory" or "NuDB" or "rwdb" (default: "NuDB")
- `--ipfs` - Include IPFS server in deployment (default: false)
- `--deploy` - Deploy as Docker image to registry (default: false)
- `--server` - Build server URL (optional)
- `--public_key` - Validator list public key
- `--import_key` - Import validator list key

**Examples:**
```bash
# Create standalone with current version
xrpld-netgen up:standalone --protocol xahau

# Create with specific version and IPFS
xrpld-netgen up:standalone --protocol xahau --version 2025.7.9-release+1951 --ipfs

# Create with Memory database for testing
xrpld-netgen up:standalone --protocol xrpl --nodedb_type Memory
```

#### Stop a Standalone Ledger

Stop and remove a standalone ledger:

```bash
xrpld-netgen down:standalone [OPTIONS]
```

**Options:**
- `--protocol` - Protocol: "xrpl" or "xahau" (default: "xahau")
- `--version` - Build version (optional)
- `--name` - Specific network name (optional)

**Example:**
```bash
xrpld-netgen down:standalone --protocol xahau --version 2025.7.9-release+1951
```

#### View Standalone Logs

View logs from a standalone ledger:

```bash
xrpld-netgen logs:standalone
```

---

## Additional Features

### Network Explorer UI

All networks (multi-validator, local, and standalone) automatically include a Network Explorer UI accessible at [http://localhost:4000](http://localhost:4000). This provides real-time monitoring of your local network.

### IPFS Integration

When using the `--ipfs` flag with standalone ledgers, an IPFS server is deployed with the following ports:
- **4001**: IPFS swarm port
- **5001**: IPFS API port
- **8080**: IPFS gateway port

### Database Options

Choose between two database types:
- **NuDB** (default): Persistent database, slower but preserves data
- **Memory**: In-memory database, faster for testing, data lost on restart

### Genesis Mode

Use the `--genesis` flag when creating networks to enable genesis mode, which affects how amendments are initialized.

### Custom Binaries

Use locally built xrpld binaries with the `--binary_name` option or by placing your binary in the expected location. This is significantly faster than building inside Docker containers.

## Support

For any issues or questions regarding the XRPLD Network Generator CLI, please refer to the repository's issue tracker or contact the maintainers.

## Contributing

To install the XRPLD Network Generator CLI, clone the repository to your local machine and navigate to the directory containing the `cli.py` file.

```bash
git clone https://github.com/Transia-RnD/xrpld-network-gen
cd xrpld-network-gen
```
