"""Ansible deployment file generator for xrpld_lab.

Generates a complete ansible directory for deploying xrpld clusters
to remote servers, with optional per-host services (nginx, redis,
faucet, stream, debug, compiler) and idempotent run.sh that skips
already-completed playbook stages on rebuild.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

import yaml

from xrpld_lab.models import (
    AnsibleConfig,
    PortSet,
    ServicesHost,
)


# ---------------------------------------------------------------------------
# Node registration
# ---------------------------------------------------------------------------


@dataclass
class AnsibleNode:
    name: str
    ip: str
    ports: PortSet
    config_path: str
    role: str  # "validator" or "peer"


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


class AnsibleBuilder:
    """Generates ansible deployment files for an xrpld cluster."""

    def __init__(
        self,
        cluster_dir: str,
        config: AnsibleConfig,
        image_name: str,
        network_name: str = "loadnet",
    ):
        self.cluster_dir = cluster_dir
        self.config = config
        self.image_name = image_name
        self.network_name = network_name
        self.ansible_dir = os.path.join(cluster_dir, "ansible")
        self._nodes: List[AnsibleNode] = []

    def add_node(
        self,
        name: str,
        ip: str,
        ports: PortSet,
        config_path: str,
        role: str = "validator",
    ) -> AnsibleBuilder:
        self._nodes.append(AnsibleNode(name, ip, ports, config_path, role))
        return self

    def write(self) -> str:
        """Write all ansible files and return the ansible directory path."""
        os.makedirs(self.ansible_dir, exist_ok=True)
        os.makedirs(os.path.join(self.ansible_dir, "host_vars"), exist_ok=True)

        self._write_hosts_txt()
        self._write_host_vars()
        self._write_deps_yml()
        self._write_main_yml()
        self._write_clean_yml()
        self._write_clean_sh()

        for svc_host in self.config.services:
            self._write_services_host(svc_host)

        self._write_run_sh()

        return self.ansible_dir

    # ------------------------------------------------------------------
    # hosts.txt
    # ------------------------------------------------------------------

    def _write_hosts_txt(self) -> None:
        c = self.config
        lines = [
            "",
            "# this is a basic file putting different hosts into categories",
            "# used by ansible to determine which actions to run on which hosts",
            "[all]",
            "    ",
        ]
        for node in self._nodes:
            lines.append(self._host_line(node.ip))

        for svc_host in c.services:
            lines.append("")
            lines.append(f"[{svc_host.name}]")
            lines.append(self._host_line(svc_host.ip))

        lines.append("")
        self._file_write(os.path.join(self.ansible_dir, "hosts.txt"), "\n".join(lines))

    def _host_line(self, ip: str) -> str:
        c = self.config
        return (
            f"{ip} ansible_port={c.ssh_port}"
            f" ansible_user={c.ssh_user}"
            f" ansible_ssh_private_key_file={c.ssh_key_path}"
            f" vars_file=host_vars/{ip}.yml "
        )

    # ------------------------------------------------------------------
    # host_vars/{ip}.yml
    # ------------------------------------------------------------------

    def _write_host_vars(self) -> None:
        hv_dir = os.path.join(self.ansible_dir, "host_vars")
        for node in self._nodes:
            data = {
                "config_path": node.config_path,
                "docker_container_name": node.name,
                "docker_container_ports": [
                    f"{node.ports.rpc_public}:{node.ports.rpc_public}",
                    f"{node.ports.rpc_admin}:{node.ports.rpc_admin}",
                    f"{node.ports.ws_public}:{node.ports.ws_public}",
                    f"{node.ports.ws_admin}:{node.ports.ws_admin}",
                    f"{node.ports.peer}:{node.ports.peer}",
                ],
                "docker_env_variables": {
                    "RPC_PUBLIC": str(node.ports.rpc_public),
                    "RPC_ADMIN": str(node.ports.rpc_admin),
                    "WS_PUBLIC": str(node.ports.ws_public),
                    "WS_ADMIN": str(node.ports.ws_admin),
                    "PEER": str(node.ports.peer),
                },
                "docker_image_name": self.image_name,
                "docker_network_name": self.network_name,
                "docker_volumes": [
                    "/opt/ripple/config:/opt/ripple/config",
                    "/opt/ripple/log:/opt/ripple/log",
                    "/opt/ripple/lib:/opt/ripple/lib",
                    "/var/lib/xrpld/db:/var/lib/xrpld/db",
                ],
                "peer_port": node.ports.peer,
                "ssh_port": self.config.ssh_port,
                "volumes": [
                    "/opt/ripple/config",
                    "/opt/ripple/log",
                    "/opt/ripple/lib",
                    "/var/lib/xrpld/db",
                ],
                "ws_port": node.ports.ws_public,
            }
            path = os.path.join(hv_dir, f"{node.ip}.yml")
            with open(path, "w") as f:
                yaml.dump(data, f, explicit_start=True, default_flow_style=False)

    # ------------------------------------------------------------------
    # deps.yml
    # ------------------------------------------------------------------

    def _write_deps_yml(self) -> None:
        self._file_write(os.path.join(self.ansible_dir, "deps.yml"), _DEPS_YML)

    # ------------------------------------------------------------------
    # main.yml
    # ------------------------------------------------------------------

    def _write_main_yml(self) -> None:
        self._file_write(os.path.join(self.ansible_dir, "main.yml"), _MAIN_YML)

    # ------------------------------------------------------------------
    # clean.yml / clean.sh
    # ------------------------------------------------------------------

    def _write_clean_yml(self) -> None:
        self._file_write(os.path.join(self.ansible_dir, "clean.yml"), _CLEAN_YML)

    def _write_clean_sh(self) -> None:
        content = (
            "#!/bin/sh\n"
            "export ANSIBLE_HOST_KEY_CHECKING=False\n"
            "ansible -i hosts.txt all -u ubuntu -m ping\n"
            "ansible-playbook -i hosts.txt clean.yml\n"
            "rm -f .done_*\n"
        )
        self._file_write_executable(os.path.join(self.ansible_dir, "clean.sh"), content)

    # ------------------------------------------------------------------
    # Per-ServicesHost file generation
    # ------------------------------------------------------------------

    def _write_services_host(self, host: ServicesHost) -> None:
        host_dir = os.path.join(self.ansible_dir, "services", host.name)
        os.makedirs(host_dir, exist_ok=True)

        if host.nginx:
            self._write_nginx(host_dir, host)
        if host.redis:
            self._write_redis(host_dir, host)
        if host.faucet:
            self._write_faucet(host_dir, host)
        if host.stream:
            self._write_stream(host_dir, host)
        if host.debug:
            self._write_debug(host_dir, host)
        if host.compiler:
            self._write_compiler(host_dir, host)

    # ------------------------------------------------------------------
    # run.sh — smart runner with skip-on-success
    # ------------------------------------------------------------------

    def _write_run_sh(self) -> None:
        lines = [
            "#!/bin/bash",
            "set -e",
            "",
            'SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"',
            'cd "$SCRIPT_DIR"',
            "",
            "# Parse flags",
            "FORCE=false",
            'for arg in "$@"; do',
            '  case "$arg" in',
            "    --force) FORCE=true ;;",
            "  esac",
            "done",
            "",
            "# Run a playbook once. Skips if .done_{name} marker exists.",
            "# Usage: run_once <name> <playbook> [extra args...]",
            "run_once() {",
            "  local name=$1; shift",
            "  local playbook=$1; shift",
            '  if [ "$FORCE" = false ] && [ -f ".done_${name}" ]; then',
            '    echo "SKIP: ${playbook} (already completed'
            ' — delete .done_${name} or use --force to re-run)"',
            "    return 0",
            "  fi",
            '  echo "RUNNING: ${playbook}"',
            '  if ansible-playbook -i hosts.txt "${playbook}" "$@"; then',
            '    touch ".done_${name}"',
            '    echo "DONE: ${playbook}"',
            "  else",
            '    echo "FAILED: ${playbook}"',
            "    return 1",
            "  fi",
            "}",
            "",
            "# Run a playbook every time (no skip logic).",
            "run_always() {",
            "  local playbook=$1; shift",
            '  echo "RUNNING: ${playbook}"',
            '  ansible-playbook -i hosts.txt "${playbook}" "$@"',
            "}",
            "",
            "export ANSIBLE_HOST_KEY_CHECKING=False",
            "",
            "# SSH agent",
            'eval "$(ssh-agent -s)"',
            "ssh-add --apple-use-keychain $SSH_PATH",
            "",
            "# Ping all hosts",
            "ansible -i hosts.txt all -u ubuntu -m ping",
            "",
            "# --- Core playbooks ---",
            "run_once deps deps.yml",
            "run_always main.yml",
        ]

        for host in self.config.services:
            n = host.name
            prefix = f"services/{n}"
            lines.append("")
            lines.append(f"# --- Services: {n} ({host.ip}) ---")

            if host.nginx:
                lines.append(f"run_once {n}_nginx_deps {prefix}/nginx/deps.yml")
                lines.append(f"run_once {n}_nginx_ssl {prefix}/nginx/ssl.yml")
                lines.append(f"run_once {n}_nginx {prefix}/nginx/main.yml")
            if host.redis:
                lines.append(f"run_once {n}_redis {prefix}/redis/main.yml")
            if host.faucet:
                lines.append(f"run_once {n}_faucet {prefix}/faucet/main.yml")
            if host.stream:
                lines.append(f"run_once {n}_stream {prefix}/stream/main.yml")
            if host.debug:
                lines.append(f"run_once {n}_debug {prefix}/debug/main.yml")
            if host.compiler:
                lines.append(f"run_once {n}_compiler {prefix}/compiler/main.yml")

        lines.append("")
        lines.append('echo ""')
        lines.append('echo "Deployment complete."')
        lines.append("")

        self._file_write_executable(
            os.path.join(self.ansible_dir, "run.sh"), "\n".join(lines)
        )

    # ------------------------------------------------------------------
    # Service writers (per-host)
    # ------------------------------------------------------------------

    def _write_nginx(self, host_dir: str, host: ServicesHost) -> None:
        nginx_dir = os.path.join(host_dir, "nginx")
        os.makedirs(nginx_dir, exist_ok=True)
        cfg = host.nginx

        node = self._node_for_ip(host.ip)
        vars_data = {
            "IP": "0.0.0.0",
            "PORT": cfg.ws_port or (str(node.ports.ws_public) if node else "6018"),
            "SSL_CERT": f"/etc/ssl/certs/{cfg.domain}.csr.pem",
            "SSL_KEY": f"/etc/ssl/private/{cfg.domain}.pem",
            "SSL_CN": cfg.domain,
            "SSL_O": cfg.ssl_org,
            "SSL_OU": cfg.ssl_ou,
            "RPC_IP": "0.0.0.0",
            "RPC_PORT": cfg.rpc_port
            or (str(node.ports.rpc_public) if node else "5017"),
            "RPC_SSL_CERT": f"/etc/ssl/certs/rpc.{cfg.domain}.csr.pem",
            "RPC_SSL_KEY": f"/etc/ssl/private/rpc.{cfg.domain}.pem",
            "RPC_SSL_CN": f"rpc.{cfg.domain}",
            "FAUCET_IP": "0.0.0.0",
            "FAUCET_PORT": cfg.faucet_port,
            "FAUCET_SSL_CERT": f"/etc/ssl/certs/faucet.{cfg.domain}.csr.pem",
            "FAUCET_SSL_KEY": f"/etc/ssl/private/faucet.{cfg.domain}.pem",
            "FAUCET_SSL_CN": f"faucet.{cfg.domain}",
            "DEBUG_IP": "0.0.0.0",
            "DEBUG_PORT": cfg.debug_port,
            "DEBUG_SSL_CERT": f"/etc/ssl/certs/debug.{cfg.domain}.csr.pem",
            "DEBUG_SSL_KEY": f"/etc/ssl/private/debug.{cfg.domain}.pem",
            "DEBUG_SSL_CN": f"debug.{cfg.domain}",
            "COMPILER_IP": "0.0.0.0",
            "COMPILER_PORT": cfg.compiler_port,
            "COMPILER_SSL_CERT": f"/etc/ssl/certs/compiler.{cfg.domain}.csr.pem",
            "COMPILER_SSL_KEY": f"/etc/ssl/private/compiler.{cfg.domain}.pem",
            "COMPILER_SSL_CN": f"compiler.{cfg.domain}",
        }
        self._write_vars(os.path.join(nginx_dir, "vars.yml"), vars_data)
        self._file_write(
            os.path.join(nginx_dir, "deps.yml"),
            _NGINX_DEPS_TPL.format(group=host.name, ssh_port=self.config.ssh_port),
        )
        self._file_write(
            os.path.join(nginx_dir, "ssl.yml"),
            _NGINX_SSL_TPL.format(group=host.name),
        )
        self._file_write(
            os.path.join(nginx_dir, "main.yml"),
            _NGINX_MAIN_TPL.format(group=host.name),
        )

    def _write_redis(self, host_dir: str, host: ServicesHost) -> None:
        svc_dir = os.path.join(host_dir, "redis")
        os.makedirs(svc_dir, exist_ok=True)
        cfg = host.redis
        self._write_vars(os.path.join(svc_dir, "vars.yml"), {
            "docker_network_name": cfg.network_name,
            "docker_image_name": cfg.image,
            "docker_container_name": cfg.container_name,
            "docker_container_ports": ["6379:6379"],
        })
        self._file_write(
            os.path.join(svc_dir, "main.yml"),
            _REDIS_MAIN_TPL.format(group=host.name),
        )

    def _write_faucet(self, host_dir: str, host: ServicesHost) -> None:
        svc_dir = os.path.join(host_dir, "faucet")
        os.makedirs(svc_dir, exist_ok=True)
        cfg = host.faucet
        self._write_vars(os.path.join(svc_dir, "vars.yml"), {
            "docker_image_name": cfg.image,
            "docker_container_name": "faucet",
            "docker_container_ports": [f"{cfg.port}:{cfg.port}"],
            "docker_env_variables": {
                "XRPL_FAUCET_URL": cfg.ws_url,
                "XRPL_NETWORK_ID": cfg.network_id,
                "XRPL_FAUCET_SEED": cfg.seed,
            },
        })
        self._file_write(
            os.path.join(svc_dir, "main.yml"),
            _FAUCET_MAIN_TPL.format(group=host.name),
        )

    def _write_stream(self, host_dir: str, host: ServicesHost) -> None:
        svc_dir = os.path.join(host_dir, "stream")
        os.makedirs(svc_dir, exist_ok=True)
        cfg = host.stream
        self._write_vars(os.path.join(svc_dir, "vars.yml"), {
            "websocketd_port": cfg.port,
            "docker_container_name": cfg.container_name,
            "log_path": cfg.log_path,
        })
        self._file_write(
            os.path.join(svc_dir, "main.yml"),
            _STREAM_MAIN_TPL.format(group=host.name),
        )

    def _write_debug(self, host_dir: str, host: ServicesHost) -> None:
        svc_dir = os.path.join(host_dir, "debug")
        os.makedirs(svc_dir, exist_ok=True)
        cfg = host.debug
        endpoint = cfg.endpoint
        if not endpoint:
            stream_port = host.stream.port if host.stream else 1400
            endpoint = f"ws://{host.ip}:{stream_port}/"
        self._write_vars(os.path.join(svc_dir, "vars.yml"), {
            "docker_network_name": cfg.network_name,
            "docker_image_name": cfg.image,
            "docker_container_name": "debugstream",
            "docker_container_ports": [f"{cfg.port}:{cfg.port}"],
            "docker_env_variables": {
                "PORT": str(cfg.port),
                "ENDPOINT": endpoint,
                "DEBUG": "stream*",
                "REDIS_HOST": cfg.redis_host,
                "REDIS_PORT": cfg.redis_port,
            },
        })
        self._file_write(
            os.path.join(svc_dir, "main.yml"),
            _DEBUG_MAIN_TPL.format(group=host.name),
        )

    def _write_compiler(self, host_dir: str, host: ServicesHost) -> None:
        svc_dir = os.path.join(host_dir, "compiler")
        os.makedirs(svc_dir, exist_ok=True)
        cfg = host.compiler
        data: dict = {
            "docker_image_name": cfg.image,
            "docker_container_name": "compiler-api",
            "docker_container_ports": [f"{cfg.port}:{cfg.port}"],
            "docker_env_variables": {"PORT": str(cfg.port)},
            "compiler_repo": cfg.repo,
            "compiler_branch": cfg.branch,
        }
        if cfg.volumes:
            data["docker_volumes"] = cfg.volumes
        self._write_vars(os.path.join(svc_dir, "vars.yml"), data)
        self._file_write(
            os.path.join(svc_dir, "main.yml"),
            _COMPILER_MAIN_TPL.format(group=host.name),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _node_for_ip(self, ip: str) -> AnsibleNode | None:
        for n in self._nodes:
            if n.ip == ip:
                return n
        return None

    @staticmethod
    def _write_vars(path: str, data: dict) -> None:
        with open(path, "w") as f:
            yaml.dump(data, f, explicit_start=True, default_flow_style=False)

    @staticmethod
    def _file_write(path: str, content: str) -> None:
        with open(path, "w") as f:
            f.write(content)

    @staticmethod
    def _file_write_executable(path: str, content: str) -> None:
        with open(path, "w") as f:
            f.write(content)
        os.chmod(path, 0o755)


# ======================================================================
# Static playbook templates
# ======================================================================

_DEPS_YML = """---
- hosts: all
  become: true
  remote_user: root
  tasks:
  - name: Install packages that allow apt to be used over HTTPS
    apt:
      name: "{{ packages }}"
      state: present
      update_cache: yes
    vars:
      packages:
      - apt-transport-https
      - ca-certificates
      - curl
      - gnupg-agent
      - software-properties-common
  - name: Add an apt signing key for Docker
    apt_key:
      url: https://download.docker.com/linux/ubuntu/gpg
      state: present
  - name: Add apt repository for stable version
    apt_repository:
      repo: deb [arch=amd64] https://download.docker.com/linux/ubuntu focal stable
      state: present
  - name: install nodejs prerequisites
    apt:
      name:
        - apt-transport-https
        - gcc
        - g++
        - make
      state: present
  - name: add nodejs apt key
    apt_key:
      url: https://deb.nodesource.com/gpgkey/nodesource.gpg.key
      state: present
  - name: add nodejs repository
    apt_repository:
      repo: deb https://deb.nodesource.com/node_16.x focal main
      state: present
      update_cache: yes
  - name: install nodejs
    apt:
      name: nodejs
      state: present
  - name: Install docker and its dependencies
    apt:
      name: "{{ packages }}"
      state: present
      update_cache: yes
    vars:
      packages:
      - docker-ce
      - docker-ce-cli
      - containerd.io
  - name: verify docker installed, enabled, and started
    service:
      name: docker
      state: started
      enabled: yes
  - name: Remove swapfile from /etc/fstab
    mount:
      name: "{{ item }}"
      fstype: swap
      state: absent
    with_items:
      - swap
      - none
  - name: Disable swap
    command: swapoff -a
    when: ansible_swaptotal_mb >= 0
  - name: add ubuntu user to docker
    user:
      name: ubuntu
      group: docker
  - name: Ensure UFW is installed
    apt:
      name: ufw
      state: present
  - name: Enable UFW
    ufw:
      state: enabled
      policy: allow
      direction: incoming
  - name: Enable SSH
    ufw:
      rule: limit
      port: "{{ ssh_port }}"
      proto: tcp
  - name: Enable WS
    ufw:
      rule: allow
      port: "{{ ws_port }}"
      proto: tcp
  - name: Enable Peer
    ufw:
      rule: allow
      port: "{{ peer_port }}"
      proto: tcp
  - name: Stop and disable the unattended-upgrades service
    service:
      name: unattended-upgrades
      state: stopped
      enabled: no
  - name: reboot to apply swap disable
    reboot:
      reboot_timeout: 180
