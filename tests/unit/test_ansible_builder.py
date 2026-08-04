#!/usr/bin/env python
# coding: utf-8

import os
import yaml
import pytest

from xrpld_lab.models import (
    AnsibleConfig,
    NginxConfig,
    RedisConfig,
    FaucetConfig,
    StreamConfig,
    DebugConfig,
    CompilerConfig,
    PortSet,
    NodeRole,
    ServicesHost,
)
from xrpld_lab.ansible_builder import AnsibleBuilder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validator_ports(index: int = 1) -> PortSet:
    return PortSet.for_node(index, NodeRole.VALIDATOR)


def _peer_ports(index: int = 1) -> PortSet:
    return PortSet.for_node(index, NodeRole.PEER)


def _basic_config() -> AnsibleConfig:
    return AnsibleConfig(
        ssh_port=20,
        ssh_user="ubuntu",
        ssh_key_path="~/.ssh/id_rsa",
        vips=["10.0.0.1", "10.0.0.2"],
        pips=["10.0.0.10"],
    )


def _build_basic(tmp_path) -> AnsibleBuilder:
    cluster_dir = str(tmp_path / "test-cluster")
    os.makedirs(cluster_dir, exist_ok=True)
    config = _basic_config()
    builder = AnsibleBuilder(
        cluster_dir=cluster_dir,
        config=config,
        image_name="transia/cluster:abc123",
    )
    builder.add_node("vnode1", "10.0.0.1", _validator_ports(1), f"{cluster_dir}/vnode1/config/", "validator")
    builder.add_node("vnode2", "10.0.0.2", _validator_ports(2), f"{cluster_dir}/vnode2/config/", "validator")
    builder.add_node("pnode1", "10.0.0.10", _peer_ports(1), f"{cluster_dir}/pnode1/config/", "peer")
    return builder


def _services_host(name="proxy", ip="10.0.0.10", **kwargs) -> ServicesHost:
    return ServicesHost(name=name, ip=ip, **kwargs)


# ===========================================================================
# Core file generation
# ===========================================================================


class TestCoreFiles:
    def test_write_creates_ansible_dir(self, tmp_path):
        builder = _build_basic(tmp_path)
        result = builder.write()
        assert os.path.isdir(result)

    def test_write_creates_hosts_txt(self, tmp_path):
        builder = _build_basic(tmp_path)
        builder.write()
        assert os.path.exists(os.path.join(builder.ansible_dir, "hosts.txt"))

    def test_write_creates_host_vars(self, tmp_path):
        builder = _build_basic(tmp_path)
        builder.write()
        hv_dir = os.path.join(builder.ansible_dir, "host_vars")
        assert os.path.exists(os.path.join(hv_dir, "10.0.0.1.yml"))
        assert os.path.exists(os.path.join(hv_dir, "10.0.0.2.yml"))
        assert os.path.exists(os.path.join(hv_dir, "10.0.0.10.yml"))

    def test_write_creates_deps_yml(self, tmp_path):
        builder = _build_basic(tmp_path)
        builder.write()
        assert os.path.exists(os.path.join(builder.ansible_dir, "deps.yml"))

    def test_write_creates_main_yml(self, tmp_path):
        builder = _build_basic(tmp_path)
        builder.write()
        assert os.path.exists(os.path.join(builder.ansible_dir, "main.yml"))

    def test_write_creates_clean_yml(self, tmp_path):
        builder = _build_basic(tmp_path)
        builder.write()
        assert os.path.exists(os.path.join(builder.ansible_dir, "clean.yml"))

    def test_write_creates_clean_sh(self, tmp_path):
        builder = _build_basic(tmp_path)
        builder.write()
        path = os.path.join(builder.ansible_dir, "clean.sh")
        assert os.path.exists(path)
        assert os.access(path, os.X_OK)

    def test_write_creates_run_sh(self, tmp_path):
        builder = _build_basic(tmp_path)
        builder.write()
        path = os.path.join(builder.ansible_dir, "run.sh")
        assert os.path.exists(path)
        assert os.access(path, os.X_OK)


# ===========================================================================
# hosts.txt content
# ===========================================================================


