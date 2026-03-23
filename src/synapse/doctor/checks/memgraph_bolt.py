from __future__ import annotations

import logging
import socket

import docker
import docker.errors

from synapse.doctor.base import CheckResult

log = logging.getLogger(__name__)

_BOLT_PORT = 7687
_BOLT_MAGIC = b"\x60\x60\xb0\x17"
_BOLT_VERSIONS = (
    b"\x00\x00\x04\x04"
    b"\x00\x00\x03\x04"
    b"\x00\x00\x00\x04"
    b"\x00\x00\x00\x03"
)


class MemgraphBoltCheck:
    group = "core"

    def run(self) -> CheckResult:
        # D-05: if Docker is down, skip Memgraph check — it cannot succeed
        try:
            docker.from_env().ping()
        except docker.errors.DockerException:
            return CheckResult(
                name="Memgraph",
                status="warn",
                detail="Docker not available \u2014 cannot check Memgraph",
                fix=None,
                group=self.group,
            )

        try:
            with socket.create_connection(("localhost", _BOLT_PORT), timeout=2.0) as s:
                s.sendall(_BOLT_MAGIC + _BOLT_VERSIONS)
                resp = s.recv(4)
                if len(resp) == 4:
                    return CheckResult(
                        name="Memgraph",
                        status="pass",
                        detail=f"Memgraph Bolt port {_BOLT_PORT} is reachable",
                        fix=None,
                        group=self.group,
                    )
        except OSError:
            pass

        return CheckResult(
            name="Memgraph",
            status="fail",
            detail=f"Memgraph not reachable on localhost:{_BOLT_PORT}",
            fix="Start Memgraph: docker compose up -d",
            group=self.group,
        )
