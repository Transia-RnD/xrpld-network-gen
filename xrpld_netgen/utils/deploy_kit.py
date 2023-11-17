#!/usr/bin/env python
# coding: utf-8

import requests
import os
from xrpl_helpers.common.utils import write_file


def build_entrypoint(root_path: str, genesis: False, quorum: int):
    entrypoint: str = """
#!/bin/bash

rippledconfig=`/bin/cat /config/rippled.cfg 2>/dev/null | wc -l`
validatorstxt=`/bin/cat /config/validators.txt 2>/dev/null | wc -l`

mkdir -p /config

if [[ "$rippledconfig" -gt "0" && "$validatorstxt" -gt "0" ]]; then

    echo "Existing rippled config at host /config/, using them."
    mkdir -p /etc/opt/ripple

    /bin/cat /config/rippled.cfg > /etc/opt/ripple/rippled.cfg
    /bin/cat /config/validators.txt > /etc/opt/ripple/validators.txt

fi

# Start rippled, Passthrough other arguments
"""
    exec: str = f'exec /app/rippled --conf /etc/opt/ripple/rippled.cfg "$@"'
    exec_quorum: str = (
        f'exec /app/rippled --conf /etc/opt/ripple/rippled.cfg --quorum={quorum} "$@"'
    )
    exec_genesis: str = f'exec /app/rippled --ledgerfile /genesis.json --conf /etc/opt/ripple/rippled.cfg --quorum={quorum} "$@"'

    entrypoint += "\n"
    if genesis:
        entrypoint += exec_genesis
    else:
        if quorum:
            entrypoint += exec_quorum
        else:
            entrypoint += exec

    write_file(f"{root_path}/entrypoint", entrypoint)


def create_dockerfile(
    binary,
    image_name,
    rpc_public_port,
    rpc_admin_port,
    ws_public_port,
    ws_admin_port,
    peer_port,
    include_genesis=False,
    quorum=None,
    standalone=None,
):
    dockerfile = f"""
    FROM {image_name} as base

    WORKDIR /app

    LABEL maintainer="dangell@transia.co"

    RUN export LANGUAGE=C.UTF-8; export LANG=C.UTF-8; export LC_ALL=C.UTF-8; export DEBIAN_FRONTEND=noninteractive

    COPY config /config
    COPY entrypoint /entrypoint.sh
    """

    if include_genesis:
        dockerfile += "COPY genesis.json /genesis.json\n"

    if binary:
        dockerfile += "COPY rippled /app/rippled\n"

    dockerfile += f"""
    RUN chmod +x /entrypoint.sh && \
        echo '#!/bin/bash' > /usr/bin/server_info && echo '/entrypoint.sh server_info' >> /usr/bin/server_info && \
        chmod +x /usr/bin/server_info

    EXPOSE 80 443 {rpc_public_port} {rpc_admin_port} {ws_public_port} {ws_admin_port} {peer_port} {peer_port}/udp
    """

    if include_genesis:
        dockerfile += f'ENTRYPOINT [ "/entrypoint.sh", "/genesis.json", "{quorum}", "{standalone}" ]'
    else:
        dockerfile += 'ENTRYPOINT [ "/entrypoint.sh" ]'

    return dockerfile


def download_binary(url: str, save_path: str):
    # Check if the file already exists
    if os.path.exists(save_path):
        print(f"The file {save_path} already exists.")
        return

    try:
        # Send a GET request to the URL
        response = requests.get(url, stream=True)

        # Raise an exception if the request was unsuccessful
        response.raise_for_status()

        # Open the file in binary write mode and save the content to the file
        with open(save_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)

        # Set the file permissions to be readable and executable by the owner
        os.chmod(save_path, 0o755)
        print(f"Download complete. File saved as {save_path}")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
