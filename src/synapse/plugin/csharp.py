from __future__ import annotations

from synapse.indexer.attribute_extractor import CSharpAttributeExtractor
from synapse.indexer.base_type_extractor import CSharpBaseTypeExtractor
from synapse.indexer.call_extractor import TreeSitterCallExtractor
from synapse.indexer.import_extractor import CSharpImportExtractor
from synapse.indexer.type_ref_extractor import TreeSitterTypeRefExtractor
from synapse.lsp.csharp import CSharpLSPAdapter


class CSharpPlugin:
    @property
    def name(self) -> str:
        return "csharp"

    @property
    def file_extensions(self) -> frozenset[str]:
        return frozenset({".cs"})

    def create_lsp_adapter(self, root_path: str) -> CSharpLSPAdapter:
        return CSharpLSPAdapter.create(root_path)

    def create_call_extractor(self) -> TreeSitterCallExtractor:
        return TreeSitterCallExtractor()

    def create_import_extractor(self) -> CSharpImportExtractor:
        return CSharpImportExtractor()

    def create_base_type_extractor(self) -> CSharpBaseTypeExtractor:
        return CSharpBaseTypeExtractor()

    def create_attribute_extractor(self) -> CSharpAttributeExtractor:
        return CSharpAttributeExtractor()

    def create_type_ref_extractor(self) -> TreeSitterTypeRefExtractor:
        return TreeSitterTypeRefExtractor()