"""

_MAIN_YML = """- hosts: all
  become: true
  remote_user: root

  tasks:
  - name: set docker to use systemd cgroups driver
    copy:
      dest: "/etc/docker/daemon.json"
      content: |
        {
          "exec-opts": ["native.cgroupdriver=systemd"]
        }
  - name: restart docker
    service:
      name: docker
      state: restarted
  - name: Remove Docker cache
    command: docker system prune --all --volumes --force
  - name: Remove Docker image
    command: docker rmi -f "{{ docker_image_name }}"
    ignore_errors: yes
  - name: Delete folders
    file:
      path: "{{ item }}"
      state: absent
    loop: "{{ volumes }}"
  - name: Create Docker Network
    docker_network:
      name: "{{ docker_network_name }}"
      state: present
  - name: Pull Docker Image
    docker_image:
      name: "{{ docker_image_name }}"
      source: pull
  - name: Copy config files to the remote server
    copy:
      src: "{{ config_path }}/"
      dest: /opt/ripple/config/
  - name: Deploy Docker Image
    docker_container:
      name: "{{ docker_container_name }}"
      image: "{{ docker_image_name }}"
      ports: "{{ docker_container_ports }}"
      volumes: "{{ docker_volumes }}"
      env: "{{ docker_env_variables }}"
      networks:
        - name: "{{ docker_network_name }}"
      state: started
      restart_policy: always
      image_name_mismatch: recreate