class TestHostsTxt:
    def test_contains_all_ips(self, tmp_path):
        builder = _build_basic(tmp_path)
        builder.write()
        content = open(os.path.join(builder.ansible_dir, "hosts.txt")).read()
        assert "10.0.0.1" in content
        assert "10.0.0.2" in content
        assert "10.0.0.10" in content

    def test_has_all_group(self, tmp_path):
        builder = _build_basic(tmp_path)
        builder.write()
        content = open(os.path.join(builder.ansible_dir, "hosts.txt")).read()
        assert "[all]" in content

    def test_no_role_based_groups(self, tmp_path):
        builder = _build_basic(tmp_path)
        builder.write()
        content = open(os.path.join(builder.ansible_dir, "hosts.txt")).read()
        assert "[validator]" not in content
        assert content.count("[all]") == 1

    def test_ssh_settings(self, tmp_path):
        builder = _build_basic(tmp_path)
        builder.write()
        content = open(os.path.join(builder.ansible_dir, "hosts.txt")).read()
        assert "ansible_port=20" in content
        assert "ansible_user=ubuntu" in content
        assert "ansible_ssh_private_key_file=~/.ssh/id_rsa" in content

    def test_vars_file_in_host_line(self, tmp_path):
        builder = _build_basic(tmp_path)
        builder.write()
        content = open(os.path.join(builder.ansible_dir, "hosts.txt")).read()
        assert "vars_file=host_vars/10.0.0.1.yml" in content
        assert "vars_file=host_vars/10.0.0.10.yml" in content

    def test_services_host_group(self, tmp_path):
        cluster_dir = str(tmp_path / "test-cluster")
        os.makedirs(cluster_dir, exist_ok=True)
        config = AnsibleConfig(
            vips=["10.0.0.1"],
            pips=["10.0.0.10"],
            services=[_services_host("proxy", "10.0.0.10", nginx=NginxConfig(domain="test.example.com"))],
        )
        builder = AnsibleBuilder(cluster_dir, config, "transia/cluster:abc")
        builder.add_node("vnode1", "10.0.0.1", _validator_ports(1), f"{cluster_dir}/vnode1/config/", "validator")
        builder.add_node("pnode1", "10.0.0.10", _peer_ports(1), f"{cluster_dir}/pnode1/config/", "peer")
        builder.write()
        content = open(os.path.join(builder.ansible_dir, "hosts.txt")).read()
        assert "[proxy]" in content
        proxy_section = content.split("[proxy]")[1]
        assert "10.0.0.10" in proxy_section

    def test_multiple_services_host_groups(self, tmp_path):
        cluster_dir = str(tmp_path / "test-cluster")
        os.makedirs(cluster_dir, exist_ok=True)
        config = AnsibleConfig(
            vips=["10.0.0.1"],
            pips=["10.0.0.10", "10.0.0.11"],
            services=[
                _services_host("proxy", "10.0.0.10", nginx=NginxConfig(domain="a.example.com")),
                _services_host("infra", "10.0.0.11", redis=RedisConfig()),
            ],
        )
        builder = AnsibleBuilder(cluster_dir, config, "transia/cluster:abc")
        builder.add_node("vnode1", "10.0.0.1", _validator_ports(1), f"{cluster_dir}/vnode1/config/", "validator")
        builder.add_node("pnode1", "10.0.0.10", _peer_ports(1), f"{cluster_dir}/pnode1/config/", "peer")
        builder.add_node("pnode2", "10.0.0.11", _peer_ports(2), f"{cluster_dir}/pnode2/config/", "peer")
        builder.write()
        content = open(os.path.join(builder.ansible_dir, "hosts.txt")).read()
        assert "[proxy]" in content
        assert "[infra]" in content


# ===========================================================================
# host_vars content
# ===========================================================================


