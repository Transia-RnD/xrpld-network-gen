# docker build --platform linux/x86_64 --tag xahauci/xahaud:2024.9.11 -f deploy.xahau.dockerfile --no-cache .
# docker push xahauci/xahaud:2024.9.11
FROM ubuntu:jammy as base

WORKDIR /opt/xahau

LABEL maintainer="dangell@transia.co"

RUN export LANGUAGE=C.UTF-8; export LANG=C.UTF-8; export LC_ALL=C.UTF-8; export DEBIAN_FRONTEND=noninteractive

COPY rippled.2024.1.25-release+738 /opt/xahau/bin/xahaud
COPY config/validators.txt /opt/xahau/etc/validators.txt

ENV RPC_ADMIN=5005
ENV WS_PUBLIC=80
ENV WS_ADMIN=6006

EXPOSE $RPC_ADMIN $WS_PUBLIC $WS_ADMIN

# ENTRYPOINT /bin/bash
CMD ["/opt/xahau/bin/xahaud -a --conf /opt/xahau/etc/xahaud.cfg"]