"""

_CLEAN_YML = """- hosts: all
  become: true
  remote_user: root

  tasks:
  - name: Stop Docker Container
    docker_container:
      name: "{{ docker_container_name }}"
      state: stopped
    ignore_errors: yes
  - name: Remove Docker cache
    command: docker system prune --all --volumes --force
  - name: Remove Docker image
    command: docker rmi -f "{{ docker_image_name }}"
    ignore_errors: yes
  - name: Remove Docker network
    docker_network:
      name: "{{ docker_network_name }}"
      state: absent
  - name: Delete folders
    file:
      path: "{{ item }}"
      state: absent
    loop: "{{ volumes }}"
"""

# --- Nginx templates (use {group} and {ssh_port} placeholders) ---

_NGINX_DEPS_TPL = """---
- hosts: {group}
  become: true
  remote_user: root
  tasks:
  - name: Install NGINX
    apt:
      name: nginx
      state: present
  - name: Disable NGINX Default Virtual Host
    command:
      cmd: unlink /etc/nginx/sites-enabled/default
    ignore_errors: yes
  - name: Ensure UFW is installed
    apt:
      name: ufw
      state: present
  - name: Enable UFW
    ufw:
      state: enabled
      policy: allow
      direction: incoming
  - name: Enable SSH
    ufw:
      rule: limit
      port: {ssh_port}
      proto: tcp
  - name: Enable 80
    ufw:
      rule: allow
      port: 80
      proto: tcp
  - name: Enable 443
    ufw:
      rule: allow
      port: 443
      proto: tcp
  - name: Stop and disable the unattended-upgrades service
    service:
      name: unattended-upgrades
      state: stopped
      enabled: no
  - name: Generate dhparam
    command: openssl dhparam -out /etc/ssl/dhparam.pem 2048
    args:
      creates: "/etc/ssl/dhparam.pem"
    become_user: root
  - name: Delete existing ssl-params
    file:
      path: /etc/nginx/snippets/ssl-params.conf
      state: absent
  - name: Create NGINX SSL Params File
    file:
      path: /etc/nginx/snippets/ssl-params.conf
      state: touch
  - name: Write NGINX SSL Params
    blockinfile:
        path: /etc/nginx/snippets/ssl-params.conf
        marker: ""
        block: |
          ssl_protocols TLSv1.2 TLSv1.3;
          ssl_prefer_server_ciphers on;
          ssl_ciphers "EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH";
          ssl_ecdh_curve secp384r1;
          ssl_session_cache shared:SSL:10m;
          add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
          add_header X-Frame-Options DENY;
          add_header X-Content-Type-Options nosniff;
          add_header X-XSS-Protection "1; mode=block";
          ssl_dhparam /etc/ssl/dhparam.pem;
  - name: Restart NGINX
    service:
      name: nginx
      state: restarted
      enabled: yes