class TestHostVars:
    def test_validator_host_vars_structure(self, tmp_path):
        builder = _build_basic(tmp_path)
        builder.write()
        path = os.path.join(builder.ansible_dir, "host_vars", "10.0.0.1.yml")
        with open(path) as f:
            data = yaml.safe_load(f)

        assert data["docker_container_name"] == "vnode1"
        assert data["docker_image_name"] == "transia/cluster:abc123"
        assert data["docker_network_name"] == "loadnet"
        assert data["ssh_port"] == 20
        assert isinstance(data["docker_container_ports"], list)
        assert len(data["docker_container_ports"]) == 5

    def test_host_vars_has_env_variables(self, tmp_path):
        builder = _build_basic(tmp_path)
        builder.write()
        path = os.path.join(builder.ansible_dir, "host_vars", "10.0.0.1.yml")
        with open(path) as f:
            data = yaml.safe_load(f)

        env = data["docker_env_variables"]
        assert "RPC_PUBLIC" in env
        assert "RPC_ADMIN" in env
        assert "WS_PUBLIC" in env
        assert "WS_ADMIN" in env
        assert "PEER" in env

    def test_host_vars_has_volumes(self, tmp_path):
        builder = _build_basic(tmp_path)
        builder.write()
        path = os.path.join(builder.ansible_dir, "host_vars", "10.0.0.1.yml")
        with open(path) as f:
            data = yaml.safe_load(f)

        assert "/opt/ripple/config:/opt/ripple/config" in data["docker_volumes"]
        assert "/opt/ripple/config" in data["volumes"]

    def test_peer_host_vars(self, tmp_path):
        builder = _build_basic(tmp_path)
        builder.write()
        path = os.path.join(builder.ansible_dir, "host_vars", "10.0.0.10.yml")
        with open(path) as f:
            data = yaml.safe_load(f)

        assert data["docker_container_name"] == "pnode1"

    def test_config_path_set_correctly(self, tmp_path):
        builder = _build_basic(tmp_path)
        builder.write()
        path = os.path.join(builder.ansible_dir, "host_vars", "10.0.0.1.yml")
        with open(path) as f:
            data = yaml.safe_load(f)

        assert data["config_path"].endswith("/vnode1/config/")


# ===========================================================================
# run.sh content
# ===========================================================================


class TestRunSh:
    def test_has_run_once_function(self, tmp_path):
        builder = _build_basic(tmp_path)
        builder.write()
        content = open(os.path.join(builder.ansible_dir, "run.sh")).read()
        assert "run_once()" in content

    def test_has_run_always_function(self, tmp_path):
        builder = _build_basic(tmp_path)
        builder.write()
        content = open(os.path.join(builder.ansible_dir, "run.sh")).read()
        assert "run_always()" in content

    def test_deps_uses_run_once(self, tmp_path):
        builder = _build_basic(tmp_path)
        builder.write()
        content = open(os.path.join(builder.ansible_dir, "run.sh")).read()
        assert "run_once deps deps.yml" in content

    def test_main_uses_run_always(self, tmp_path):
        builder = _build_basic(tmp_path)
        builder.write()
        content = open(os.path.join(builder.ansible_dir, "run.sh")).read()
        assert "run_always main.yml" in content

    def test_has_force_flag(self, tmp_path):
        builder = _build_basic(tmp_path)
        builder.write()
        content = open(os.path.join(builder.ansible_dir, "run.sh")).read()
        assert "--force" in content

    def test_checks_done_marker(self, tmp_path):
        builder = _build_basic(tmp_path)
        builder.write()
        content = open(os.path.join(builder.ansible_dir, "run.sh")).read()
        assert ".done_" in content

    def test_no_optional_services_by_default(self, tmp_path):
        builder = _build_basic(tmp_path)
        builder.write()
        content = open(os.path.join(builder.ansible_dir, "run.sh")).read()
        assert "nginx" not in content
        assert "redis" not in content
        assert "faucet" not in content


# ===========================================================================
# Optional services: not created when not configured
# ===========================================================================


class TestOptionalServicesAbsent:
    def test_no_services_dir(self, tmp_path):
        builder = _build_basic(tmp_path)
        builder.write()
        assert not os.path.exists(os.path.join(builder.ansible_dir, "services"))

    def test_no_nginx_dir(self, tmp_path):
        builder = _build_basic(tmp_path)
        builder.write()
        assert not os.path.exists(os.path.join(builder.ansible_dir, "nginx"))

    def test_no_redis_dir(self, tmp_path):
        builder = _build_basic(tmp_path)
        builder.write()
        assert not os.path.exists(os.path.join(builder.ansible_dir, "redis"))

    def test_no_faucet_dir(self, tmp_path):
        builder = _build_basic(tmp_path)
        builder.write()
        assert not os.path.exists(os.path.join(builder.ansible_dir, "faucet"))

    def test_no_stream_dir(self, tmp_path):
        builder = _build_basic(tmp_path)
        builder.write()
        assert not os.path.exists(os.path.join(builder.ansible_dir, "stream"))

    def test_no_debug_dir(self, tmp_path):
        builder = _build_basic(tmp_path)
        builder.write()
        assert not os.path.exists(os.path.join(builder.ansible_dir, "debug"))

    def test_no_compiler_dir(self, tmp_path):
        builder = _build_basic(tmp_path)
        builder.write()
        assert not os.path.exists(os.path.join(builder.ansible_dir, "compiler"))


