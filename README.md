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

- Create multi-validator networks with custom configurations
- Start, stop, and remove networks with simple commands
- Update individual nodes to different versions
- Enable/disable amendments on specific nodes
- Support for both XRPL and Xahau protocols
- Use locally built binaries instead of building in Docker

### Current Versions

- Ripple: `2.3.0`
- Xahau: `2024.11.18-release+1141`

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

The CLI provides several commands to manage XRPLD networks and standalone ledgers:

### Available Protocols

- xrpl
- xahau

### Create a new Network

To create a network or standalone ledger, use the `create:network` command followed by the name of the network or standalone ledger.

```bash
xrpld-netgen create:network --protocol [PROTOCOL] --build_version [BUILD_VERSION] --validators [NUM_VALIDATORS]
```

### Start a Network or Standalone Ledger

To start a network or standalone ledger, use the `up` command followed by the name of the network or standalone ledger.

```bash
xrpld-netgen up --name [PROTOCOL] + [BUILD_VERSION]
```

### Stop a Network or Standalone Ledger

To stop a running network or standalone ledger, use the `down` command followed by the name of the network or standalone ledger.

```bash
xrpld-netgen down --name [PROTOCOL] + [BUILD_VERSION]
```

### Remove a Network or Standalone Ledger

To remove an existing network or standalone ledger, use the `remove` command followed by the name of the network or standalone ledger.

```bash
xrpld-netgen remove --name [PROTOCOL] + [BUILD_VERSION]
```

### Update a Node in the Network

To update a node in the network, use the `update:version` command followed by the node ID and the new version.

```bash
xrpld-netgen update:version --node_id [NODE_ID] --node_type [NODE_TYPE] --version [NEW_VERSION]
```

### Enable an Amendment on a Node

To enable an amendment on a node, use the `enable:amendment` command followed by the amendment name and node ID.

```bash
xrpld-netgen enable:amendment --amendment_name [AMENDMENT_NAME] --node_id [NODE_ID] --node_type [NODE_TYPE]
```

### Create a Standalone Ledger

To create a standalone ledger, use the `up:standalone` command with the necessary parameters.

```bash
xrpld-netgen up:standalone --version [BUILD_VERSION]
```

> If version is omitted then the current release is built

### Remove a Standalone Ledger

To remove a standalone ledger, use the `down:standalone` command.

```bash
xrpld-netgen down:standalone --name [PROTOCOL] + [BUILD_VERSION]
```

> `name` is not required when running current release

## Support

For any issues or questions regarding the XRPLD Network Generator CLI, please refer to the repository's issue tracker or contact the maintainers.

## Contributing

To install the XRPLD Network Generator CLI, clone the repository to your local machine and navigate to the directory containing the `cli.py` file.

```bash
git clone https://github.com/Transia-RnD/xrpld-network-gen
cd xrpld-network-gen
```
