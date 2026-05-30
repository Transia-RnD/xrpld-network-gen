#!/usr/bin/env python
# coding: utf-8

import os

from xrpld_lab.models import GcpConfig
from xrpld_lab.infra.provisioner import GcpProvisioner, harvest_ips, render_tfvars


def _gcp(**kw) -> GcpConfig:
    base = dict(
        project="my-proj",
        validator_zones=["us-central1-a", "europe-west1-b"],
        peer_zones=["us-west1-a"],
    )
    base.update(kw)
    return GcpConfig(**base)


# ---------------------------------------------------------------------------
# render_tfvars
# ---------------------------------------------------------------------------


class TestTfvars:
    def test_core_values(self):
        tf = render_tfvars(_gcp(), "perf1")
        assert 'project         = "my-proj"' in tf
        assert 'cluster         = "perf1"' in tf
        assert 'machine_type    = "n2-standard-8"' in tf
        assert "disk_gb         = 100" in tf

    def test_zone_lists_are_hcl(self):
        tf = render_tfvars(_gcp(), "perf1")
        assert 'validator_zones = ["us-central1-a", "europe-west1-b"]' in tf
        assert 'peer_zones      = ["us-west1-a"]' in tf

    def test_region_derived_from_first_validator_zone(self):
        tf = render_tfvars(_gcp(), "perf1")
        assert 'region          = "us-central1"' in tf

    def test_pubkey_path_expanded(self):
        tf = render_tfvars(_gcp(ssh_pubkey_path="~/.ssh/id_rsa.pub"), "perf1")
        assert "~" not in tf.split("ssh_pubkey_path")[1].split("\n")[0]

    def test_open_ports_default(self):
        tf = render_tfvars(_gcp(), "perf1")
        assert '"51235-51740"' in tf
        assert '"22"' in tf


# ---------------------------------------------------------------------------
# harvest_ips
# ---------------------------------------------------------------------------


class TestHarvest:
    def test_parses_terraform_output(self):
        out = {
            "validator_ips": {"value": ["1.1.1.1", "2.2.2.2"]},
            "peer_ips": {"value": ["3.3.3.3"]},
        }
        vips, pips = harvest_ips(out)
        assert vips == ["1.1.1.1", "2.2.2.2"]
        assert pips == ["3.3.3.3"]

    def test_missing_keys_yield_empty(self):
        vips, pips = harvest_ips({})
        assert vips == [] and pips == []

    def test_null_value_yields_empty(self):
        vips, pips = harvest_ips({"validator_ips": {"value": None}, "peer_ips": {}})
        assert vips == [] and pips == []


# ---------------------------------------------------------------------------
# GcpProvisioner.write (stages module + tfvars, no terraform needed)
# ---------------------------------------------------------------------------


class TestWrite:
    def test_stages_module_and_tfvars(self, tmp_path):
        work = str(tmp_path / "infra")
        prov = GcpProvisioner(_gcp(), "perf1", work)
        prov.write()
        for fname in ("main.tf", "variables.tf", "outputs.tf", "terraform.tfvars"):
            assert os.path.isfile(os.path.join(work, fname)), fname
        with open(os.path.join(work, "terraform.tfvars")) as f:
            assert 'project         = "my-proj"' in f.read()


# ---------------------------------------------------------------------------
# GcpConfig derived properties
# ---------------------------------------------------------------------------


class TestGcpConfig:
    def test_counts_track_zones(self):
        g = _gcp(validator_zones=["a-a", "b-b", "c-c"], peer_zones=["d-d"])
        assert g.num_validators == 3
        assert g.num_peers == 1

    def test_region_strips_zone_suffix(self):
        assert _gcp(validator_zones=["asia-east1-a"]).region == "asia-east1"
