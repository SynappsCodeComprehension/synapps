from __future__ import annotations

import re
from dataclasses import dataclass, field

from synapps.indexer.http.interface import HttpClientCall, HttpEndpointDef
from synapps.indexer.http.route_utils import strip_base_url_variable

_PARAM_RE = re.compile(r"^\{[^}]+\}$")
_API_PREFIXES = ["/api", "/api/v1", "/api/v2"]


@dataclass
class MatchedEndpoint:
    """Result of matching: an endpoint with its server def (if any) and client calls (if any)."""

    route: str
    http_method: str
    endpoint_def: HttpEndpointDef | None = None
    client_calls: list[HttpClientCall] = field(default_factory=list)


def _segments(route: str) -> list[str]:
    return [s for s in route.split("/") if s]


def _routes_match(server_segs: list[str], client_segs: list[str]) -> bool:
    if len(server_segs) != len(client_segs):
        return False
    for s_seg, c_seg in zip(server_segs, client_segs):
        s_is_param = bool(_PARAM_RE.match(s_seg))
        c_is_param = bool(_PARAM_RE.match(c_seg))
        if s_is_param and c_is_param:
            continue
        if s_is_param != c_is_param:
            return False
        if s_seg != c_seg:
            return False
    return True


def match_endpoints(
    endpoint_defs: list[HttpEndpointDef],
    client_calls: list[HttpClientCall],
) -> list[MatchedEndpoint]:
    """Match client HTTP calls to server endpoint definitions by route and HTTP method."""
    if not endpoint_defs and not client_calls:
        return []

    server_by_method: dict[str, list[tuple[list[str], HttpEndpointDef]]] = {}
    results_by_key: dict[tuple[str, str], MatchedEndpoint] = {}

    for ep in endpoint_defs:
        segs = _segments(ep.route)
        server_by_method.setdefault(ep.http_method, []).append((segs, ep))
        key = (ep.route, ep.http_method)
        if key not in results_by_key:
            results_by_key[key] = MatchedEndpoint(
                route=ep.route, http_method=ep.http_method, endpoint_def=ep,
            )

    unmatched_calls: list[HttpClientCall] = []

    for call in client_calls:
        stripped_route = strip_base_url_variable(call.route)
        call_segs = _segments(stripped_route)
        matched = False

        candidates = [call_segs]
        for prefix in _API_PREFIXES:
            candidates.append(_segments(prefix + "/" + stripped_route.lstrip("/")))

        for candidate_segs in candidates:
            if matched:
                break
            for server_segs, ep in server_by_method.get(call.http_method, []):
                if _routes_match(server_segs, candidate_segs):
                    key = (ep.route, ep.http_method)
                    results_by_key[key].client_calls.append(call)
                    matched = True
                    break

        if not matched:
            unmatched_calls.append(call)

    for call in unmatched_calls:
        key = (call.route, call.http_method)
        if key in results_by_key:
            results_by_key[key].client_calls.append(call)
        else:
            results_by_key[key] = MatchedEndpoint(
                route=call.route, http_method=call.http_method, client_calls=[call],
            )

    return list(results_by_key.values())
