# XRPLD Network Generator CLI Documentation

## Overview

The XRPLD Network Generator CLI is a command-line interface tool designed to facilitate the creation, management, and interaction with XRPLD networks and standalone ledgers. This tool allows users to easily start, stop, remove, and update XRPLD nodes, as well as enable amendments on the network.

### Current Versions

- XRPL: `2.2.3`
- Xahau: `2024.9.11-release+985`

## Prerequisites

Before using the XRPLD Network Generator CLI, ensure that you have the following prerequisites installed:

- Python ^3.9.6
- Docker
- Git (for cloning the repository)

## Installation

To install the XRPLD Network Generator CLI, use pypi to install the package.

```bash
pip3 install xrpld-netgen
```

## Usage

The CLI provides several commands to manage XRPLD networks and standalone ledgers:

### Create a new Network

To start a network or standalone ledger, use the `start` command followed by the name of the network or standalone ledger.

```bash
xrpld-netgen create:network --protocol [PROTOCOL] --build_version [BUILD_VERSION] --validators [NUM_VALIDATORS]
```

### Start a Network or Standalone Ledger

To start a network or standalone ledger, use the `start` command followed by the name of the network or standalone ledger.

```bash
xrpld-netgen start --name [PROTOCOL] + [BUILD_VERSION]
```

### Stop a Network or Standalone Ledger

To stop a running network or standalone ledger, use the `stop` command followed by the name of the network or standalone ledger.

```bash
xrpld-netgen stop --name [PROTOCOL] + [BUILD_VERSION]
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
