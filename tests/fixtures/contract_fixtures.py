from typing import NotRequired
from typing_extensions import TypedDict


# --- Search ---


class SearchSymbolsResult(TypedDict):
    full_name: str
    name: str
    kind: str
    file_path: str
    line: int
    language: str


# --- Navigate ---


class FindCallersResult(TypedDict):
    full_name: str
    file_path: str
    line: int
    signature: NotRequired[str]


class FindCalleesResult(TypedDict):
    full_name: str
    name: str
    file_path: str
    line: int
    signature: NotRequired[str]


class FindImplementationsResult(TypedDict):
    full_name: str
    signature: NotRequired[str]


class FindUsagesResult(TypedDict):
    full_name: str
    kind: str
    file_path: str
    line: int


class FindDependenciesResult(TypedDict):
    type: dict
    depth: int


class GetHierarchyResult(TypedDict):
    parents: list
    children: list
    implements: list


class GetSymbolResult(TypedDict):
    full_name: str
    _labels: NotRequired[list]
    is_abstract: NotRequired[bool]


class GetContextForResult(TypedDict):
    source: str
    callees: NotRequired[list]
    members: NotRequired[list]


class GetCallDepthResult(TypedDict):
    root: str
    callees: list
    depth_limit: int


# --- Analysis ---


class GetIndexStatusResult(TypedDict):
    path: str
    file_count: NotRequired[int]
    commit: NotRequired[str]


class GetArchitectureOverviewResult(TypedDict):
    packages: list
    stats: dict


class FindDeadCodeResult(TypedDict):
    methods: list
    stats: dict


class FindUntestedResult(TypedDict):
    methods: list
    stats: dict


# --- HTTP ---


class FindHttpEndpointsResult(TypedDict):
    route: str
    http_method: str
    handler_full_name: str
    file_path: str
    line: int
    language: str
    has_server_handler: bool


class TraceHttpDependencyResult(TypedDict):
    route: str
    http_method: str
    has_server_handler: bool
    server_handler: dict | None
    client_callers: list


# --- Misc ---


class FindTypeReferencesResult(TypedDict):
    symbol: dict
    kind: str


class ListProjectsResult(TypedDict):
    path: str


class ListSummarizedResult(TypedDict):
    full_name: str
