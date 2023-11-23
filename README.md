# xrpld-network-gen CLI

This is a command-line interface (CLI) for building xrpld networks and standalone ledgers. 

## Commands

### start

This command starts a network.

Parameters:
- `--name`: The name of the network. This parameter is required.

### start:local

The `start:local` command is used to start a local network. This command is typically run in the build directory of the rippled or xahau build. 

When you run `start:local`, it creates a standalone binary and runs the explorer. This is particularly useful for testing and development purposes, as it allows you to run a local instance of the network.

Parameters:
- `--public_key`: The public vl key. This parameter is optional.
- `--import_key`: The import vl key. This parameter is optional.
- `--protocol`: The protocol of the network. This parameter is optional.
- `--network_id`: The network id. This parameter is optional and should be an integer.

### stop

This command stops a network.

Parameters:
- `--name`: The name of the network. This parameter is required.

### stop:local

This command stops a local network. It does not require any parameters.

### remove

This command removes a network.

Parameters:
- `--name`: The name of the network. This parameter is required.

### create:network

This command creates a network.

Parameters:
- `--protocol`: The protocol of the network. This parameter is optional.
- `--name`: The name of the network. This parameter is required.
- `--num_validators`: The number of validators. This parameter is optional.
- `--num_peers`: The number of peers. This parameter is optional.
- `--network_id`: The network id. This parameter is optional and should be an integer.
- `--image_name`: The image name. This parameter is optional.

### create:standalone

This command creates a standalone binary.

Parameters:
- `--public_key`: The public vl key. This parameter is optional.
- `--import_key`: The import vl key. This parameter is optional.
- `--protocol`: The protocol of the network. This parameter is optional.
- `--network_id`: The network id. This parameter is optional and should be an integer.
- `--server`: The build server. This parameter is optional.
- `--version`: The build version. This parameter is required.

## Usage

To use the CLI, simply call the desired command with the appropriate parameters. For example:

```
xrpld-netgen start --name MyNetwork
```

This will start a network named "MyNetwork".