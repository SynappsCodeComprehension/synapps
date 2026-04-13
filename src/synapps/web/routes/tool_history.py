from __future__ import annotations

from fastapi import APIRouter

from synapps.service import SynappsService


def router(service: SynappsService) -> APIRouter:
    r = APIRouter(tags=["Tool History"])

    @r.get("/tool_history")
    def tool_history(
        tool: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        return service.get_tool_history(tool=tool, status=status, limit=limit, offset=offset)

    return r
