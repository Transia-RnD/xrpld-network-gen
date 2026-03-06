#!/bin/bash

poetry run python ./xrpld_netgen/cideploy/deploy.py && \
cd xrpld_netgen/cideploy && \
chmod +x xahaud && \
docker build --platform linux/x86_64 --tag xahauci/xahaud:2025.7.9 -f deploy.xahau.dockerfile --no-cache . && \
docker build --platform linux/x86_64 --tag xahauci/xahaud:latest -f deploy.xahau.dockerfile --no-cache . && \
docker push xahauci/xahaud:2025.7.9 && \
docker push xahauci/xahaud:latest && \
echo "Deployed xahaud CI image successfully."