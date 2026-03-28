import pytest
import tree_sitter_c_sharp
from tree_sitter import Language, Parser
from synapps.indexer.csharp.csharp_import_extractor import CSharpImportExtractor

_lang = Language(tree_sitter_c_sharp.language())
_parser = Parser(_lang)


def _parse(source: str):
    return _parser.parse(bytes(source, "utf-8"))


@pytest.fixture()
def extractor() -> CSharpImportExtractor:
    return CSharpImportExtractor()


def test_extract_simple_using(extractor: CSharpImportExtractor) -> None:
    source = "using System.Collections.Generic;\nclass Foo {}"
    result = extractor.extract("/proj/Foo.cs", _parse(source))
    assert "System.Collections.Generic" in result


def test_extract_multiple_usings(extractor: CSharpImportExtractor) -> None:
    source = "using System;\nusing System.IO;\nclass Foo {}"
    result = extractor.extract("/proj/Foo.cs", _parse(source))
    assert "System" in result
    assert "System.IO" in result


def test_extract_ignores_static_using(extractor: CSharpImportExtractor) -> None:
    source = "using static System.Math;\nclass Foo {}"
    result = extractor.extract("/proj/Foo.cs", _parse(source))
    assert result == []


def test_extract_empty_file(extractor: CSharpImportExtractor) -> None:
    assert extractor.extract("/proj/Foo.cs", _parse("")) == []


def test_extract_no_duplicates(extractor: CSharpImportExtractor) -> None:
    source = "using System;\nusing System;\nclass Foo {}"
    result = extractor.extract("/proj/Foo.cs", _parse(source))
    assert result.count("System") == 1


def test_extract_ignores_alias_using(extractor: CSharpImportExtractor) -> None:
    source = "using Alias = System.IO;\nclass Foo {}"
    result = extractor.extract("/proj/Foo.cs", _parse(source))
    assert result == []
