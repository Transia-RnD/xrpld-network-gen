#!/usr/bin/env bash

errors=0

which_docker=$(which docker)
[[ "$which_docker" = "" ]] && echo -e "❌ docker not installed" && errors=1 || echo "✅ docker installed"

has_internet=$(curl --connect-timeout 2 --silent https://build.xahau.tech/ | grep Index| wc -l| xargs)
[[ "$has_internet" -lt 2 ]] && echo -e "❌ cannot reach xahau build server" && errors=1 || echo "✅ can reach xahau build server"

can_run_docker=$(docker run --platform linux/amd64 --rm ubuntur uname -a 2>&1|grep x86_64|wc -l|xargs)
[[ "$can_run_docker" -gt 0 ]] && echo -e "❌ can run linux/amd64 in docker" && errors=1 || echo "✅ can run linux/amd64 in docker"

exit $errors