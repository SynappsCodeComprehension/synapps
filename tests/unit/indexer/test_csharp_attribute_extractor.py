import tree_sitter_c_sharp
from tree_sitter import Language, Parser
from synapse.indexer.csharp.csharp_attribute_extractor import CSharpAttributeExtractor

_lang = Language(tree_sitter_c_sharp.language())
_parser = Parser(_lang)


def _parse(source: str):
    return _parser.parse(bytes(source, "utf-8"))


def test_extracts_class_attribute() -> None:
    source = """
[ApiController]
public class TaskController { }
"""
    extractor = CSharpAttributeExtractor()
    results = extractor.extract("test.cs", _parse(source))
    assert ("TaskController", ["ApiController"]) in results


def test_extracts_method_attribute() -> None:
    source = """
public class MyController {
    [HttpGet]
    public void Get() { }
}
"""
    extractor = CSharpAttributeExtractor()
    results = extractor.extract("test.cs", _parse(source))
    assert ("Get", ["HttpGet"]) in results


def test_extracts_multiple_attributes() -> None:
    source = """
[ApiController]
[Route("api/[controller]")]
public class TaskController { }
"""
    extractor = CSharpAttributeExtractor()
    results = extractor.extract("test.cs", _parse(source))
    attrs = dict(results)
    assert "ApiController" in attrs["TaskController"]
    assert "Route" in attrs["TaskController"]


def test_strips_attribute_suffix() -> None:
    source = """
[ApiControllerAttribute]
public class TaskController { }
"""
    extractor = CSharpAttributeExtractor()
    results = extractor.extract("test.cs", _parse(source))
    attrs = dict(results)
    assert "ApiController" in attrs["TaskController"]


def test_preserves_namespace_qualification() -> None:
    source = """
[System.Serializable]
public class Dto { }
"""
    extractor = CSharpAttributeExtractor()
    results = extractor.extract("test.cs", _parse(source))
    attrs = dict(results)
    assert "System.Serializable" in attrs["Dto"]


def test_extracts_property_attribute() -> None:
    source = """
public class Model {
    [Required]
    public string Name { get; set; }
}
"""
    extractor = CSharpAttributeExtractor()
    results = extractor.extract("test.cs", _parse(source))
    assert ("Name", ["Required"]) in results


def test_extracts_field_attribute() -> None:
    source = """
public class Model {
    [JsonIgnore]
    private string _cache;
}
"""
    extractor = CSharpAttributeExtractor()
    results = extractor.extract("test.cs", _parse(source))
    assert ("_cache", ["JsonIgnore"]) in results


def test_empty_source_returns_empty() -> None:
    extractor = CSharpAttributeExtractor()
    assert extractor.extract("test.cs", _parse("")) == []
    assert extractor.extract("test.cs", _parse("   ")) == []


def test_no_attributes_returns_empty() -> None:
    source = "public class Plain { }"
    extractor = CSharpAttributeExtractor()
    assert extractor.extract("test.cs", _parse(source)) == []


def test_attribute_with_arguments_extracts_name_only() -> None:
    source = """
[Route("api/tasks")]
public class TaskController { }
"""
    extractor = CSharpAttributeExtractor()
    results = extractor.extract("test.cs", _parse(source))
    attrs = dict(results)
    assert "Route" in attrs["TaskController"]
