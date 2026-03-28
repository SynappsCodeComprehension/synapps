import pytest
import tree_sitter_java
from tree_sitter import Language, Parser
from synapps.indexer.java.java_import_extractor import JavaImportExtractor

_lang = Language(tree_sitter_java.language())
_parser = Parser(_lang)


def _parse(source: str):
    return _parser.parse(bytes(source, "utf-8"))


@pytest.fixture
def extractor():
    return JavaImportExtractor()


# ---------------------------------------------------------------------------
# Single / multiple imports
# ---------------------------------------------------------------------------


def test_single_import(extractor):
    source = """\
import java.util.List;

public class MyClass {}
"""
    results = extractor.extract("/proj/MyClass.java", _parse(source))
    assert results == ["java.util.List"]


def test_multiple_imports(extractor):
    source = """\
import java.util.List;
import java.util.Map;

public class MyClass {}
"""
    results = extractor.extract("/proj/MyClass.java", _parse(source))
    assert "java.util.List" in results
    assert "java.util.Map" in results
    assert len(results) == 2


# ---------------------------------------------------------------------------
# Wildcard imports
# ---------------------------------------------------------------------------


def test_wildcard_import(extractor):
    source = """\
import java.util.*;

public class MyClass {}
"""
    results = extractor.extract("/proj/MyClass.java", _parse(source))
    assert "java.util.*" in results


# ---------------------------------------------------------------------------
# Static imports
# ---------------------------------------------------------------------------


def test_static_import(extractor):
    source = """\
import static java.lang.Math.PI;

public class MyClass {}
"""
    results = extractor.extract("/proj/MyClass.java", _parse(source))
    assert len(results) == 1
    assert "Math" in results[0] or "java.lang.Math.PI" in results[0]


def test_static_wildcard_import(extractor):
    source = """\
import static java.lang.Math.*;

public class MyClass {}
"""
    results = extractor.extract("/proj/MyClass.java", _parse(source))
    assert len(results) == 1
    # Should contain the wildcard path
    assert "*" in results[0]


# ---------------------------------------------------------------------------
# No imports / empty source
# ---------------------------------------------------------------------------


def test_no_imports(extractor):
    source = """\
public class MyClass {
    private int count;
}
"""
    results = extractor.extract("/proj/MyClass.java", _parse(source))
    assert results == []


def test_empty_source(extractor):
    results = extractor.extract("/proj/MyClass.java", _parse(""))
    assert results == []


def test_whitespace_source(extractor):
    results = extractor.extract("/proj/MyClass.java", _parse("   \n  "))
    assert results == []


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def test_deduplicates_same_import(extractor):
    source = """\
import java.util.List;
import java.util.List;

public class MyClass {}
"""
    results = extractor.extract("/proj/MyClass.java", _parse(source))
    assert results.count("java.util.List") == 1