"""

_NGINX_SSL_TPL = """- hosts: {group}
  become: true
  remote_user: root

  vars_files:
    - vars.yml

  tasks:
  - name: Check WSS cert exists
    stat:
      path: "{{{{ SSL_CERT }}}}"
    register: wss_cert
  - name: Create WSS private key
    community.crypto.openssl_privatekey:
      path: "{{{{ SSL_KEY }}}}"
    when: not wss_cert.stat.exists
  - name: Create WSS CSR
    community.crypto.openssl_csr_pipe:
      privatekey_path: "{{{{ SSL_KEY }}}}"
      common_name: "{{{{ SSL_CN }}}}"
      organization_name: "{{{{ SSL_O }}}}"
      organizational_unit_name: "{{{{ SSL_OU }}}}"
    register: csr
    when: not wss_cert.stat.exists
  - name: Create WSS self-signed certificate
    community.crypto.x509_certificate:
      path: "{{{{ SSL_CERT }}}}"
      csr_content: "{{{{ csr.csr }}}}"
      privatekey_path: "{{{{ SSL_KEY }}}}"
      provider: selfsigned
    when: not wss_cert.stat.exists
  - name: Check RPC cert exists
    stat:
      path: "{{{{ RPC_SSL_CERT }}}}"
    register: rpc_cert
  - name: Create RPC private key
    community.crypto.openssl_privatekey:
      path: "{{{{ RPC_SSL_KEY }}}}"
    when: not rpc_cert.stat.exists
  - name: Create RPC CSR
    community.crypto.openssl_csr_pipe:
      privatekey_path: "{{{{ RPC_SSL_KEY }}}}"
      common_name: "{{{{ RPC_SSL_CN }}}}"
      organization_name: "{{{{ SSL_O }}}}"
      organizational_unit_name: "{{{{ SSL_OU }}}}"
    register: csr
    when: not rpc_cert.stat.exists
  - name: Create RPC self-signed certificate
    community.crypto.x509_certificate:
      path: "{{{{ RPC_SSL_CERT }}}}"
      csr_content: "{{{{ csr.csr }}}}"
      privatekey_path: "{{{{ RPC_SSL_KEY }}}}"
      provider: selfsigned
    when: not rpc_cert.stat.exists
  - name: Check Faucet cert exists
    stat:
      path: "{{{{ FAUCET_SSL_CERT }}}}"
    register: faucet_cert
  - name: Create Faucet private key
    community.crypto.openssl_privatekey:
      path: "{{{{ FAUCET_SSL_KEY }}}}"
    when: not faucet_cert.stat.exists
  - name: Create Faucet CSR
    community.crypto.openssl_csr_pipe:
      privatekey_path: "{{{{ FAUCET_SSL_KEY }}}}"
      common_name: "{{{{ FAUCET_SSL_CN }}}}"
      organization_name: "{{{{ SSL_O }}}}"
      organizational_unit_name: "{{{{ SSL_OU }}}}"
    register: csr
    when: not faucet_cert.stat.exists
  - name: Create Faucet self-signed certificate
    community.crypto.x509_certificate:
      path: "{{{{ FAUCET_SSL_CERT }}}}"
      csr_content: "{{{{ csr.csr }}}}"
      privatekey_path: "{{{{ FAUCET_SSL_KEY }}}}"
      provider: selfsigned
    when: not faucet_cert.stat.exists
  - name: Check Debug cert exists
    stat:
      path: "{{{{ DEBUG_SSL_CERT }}}}"
    register: debug_cert
  - name: Create Debug private key
    community.crypto.openssl_privatekey:
      path: "{{{{ DEBUG_SSL_KEY }}}}"
    when: not debug_cert.stat.exists
  - name: Create Debug CSR
    community.crypto.openssl_csr_pipe:
      privatekey_path: "{{{{ DEBUG_SSL_KEY }}}}"
      common_name: "{{{{ DEBUG_SSL_CN }}}}"
      organization_name: "{{{{ SSL_O }}}}"
      organizational_unit_name: "{{{{ SSL_OU }}}}"
    register: csr
    when: not debug_cert.stat.exists
  - name: Create Debug self-signed certificate
    community.crypto.x509_certificate:
      path: "{{{{ DEBUG_SSL_CERT }}}}"
      csr_content: "{{{{ csr.csr }}}}"
      privatekey_path: "{{{{ DEBUG_SSL_KEY }}}}"
      provider: selfsigned
    when: not debug_cert.stat.exists
  - name: Check Compiler cert exists
    stat:
      path: "{{{{ COMPILER_SSL_CERT }}}}"
    register: compiler_cert
  - name: Create Compiler private key
    community.crypto.openssl_privatekey:
      path: "{{{{ COMPILER_SSL_KEY }}}}"
    when: not compiler_cert.stat.exists
  - name: Create Compiler CSR
    community.crypto.openssl_csr_pipe:
      privatekey_path: "{{{{ COMPILER_SSL_KEY }}}}"
      common_name: "{{{{ COMPILER_SSL_CN }}}}"
      organization_name: "{{{{ SSL_O }}}}"
      organizational_unit_name: "{{{{ SSL_OU }}}}"
    register: csr
    when: not compiler_cert.stat.exists
  - name: Create Compiler self-signed certificate
    community.crypto.x509_certificate:
      path: "{{{{ COMPILER_SSL_CERT }}}}"
      csr_content: "{{{{ csr.csr }}}}"
      privatekey_path: "{{{{ COMPILER_SSL_KEY }}}}"
      provider: selfsigned
    when: not compiler_cert.stat.exists
