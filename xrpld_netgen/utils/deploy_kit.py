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
    name,
    node_dir,
    image_name,
    rpc_public_port,
    rpc_admin_port,
    ws_public_port,
    ws_admin_port,
    peer_port,
    include_genesis=False,
    quorum=0,
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

    dockerfile += f"""
    RUN chmod +x /entrypoint.sh && \
        echo '#!/bin/bash' > /usr/bin/server_info && echo '/entrypoint.sh server_info' >> /usr/bin/server_info && \
        chmod +x /usr/bin/server_info

    EXPOSE 80 443 {rpc_public_port} {rpc_admin_port} {ws_public_port} {ws_admin_port} {peer_port} {peer_port}/udp
    """

    if include_genesis:
        dockerfile += f'ENTRYPOINT [ "/entrypoint.sh", "/genesis.json", {quorum} ]'
    else:
        dockerfile += 'ENTRYPOINT [ "/entrypoint.sh" ]'

    with open(f"{name}-cluster/{node_dir}/Dockerfile", "w") as file:
        file.write(dockerfile)
