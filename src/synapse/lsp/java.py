from __future__ import annotations

import logging
import time
from pathlib import Path

from synapse.lsp.interface import IndexSymbol, LSPAdapter, LSPResolverBackend, SymbolKind
from synapse.lsp.util import build_full_name

log = logging.getLogger(__name__)

# Maps LSP SymbolKind integers to Synapse SymbolKind.
# Per D-23: Java-specific kind mapping for Eclipse JDT LS.
_LSP_KIND_MAP: dict[int, SymbolKind] = {
    3: SymbolKind.NAMESPACE,   # package
    5: SymbolKind.CLASS,       # class
    6: SymbolKind.METHOD,      # method
    7: SymbolKind.PROPERTY,    # property
    8: SymbolKind.FIELD,       # field
    9: SymbolKind.METHOD,      # constructor (promoted to "constructor" kind in Guard 7)
    10: SymbolKind.ENUM,       # enum -> :Class with kind='enum' (mapped to CLASS label in indexer)
    11: SymbolKind.INTERFACE,  # interface
    12: SymbolKind.METHOD,     # function (shouldn't occur but handle gracefully)
    14: SymbolKind.FIELD,      # constant (static final fields)
}

# Directories excluded from workspace file discovery (per D-03).
_EXCLUDE_DIRS = frozenset({
    ".git", "target", "build", ".gradle", ".idea", "bin", ".settings", ".mvn",
})


class JavaLSPAdapter:
    """Wraps an EclipseJDTLS instance to provide the LSPAdapter interface for Java."""

    def __init__(self, language_server: LSPResolverBackend) -> None:
        self._ls = language_server

    @property
    def language_server(self) -> LSPResolverBackend:
        return self._ls

    @classmethod
    def create(cls, root_path: str) -> JavaLSPAdapter:
        """Start the Eclipse JDT LS and return a ready adapter."""
        from solidlsp.language_servers.eclipse_jdtls import EclipseJDTLS
        from solidlsp.ls_config import Language, LanguageServerConfig
        from solidlsp.settings import SolidLSPSettings

        config = LanguageServerConfig(code_language=Language.JAVA)
        settings = SolidLSPSettings()
        ls = EclipseJDTLS(
            config=config,
            repository_root_path=root_path,
            solidlsp_settings=settings,
        )
        log.info("Starting Eclipse JDT LS for %s", root_path)
        t0 = time.monotonic()
        ls.start()
        log.info("Eclipse JDT LS ready in %.1fs", time.monotonic() - t0)
        return cls(ls)

    def get_workspace_files(self, root_path: str) -> list[str]:
        t0 = time.monotonic()
        files: list[str] = []
        for path in Path(root_path).rglob("*.java"):
            if not any(part in _EXCLUDE_DIRS for part in path.parts):
                files.append(str(path))
        log.info("Discovered %d Java files in %.1fs", len(files), time.monotonic() - t0)
        return files

    def get_document_symbols(self, file_path: str) -> list[IndexSymbol]:
        try:
            t0 = time.monotonic()
            raw = self._ls.request_document_symbols(file_path)
            elapsed = time.monotonic() - t0
            if raw is None:
                return []
            result: list[IndexSymbol] = []
            for root in raw.root_symbols:
                self._traverse(root, file_path, parent_full_name=None, result=result)
            if elapsed > 2.0:
                log.info(
                    "Slow document symbols: %s took %.1fs (%d symbols)",
                    file_path, elapsed, len(result),
                )
            return result
        except Exception:
            log.exception("Failed to get symbols for %s", file_path)
            return []

    def _traverse(
        self,
        raw: dict,
        file_path: str,
        parent_full_name: str | None,
        result: list[IndexSymbol],
    ) -> None:
        sym = self._convert(raw, file_path, parent_full_name)
        result.append(sym)
        for child in raw.get("children", []):
            self._traverse(child, file_path, parent_full_name=sym.full_name, result=result)

    def _convert(self, raw: dict, file_path: str, parent_full_name: str | None) -> IndexSymbol:
        kind_int = raw.get("kind", 0)
        kind = _LSP_KIND_MAP.get(kind_int)
        if kind is None:
            log.debug(
                "Unmapped LSP SymbolKind %d for symbol %s, defaulting to CLASS",
                kind_int, raw.get("name", "?"),
            )
            kind = SymbolKind.CLASS

        name = raw.get("name", "")
        full_name = build_full_name(raw)

        # D-05: If build_full_name returns just the symbol name (no container),
        # the symbol likely has no package declaration. Fall back to parent_full_name
        # chain if available.
        if full_name == name and parent_full_name:
            full_name = f"{parent_full_name}.{name}"

        range_obj = raw.get("location", {}).get("range", {})
        line = range_obj.get("start", {}).get("line", 0)
        end_line = range_obj.get("end", {}).get("line", 0)
        detail = raw.get("detail", "") or ""

        return IndexSymbol(
            name=name,
            full_name=full_name,
            kind=kind,
            file_path=file_path,
            line=line,
            end_line=end_line,
            signature=detail,
            is_abstract="abstract" in detail.lower(),
            is_static="static" in detail.lower(),
            parent_full_name=parent_full_name,
        )

    def find_method_calls(self, symbol: IndexSymbol) -> list[str]:
        return []

    def find_overridden_method(self, symbol: IndexSymbol) -> str | None:
        return None

    def shutdown(self) -> None:
        self._ls.stop()