# ===========================================================================
# Optional: Nginx
# ===========================================================================


class TestNginx:
    def _builder_with_nginx(self, tmp_path):
        cluster_dir = str(tmp_path / "test-cluster")
        os.makedirs(cluster_dir, exist_ok=True)
        config = AnsibleConfig(
            vips=["10.0.0.1"],
            pips=["10.0.0.10"],
            services=[
                ServicesHost(
                    name="proxy",
                    ip="10.0.0.10",
                    nginx=NginxConfig(
                        domain="test.example.com",
                        ssl_org="TestOrg",
                        ssl_ou="TestOU",
                    ),
                ),
            ],
        )
        builder = AnsibleBuilder(cluster_dir, config, "transia/cluster:abc")
        builder.add_node("vnode1", "10.0.0.1", _validator_ports(1), f"{cluster_dir}/vnode1/config/", "validator")
        builder.add_node("pnode1", "10.0.0.10", _peer_ports(1), f"{cluster_dir}/pnode1/config/", "peer")
        return builder

    def test_creates_nginx_dir(self, tmp_path):
        builder = self._builder_with_nginx(tmp_path)
        builder.write()
        assert os.path.isdir(os.path.join(builder.ansible_dir, "services", "proxy", "nginx"))

    def test_creates_nginx_deps(self, tmp_path):
        builder = self._builder_with_nginx(tmp_path)
        builder.write()
        assert os.path.exists(os.path.join(builder.ansible_dir, "services", "proxy", "nginx", "deps.yml"))

    def test_creates_nginx_ssl(self, tmp_path):
        builder = self._builder_with_nginx(tmp_path)
        builder.write()
        assert os.path.exists(os.path.join(builder.ansible_dir, "services", "proxy", "nginx", "ssl.yml"))

    def test_creates_nginx_main(self, tmp_path):
        builder = self._builder_with_nginx(tmp_path)
        builder.write()
        assert os.path.exists(os.path.join(builder.ansible_dir, "services", "proxy", "nginx", "main.yml"))

    def test_creates_nginx_vars(self, tmp_path):
        builder = self._builder_with_nginx(tmp_path)
        builder.write()
        path = os.path.join(builder.ansible_dir, "services", "proxy", "nginx", "vars.yml")
        assert os.path.exists(path)
        with open(path) as f:
            data = yaml.safe_load(f)
        assert data["SSL_CN"] == "test.example.com"
        assert data["SSL_O"] == "TestOrg"
        assert data["SSL_OU"] == "TestOU"
        assert data["RPC_SSL_CN"] == "rpc.test.example.com"
        assert data["FAUCET_SSL_CN"] == "faucet.test.example.com"

    def test_run_sh_includes_nginx(self, tmp_path):
        builder = self._builder_with_nginx(tmp_path)
        builder.write()
        content = open(os.path.join(builder.ansible_dir, "run.sh")).read()
        assert "services/proxy/nginx/deps.yml" in content
        assert "services/proxy/nginx/ssl.yml" in content
        assert "services/proxy/nginx/main.yml" in content

    def test_nginx_playbook_targets_host_group(self, tmp_path):
        builder = self._builder_with_nginx(tmp_path)
        builder.write()
        path = os.path.join(builder.ansible_dir, "services", "proxy", "nginx", "main.yml")
        content = open(path).read()
        assert "hosts: proxy" in content

    def test_ssl_all_selfsigned_by_default(self, tmp_path):
        builder = self._builder_with_nginx(tmp_path)
        builder.write()
        path = os.path.join(builder.ansible_dir, "services", "proxy", "nginx", "ssl.yml")
        content = open(path).read()
        assert "certbot" not in content
        for label in ("WSS", "RPC", "Faucet", "Debug", "Compiler"):
            assert f"Create {label} self-signed certificate" in content


