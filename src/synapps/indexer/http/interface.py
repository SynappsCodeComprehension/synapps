from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from tree_sitter import Tree

from synapps.lsp.interface import IndexSymbol


@dataclass(frozen=True)
class HttpEndpointDef:
    """A server-side HTTP endpoint definition extracted from source."""

    route: str
    http_method: str
    handler_full_name: str
    line: int


@dataclass(frozen=True)
class HttpClientCall:
    """A client-side HTTP call extracted from source."""

    route: str
    http_method: str
    caller_full_name: str
    line: int
    col: int


@dataclass
class HttpExtractionResult:
    """Combined result from an HTTP extractor — may contain server defs, client calls, or both."""

    endpoint_defs: list[HttpEndpointDef] = field(default_factory=list)
    client_calls: list[HttpClientCall] = field(default_factory=list)


class HttpExtractor(Protocol):
    """Protocol for language-specific HTTP extraction."""

    def extract(
        self,
        file_path: str,
        tree: Tree,
        symbols: list[IndexSymbol],
    ) -> HttpExtractionResult: ...
