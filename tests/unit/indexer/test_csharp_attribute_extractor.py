from synapse.indexer.csharp.csharp_attribute_extractor import CSharpAttributeExtractor


def test_extracts_class_attribute() -> None:
    source = """
[ApiController]
public class TaskController { }
"""
    extractor = CSharpAttributeExtractor()
    results = extractor.extract("test.cs", source)
    assert ("TaskController", ["ApiController"]) in results


def test_extracts_method_attribute() -> None:
    source = """
public class MyController {
    [HttpGet]
    public void Get() { }
}
"""
    extractor = CSharpAttributeExtractor()
    results = extractor.extract("test.cs", source)
    assert ("Get", ["HttpGet"]) in results


def test_extracts_multiple_attributes() -> None:
    source = """
[ApiController]
[Route("api/[controller]")]
public class TaskController { }
"""
    extractor = CSharpAttributeExtractor()
    results = extractor.extract("test.cs", source)
    attrs = dict(results)
    assert "ApiController" in attrs["TaskController"]
    assert "Route" in attrs["TaskController"]


def test_strips_attribute_suffix() -> None:
    source = """
[ApiControllerAttribute]
public class TaskController { }
"""
    extractor = CSharpAttributeExtractor()
    results = extractor.extract("test.cs", source)
    attrs = dict(results)
    assert "ApiController" in attrs["TaskController"]


def test_preserves_namespace_qualification() -> None:
    source = """
[System.Serializable]
public class Dto { }
"""
    extractor = CSharpAttributeExtractor()
    results = extractor.extract("test.cs", source)
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
    results = extractor.extract("test.cs", source)
    assert ("Name", ["Required"]) in results


def test_extracts_field_attribute() -> None:
    source = """
public class Model {
    [JsonIgnore]
    private string _cache;
}
"""
    extractor = CSharpAttributeExtractor()
    results = extractor.extract("test.cs", source)
    assert ("_cache", ["JsonIgnore"]) in results


def test_empty_source_returns_empty() -> None:
    extractor = CSharpAttributeExtractor()
    assert extractor.extract("test.cs", "") == []
    assert extractor.extract("test.cs", "   ") == []


def test_no_attributes_returns_empty() -> None:
    source = "public class Plain { }"
    extractor = CSharpAttributeExtractor()
    assert extractor.extract("test.cs", source) == []


def test_attribute_with_arguments_extracts_name_only() -> None:
    source = """
[Route("api/tasks")]
public class TaskController { }
"""
    extractor = CSharpAttributeExtractor()
    results = extractor.extract("test.cs", source)
    attrs = dict(results)
    assert "Route" in attrs["TaskController"]
