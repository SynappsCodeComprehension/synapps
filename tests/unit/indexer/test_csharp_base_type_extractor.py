import pytest
import tree_sitter_c_sharp
from tree_sitter import Language, Parser
from synapps.indexer.csharp.csharp_base_type_extractor import CSharpBaseTypeExtractor

_lang = Language(tree_sitter_c_sharp.language())
_parser = Parser(_lang)


def _parse(source: str):
    return _parser.parse(bytes(source, "utf-8"))


@pytest.fixture()
def extractor() -> CSharpBaseTypeExtractor:
    return CSharpBaseTypeExtractor()


def test_extract_class_with_base_class(extractor: CSharpBaseTypeExtractor) -> None:
    source = "class Dog : Animal {}"
    result = extractor.extract("/proj/Dog.cs", _parse(source))
    assert any(r[:3] == ("Dog", "Animal", True) for r in result)


def test_extract_class_implementing_interface(extractor: CSharpBaseTypeExtractor) -> None:
    source = "class UserService : IUserService {}"
    result = extractor.extract("/proj/UserService.cs", _parse(source))
    assert any(r[:3] == ("UserService", "IUserService", True) for r in result)


def test_extract_class_with_multiple_bases_marks_first(extractor: CSharpBaseTypeExtractor) -> None:
    source = "class Repo : BaseRepo, IRepo, IDisposable {}"
    result = extractor.extract("/proj/Repo.cs", _parse(source))
    first_flags = {base: is_first for _, base, is_first, _, _ in result}
    assert first_flags["BaseRepo"] is True
    assert first_flags["IRepo"] is False
    assert first_flags["IDisposable"] is False


def test_extract_interface_inheriting_interface(extractor: CSharpBaseTypeExtractor) -> None:
    source = "interface IService : IDisposable {}"
    result = extractor.extract("/proj/IService.cs", _parse(source))
    assert any(r[:3] == ("IService", "IDisposable", True) for r in result)


def test_extract_no_bases(extractor: CSharpBaseTypeExtractor) -> None:
    source = "class Foo {}"
    result = extractor.extract("/proj/Foo.cs", _parse(source))
    assert result == []


def test_extract_generic_base_class(extractor: CSharpBaseTypeExtractor) -> None:
    source = "class MyList : List<string> {}"
    result = extractor.extract("/proj/MyList.cs", _parse(source))
    names = {base for _, base, _, _, _ in result}
    assert "List" in names


def test_extract_record_with_base(extractor: CSharpBaseTypeExtractor) -> None:
    source = "record Dog : Animal {}"
    result = extractor.extract("/proj/Dog.cs", _parse(source))
    assert any(r[:3] == ("Dog", "Animal", True) for r in result)


def test_extract_empty_file(extractor: CSharpBaseTypeExtractor) -> None:
    assert extractor.extract("/proj/Foo.cs", _parse("")) == []


def test_extract_class_with_qualified_interface(extractor: CSharpBaseTypeExtractor) -> None:
    """Qualified names like 'Services.IMeetingService' must be extracted as 'IMeetingService'."""
    source = "class MeetingService : Services.IMeetingService {}"
    result = extractor.extract("/proj/MeetingService.cs", _parse(source))
    names = {base for _, base, _, _, _ in result}
    assert "IMeetingService" in names, f"Expected 'IMeetingService', got: {names}"


def test_extract_class_with_deeply_qualified_base(extractor: CSharpBaseTypeExtractor) -> None:
    """Deeply qualified names like 'A.B.C.IService' must resolve to 'IService'."""
    source = "class Service : A.B.C.IService {}"
    result = extractor.extract("/proj/Service.cs", _parse(source))
    names = {base for _, base, _, _, _ in result}
    assert "IService" in names, f"Expected 'IService', got: {names}"


def test_extract_mixed_simple_and_qualified_bases(extractor: CSharpBaseTypeExtractor) -> None:
    """Mix of qualified and unqualified bases must all be extracted."""
    source = "class Repo : Base.AbstractRepo, IRepo, System.IDisposable {}"
    result = extractor.extract("/proj/Repo.cs", _parse(source))
    names = {base for _, base, _, _, _ in result}
    assert "AbstractRepo" in names
    assert "IRepo" in names
    assert "IDisposable" in names


def test_extract_positions_are_integers(extractor: CSharpBaseTypeExtractor) -> None:
    """Positions (line, col) must be non-negative integers from tree-sitter start_point."""
    source = "class Dog : Animal {}"
    result = extractor.extract("/proj/Dog.cs", _parse(source))
    assert len(result) == 1
    _, _, _, line, col = result[0]
    assert isinstance(line, int) and line >= 0
    assert isinstance(col, int) and col >= 0
