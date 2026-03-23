from __future__ import annotations

import logging
import platform

import docker
import docker.errors

from synapse.doctor.base import CheckResult

log = logging.getLogger(__name__)


class DockerDaemonCheck:
    group = "core"

    def run(self) -> CheckResult:
        try:
            client = docker.from_env()
            client.ping()
        except docker.errors.DockerException as exc:
            return CheckResult(
                name="Docker daemon",
                status="fail",
                detail=f"Docker daemon not reachable: {exc}",
                fix=_docker_fix_instructions(),
                group=self.group,
            )
        return CheckResult(
            name="Docker daemon",
            status="pass",
            detail="Docker daemon is running",
            fix=None,
            group=self.group,
        )


def _docker_fix_instructions() -> str:
    if platform.system() == "Darwin":
        return "Install Docker Desktop: https://docs.docker.com/desktop/install/mac-install/ then start it."
    return "Install Docker: sudo apt-get install docker.io && sudo systemctl start docker"
