"""Platform deployment orchestration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from edge_installer.config.models import InstallationConfig
from edge_installer.config.validation import ensure_valid
from edge_installer.deployment.ansible import AnsibleRunner
from edge_installer.deployment.environment import build_ansible_extra_vars, platform_url
from edge_installer.deployment.inventory import write_inventory
from edge_installer.deployment.ssh import wait_for_server
from edge_installer.exceptions import InstallerError
from edge_installer.health.service import HealthService
from edge_installer.providers.aws.outputs import TerraformOutputs
from edge_installer.providers.aws.provider import AwsEc2Provider
from edge_installer.state.models import InstallationState
from edge_installer.state.paths import installation_dir, installation_state_file
from edge_installer.state.store import InstallationLock, load_state, save_state

logger = logging.getLogger(__name__)

STAGES = (
    "Validating configuration",
    "Planning AWS infrastructure",
    "Creating EC2 instance",
    "Waiting for SSH",
    "Installing Docker",
    "Deploying platform",
    "Running migrations",
    "Verifying health",
)


@dataclass(frozen=True)
class ApplyResult:
    state: InstallationState
    outputs: TerraformOutputs
    health: dict[str, str]


class PlatformDeploymentService:
    def __init__(self, config: InstallationConfig) -> None:
        self.config = config
        self.provider = AwsEc2Provider(config)
        self.ansible = AnsibleRunner()
        self.health = HealthService()

    def validate(self) -> None:
        ensure_valid(self.config)

    def plan(self) -> dict[str, object]:
        self.validate()
        return self.provider.plan()

    def apply(self) -> ApplyResult:
        self.validate()
        name = self.config.installation.name
        with InstallationLock(name):
            logger.info("[1/8] %s", STAGES[0])
            outputs = self._apply_infrastructure()
            logger.info("[4/8] %s", STAGES[3])
            self._wait_for_ssh(outputs)
            logger.info("[5/8] %s", STAGES[4])
            self._provision_server(outputs)
            logger.info("[6/8] %s", STAGES[5])
            self._deploy_platform(outputs)
            logger.info("[7/8] %s", STAGES[6])
            url = platform_url(self.config, outputs)
            logger.info("[8/8] %s", STAGES[7])
            report = self.health.verify(
                url,
                timeout_seconds=self.config.deployment.health_check_timeout_seconds,
            )
            state = self._save_state(outputs, url, report.as_dict())
            return ApplyResult(state=state, outputs=outputs, health=report.as_dict())

    def status(self) -> dict[str, object]:
        state = load_state(self.config.installation.name)
        result: dict[str, object] = {"state": state.model_dump() if state else None}
        try:
            outputs = self.provider.terraform.read_outputs()
            result["infrastructure"] = outputs.model_dump()
            if state and state.platform_url:
                result["health"] = self.health.verify(
                    state.platform_url,
                    timeout_seconds=self.config.deployment.health_check_timeout_seconds,
                ).as_dict()
        except InstallerError:
            result["health"] = {"status": "unknown"}
        return result

    def upgrade(self) -> ApplyResult:
        state = load_state(self.config.installation.name)
        if state is None:
            raise InstallerError("Installation not found.", stage="upgrade")
        name = self.config.installation.name
        with InstallationLock(name):
            outputs = self.provider.terraform.read_outputs()
            extra = build_ansible_extra_vars(self.config, outputs)
            inventory = installation_dir(name) / "inventory.ini"
            write_inventory(path=inventory, outputs=outputs, config=self.config)
            self.ansible.run_playbook("upgrade.yml", inventory=inventory, extra_vars=extra)
            url = platform_url(self.config, outputs)
            report = self.health.verify(
                url,
                timeout_seconds=self.config.deployment.health_check_timeout_seconds,
            )
            state.platform_version = self.config.platform.version
            state.updated_at = datetime.now(UTC)
            save_state(state)
            return ApplyResult(state=state, outputs=outputs, health=report.as_dict())

    def destroy(self) -> None:
        name = self.config.installation.name
        with InstallationLock(name):
            try:
                state = load_state(name)
                if state and state.public_ip:
                    outputs = TerraformOutputs(
                        instance_id=state.instance_id or "",
                        public_ip=state.public_ip,
                        elastic_ip=state.elastic_ip or "",
                        private_ip="",
                        region=state.region,
                        ssh_username="ubuntu",
                        security_group_id="",
                    )
                    inventory = installation_dir(name) / "inventory.ini"
                    write_inventory(path=inventory, outputs=outputs, config=self.config)
                    self.ansible.run_playbook(
                        "destroy.yml",
                        inventory=inventory,
                        extra_vars={"installation_name": name},
                    )
            except InstallerError:
                logger.warning("Remote destroy playbook skipped or failed.")
            self.provider.destroy()
            state_path = installation_state_file(name)
            state_path.unlink(missing_ok=True)

    def _apply_infrastructure(self) -> TerraformOutputs:
        logger.info("[2/8] %s", STAGES[1])
        self.provider.terraform.init()
        logger.info("[3/8] %s", STAGES[2])
        return self.provider.apply()

    def _wait_for_ssh(self, outputs: TerraformOutputs) -> None:
        key_path = Path(self.config.aws.ssh_private_key_path).expanduser()
        wait_for_server(
            outputs.connect_ip,
            outputs.ssh_username,
            key_path,
            timeout_seconds=self.config.deployment.health_check_timeout_seconds,
        )

    def _provision_server(self, outputs: TerraformOutputs) -> None:
        inventory = installation_dir(self.config.installation.name) / "inventory.ini"
        write_inventory(path=inventory, outputs=outputs, config=self.config)
        extra = build_ansible_extra_vars(self.config, outputs)
        self.ansible.run_playbook("provision.yml", inventory=inventory, extra_vars=extra)

    def _deploy_platform(self, outputs: TerraformOutputs) -> None:
        inventory = installation_dir(self.config.installation.name) / "inventory.ini"
        extra = build_ansible_extra_vars(self.config, outputs)
        self.ansible.run_playbook("deploy.yml", inventory=inventory, extra_vars=extra)

    def _save_state(
        self,
        outputs: TerraformOutputs,
        url: str,
        health: dict[str, str],
    ) -> InstallationState:
        existing = load_state(self.config.installation.name)
        state = existing or InstallationState(
            name=self.config.installation.name,
            provider=self.config.installation.provider,
            environment=self.config.installation.environment,
            region=outputs.region,
            platform_version=self.config.platform.version,
        )
        state.instance_id = outputs.instance_id
        state.public_ip = outputs.public_ip
        state.elastic_ip = outputs.elastic_ip or None
        state.platform_url = url
        state.platform_version = self.config.platform.version
        state.installed_components = self.config.enabled_component_names()
        save_state(state)
        return state
