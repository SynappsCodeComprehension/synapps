"""Tests for ParsedFile dataclass and plugin parse_file methods."""
from synapse.indexer.tree_sitter_util import ParsedFile
from synapse.plugin.python import PythonPlugin
from synapse.plugin.typescript import TypeScriptPlugin
from synapse.plugin.java import JavaPlugin
from synapse.plugin.csharp import CSharpPlugin


def test_parsed_file_holds_source_and_tree():
    plugin = PythonPlugin()
    source = "def foo(): pass"
    pf = plugin.parse_file("/tmp/test.py", source)
    assert isinstance(pf, ParsedFile)
    assert pf.file_path == "/tmp/test.py"
    assert pf.source == source
    assert pf.tree.root_node.type == "module"


def test_parsed_file_is_frozen():
    plugin = PythonPlugin()
    pf = plugin.parse_file("/tmp/test.py", "x = 1")
    try:
        pf.source = "y = 2"
        assert False, "Should be frozen"
    except AttributeError:
        pass


def test_python_plugin_parse_file():
    plugin = PythonPlugin()
    pf = plugin.parse_file("/tmp/test.py", "class Foo: pass")
    assert pf.tree.root_node.type == "module"


def test_typescript_plugin_parse_file_ts():
    plugin = TypeScriptPlugin()
    pf = plugin.parse_file("/tmp/test.ts", "function foo() {}")
    assert pf.tree.root_node.type == "program"


def test_typescript_plugin_parse_file_tsx():
    plugin = TypeScriptPlugin()
    pf = plugin.parse_file("/tmp/test.tsx", "const App = () => <div/>;")
    assert pf.tree.root_node.type == "program"


def test_java_plugin_parse_file():
    plugin = JavaPlugin()
    pf = plugin.parse_file("/tmp/Test.java", "class Test {}")
    assert pf.tree.root_node.type == "program"


def test_csharp_plugin_parse_file():
    plugin = CSharpPlugin()
    pf = plugin.parse_file("/tmp/Test.cs", "class Test {}")
    assert pf.tree.root_node.type == "compilation_unit"
