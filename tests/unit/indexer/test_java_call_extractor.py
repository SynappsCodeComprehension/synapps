import pytest
import tree_sitter_java
from tree_sitter import Language, Parser
from synapse.indexer.java.java_call_extractor import JavaCallExtractor

_lang = Language(tree_sitter_java.language())
_parser = Parser(_lang)


def _parse(source: str):
    return _parser.parse(bytes(source, "utf-8"))


@pytest.fixture
def extractor():
    return JavaCallExtractor()


# ---------------------------------------------------------------------------
# Basic call extraction
# ---------------------------------------------------------------------------


def test_simple_method_call(extractor):
    source = """\
public class MyClass {
    public void caller() {
        obj.method();
    }
}
"""
    symbol_map = {("/proj/MyClass.java", 1): "com.example.MyClass.caller"}
    results = extractor.extract("/proj/MyClass.java", _parse(source), symbol_map)
    callees = [callee for _, callee, *_ in results]
    assert "method" in callees


def test_chained_method_call(extractor):
    source = """\
public class MyClass {
    public void caller() {
        obj.method().chain();
    }
}
"""
    symbol_map = {("/proj/MyClass.java", 1): "com.example.MyClass.caller"}
    results = extractor.extract("/proj/MyClass.java", _parse(source), symbol_map)
    callees = [callee for _, callee, *_ in results]
    assert "method" in callees
    assert "chain" in callees


def test_constructor_call(extractor):
    source = """\
public class MyClass {
    public void factory() {
        Foo f = new Foo();
    }
}
"""
    symbol_map = {("/proj/MyClass.java", 1): "com.example.MyClass.factory"}
    results = extractor.extract("/proj/MyClass.java", _parse(source), symbol_map)
    callees = [callee for _, callee, *_ in results]
    assert "Foo" in callees


def test_static_method_call(extractor):
    source = """\
public class MyClass {
    public void caller() {
        ClassName.staticMethod();
    }
}
"""
    symbol_map = {("/proj/MyClass.java", 1): "com.example.MyClass.caller"}
    results = extractor.extract("/proj/MyClass.java", _parse(source), symbol_map)
    callees = [callee for _, callee, *_ in results]
    assert "staticMethod" in callees


def test_function_call_within_method(extractor):
    source = """\
public class MyClass {
    public void caller() {
        baz();
    }
}
"""
    symbol_map = {("/proj/MyClass.java", 1): "com.example.MyClass.caller"}
    results = extractor.extract("/proj/MyClass.java", _parse(source), symbol_map)
    callees = [callee for _, callee, *_ in results]
    assert "baz" in callees


def test_caller_full_name_is_set(extractor):
    source = """\
public class MyClass {
    public void caller() {
        helper();
    }
}
"""
    symbol_map = {("/proj/MyClass.java", 1): "com.example.MyClass.caller"}
    results = extractor.extract("/proj/MyClass.java", _parse(source), symbol_map)
    assert any(caller == "com.example.MyClass.caller" for caller, *_ in results)


# ---------------------------------------------------------------------------
# No calls / empty source
# ---------------------------------------------------------------------------


def test_no_calls(extractor):
    source = """\
public class MyClass {
    private int count;
    private String name;
}
"""
    symbol_map = {}
    results = extractor.extract("/proj/MyClass.java", _parse(source), symbol_map)
    assert results == []


def test_empty_source(extractor):
    assert extractor.extract("/proj/MyClass.java", _parse(""), {}) == []


def test_whitespace_source(extractor):
    assert extractor.extract("/proj/MyClass.java", _parse("   \n  "), {}) == []


# ---------------------------------------------------------------------------
# Line indexing and deduplication
# ---------------------------------------------------------------------------


def test_call_line_is_1indexed(extractor):
    source = """\
public class MyClass {
    public void caller() {
        helper();
    }
}
"""
    symbol_map = {("/proj/MyClass.java", 1): "com.example.MyClass.caller"}
    results = extractor.extract("/proj/MyClass.java", _parse(source), symbol_map)
    lines = [line for _, _, line, _ in results]
    # helper() is on line 3 (1-indexed)
    assert 3 in lines