"""

_NGINX_MAIN_TPL = """- hosts: {group}
  become: true
  remote_user: root

  vars_files:
    - vars.yml

  tasks:
  # WSS reverse proxy
  - name: Delete existing WSS conf
    file:
      path: "/etc/nginx/sites-available/{{{{ SSL_CN }}}}_proxy.conf"
      state: absent
  - name: Create WSS conf file
    file:
      path: "/etc/nginx/sites-available/{{{{ SSL_CN }}}}_proxy.conf"
      state: touch
  - name: Write WSS proxy config
    blockinfile:
        path: "/etc/nginx/sites-available/{{{{ SSL_CN }}}}_proxy.conf"
        marker: ""
        block: |
          server {{
              listen 80;
              server_name "{{{{ SSL_CN }}}}";
              return 301 https://$host$request_uri;
          }}
          server {{
              listen 443 ssl;
              server_name "{{{{ SSL_CN }}}}";
              ssl_certificate "/etc/ssl/certs/{{{{ SSL_CN }}}}.csr.pem";
              ssl_certificate_key "/etc/ssl/private/{{{{ SSL_CN }}}}.pem";
              include /etc/nginx/snippets/ssl-params.conf;
              access_log /var/log/nginx/access.log;
              location / {{
                  proxy_hide_header X-Powered-By;
                  proxy_pass_header Authorization;
                  proxy_set_header Upgrade $http_upgrade;
                  proxy_set_header Host $host;
                  proxy_set_header X-Real-IP $remote_addr;
                  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                  proxy_set_header X-Forwarded-Host $host;
                  proxy_set_header X-Forwarded-Proto $scheme;
                  proxy_http_version 1.1;
                  proxy_set_header Connection "upgrade";
                  proxy_read_timeout 90s;
                  proxy_redirect off;
                  proxy_pass http://{{{{ IP }}}}:{{{{ PORT }}}};
                  proxy_cache_bypass $http_upgrade;
                  add_header 'Access-Control-Allow-Origin' '*' always;
              }}
          }}
  - name: Link WSS proxy
    command:
      cmd: "ln -s /etc/nginx/sites-available/{{{{ SSL_CN }}}}_proxy.conf /etc/nginx/sites-enabled/{{{{ SSL_CN }}}}_proxy.conf"
    ignore_errors: yes
  # RPC reverse proxy
  - name: Delete existing RPC conf
    file:
      path: "/etc/nginx/sites-available/{{{{ RPC_SSL_CN }}}}_proxy.conf"
      state: absent
  - name: Create RPC conf file
    file:
      path: "/etc/nginx/sites-available/{{{{ RPC_SSL_CN }}}}_proxy.conf"
      state: touch
  - name: Write RPC proxy config
    blockinfile:
        path: "/etc/nginx/sites-available/{{{{ RPC_SSL_CN }}}}_proxy.conf"
        marker: ""
        block: |
          server {{
              listen 80;
              server_name "{{{{ RPC_SSL_CN }}}}";
              return 301 https://$host$request_uri;
          }}
          server {{
              listen 443 ssl;
              server_name "{{{{ RPC_SSL_CN }}}}";
              ssl_certificate "/etc/ssl/certs/{{{{ RPC_SSL_CN }}}}.csr.pem";
              ssl_certificate_key "/etc/ssl/private/{{{{ RPC_SSL_CN }}}}.pem";
              include /etc/nginx/snippets/ssl-params.conf;
              access_log /var/log/nginx/access.log;
              location / {{
                  proxy_hide_header X-Powered-By;
                  proxy_pass_header Authorization;
                  proxy_set_header Upgrade $http_upgrade;
                  proxy_set_header Host $host;
                  proxy_set_header X-Real-IP $remote_addr;
                  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                  proxy_set_header X-Forwarded-Host $host;
                  proxy_set_header X-Forwarded-Proto $scheme;
                  proxy_http_version 1.1;
                  proxy_set_header Connection "upgrade";
                  proxy_read_timeout 90s;
                  proxy_redirect off;
                  proxy_pass http://{{{{ RPC_IP }}}}:{{{{ RPC_PORT }}}};
                  proxy_cache_bypass $http_upgrade;
                  add_header 'Access-Control-Allow-Origin' '*' always;
              }}
          }}
  - name: Link RPC proxy
    command:
      cmd: "ln -s /etc/nginx/sites-available/{{{{ RPC_SSL_CN }}}}_proxy.conf /etc/nginx/sites-enabled/{{{{ RPC_SSL_CN }}}}_proxy.conf"
    ignore_errors: yes
  # Faucet reverse proxy
  - name: Delete existing Faucet conf
    file:
      path: "/etc/nginx/sites-available/{{{{ FAUCET_SSL_CN }}}}_proxy.conf"
      state: absent
  - name: Create Faucet conf file
    file:
      path: "/etc/nginx/sites-available/{{{{ FAUCET_SSL_CN }}}}_proxy.conf"
      state: touch
  - name: Write Faucet proxy config
    blockinfile:
        path: "/etc/nginx/sites-available/{{{{ FAUCET_SSL_CN }}}}_proxy.conf"
        marker: ""
        block: |
          server {{
              listen 80;
              server_name "{{{{ FAUCET_SSL_CN }}}}";
              return 301 https://$host$request_uri;
          }}
          server {{
              listen 443 ssl;
              server_name "{{{{ FAUCET_SSL_CN }}}}";
              ssl_certificate "/etc/ssl/certs/{{{{ FAUCET_SSL_CN }}}}.csr.pem";
              ssl_certificate_key "/etc/ssl/private/{{{{ FAUCET_SSL_CN }}}}.pem";
              include /etc/nginx/snippets/ssl-params.conf;
              access_log /var/log/nginx/access.log;
              location / {{
                  proxy_hide_header X-Powered-By;
                  proxy_pass_header Authorization;
                  proxy_set_header Upgrade $http_upgrade;
                  proxy_set_header Host $host;
                  proxy_set_header X-Real-IP $remote_addr;
                  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                  proxy_set_header X-Forwarded-Host $host;
                  proxy_set_header X-Forwarded-Proto $scheme;
                  proxy_http_version 1.1;
                  proxy_set_header Connection "upgrade";
                  proxy_read_timeout 90s;
                  proxy_redirect off;
                  proxy_pass http://{{{{ FAUCET_IP }}}}:{{{{ FAUCET_PORT }}}};
                  proxy_cache_bypass $http_upgrade;
              }}
          }}
  - name: Link Faucet proxy
    command:
      cmd: "ln -s /etc/nginx/sites-available/{{{{ FAUCET_SSL_CN }}}}_proxy.conf /etc/nginx/sites-enabled/{{{{ FAUCET_SSL_CN }}}}_proxy.conf"
    ignore_errors: yes
  # Debug reverse proxy
  - name: Delete existing Debug conf
    file:
      path: "/etc/nginx/sites-available/{{{{ DEBUG_SSL_CN }}}}_proxy.conf"
      state: absent
  - name: Create Debug conf file
    file:
      path: "/etc/nginx/sites-available/{{{{ DEBUG_SSL_CN }}}}_proxy.conf"
      state: touch
  - name: Write Debug proxy config
    blockinfile:
        path: "/etc/nginx/sites-available/{{{{ DEBUG_SSL_CN }}}}_proxy.conf"
        marker: ""
        block: |
          server {{
              listen 80;
              server_name "{{{{ DEBUG_SSL_CN }}}}";
              return 301 https://$host$request_uri;
          }}
          server {{
              listen 443 ssl;
              server_name "{{{{ DEBUG_SSL_CN }}}}";
              ssl_certificate "/etc/ssl/certs/{{{{ DEBUG_SSL_CN }}}}.csr.pem";
              ssl_certificate_key "/etc/ssl/private/{{{{ DEBUG_SSL_CN }}}}.pem";
              include /etc/nginx/snippets/ssl-params.conf;
              access_log /var/log/nginx/access.log;
              location / {{
                  proxy_hide_header X-Powered-By;
                  proxy_pass_header Authorization;
                  proxy_set_header Upgrade $http_upgrade;
                  proxy_set_header Host $host;
                  proxy_set_header X-Real-IP $remote_addr;
                  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                  proxy_set_header X-Forwarded-Host $host;
                  proxy_set_header X-Forwarded-Proto $scheme;
                  proxy_http_version 1.1;
                  proxy_set_header Connection "upgrade";
                  proxy_read_timeout 90s;
                  proxy_redirect off;
                  proxy_pass http://{{{{ DEBUG_IP }}}}:{{{{ DEBUG_PORT }}}};
                  proxy_cache_bypass $http_upgrade;
              }}
          }}
  - name: Link Debug proxy
    command:
      cmd: "ln -s /etc/nginx/sites-available/{{{{ DEBUG_SSL_CN }}}}_proxy.conf /etc/nginx/sites-enabled/{{{{ DEBUG_SSL_CN }}}}_proxy.conf"
    ignore_errors: yes
  # Compiler reverse proxy
  - name: Delete existing Compiler conf
    file:
      path: "/etc/nginx/sites-available/{{{{ COMPILER_SSL_CN }}}}_proxy.conf"
      state: absent
  - name: Create Compiler conf file
    file:
      path: "/etc/nginx/sites-available/{{{{ COMPILER_SSL_CN }}}}_proxy.conf"
      state: touch
  - name: Write Compiler proxy config
    blockinfile:
        path: "/etc/nginx/sites-available/{{{{ COMPILER_SSL_CN }}}}_proxy.conf"
        marker: ""
        block: |
          server {{
              listen 80;
              server_name "{{{{ COMPILER_SSL_CN }}}}";
              return 301 https://$host$request_uri;
          }}
          server {{
              listen 443 ssl;
              server_name "{{{{ COMPILER_SSL_CN }}}}";
              ssl_certificate "/etc/ssl/certs/{{{{ COMPILER_SSL_CN }}}}.csr.pem";
              ssl_certificate_key "/etc/ssl/private/{{{{ COMPILER_SSL_CN }}}}.pem";
              include /etc/nginx/snippets/ssl-params.conf;
              access_log /var/log/nginx/access.log;
              location / {{
                  proxy_hide_header X-Powered-By;
                  proxy_pass_header Authorization;
                  proxy_set_header Upgrade $http_upgrade;
                  proxy_set_header Host $host;
                  proxy_set_header X-Real-IP $remote_addr;
                  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                  proxy_set_header X-Forwarded-Host $host;
                  proxy_set_header X-Forwarded-Proto $scheme;
                  proxy_http_version 1.1;
                  proxy_set_header Connection "upgrade";
                  proxy_read_timeout 90s;
                  proxy_redirect off;
                  proxy_pass http://{{{{ COMPILER_IP }}}}:{{{{ COMPILER_PORT }}}};
                  proxy_cache_bypass $http_upgrade;
              }}
          }}
  - name: Link Compiler proxy
    command:
      cmd: "ln -s /etc/nginx/sites-available/{{{{ COMPILER_SSL_CN }}}}_proxy.conf /etc/nginx/sites-enabled/{{{{ COMPILER_SSL_CN }}}}_proxy.conf"
    ignore_errors: yes
  - name: Restart NGINX
    service:
      name: nginx
      state: restarted
      enabled: yes