class TestNginxLetsEncrypt:
    def _builder(self, tmp_path, **nginx_kwargs):
        cluster_dir = str(tmp_path / "test-cluster")
        os.makedirs(cluster_dir, exist_ok=True)
        config = AnsibleConfig(
            vips=["10.0.0.1"],
            pips=["10.0.0.10"],
            services=[
                ServicesHost(
                    name="proxy",
                    ip="10.0.0.10",
                    nginx=NginxConfig(
                        domain="test.example.com",
                        ssl_org="TestOrg",
                        ssl_ou="TestOU",
                        **nginx_kwargs,
                    ),
                ),
            ],
        )
        builder = AnsibleBuilder(cluster_dir, config, "transia/cluster:abc")
        builder.add_node("vnode1", "10.0.0.1", _validator_ports(1), f"{cluster_dir}/vnode1/config/", "validator")
        builder.add_node("pnode1", "10.0.0.10", _peer_ports(1), f"{cluster_dir}/pnode1/config/", "peer")
        return builder

    def test_ssl_yml_issues_letsencrypt_for_selected_services(self, tmp_path):
        builder = self._builder(
            tmp_path,
            letsencrypt_services=["rpc", "faucet"],
            letsencrypt_email="ops@example.com",
        )
        builder.write()
        path = os.path.join(builder.ansible_dir, "services", "proxy", "nginx", "ssl.yml")
        content = open(path).read()
        assert "Install certbot" in content
        assert "-m ops@example.com --cert-name rpc.test.example.com -d rpc.test.example.com" in content
        assert "--cert-name faucet.test.example.com -d faucet.test.example.com" in content
        # LE services get no self-signed cert; the rest keep theirs
        assert "Create RPC self-signed certificate" not in content
        assert "Create Faucet self-signed certificate" not in content
        assert "Create WSS self-signed certificate" in content
        assert "Create Debug self-signed certificate" in content
        assert "Create Compiler self-signed certificate" in content

    def test_vars_point_at_letsencrypt_paths(self, tmp_path):
        builder = self._builder(tmp_path, letsencrypt_services=["rpc", "faucet"])
        builder.write()
        path = os.path.join(builder.ansible_dir, "services", "proxy", "nginx", "vars.yml")
        with open(path) as f:
            data = yaml.safe_load(f)
        assert data["RPC_SSL_CERT"] == "/etc/letsencrypt/live/rpc.test.example.com/fullchain.pem"
        assert data["RPC_SSL_KEY"] == "/etc/letsencrypt/live/rpc.test.example.com/privkey.pem"
        assert data["FAUCET_SSL_CERT"] == "/etc/letsencrypt/live/faucet.test.example.com/fullchain.pem"
        assert data["FAUCET_SSL_KEY"] == "/etc/letsencrypt/live/faucet.test.example.com/privkey.pem"
        # untouched services keep self-signed paths
        assert data["SSL_CERT"] == "/etc/ssl/certs/test.example.com.csr.pem"
        assert data["DEBUG_SSL_CERT"] == "/etc/ssl/certs/debug.test.example.com.csr.pem"

    def test_no_email_registers_unsafely(self, tmp_path):
        builder = self._builder(tmp_path, letsencrypt_services=["rpc"])
        builder.write()
        path = os.path.join(builder.ansible_dir, "services", "proxy", "nginx", "ssl.yml")
        content = open(path).read()
        assert "--register-unsafely-without-email" in content

    def test_wss_uses_bare_domain(self, tmp_path):
        builder = self._builder(tmp_path, letsencrypt_services=["wss"])
        builder.write()
        path = os.path.join(builder.ansible_dir, "services", "proxy", "nginx", "vars.yml")
        with open(path) as f:
            data = yaml.safe_load(f)
        assert data["SSL_CERT"] == "/etc/letsencrypt/live/test.example.com/fullchain.pem"

    def test_unknown_service_raises(self, tmp_path):
        builder = self._builder(tmp_path, letsencrypt_services=["bogus"])
        with pytest.raises(ValueError, match="bogus"):
            builder.write()

    def test_ssl_yml_is_valid_yaml(self, tmp_path):
        builder = self._builder(
            tmp_path,
            letsencrypt_services=["rpc", "faucet"],
            letsencrypt_email="ops@example.com",
        )
        builder.write()
        path = os.path.join(builder.ansible_dir, "services", "proxy", "nginx", "ssl.yml")
        with open(path) as f:
            plays = yaml.safe_load(f)
        assert plays[0]["hosts"] == "proxy"
        assert any("certbot" in str(t.get("command", "")) for t in plays[0]["tasks"])