def test_deduplicates_identical_entries(extractor):
    source = """\
public class MyClass {
    public void caller() {
        foo();
        foo();
    }
}
"""
    symbol_map = {("/proj/MyClass.java", 1): "com.example.MyClass.caller"}
    results = extractor.extract("/proj/MyClass.java", _parse(source), symbol_map)
    seen = set()
    for entry in results:
        assert entry not in seen, f"Duplicate entry: {entry}"
        seen.add(entry)


# ---------------------------------------------------------------------------
# _sites_seen counter
# ---------------------------------------------------------------------------


def test_sites_seen_counts_calls(extractor):
    source = """\
public class MyClass {
    public void methodA() { foo(); }
    public void methodB() { bar(); }
    public void methodC() { baz(); }
}
"""
    symbol_map = {
        ("/proj/MyClass.java", 1): "pkg.MyClass.methodA",
        ("/proj/MyClass.java", 2): "pkg.MyClass.methodB",
        ("/proj/MyClass.java", 3): "pkg.MyClass.methodC",
    }
    extractor.extract("/proj/MyClass.java", _parse(source), symbol_map)
    assert extractor._sites_seen == 3


def test_sites_seen_zero_for_empty_source(extractor):
    extractor.extract("/proj/MyClass.java", _parse(""), {})
    assert extractor._sites_seen == 0


def test_sites_seen_resets_per_extract_call(extractor):
    source_three = """\
public class A {
    public void caller() {
        a();
        b();
        c();
    }
}
"""
    source_one = """\
public class B {
    public void caller() {
        x();
    }
}
"""
    symbol_map_three = {("/proj/A.java", 1): "pkg.A.caller"}
    symbol_map_one = {("/proj/B.java", 1): "pkg.B.caller"}

    extractor.extract("/proj/A.java", _parse(source_three), symbol_map_three)
    assert extractor._sites_seen == 3

    extractor.extract("/proj/B.java", _parse(source_one), symbol_map_one)
    assert extractor._sites_seen == 1


# ---------------------------------------------------------------------------
# Scope detection — class-body field initializer calls must be skipped
# ---------------------------------------------------------------------------


def test_skips_field_initializer_call(extractor):
    """Regression: calls in field initializers (class body) must be skipped."""
    source = """\
public class MyClass {
    private List<String> items = Arrays.asList("a", "b");
    public void realMethod() {
        helper();
    }
}
"""
    symbol_map = {("/proj/MyClass.java", 2): "pkg.MyClass.realMethod"}
    results = extractor.extract("/proj/MyClass.java", _parse(source), symbol_map)
    callees = [callee for _, callee, *_ in results]
    assert "helper" in callees
    assert "asList" not in callees


def test_skips_static_field_initializer(extractor):
    """Regression: static field initializers are class-body scope."""
    source = """\
public class Config {
    private static final Logger LOG = LoggerFactory.getLogger(Config.class);
    public void run() {
        LOG.info("running");
    }
}
"""
    symbol_map = {("/proj/Config.java", 2): "pkg.Config.run"}
    results = extractor.extract("/proj/Config.java", _parse(source), symbol_map)
    callees = [callee for _, callee, *_ in results]
    assert "info" in callees
    assert "getLogger" not in callees


def test_includes_constructor_body_calls(extractor):
    """Calls inside constructors should be included."""
    source = """\
public class Service {
    public Service() {
        init();
    }
}
"""
    symbol_map = {("/proj/Service.java", 1): "pkg.Service.Service"}
    results = extractor.extract("/proj/Service.java", _parse(source), symbol_map)
    callees = [callee for _, callee, *_ in results]
    assert "init" in callees


def test_includes_lambda_body_calls(extractor):
    """Calls inside lambdas should be included (lambda is a method scope)."""
    source = """\
public class MyClass {
    public void run() {
        list.forEach(item -> process(item));
    }
}
"""
    symbol_map = {("/proj/MyClass.java", 1): "pkg.MyClass.run"}
    results = extractor.extract("/proj/MyClass.java", _parse(source), symbol_map)
    callees = [callee for _, callee, *_ in results]
    assert "forEach" in callees
