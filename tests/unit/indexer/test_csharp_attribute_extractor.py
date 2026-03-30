import tree_sitter_c_sharp
from tree_sitter import Language, Parser
from synapps.indexer.csharp.csharp_attribute_extractor import CSharpAttributeExtractor

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


def test_extracts_static_method_modifier() -> None:
    source = """
public class MyService {
    public static string GetName() { return ""; }
}
"""
    extractor = CSharpAttributeExtractor()
    results = extractor.extract("test.cs", _parse(source))
    attrs = dict(results)
    assert "GetName" in attrs
    assert "static" in attrs["GetName"]


def test_extracts_async_method_modifier() -> None:
    source = """
public class MyService {
    public async Task<string> FetchDataAsync() { return ""; }
}
"""
    extractor = CSharpAttributeExtractor()
    results = extractor.extract("test.cs", _parse(source))
    attrs = dict(results)
    assert "FetchDataAsync" in attrs
    assert "async" in attrs["FetchDataAsync"]


def test_extracts_abstract_method_modifier() -> None:
    source = """
public abstract class Base {
    public abstract void DoWork();
}
"""
    extractor = CSharpAttributeExtractor()
    results = extractor.extract("test.cs", _parse(source))
    attrs = dict(results)
    assert "DoWork" in attrs
    assert "abstract" in attrs["DoWork"]
    assert "Base" in attrs
    assert "abstract" in attrs["Base"]


def test_extracts_combined_modifiers() -> None:
    source = """
public class MyController {
    public static async Task<bool> ValidateAsync() { return true; }
}
"""
    extractor = CSharpAttributeExtractor()
    results = extractor.extract("test.cs", _parse(source))
    attrs = dict(results)
    assert "ValidateAsync" in attrs
    assert "static" in attrs["ValidateAsync"]
    assert "async" in attrs["ValidateAsync"]


def test_extracts_virtual_override_modifiers() -> None:
    source = """
public class Base {
    public virtual void Speak() { }
}
public class Derived : Base {
    public override void Speak() { }
}
"""
    extractor = CSharpAttributeExtractor()
    results = extractor.extract("test.cs", _parse(source))
    attrs = dict(results)
    base_speak = [attrs for name, attrs in results if name == "Speak"]
    assert any("virtual" in a for a in base_speak)
    assert any("override" in a for a in base_speak)


def test_modifiers_combined_with_attributes() -> None:
    source = """
public class MyController {
    [HttpGet]
    public static async Task<string> GetAsync() { return ""; }
}
"""
    extractor = CSharpAttributeExtractor()
    results = extractor.extract("test.cs", _parse(source))
    attrs = dict(results)
    assert "GetAsync" in attrs
    assert "HttpGet" in attrs["GetAsync"]
    assert "static" in attrs["GetAsync"]
    assert "async" in attrs["GetAsync"]


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


# ---------------------------------------------------------------------------
# Regression: method name must be extracted from the named 'name' field,
# not the first identifier (which could be an attribute or return type)
# ---------------------------------------------------------------------------


def test_fact_attribute_extracted_for_async_task_method() -> None:
    """[Fact] on async Task<T> methods must resolve to the method name, not 'Task'."""
    source = """
public class UserTests {
    [Fact]
    public async Task InvokeAsync_ReturnsOk() { }
}
"""
    extractor = CSharpAttributeExtractor()
    results = extractor.extract("test.cs", _parse(source))
    attrs = dict(results)
    assert "InvokeAsync_ReturnsOk" in attrs
    assert "Fact" in attrs["InvokeAsync_ReturnsOk"]


def test_theory_attribute_extracted_for_generic_return() -> None:
    """[Theory] on methods with generic return types (Task<bool>) must use the method name."""
    source = """
public class ServiceTests {
    [Theory]
    [InlineData(1)]
    public async Task<bool> Validate_ReturnsFalse(int id) { return false; }
}
"""
    extractor = CSharpAttributeExtractor()
    results = extractor.extract("test.cs", _parse(source))
    attrs = dict(results)
    assert "Validate_ReturnsFalse" in attrs
    assert "Theory" in attrs["Validate_ReturnsFalse"]


def test_fact_on_void_method_still_works() -> None:
    """Regression guard: simple void methods still extract correctly."""
    source = """
public class Tests {
    [Fact]
    public void Simple_Test() { }
}
"""
    extractor = CSharpAttributeExtractor()
    results = extractor.extract("test.cs", _parse(source))
    attrs = dict(results)
    assert "Simple_Test" in attrs
    assert "Fact" in attrs["Simple_Test"]


def test_multiple_attributed_methods_in_class() -> None:
    """All methods in a class get their own attributes, not mixed up."""
    source = """
public class MixedTests {
    [Fact]
    public async Task First_Test() { }

    [Theory]
    [InlineData("x")]
    public async Task<string> Second_Test(string input) { return input; }

    public void Helper() { }
}
"""
    extractor = CSharpAttributeExtractor()
    results = extractor.extract("test.cs", _parse(source))
    attrs = dict(results)
    assert "First_Test" in attrs
    assert "Fact" in attrs["First_Test"]
    assert "Second_Test" in attrs
    assert "Theory" in attrs["Second_Test"]
    # Helper has no attributes but has async modifier — should not appear
    assert "Helper" not in attrs