# ===========================================================================
# Optional: Redis
# ===========================================================================


class TestRedis:
    def test_creates_redis_files(self, tmp_path):
        cluster_dir = str(tmp_path / "test-cluster")
        os.makedirs(cluster_dir, exist_ok=True)
        config = AnsibleConfig(
            vips=["10.0.0.1"],
            pips=["10.0.0.10"],
            services=[
                ServicesHost(name="infra", ip="10.0.0.10", redis=RedisConfig()),
            ],
        )
        builder = AnsibleBuilder(cluster_dir, config, "transia/cluster:abc")
        builder.add_node("vnode1", "10.0.0.1", _validator_ports(1), f"{cluster_dir}/vnode1/config/", "validator")
        builder.add_node("pnode1", "10.0.0.10", _peer_ports(1), f"{cluster_dir}/pnode1/config/", "peer")
        builder.write()

        assert os.path.exists(os.path.join(builder.ansible_dir, "services", "infra", "redis", "main.yml"))
        assert os.path.exists(os.path.join(builder.ansible_dir, "services", "infra", "redis", "vars.yml"))

        with open(os.path.join(builder.ansible_dir, "services", "infra", "redis", "vars.yml")) as f:
            data = yaml.safe_load(f)
        assert data["docker_image_name"] == "redis"
        assert data["docker_container_name"] == "alpha-redis-main"

    def test_redis_playbook_targets_host_group(self, tmp_path):
        cluster_dir = str(tmp_path / "test-cluster")
        os.makedirs(cluster_dir, exist_ok=True)
        config = AnsibleConfig(
            vips=["10.0.0.1"],
            pips=["10.0.0.10"],
            services=[ServicesHost(name="infra", ip="10.0.0.10", redis=RedisConfig())],
        )
        builder = AnsibleBuilder(cluster_dir, config, "transia/cluster:abc")
        builder.add_node("vnode1", "10.0.0.1", _validator_ports(1), f"{cluster_dir}/vnode1/config/", "validator")
        builder.add_node("pnode1", "10.0.0.10", _peer_ports(1), f"{cluster_dir}/pnode1/config/", "peer")
        builder.write()
        content = open(os.path.join(builder.ansible_dir, "services", "infra", "redis", "main.yml")).read()
        assert "hosts: infra" in content


# ===========================================================================
# Optional: Faucet
# ===========================================================================


class TestFaucet:
    def test_creates_faucet_files(self, tmp_path):
        cluster_dir = str(tmp_path / "test-cluster")
        os.makedirs(cluster_dir, exist_ok=True)
        config = AnsibleConfig(
            vips=["10.0.0.1"],
            pips=["10.0.0.10"],
            services=[
                ServicesHost(
                    name="proxy",
                    ip="10.0.0.10",
                    faucet=FaucetConfig(
                        ws_url="wss://test.example.com",
                        network_id="21337",
                        seed="sEdTest",
                    ),
                ),
            ],
        )
        builder = AnsibleBuilder(cluster_dir, config, "transia/cluster:abc")
        builder.add_node("vnode1", "10.0.0.1", _validator_ports(1), f"{cluster_dir}/vnode1/config/", "validator")
        builder.add_node("pnode1", "10.0.0.10", _peer_ports(1), f"{cluster_dir}/pnode1/config/", "peer")
        builder.write()

        assert os.path.exists(os.path.join(builder.ansible_dir, "services", "proxy", "faucet", "main.yml"))
        with open(os.path.join(builder.ansible_dir, "services", "proxy", "faucet", "vars.yml")) as f:
            data = yaml.safe_load(f)
        assert data["docker_env_variables"]["XRPL_FAUCET_URL"] == "wss://test.example.com"
        assert data["docker_env_variables"]["XRPL_NETWORK_ID"] == "21337"


# ===========================================================================
# Optional: Stream
# ===========================================================================


