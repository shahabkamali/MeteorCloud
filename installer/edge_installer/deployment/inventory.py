"""Ansible inventory generation."""

from __future__ import annotations

from pathlib import Path

from edge_installer.config.models import InstallationConfig
from edge_installer.providers.aws.outputs import TerraformOutputs


def write_inventory(
    *,
    path: Path,
    outputs: TerraformOutputs,
    config: InstallationConfig,
) -> None:
    key_path = Path(config.aws.ssh_private_key_path).expanduser()
    host = outputs.connect_ip
    content = (
        "[platform]\n"
        f"platform ansible_host={host} "
        f"ansible_user={outputs.ssh_username} "
        f"ansible_ssh_private_key_file={key_path}\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