"""

# --- Service templates (use {group} placeholder for hosts: directive) ---

_REDIS_MAIN_TPL = """- hosts: {group}
  become: true
  remote_user: root

  vars_files:
    - vars.yml

  tasks:
  - name: set docker to use systemd cgroups driver
    copy:
      dest: "/etc/docker/daemon.json"
      content: |
        {{
          "exec-opts": ["native.cgroupdriver=systemd"]
        }}
  - name: Stop Docker Container
    command: docker stop "{{{{ docker_container_name }}}}"
    ignore_errors: yes
  - name: Remove Docker image
    command: docker rmi -f "{{{{ docker_image_name }}}}"
    ignore_errors: yes
  - name: Create Docker Network
    docker_network:
      name: "{{{{ docker_network_name }}}}"
      state: present
  - name: Pull Docker Image
    docker_image:
      name: "{{{{ docker_image_name }}}}"
      source: pull
  - name: Deploy Docker Image
    docker_container:
      name: "{{{{ docker_container_name }}}}"
      image: "{{{{ docker_image_name }}}}"
      networks:
        - name: "{{{{ docker_network_name }}}}"
      state: started
      restart_policy: always
      image_name_mismatch: recreate
"""

_FAUCET_MAIN_TPL = """- hosts: {group}
  become: true
  remote_user: root

  vars_files:
    - vars.yml

  tasks:
  - name: set docker to use systemd cgroups driver
    copy:
      dest: "/etc/docker/daemon.json"
      content: |
        {{
          "exec-opts": ["native.cgroupdriver=systemd"]
        }}
  - name: Remove Docker image
    command: docker rmi -f "{{{{ docker_image_name }}}}"
    ignore_errors: yes
  - name: Pull Docker Image
    docker_image:
      name: "{{{{ docker_image_name }}}}"
      source: pull
  - name: Deploy Docker Image
    docker_container:
      name: "{{{{ docker_container_name }}}}"
      image: "{{{{ docker_image_name }}}}"
      ports: "{{{{ docker_container_ports }}}}"
      env: "{{{{ docker_env_variables }}}}"
      state: started
      restart_policy: always
      image_name_mismatch: recreate