class TestStream:
    def test_creates_stream_files(self, tmp_path):
        cluster_dir = str(tmp_path / "test-cluster")
        os.makedirs(cluster_dir, exist_ok=True)
        config = AnsibleConfig(
            vips=["10.0.0.1"],
            pips=["10.0.0.10"],
            services=[
                ServicesHost(
                    name="proxy",
                    ip="10.0.0.10",
                    stream=StreamConfig(port=1400, container_name="pnode1"),
                ),
            ],
        )
        builder = AnsibleBuilder(cluster_dir, config, "transia/cluster:abc")
        builder.add_node("vnode1", "10.0.0.1", _validator_ports(1), f"{cluster_dir}/vnode1/config/", "validator")
        builder.add_node("pnode1", "10.0.0.10", _peer_ports(1), f"{cluster_dir}/pnode1/config/", "peer")
        builder.write()

        assert os.path.exists(os.path.join(builder.ansible_dir, "services", "proxy", "stream", "main.yml"))
        with open(os.path.join(builder.ansible_dir, "services", "proxy", "stream", "vars.yml")) as f:
            data = yaml.safe_load(f)
        assert data["websocketd_port"] == 1400
        assert data["docker_container_name"] == "pnode1"


# ===========================================================================
# Optional: Debug
# ===========================================================================


class TestDebug:
    def test_creates_debug_files(self, tmp_path):
        cluster_dir = str(tmp_path / "test-cluster")
        os.makedirs(cluster_dir, exist_ok=True)
        config = AnsibleConfig(
            vips=["10.0.0.1"],
            pips=["10.0.0.10"],
            services=[
                ServicesHost(
                    name="proxy",
                    ip="10.0.0.10",
                    stream=StreamConfig(port=1400),
                    debug=DebugConfig(endpoint="ws://10.0.0.10:1400/"),
                ),
            ],
        )
        builder = AnsibleBuilder(cluster_dir, config, "transia/cluster:abc")
        builder.add_node("vnode1", "10.0.0.1", _validator_ports(1), f"{cluster_dir}/vnode1/config/", "validator")
        builder.add_node("pnode1", "10.0.0.10", _peer_ports(1), f"{cluster_dir}/pnode1/config/", "peer")
        builder.write()

        assert os.path.exists(os.path.join(builder.ansible_dir, "services", "proxy", "debug", "main.yml"))
        with open(os.path.join(builder.ansible_dir, "services", "proxy", "debug", "vars.yml")) as f:
            data = yaml.safe_load(f)
        assert data["docker_image_name"] == "transia/debugstream"
        assert data["docker_env_variables"]["ENDPOINT"] == "ws://10.0.0.10:1400/"


# ===========================================================================
# Optional: Compiler
# ===========================================================================


class TestCompiler:
    def test_creates_compiler_files(self, tmp_path):
        cluster_dir = str(tmp_path / "test-cluster")
        os.makedirs(cluster_dir, exist_ok=True)
        config = AnsibleConfig(
            vips=["10.0.0.1"],
            pips=["10.0.0.10"],
            services=[
                ServicesHost(name="infra", ip="10.0.0.10", compiler=CompilerConfig()),
            ],
        )
        builder = AnsibleBuilder(cluster_dir, config, "transia/cluster:abc")
        builder.add_node("vnode1", "10.0.0.1", _validator_ports(1), f"{cluster_dir}/vnode1/config/", "validator")
        builder.add_node("pnode1", "10.0.0.10", _peer_ports(1), f"{cluster_dir}/pnode1/config/", "peer")
        builder.write()

        assert os.path.exists(os.path.join(builder.ansible_dir, "services", "infra", "compiler", "main.yml"))
        with open(os.path.join(builder.ansible_dir, "services", "infra", "compiler", "vars.yml")) as f:
            data = yaml.safe_load(f)
        assert data["docker_image_name"] == "transia/compiler-api:latest"
        assert data["compiler_repo"] == "git@github.com:Transia-RnD/xrpl-hooks-compiler.git"


# ===========================================================================
# Full deployment with all services (multi-host)
# ===========================================================================


