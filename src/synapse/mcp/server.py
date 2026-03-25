from __future__ import annotations

import logging
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from synapse.container import ConnectionManager
from synapse.graph.schema import ensure_schema
from synapse.mcp.instructions import SERVER_INSTRUCTIONS
from synapse.mcp.tools import register_tools
from synapse.service import SynapseService

log = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    path = str(Path.cwd())
    conn = ConnectionManager(path).get_connection()
    ensure_schema(conn)
    service = SynapseService(conn)

    mcp = FastMCP("synapse", instructions=SERVER_INSTRUCTIONS)
    register_tools(mcp, service, project_path=path)
    mcp.run()
