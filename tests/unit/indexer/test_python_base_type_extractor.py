import pytest
import tree_sitter_python
from tree_sitter import Language, Parser
from synapps.indexer.python.python_base_type_extractor import PythonBaseTypeExtractor

_lang = Language(tree_sitter_python.language())
_parser = Parser(_lang)


def _parse(source: str):
    return _parser.parse(bytes(source, "utf-8"))


@pytest.fixture()
def extractor() -> PythonBaseTypeExtractor:
    return PythonBaseTypeExtractor()


def test_single_inheritance(extractor: PythonBaseTypeExtractor) -> None:
    source = "class Dog(Animal): pass"
    result = extractor.extract("test.py", _parse(source))
    assert len(result) == 1
    assert result[0][:3] == ("Dog", "Animal", True)


def test_multiple_inheritance(extractor: PythonBaseTypeExtractor) -> None:
    source = "class Formatter(TextMixin, SerializeMixin): pass"
    result = extractor.extract("test.py", _parse(source))
    assert len(result) == 2
    assert result[0][:3] == ("Formatter", "TextMixin", True)
    assert result[1][:3] == ("Formatter", "SerializeMixin", False)


def test_abc_inheritance(extractor: PythonBaseTypeExtractor) -> None:
    source = "class IAnimal(ABC): pass"
    result = extractor.extract("test.py", _parse(source))
    assert len(result) == 1
    assert result[0][:3] == ("IAnimal", "ABC", True)


def test_no_base_class(extractor: PythonBaseTypeExtractor) -> None:
    source = "class Standalone: pass"
    result = extractor.extract("test.py", _parse(source))
    assert result == []


def test_dotted_base(extractor: PythonBaseTypeExtractor) -> None:
    source = "class Foo(mymod.Base): pass"
    result = extractor.extract("test.py", _parse(source))
    assert len(result) == 1
    assert result[0][:3] == ("Foo", "Base", True)


def test_nested_class(extractor: PythonBaseTypeExtractor) -> None:
    source = "class Outer:\n  class Inner(Base): pass"
    result = extractor.extract("test.py", _parse(source))
    assert any(r[:3] == ("Inner", "Base", True) for r in result)


def test_empty_source(extractor: PythonBaseTypeExtractor) -> None:
    result = extractor.extract("test.py", _parse(""))
    assert result == []


def test_positions_are_integers(extractor: PythonBaseTypeExtractor) -> None:
    """Positions (line, col) must be non-negative integers from tree-sitter start_point."""
    source = "class Dog(Animal): pass"
    result = extractor.extract("test.py", _parse(source))
    assert len(result) == 1
    _, _, _, line, col = result[0]
    assert isinstance(line, int) and line >= 0
    assert isinstance(col, int) and col >= 0


def test_dotted_base_position_points_to_leaf(extractor: PythonBaseTypeExtractor) -> None:
    """For 'mymod.Base', position should point to 'Base' identifier, not the attribute node."""
    source = "class Foo(mymod.Base): pass"
    result = extractor.extract("test.py", _parse(source))
    assert len(result) == 1
    _, base_name, _, line, col = result[0]
    assert base_name == "Base"
    # 'Base' starts after 'mymod.' (6 chars), so col >= 6
    assert col >= 6
