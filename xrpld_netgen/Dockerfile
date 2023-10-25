ARG IMAGE_NAME
# FROM --platform=$BUILDPLATFORM ${IMAGE_NAME} as base
FROM ${IMAGE_NAME} as base

WORKDIR /app

LABEL maintainer="dangell@transia.co"

ARG RPC_PUBLIC_PORT
ENV RPC_PUBLIC_PORT $RPC_PUBLIC_PORT
ARG RPC_ADMIN_PORT
ENV RPC_ADMIN_PORT $RPC_ADMIN_PORT
ARG WS_PUBLIC_PORT
ENV WS_PUBLIC_PORT $WS_PUBLIC_PORT
ARG WS_ADMIN_PORT
ENV WS_ADMIN_PORT $WS_ADMIN_PORT
ARG PEER_PORT
ENV PEER_PORT $PEER_PORT

RUN export LANGUAGE=C.UTF-8; export LANG=C.UTF-8; export LC_ALL=C.UTF-8; export DEBIAN_FRONTEND=noninteractive

COPY config /config
COPY entrypoint /entrypoint.sh

RUN chmod +x /entrypoint.sh && \
    echo '#!/bin/bash' > /usr/bin/server_info && echo '/entrypoint.sh server_info' >> /usr/bin/server_info && \
    chmod +x /usr/bin/server_info

EXPOSE 80 443 $RPC_PUBLIC_PORT $RPC_ADMIN_PORT $WS_PUBLIC_PORT $WS_ADMIN_PORT $PEER_PORT $PEER_PORT/udp

ENTRYPOINT [ "/entrypoint.sh" ]