"""

_STREAM_MAIN_TPL = """---
- hosts: {group}
  become: true
  remote_user: root

  vars_files:
    - vars.yml

  tasks:
  - name: Download websocketd
    get_url:
      url: "https://github.com/joewalnes/websocketd/releases/download/v0.4.1/websocketd-0.4.1-linux_amd64.zip"
      dest: "/tmp/websocketd.zip"
  - name: Install unzip
    package:
      name: unzip
      state: present
  - name: Unzip websocketd
    unarchive:
      src: "/tmp/websocketd.zip"
      dest: "/usr/local/bin/"
      remote_src: yes
  - name: Make websocketd executable
    file:
      path: "/usr/local/bin/websocketd"
      mode: '0755'
  - name: Create log viewer script
    copy:
      dest: "/usr/local/bin/node-logviewer.sh"
      mode: '0755'
      content: |
        #!/bin/bash
        docker exec {{{{ docker_container_name }}}} tail -f {{{{ log_path }}}}
  - name: Create systemd service
    copy:
      dest: "/etc/systemd/system/websocketd-node-logs.service"
      content: |
        [Unit]
        Description=WebSocket Log Viewer for node
        After=docker.service
        Requires=docker.service

        [Service]
        Type=simple
        ExecStart=/usr/local/bin/websocketd --port={{{{ websocketd_port }}}} /usr/local/bin/node-logviewer.sh
        Restart=always
        RestartSec=10

        [Install]
        WantedBy=multi-user.target
  - name: Reload systemd
    systemd:
      daemon_reload: yes
  - name: Enable and start log viewer
    systemd:
      name: websocketd-node-logs
      enabled: yes
      state: restarted