class TestFullDeployment:
    def test_all_services_enabled(self, tmp_path):
        cluster_dir = str(tmp_path / "full-cluster")
        os.makedirs(cluster_dir, exist_ok=True)
        config = AnsibleConfig(
            ssh_port=1988,
            ssh_user="root",
            ssh_key_path="~/.ssh/xrpl-labs",
            vips=["79.110.60.99", "79.110.60.100", "79.110.60.101"],
            pips=["79.110.60.105"],
            services=[
                ServicesHost(
                    name="proxy",
                    ip="79.110.60.105",
                    nginx=NginxConfig(
                        domain="alphanet.xrpl.org",
                        ssl_org="Transia LLC.",
                        ssl_ou="Transia RnD",
                    ),
                    faucet=FaucetConfig(
                        ws_url="wss://alphanet.xrpl.org",
                        network_id="21565",
                        seed="sEdTest",
                    ),
                    stream=StreamConfig(),
                    debug=DebugConfig(),
                ),
                ServicesHost(
                    name="infra",
                    ip="79.110.60.105",
                    redis=RedisConfig(),
                    compiler=CompilerConfig(),
                ),
            ],
        )
        builder = AnsibleBuilder(cluster_dir, config, "transia/cluster:abc123")
        for i, ip in enumerate(config.vips, 1):
            builder.add_node(f"vnode{i}", ip, _validator_ports(i), f"{cluster_dir}/vnode{i}/config/", "validator")
        for i, ip in enumerate(config.pips, 1):
            builder.add_node(f"pnode{i}", ip, _peer_ports(i), f"{cluster_dir}/pnode{i}/config/", "peer")
        builder.write()

        run_sh = open(os.path.join(builder.ansible_dir, "run.sh")).read()
        assert "services/proxy/nginx/deps.yml" in run_sh
        assert "services/proxy/nginx/ssl.yml" in run_sh
        assert "services/proxy/nginx/main.yml" in run_sh
        assert "services/proxy/faucet/main.yml" in run_sh
        assert "services/proxy/stream/main.yml" in run_sh
        assert "services/proxy/debug/main.yml" in run_sh
        assert "services/infra/redis/main.yml" in run_sh
        assert "services/infra/compiler/main.yml" in run_sh

        for svc in ["nginx", "faucet", "stream", "debug"]:
            assert os.path.isdir(os.path.join(builder.ansible_dir, "services", "proxy", svc))
        for svc in ["redis", "compiler"]:
            assert os.path.isdir(os.path.join(builder.ansible_dir, "services", "infra", svc))

        hosts = open(os.path.join(builder.ansible_dir, "hosts.txt")).read()
        assert "ansible_port=1988" in hosts
        assert "ansible_user=root" in hosts
        assert "ansible_ssh_private_key_file=~/.ssh/xrpl-labs" in hosts
        assert "79.110.60.99" in hosts
        assert "79.110.60.105" in hosts
        assert "[proxy]" in hosts
        assert "[infra]" in hosts

    def test_single_host_all_services(self, tmp_path):
        cluster_dir = str(tmp_path / "single-host")
        os.makedirs(cluster_dir, exist_ok=True)
        config = AnsibleConfig(
            vips=["10.0.0.1"],
            pips=["10.0.0.10"],
            services=[
                ServicesHost(
                    name="main",
                    ip="10.0.0.10",
                    nginx=NginxConfig(domain="test.example.com"),
                    redis=RedisConfig(),
                    faucet=FaucetConfig(ws_url="wss://test.example.com", network_id="21337", seed="sEdTest"),
                    stream=StreamConfig(),
                    debug=DebugConfig(),
                    compiler=CompilerConfig(),
                ),
            ],
        )
        builder = AnsibleBuilder(cluster_dir, config, "transia/cluster:abc")
        builder.add_node("vnode1", "10.0.0.1", _validator_ports(1), f"{cluster_dir}/vnode1/config/", "validator")
        builder.add_node("pnode1", "10.0.0.10", _peer_ports(1), f"{cluster_dir}/pnode1/config/", "peer")
        builder.write()

        for svc in ["nginx", "redis", "faucet", "stream", "debug", "compiler"]:
            assert os.path.isdir(os.path.join(builder.ansible_dir, "services", "main", svc))

        run_sh = open(os.path.join(builder.ansible_dir, "run.sh")).read()
        for svc in ["nginx", "redis", "faucet", "stream", "debug", "compiler"]:
            assert f"services/main/{svc}/main.yml" in run_sh


# ===========================================================================
# Chaining
# ===========================================================================


class TestChaining:
    def test_add_node_returns_self(self, tmp_path):
        cluster_dir = str(tmp_path / "test-cluster")
        os.makedirs(cluster_dir, exist_ok=True)
        config = _basic_config()
        builder = AnsibleBuilder(cluster_dir, config, "transia/cluster:abc")
        result = builder.add_node("vnode1", "10.0.0.1", _validator_ports(1), f"{cluster_dir}/vnode1/config/")
        assert result is builder
