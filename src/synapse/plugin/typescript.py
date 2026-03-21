from __future__ import annotations

from synapse.indexer.typescript.typescript_attribute_extractor import TypeScriptAttributeExtractor
from synapse.indexer.typescript.typescript_base_type_extractor import TypeScriptBaseTypeExtractor
from synapse.indexer.typescript.typescript_call_extractor import TypeScriptCallExtractor
from synapse.indexer.typescript.typescript_import_extractor import TypeScriptImportExtractor
from synapse.indexer.typescript.typescript_type_ref_extractor import TypeScriptTypeRefExtractor
from synapse.lsp.typescript import TypeScriptLSPAdapter


class TypeScriptPlugin:
    @property
    def name(self) -> str:
        return "typescript"

    @property
    def file_extensions(self) -> frozenset[str]:
        return frozenset({".ts", ".tsx", ".js", ".jsx", ".mts", ".cts", ".mjs", ".cjs"})

    def create_lsp_adapter(self, root_path: str) -> TypeScriptLSPAdapter:
        return TypeScriptLSPAdapter.create(root_path)

    def create_call_extractor(self) -> TypeScriptCallExtractor:
        return TypeScriptCallExtractor()

    def create_import_extractor(self, source_root: str = "") -> TypeScriptImportExtractor:
        return TypeScriptImportExtractor(source_root=source_root)

    def create_base_type_extractor(self) -> TypeScriptBaseTypeExtractor:
        return TypeScriptBaseTypeExtractor()

    def create_attribute_extractor(self) -> TypeScriptAttributeExtractor:
        return TypeScriptAttributeExtractor()

    def create_type_ref_extractor(self) -> TypeScriptTypeRefExtractor:
        return TypeScriptTypeRefExtractor()

    def create_assignment_extractor(self) -> None:
        return None