"""

_DEBUG_MAIN_TPL = """- hosts: {group}
  become: true
  remote_user: root

  vars_files:
    - vars.yml

  tasks:
  - name: set docker to use systemd cgroups driver
    copy:
      dest: "/etc/docker/daemon.json"
      content: |
        {{
          "exec-opts": ["native.cgroupdriver=systemd"]
        }}
  - name: Remove Docker image
    command: docker rmi -f "{{{{ docker_image_name }}}}"
    ignore_errors: yes
  - name: Pull Docker Image
    docker_image:
      name: "{{{{ docker_image_name }}}}"
      source: pull
  - name: Deploy Docker Image
    docker_container:
      name: "{{{{ docker_container_name }}}}"
      image: "{{{{ docker_image_name }}}}"
      ports: "{{{{ docker_container_ports }}}}"
      env: "{{{{ docker_env_variables }}}}"
      networks:
        - name: "{{{{ docker_network_name }}}}"
      state: started
      restart_policy: always
      image_name_mismatch: recreate
"""

_COMPILER_MAIN_TPL = """---
- hosts: {group}
  become: true
  remote_user: root

  vars_files:
    - vars.yml

  tasks:
  - name: set docker to use systemd cgroups driver
    ansible.builtin.copy:
      dest: "/etc/docker/daemon.json"
      content: |
        {{
          "exec-opts": ["native.cgroupdriver=systemd"]
        }}
  - name: Remove existing repository directory
    ansible.builtin.file:
      path: /opt/xrpl-hooks-compiler
      state: absent
  - name: Clone repository
    ansible.builtin.git:
      repo: "{{{{ compiler_repo }}}}"
      dest: /opt/xrpl-hooks-compiler
      version: "{{{{ compiler_branch }}}}"
      force: yes
      accept_hostkey: yes
      key_file: /root/.ssh/github
    environment:
      GIT_SSH_COMMAND: "ssh -i /root/.ssh/github -o StrictHostKeyChecking=accept-new"
  - name: Run Make
    ansible.builtin.shell: make 2>&1
    args:
      chdir: /opt/xrpl-hooks-compiler/docker
      executable: /bin/bash
    changed_when: true
  - name: Build Docker image locally
    community.docker.docker_image:
      name: "{{{{ docker_image_name }}}}"
      source: build
      build:
        path: /opt/xrpl-hooks-compiler/docker
        dockerfile: .
        platform: linux/x86_64
        nocache: yes
        args:
          APP_ENV: production
          APP_PORT: "5002"
      state: present
      force_source: yes
      timeout: 900
  - name: Stop Docker Container
    ansible.builtin.command: docker stop "{{{{ docker_container_name }}}}"
    ignore_errors: yes
  - name: Deploy Docker Image
    community.docker.docker_container:
      name: "{{{{ docker_container_name }}}}"
      image: "{{{{ docker_image_name }}}}"
      ports: "{{{{ docker_container_ports }}}}"
      env: "{{{{ docker_env_variables }}}}"
      state: started
      restart_policy: always
      image_name_mismatch: recreate
"""
