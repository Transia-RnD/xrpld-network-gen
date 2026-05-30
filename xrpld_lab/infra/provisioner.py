"""GCP provisioning via terraform.

Renders ``terraform.tfvars`` from a :class:`GcpConfig`, runs terraform against
the bundled module (``infra/gcp``), and harvests the ephemeral IPs. The IPs go
straight into the lab's existing ansible pipeline as ``vips``/``pips`` — this is
the "we don't have the IP until we terraform" step.

Terraform state lives in the cluster's ``infra/`` dir, so a later ``destroy``
(or re-apply) finds it. Requires the ``terraform`` binary and authenticated
gcloud Application Default Credentials.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import List, Tuple

from xrpld_lab.models import GcpConfig

# The bundled terraform module shipped with the package.
_MODULE_DIR = os.path.join(os.path.dirname(__file__), "gcp")
_MODULE_FILES = ("main.tf", "variables.tf", "outputs.tf")


def _hcl_list(items: List[str]) -> str:
    """Render a Python list of strings as an HCL string list."""
    return "[" + ", ".join(json.dumps(i) for i in items) + "]"


def render_tfvars(gcp: GcpConfig, cluster: str) -> str:
    """Render terraform.tfvars from a GcpConfig. Pure — unit-testable."""
    lines = [
        f"project         = {json.dumps(gcp.project)}",
        f"region          = {json.dumps(gcp.region)}",
        f"cluster         = {json.dumps(cluster)}",
        f"validator_zones = {_hcl_list(gcp.validator_zones)}",
        f"peer_zones      = {_hcl_list(gcp.peer_zones)}",
        f"machine_type    = {json.dumps(gcp.machine_type)}",
        f"disk_gb         = {gcp.disk_gb}",
        f"image           = {json.dumps(gcp.image)}",
        f"ssh_user        = {json.dumps(gcp.ssh_user)}",
        f"ssh_pubkey_path = {json.dumps(os.path.expanduser(gcp.ssh_pubkey_path))}",
        f"network_tag     = {json.dumps(gcp.network_tag)}",
        f"allowed_source_ranges = {_hcl_list(gcp.allowed_source_ranges)}",
        f"open_tcp_ports  = {_hcl_list(gcp.open_tcp_ports)}",
    ]
    return "\n".join(lines) + "\n"


def harvest_ips(output_json: dict) -> Tuple[List[str], List[str]]:
    """Parse ``terraform output -json`` into (validator_ips, peer_ips). Pure."""
    vips = list(output_json.get("validator_ips", {}).get("value", []) or [])
    pips = list(output_json.get("peer_ips", {}).get("value", []) or [])
    return vips, pips


class GcpProvisioner:
    """Drives terraform for one cluster's ``infra/`` working dir."""

    def __init__(self, gcp: GcpConfig, cluster: str, work_dir: str):
        self.gcp = gcp
        self.cluster = cluster
        self.work_dir = work_dir  # <cluster_dir>/infra

    # -- file staging ---------------------------------------------------

    def write(self) -> str:
        """Stage the terraform module + rendered tfvars into work_dir."""
        os.makedirs(self.work_dir, exist_ok=True)
        for fname in _MODULE_FILES:
            shutil.copy2(os.path.join(_MODULE_DIR, fname),
                         os.path.join(self.work_dir, fname))
        with open(os.path.join(self.work_dir, "terraform.tfvars"), "w") as f:
            f.write(render_tfvars(self.gcp, self.cluster))
        return self.work_dir

    # -- terraform ------------------------------------------------------

    def _terraform(self, *args: str, capture: bool = False) -> subprocess.CompletedProcess:
        if shutil.which("terraform") is None:
            raise RuntimeError(
                "terraform not found on PATH. Install it (and authenticate "
                "gcloud ADC) to provision GCP, or run with --no-apply to only "
                "generate the module."
            )
        return subprocess.run(
            ["terraform", f"-chdir={self.work_dir}", *args],
            check=True,
            text=True,
            capture_output=capture,
        )

    def provision(self) -> Tuple[List[str], List[str]]:
        """init + apply, then harvest IPs. Returns (vips, pips)."""
        self.write()
        self._terraform("init", "-input=false")
        self._terraform("apply", "-auto-approve", "-input=false")
        out = self._terraform("output", "-json", capture=True)
        return harvest_ips(json.loads(out.stdout))

    def destroy(self) -> None:
        self._terraform("destroy", "-auto-approve", "-input=false")
