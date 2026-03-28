from __future__ import annotations

import logging
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from synapps.container import ConnectionManager
from synapps.graph.schema import ensure_schema
from synapps.mcp.instructions import SERVER_INSTRUCTIONS
from synapps.mcp.tools import register_tools
from synapps.service import SynappsService

log = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    path = str(Path.cwd())
    conn = ConnectionManager(path).get_connection()
    ensure_schema(conn)
    service = SynappsService(conn)

    mcp = FastMCP("synapps", instructions=SERVER_INSTRUCTIONS)
    register_tools(mcp, service, project_path=path)
    mcp.run()
