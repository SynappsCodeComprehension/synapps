from __future__ import annotations

from synapps.plugin.csharp import CSharpPlugin
from synapps.plugin.typescript import TypeScriptPlugin
from synapps.plugin.python import PythonPlugin
from synapps.plugin.java import JavaPlugin


def test_csharp_plugin_has_http_extractor() -> None:
    plugin = CSharpPlugin()
    extractor = plugin.create_http_extractor()
    assert extractor is not None


def test_typescript_plugin_has_http_extractor() -> None:
    plugin = TypeScriptPlugin()
    extractor = plugin.create_http_extractor()
    assert extractor is not None


def test_python_plugin_has_http_extractor() -> None:
    plugin = PythonPlugin()
    extractor = plugin.create_http_extractor()
    assert extractor is not None


def test_java_plugin_has_http_extractor() -> None:
    plugin = JavaPlugin()
    extractor = plugin.create_http_extractor()
    assert extractor is not None
