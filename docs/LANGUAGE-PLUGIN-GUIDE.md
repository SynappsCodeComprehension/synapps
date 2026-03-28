# Synapps Language Plugin Guide

This guide enables an AI agent to add full language support to Synapps by following a phased checklist. Each phase has concrete acceptance criteria that are either grep-checkable or test-runnable. No human guidance is needed beyond what is documented here.

**Prerequisites:** Familiarity with tree-sitter, LSP (Language Server Protocol), and the target language's ecosystem.

## Table of Contents

- [Phase 0: Prerequisites](#phase-0-prerequisites)
- [Phase 1: Plugin Class](#phase-1-plugin-class)
- [Phase 2: LSP Adapter](#phase-2-lsp-adapter)
- [Phase 3: Tree-Sitter Extractors](#phase-3-tree-sitter-extractors)
- [Phase 4: Integration Wiring](#phase-4-integration-wiring)
- [Phase 5: Test Fixture Project](#phase-5-test-fixture-project)
- [Phase 6: Unit Tests](#phase-6-unit-tests)
- [Phase 7: Integration Tests](#phase-7-integration-tests)
- [Appendix A: Feature Parity Matrix](#appendix-a-feature-parity-matrix)
- [Appendix B: Integration Touchpoint Map](#appendix-b-integration-touchpoint-map)
- [Appendix C: LSP Capability Checklist](#appendix-c-lsp-capability-checklist)
- [Appendix D: Troubleshooting / Common Pitfalls](#appendix-d-troubleshooting--common-pitfalls)
- [Quick Reference Card](#quick-reference-card)

---

## Phase 0: Prerequisites

Verify that the target language has the necessary infrastructure before writing any code.

### solidlsp Language Enum

- [ ] Check if the target language is already in the `Language` enum (`src/solidlsp/ls_config.py`).
  The enum currently includes: `CSHARP`, `PYTHON`, `RUST`, `JAVA`, `KOTLIN`, `TYPESCRIPT`, `GO`, `RUBY`, `DART`, `CPP`, `CPP_CCLS`, `PHP`, `R`, `PERL`, `CLOJURE`, `ELIXIR`, `ELM`.
- [ ] If the language is NOT present, add a new member to the `Language` enum:
  ```python
  # In src/solidlsp/ls_config.py
  class Language(str, Enum):
      # ... existing members ...
      {LANG_UPPER} = "{lang}"
  ```
- [ ] Verify that an LSP server implementation exists in `src/solidlsp/language_servers/`.
  Currently implemented: `csharp_language_server.py` (OmniSharp), `pyright_server.py` (Pyright), `typescript_language_server.py` (typescript-language-server).
- [ ] If no server implementation exists, create one in `src/solidlsp/language_servers/{lang}_language_server.py`. Follow the pattern of existing implementations -- each provides initialization parameters, process startup, and capability negotiation for the LSP server.

### LSP Server Selection

- [ ] Identify the LSP server for the target language (e.g., `gopls` for Go, `rust-analyzer` for Rust, `jdtls` for Java).
- [ ] Verify the LSP server supports these **required** capabilities:
  - `textDocument/documentSymbol` -- structural symbol enumeration
  - `textDocument/definition` -- definition lookup for call resolution
  - `textDocument/didOpen` -- file open notifications
  - `textDocument/didClose` -- file close notifications
- [ ] Document the initialization parameters the LSP server expects (workspace folders, settings, etc.). Reference existing servers in `src/solidlsp/language_servers/` for the pattern.

### Tree-Sitter Grammar

- [ ] Verify a tree-sitter grammar is available for the target language on PyPI. Search for `tree-sitter-{lang}` (e.g., `pip install tree-sitter-go`).
- [ ] Reference existing tree-sitter usage in `src/synapps/indexer/tree_sitter_util.py` for shared helpers (`node_text`, `find_enclosing_scope`).
- [ ] Do NOT prescribe query structures at this stage -- those are language-specific and will be defined in Phase 3.

### Acceptance Criteria

```bash
# Verify Language enum member exists
python -c "from solidlsp.ls_config import Language; print(Language.{LANG_UPPER})"

# Verify tree-sitter grammar installs
pip install tree-sitter-{lang}
python -c "import tree_sitter_{lang}"
```

---

## Phase 1: Plugin Class

Create the plugin class that implements the `LanguagePlugin` protocol.

### LanguagePlugin Protocol

The protocol is defined in `src/synapps/plugin/__init__.py` with structural typing via `@runtime_checkable`:

```python
@runtime_checkable
class LanguagePlugin(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def file_extensions(self) -> frozenset[str]: ...

    def create_lsp_adapter(self, root_path: str) -> LSPAdapter: ...

    def create_call_extractor(self): ...

    def create_import_extractor(self, source_root: str = ""): ...

    def create_base_type_extractor(self): ...

    def create_attribute_extractor(self): ...

    def create_type_ref_extractor(self) -> object | None: ...

    def create_assignment_extractor(self) -> object | None: ...
```

Every language **must** implement all 7 factory methods. If a feature does not apply, return `None`. The protocol stays uniform across all languages.

### Implementation Steps

- [ ] Create `src/synapps/plugin/{lang}.py`
- [ ] Implement the class `{Lang}Plugin` with all 9 protocol members:

| Member | Return Type | Description |
|--------|-------------|-------------|
| `name` (property) | `str` | Language identifier, e.g., `"go"` |
| `file_extensions` (property) | `frozenset[str]` | File extensions, e.g., `frozenset({".go"})` |
| `create_lsp_adapter(root_path)` | `{Lang}LSPAdapter` | Creates and returns the LSP adapter |
| `create_call_extractor()` | `{Lang}CallExtractor` | Creates the tree-sitter call site extractor |
| `create_import_extractor(source_root)` | `{Lang}ImportExtractor` | Creates the import extractor |
| `create_base_type_extractor()` | `{Lang}BaseTypeExtractor` | Creates the inheritance extractor |
| `create_attribute_extractor()` | `{Lang}AttributeExtractor` | Creates the decorator/annotation extractor |
| `create_type_ref_extractor()` | `{Lang}TypeRefExtractor \| None` | Creates the type reference extractor, or `None` if not applicable |
| `create_assignment_extractor()` | `{Lang}AssignmentExtractor \| None` | Creates the assignment extractor for DI-style field tracking, or `None` if not applicable |

- [ ] Register the plugin in `default_registry()` in `src/synapps/plugin/__init__.py`:
  ```python
  def default_registry() -> LanguageRegistry:
      from synapps.plugin.csharp import CSharpPlugin
      from synapps.plugin.python import PythonPlugin
      from synapps.plugin.typescript import TypeScriptPlugin
      from synapps.plugin.{lang} import {Lang}Plugin  # Add this

      registry = LanguageRegistry()
      registry.register(CSharpPlugin())
      registry.register(PythonPlugin())
      registry.register(TypeScriptPlugin())
      registry.register({Lang}Plugin())  # Add this
      return registry
  ```

### Reference Implementations

**PythonPlugin** (`src/synapps/plugin/python.py`):
- Returns extractors for all 7 factory methods (including `create_assignment_extractor`)
- `PythonImportExtractor` takes `source_root` parameter
- All extractors are instantiated fresh on each `create_*` call

**TypeScriptPlugin** (`src/synapps/plugin/typescript.py`):
- Returns `None` for `create_assignment_extractor()` (TypeScript does not use DI-style field tracking)
- Has 8 file extensions: `.ts`, `.tsx`, `.js`, `.jsx`, `.mts`, `.cts`, `.mjs`, `.cjs`

**CSharpPlugin** (`src/synapps/plugin/csharp.py`):
- Returns `None` for `create_assignment_extractor()`
- `CSharpImportExtractor` ignores `source_root` (C# uses namespace-based imports)

### Acceptance Criteria

```bash
python -c "
from synapps.plugin.{lang} import {Lang}Plugin
from synapps.plugin import LanguagePlugin
p = {Lang}Plugin()
assert isinstance(p, LanguagePlugin), 'Does not satisfy LanguagePlugin protocol'
assert p.name == '{lang}'
assert len(p.file_extensions) > 0
print('Plugin OK:', p.name, p.file_extensions)
"
```

---

## Phase 2: LSP Adapter

Create the LSP adapter that wraps the solidlsp language server and provides structural symbol enumeration.

### LSPAdapter Interface

Defined in `src/synapps/lsp/interface.py`:

```python
class LSPAdapter(Protocol):
    def get_workspace_files(self, root_path: str) -> list[str]: ...
    def get_document_symbols(self, file_path: str) -> list[IndexSymbol]: ...
    def find_method_calls(self, symbol: IndexSymbol) -> list[str]: ...
    def find_overridden_method(self, symbol: IndexSymbol) -> str | None: ...
    def shutdown(self) -> None: ...
```

Additionally, `LSPResolverBackend` (same file) is used by `SymbolResolver` and `CallIndexer` for Phase 2 resolution:

```python
class LSPResolverBackend(Protocol):
    repository_root_path: str
    def open_file(self, relative_file_path: str) -> AbstractContextManager[Any]: ...
    def request_definition(self, relative_file_path: str, line: int, column: int) -> list[Any]: ...
    def request_containing_symbol(self, relative_file_path: str, line: int, column: int | None = None, strict: bool = False) -> Any: ...
    def request_defining_symbol(self, relative_file_path: str, line: int, column: int, include_body: bool = False) -> Any: ...
```

The raw solidlsp instance satisfies `LSPResolverBackend` -- the adapter exposes it via the `language_server` property.

### Implementation Steps

- [ ] Create `src/synapps/lsp/{lang}.py`

- [ ] Implement `{Lang}LSPAdapter` with `__init__(self, root_path: str)`:
  - Initialize the solidlsp language server for your language
  - Store `root_path` for workspace-relative operations
  - Provide a `@classmethod create(cls, root_path: str) -> Self` factory method

- [ ] Implement `get_workspace_files(root_path: str) -> list[str]`:
  - Enumerate source files by extension (e.g., `*.go`)
  - Exclude build directories, vendor directories, generated files
  - Return absolute file paths
  - Reference: Python adapter excludes `__pycache__`, `.venv`, `node_modules`; TypeScript adapter excludes `node_modules`, `dist`, `build`, `.next`

- [ ] Implement `get_document_symbols(file_path: str) -> list[IndexSymbol]`:
  - Call LSP `textDocument/documentSymbol` on the file
  - Map LSP `SymbolKind` integers to Synapps's `IndexSymbol` instances
  - Build qualified `full_name` for each symbol

- [ ] Define `_LSP_KIND_MAP: dict[int, str]` mapping LSP SymbolKind integers to Synapps kinds:
  ```python
  _LSP_KIND_MAP = {
      5: "class",       # LSP Class
      6: "method",      # LSP Method
      7: "property",    # LSP Property
      8: "field",       # LSP Field
      11: "interface",  # LSP Interface
      12: "function",   # LSP Function
      10: "enum",       # LSP Enum
      3: "namespace",   # LSP Namespace
      # Add language-specific mappings as needed
  }
  ```

- [ ] Define `_build_{lang}_full_name(symbol, file_path, ...)`:
  - This function determines the qualified name used as the graph node identity
  - **This is a critical design decision** -- naming conventions affect symbol lookup, CALLS edges, and all graph queries
  - Reference naming strategies:
    - **C#:** Dot-separated namespace path: `MyNamespace.MyClass.MyMethod`
    - **Python:** Module-dotted path: `mypackage.mymodule.MyClass.my_method`
    - **TypeScript:** Forward-slash file path + dot-separated symbols: `src/services/auth.AuthService.login`
  - Choose the convention most natural for the target language

- [ ] Expose `language_server` property:
  ```python
  @property
  def language_server(self):
      """Raw solidlsp instance for CallIndexer/SymbolResolver access."""
      return self._ls
  ```

- [ ] Implement `shutdown()`:
  - Stop the language server process
  - Release any resources

- [ ] Implement `find_method_calls` and `find_overridden_method` as intentional stubs:
  ```python
  def find_method_calls(self, symbol: IndexSymbol) -> list[str]:
      return []  # Call resolution handled by Phase 2 tree-sitter extractors

  def find_overridden_method(self, symbol: IndexSymbol) -> str | None:
      return None  # Override detection handled by OverridesIndexer
  ```

### Testing the Adapter Standalone

Before proceeding to Phase 3, verify the adapter works in isolation:

```python
from synapps.lsp.{lang} import {Lang}LSPAdapter

adapter = {Lang}LSPAdapter.create("/path/to/test/project")
files = adapter.get_workspace_files("/path/to/test/project")
print(f"Found {len(files)} files")

symbols = adapter.get_document_symbols(files[0])
for sym in symbols:
    print(f"  {sym.kind.value}: {sym.full_name} (line {sym.line})")

adapter.shutdown()
```

### Acceptance Criteria

```bash
python -c "
from synapps.lsp.{lang} import {Lang}LSPAdapter
adapter = {Lang}LSPAdapter.create('/path/to/test/project')
files = adapter.get_workspace_files('/path/to/test/project')
assert len(files) > 0, 'No workspace files found'
symbols = adapter.get_document_symbols(files[0])
assert len(symbols) > 0, 'No symbols found in first file'
print(f'Adapter OK: {len(files)} files, {len(symbols)} symbols in first file')
adapter.shutdown()
"
```

---

## Phase 3: Tree-Sitter Extractors

Create the tree-sitter-based extractors that parse source code to find call sites, imports, inheritance, decorators, type references, and optionally assignments.

### Directory Structure

- [ ] Create `src/synapps/indexer/{lang}/` directory
- [ ] Create `src/synapps/indexer/{lang}/__init__.py` (empty)

### Shared Utilities

All extractors can use helpers from `src/synapps/indexer/tree_sitter_util.py`:

- `node_text(node) -> str` -- decode a tree-sitter node's text
- `find_enclosing_scope(line_0, sorted_lines) -> str | None` -- find the innermost scope containing a given line

Each extractor initializes its own tree-sitter parser in `__init__` using the language grammar:

```python
import tree_sitter_{lang} as ts_{lang}
from tree_sitter import Language, Parser

class {Lang}CallExtractor:
    def __init__(self):
        self._parser = Parser(Language(ts_{lang}.language()))
```

### Standard Extractors (5 required)

#### 1. Call Extractor

- [ ] Create `src/synapps/indexer/{lang}/{lang}_call_extractor.py`
- [ ] Class: `{Lang}CallExtractor`
- [ ] Method signature: `extract(file_path, source, symbol_map, *, module_name_resolver=None, class_lines=None) -> list[tuple[str, str, int, int]]`
- [ ] Returns: `list[tuple[caller_full_name, callee_simple_name, line, col]]`
- [ ] Must handle: method calls, function calls, constructor calls
- [ ] The `symbol_map` parameter is `dict[(file_path, line), full_name]` for resolving the caller scope
- [ ] Reference implementations: `python_call_extractor.py`, `typescript_call_extractor.py`

#### 2. Import Extractor

- [ ] Create `src/synapps/indexer/{lang}/{lang}_import_extractor.py`
- [ ] Class: `{Lang}ImportExtractor`
- [ ] Constructor: `__init__(self, source_root: str = "")`
- [ ] Method signature: `extract(file_path, source) -> list[...]`
- [ ] **Return type decision:**
  - Module-based languages (Python, TypeScript, Go, Rust): return `list[tuple[str, str | None]]` where each tuple is `(module_path, imported_symbol_or_None)`
  - Package/namespace-based languages (C#, Java): return `list[str]` where each string is a package/namespace name
  - The indexer dispatches on `isinstance(item, tuple)` in `_index_file_imports` -- ensure the correct type is returned
- [ ] Reference: `python_import_extractor.py` (tuple), `csharp_import_extractor.py` (string)

#### 3. Base Type Extractor

- [ ] Create `src/synapps/indexer/{lang}/{lang}_base_type_extractor.py`
- [ ] Class: `{Lang}BaseTypeExtractor`
- [ ] Method signature: `extract(file_path, source) -> list[tuple[str, str, bool]]`
- [ ] Returns: `list[tuple[class_name, base_name, is_first_base]]`
- [ ] `is_first_base` controls edge creation:
  - `True` + base is a class -> `INHERITS` edge
  - `True` + base is an interface -> `IMPLEMENTS` edge
  - `False` -> `IMPLEMENTS` edge (subsequent bases are always interfaces in C#/TS)
  - Python has special logic: ABC/Protocol bases always produce `IMPLEMENTS`
- [ ] Reference: `python_base_type_extractor.py`

#### 4. Attribute Extractor

- [ ] Create `src/synapps/indexer/{lang}/{lang}_attribute_extractor.py`
- [ ] Class: `{Lang}AttributeExtractor`
- [ ] Method signature: `extract(file_path, source) -> list[tuple[str, list[str]]]`
- [ ] Returns: `list[tuple[symbol_name, list[attribute_names]]]`
- [ ] Attributes are used to set metadata flags on graph nodes:
  - Python: `@abstractmethod`, `@staticmethod`, `@classmethod`, `ABC`, `Protocol`
  - TypeScript: `abstract`, `static`, `async`, `export`
  - C#: `[HttpGet]`, `[Authorize]`, `abstract`, `static`, `virtual`, `override`
- [ ] The attribute-to-flag mapping is in `indexer.py` `_ATTR_TO_FLAG` dict. Add new mappings there if the language introduces new markers.
- [ ] Reference: `python_attribute_extractor.py`

#### 5. Type Reference Extractor

- [ ] Create `src/synapps/indexer/{lang}/{lang}_type_ref_extractor.py`
- [ ] Class: `{Lang}TypeRefExtractor`
- [ ] Method signature: `extract(file_path, source, symbol_map, class_symbol_map, *, module_name_resolver=None) -> list[TypeRef]`
- [ ] Returns: `list[TypeRef]` where `TypeRef` is defined in `src/synapps/indexer/type_ref.py`
- [ ] Finds type annotations, type hints, parameter types, return types, and field types
- [ ] Reference: `python_type_ref_extractor.py`

### Optional Extractor

#### 6. Assignment Extractor

- [ ] Create `src/synapps/indexer/{lang}/{lang}_assignment_extractor.py` (only if the language uses constructor-injected fields / DI patterns)
- [ ] Class: `{Lang}AssignmentExtractor`
- [ ] Method signature: `extract(file_path, source, symbol_map, *, class_lines=None, module_name_resolver=None) -> list[AssignmentRef]`
- [ ] Returns: `list[AssignmentRef]` where `AssignmentRef` is defined in `src/synapps/indexer/assignment_ref.py`
- [ ] Builds field-to-type maps for assignment-aware call resolution (e.g., `self._repo = repo` -> `self._repo.save()` resolves to `Repo.save`)
- [ ] Currently only Python implements this. Return `None` from the plugin factory if not applicable.
- [ ] Reference: `python_assignment_extractor.py`

### Private Extractor Extension Points

Beyond the standard protocol extractors, languages may need custom extractors for language-specific features. For example:

- A Go plugin might add a `GoInterfaceSatisfactionExtractor` to detect implicit interface satisfaction
- A Rust plugin might add a `RustTraitImplExtractor` to track trait implementations

**Pattern for private extractors:**

1. Create the extractor class in the `src/synapps/indexer/{lang}/` directory
2. Wire it into the indexer via one of two paths:
   - **Option A:** Add a new factory method to the plugin class (not part of the protocol but callable via `getattr`)
   - **Option B:** Integrate directly in `indexer.py` behind a language guard (see Phase 4)
3. Add unit tests following the same pattern as standard extractors

### Acceptance Criteria

```bash
python -c "
from synapps.indexer.{lang}.{lang}_call_extractor import {Lang}CallExtractor
from synapps.indexer.{lang}.{lang}_import_extractor import {Lang}ImportExtractor
from synapps.indexer.{lang}.{lang}_base_type_extractor import {Lang}BaseTypeExtractor
from synapps.indexer.{lang}.{lang}_attribute_extractor import {Lang}AttributeExtractor
from synapps.indexer.{lang}.{lang}_type_ref_extractor import {Lang}TypeRefExtractor
assert hasattr({Lang}CallExtractor, 'extract')
assert hasattr({Lang}ImportExtractor, 'extract')
assert hasattr({Lang}BaseTypeExtractor, 'extract')
assert hasattr({Lang}AttributeExtractor, 'extract')
assert hasattr({Lang}TypeRefExtractor, 'extract')
print('All extractors importable with extract() method')
"
```

---

## Phase 4: Integration Wiring

Wire the new language into the shared indexer infrastructure. This phase requires understanding each language guard's semantic purpose.

### Language Guards in `src/synapps/indexer/indexer.py`

Each guard below represents a **semantic decision** about whether the new language shares that behavior. Do NOT blindly add the language to every tuple.

#### Guard 1: ABC/Protocol Pre-scan (line ~90)

```python
if self._language == "python":
```

**What it does:** Pre-scans all files with the attribute extractor to find classes inheriting from `ABC` or `Protocol`, then promotes them from `:Class` to `:Interface` label during the structural pass.

**Add your language IF:** The language has abstract base class or protocol/trait patterns where the LSP reports them as regular classes but they should be treated as interfaces in the graph. For example, Go interfaces are explicit (LSP reports them as interfaces), so Go would NOT need this guard.

#### Guard 2: Module Node Collection (line ~273)

```python
if self._language in ("python", "typescript"):
```

**What it does:** Collects module-level `full_name` values from symbols with `signature == "module"` and `kind == CLASS`. Wires a `module_name_resolver` into the call extractor so it can resolve module-scope function calls.

**Add your language IF:** The language has module-level (file-level) symbol scoping where files themselves are meaningful scoping units. Languages with explicit namespaces/packages (C#, Java) typically do NOT need this. Languages where a file is a module (Python, TypeScript, Go, Rust) typically DO need this.

#### Guard 3: Unresolved Call Site Debug Logging (line ~337)

```python
if self._language in ("python", "typescript"):
```

**What it does:** Logs per-site DEBUG messages for unresolved call sites after Phase 2 resolution.

**Add your language IF:** The language uses Phase 2 tree-sitter call resolution (most languages should). C# is excluded because its call resolution uses a different path.

#### Guard 4: Call Resolution Summary Stats (line ~342)

```python
if self._language in ("python", "typescript"):
```

**What it does:** Logs summary statistics (resolved/total/percentage) for call resolution and warns if zero CALLS edges were produced.

**Add your language IF:** The language uses Phase 2 tree-sitter call resolution (same criteria as Guard 3).

#### Guard 5: OverridesIndexer Execution (line ~363)

```python
if self._language in ("python", "typescript"):
```

**What it does:** Runs `OverridesIndexer` which uses pure Cypher `[:INHERITS*]` traversal to detect method overrides and create `OVERRIDES`/`DISPATCHES_TO` edges.

**Add your language IF:** The language has method overriding AND does NOT get override information from the LSP server. C# is excluded because OmniSharp provides override relationships directly. Most other languages should opt in.

#### Guard 6: Source Root Detection (line ~393)

```python
if self._language == "python":
    from synapps.lsp.python import detect_source_root
    self._import_extractor._source_root = detect_source_root(file_path, self._root_path or "")
elif self._language == "typescript":
    self._import_extractor._source_root = self._root_path or ""
```

**What it does:** Sets the `_source_root` on the import extractor, which is used to convert absolute file paths to relative module paths.

**Add your language as a new `elif` branch IF:** The import extractor has a `_source_root` attribute that needs to be set. Choose the appropriate strategy:
- **Python pattern:** Walk up from file looking for `__init__.py` boundaries
- **TypeScript pattern:** Use the repository root directly
- **Your language:** Determine the appropriate source root strategy (e.g., Go uses module paths from `go.mod`)

#### Guard 7: Symbol Kind Overrides (lines ~443-459)

```python
if self._language == "python":
    # Promotes __init__ -> constructor, top-level methods -> function, module symbols -> module
elif self._language == "typescript":
    # Promotes constructor -> constructor, top-level methods -> function, const_object -> const_object
```

**What it does:** Overrides the `kind` string on graph nodes when the LSP-reported kind does not match the desired graph kind. This is purely a graph labeling concern.

**Add a new `elif` branch IF:** The LSP for your language reports symbol kinds that need correction. Common overrides:
- Constructors reported as methods -> promote to `"constructor"`
- Top-level functions reported as methods -> promote to `"function"`
- Module-level symbols that need special kind values

#### Guard 8: Metadata Flag Extraction (line ~529)

```python
if self._language in ("python", "typescript"):
    set_metadata_flags(self._conn, fn, _attrs_to_flags(attrs))
```

**What it does:** Converts attribute/decorator names to boolean metadata flags (`is_abstract`, `is_static`, `is_classmethod`, `is_async`) on graph nodes using the `_ATTR_TO_FLAG` mapping.

**Add your language IF:** The language uses decorators, annotations, or modifiers that should be tracked as metadata flags. Also add any new language-specific markers to the `_ATTR_TO_FLAG` dict in `indexer.py`.

### Additional Files to Modify

#### `src/synapps/plugin/__init__.py`

- [ ] Add lazy import and `registry.register()` call in `default_registry()` (covered in Phase 1)

#### `pyproject.toml`

- [ ] Add `tree-sitter-{lang}` to `[project.dependencies]`:
  ```toml
  dependencies = [
      # ... existing deps ...
      "tree-sitter-{lang}>=X.Y",
  ]
  ```

#### `src/synapps/service.py`

- [ ] Check for any language-specific behavior in the service layer. Currently no language guards exist in `service.py` beyond what the plugin system handles automatically. Review if the new language requires service-level special cases.

#### `src/synapps/watcher/watcher.py`

- [ ] **No code change needed.** The file watcher receives `watched_extensions` from the plugin's `file_extensions` property automatically.

### Acceptance Criteria

```bash
# Index a test project
synapps index /path/to/fixture

# Verify nodes were created
python -c "
from synapps.graph.connection import GraphConnection
conn = GraphConnection.create('localhost')
rows = conn.query(\"MATCH (n) WHERE n.language = '{lang}' RETURN count(n)\")
print(f'Nodes: {rows[0][0]}')
assert rows[0][0] > 0, 'No nodes indexed'
"
```

---

## Phase 5: Test Fixture Project

Create a test fixture project that exercises all extractors and provides material for both unit and integration tests.

### Directory Structure

- [ ] Create `tests/fixtures/Synapps{Lang}Test/` directory
- [ ] Populate with source files covering all extractor scenarios

### Required Fixture Elements

The fixture must contain the following elements. Each maps to specific extractors that use it for testing:

| Fixture Element | Which Extractors/Indexers Test It | Example |
|----------------|----------------------------------|---------|
| Class with methods | `call_extractor`, `attribute_extractor`, structural indexing | `class Animal` with `speak()`, `move()` |
| Interface / trait / protocol | `base_type_extractor`, `MethodImplementsIndexer` | `interface IAnimal` or equivalent |
| Class inheriting from interface | `base_type_extractor` (`is_first=True` -> INHERITS or IMPLEMENTS based on language) | `class Dog implements IAnimal` |
| Class inheriting from class | `base_type_extractor` (class-to-class inheritance) | `class Puppy extends Dog` |
| Method calling another method | `call_extractor` (same-class and cross-class calls) | `animal.speak()` inside a service method |
| Cross-file import | `import_extractor` (module path resolution) | `import { Animal } from './animals'` |
| Decorator / annotation on class or method | `attribute_extractor` (metadata flags) | `@abstractmethod` or `abstract` keyword |
| Type annotation on parameter | `type_ref_extractor` (REFERENCES edges) | `def greet(animal: Animal)` |
| Constructor with injected dependency | `assignment_extractor` (if implemented) | `this.repo = repo` in constructor |
| Abstract/virtual method + concrete override | `OverridesIndexer` integration | abstract `speak()` + `Dog.speak()` |
| Module-level / top-level function | Symbol kind override logic | `function formatName(...)` at file scope |

### Reference Fixtures

- **C#:** `tests/fixtures/SynappsTest/` -- Controllers/, Models/, Services/ directories with `.csproj`
- **Python:** `tests/fixtures/SynappsPyTest/synappspytest/` -- `animals.py`, `services.py`, `models.py`, `utils.py`, `config.py`, `__init__.py`
- **TypeScript:** `tests/fixtures/SynappsJSTest/src/` -- `animals.ts`, `services.ts`, `models.ts`, `utils.js`, `index.ts`

**Pattern:** Fixtures are structurally parallel -- each has classes, interfaces, inheritance chains, services with dependency injection, and utility functions.

### Acceptance Criteria

```bash
# Verify fixture directory exists with source files
test -d tests/fixtures/Synapps{Lang}Test/ && \
  find tests/fixtures/Synapps{Lang}Test/ -name "*.{ext}" | head -5
```

---

## Phase 6: Unit Tests

Create unit tests for each extractor. Tests use inline source strings and verify extractor output.

### Test Files to Create

- [ ] `tests/unit/indexer/test_{lang}_call_extractor.py`
- [ ] `tests/unit/indexer/test_{lang}_import_extractor.py`
- [ ] `tests/unit/indexer/test_{lang}_base_type_extractor.py`
- [ ] `tests/unit/indexer/test_{lang}_attribute_extractor.py`
- [ ] `tests/unit/indexer/test_{lang}_type_ref_extractor.py`
- [ ] (Optional) `tests/unit/indexer/test_{lang}_assignment_extractor.py`

### Test Pattern

Each test file follows this pattern:

```python
import pytest
from synapps.indexer.{lang}.{lang}_call_extractor import {Lang}CallExtractor

@pytest.fixture
def extractor():
    return {Lang}CallExtractor()

def test_simple_method_call(extractor):
    source = '''
    // inline source code here
    '''
    symbol_map = {("test.{ext}", 1): "MyClass.myMethod"}
    results = extractor.extract("test.{ext}", source, symbol_map)
    assert len(results) == 1
    assert results[0][1] == "calledMethod"  # callee_simple_name
```

### Scenario Categories Per Extractor

**call_extractor:**
- `test_simple_method_call` -- `obj.method()`
- `test_chained_method_call` -- `obj.method().chain()`
- `test_constructor_call` -- `new ClassName()` or equivalent
- `test_static_method_call` -- `ClassName.staticMethod()`
- `test_function_call` -- `freeFunction()`
- `test_no_calls` -- file with no call sites

**import_extractor:**
- `test_single_import` -- single import statement
- `test_multiple_imports` -- multiple items from one source
- `test_relative_import` -- relative path import (if applicable)
- `test_wildcard_import` -- wildcard/star import (if applicable)
- `test_no_imports` -- file with no imports

**base_type_extractor:**
- `test_single_inheritance` -- class extends one base
- `test_multiple_inheritance` -- class extends multiple bases (if applicable)
- `test_interface_implementation` -- class implements interface
- `test_no_inheritance` -- class with no base types

**attribute_extractor:**
- `test_single_decorator` -- one decorator/annotation
- `test_multiple_decorators` -- multiple decorators on same symbol
- `test_class_and_method_decorators` -- decorators on both class and method
- `test_no_decorators` -- symbol with no decorators

**type_ref_extractor:**
- `test_parameter_type` -- typed function parameter
- `test_return_type` -- function return type annotation
- `test_field_type` -- typed class field
- `test_generic_type` -- generic/parameterized type (e.g., `List[int]`, `Array<string>`)
- `test_no_type_refs` -- file with no type annotations

### Acceptance Criteria

```bash
pytest tests/unit/indexer/test_{lang}_*.py -v
```

---

## Phase 7: Integration Tests

Create integration tests that verify the full indexing pipeline against the test fixture with a running Memgraph instance and language SDK.

### Test Files to Create

- [ ] `tests/integration/test_mcp_tools_{lang}.py`
- [ ] `tests/integration/test_cli_commands_{lang}.py`

### Test Structure

```python
import pytest

@pytest.mark.integration
@pytest.mark.timeout(10)
class TestMcpTools{Lang}:
    """Integration tests for {Lang} MCP tools."""

    def test_index_and_search(self, ...):
        """Index fixture and verify symbols are searchable."""
        ...

    def test_find_callers(self, ...):
        """Verify CALLS edges from call_extractor."""
        ...

    def test_get_hierarchy(self, ...):
        """Verify inheritance from base_type_extractor."""
        ...
```

### Prerequisites

- Memgraph running on `localhost:7687` (`docker compose up -d`)
- Language SDK installed (e.g., Go toolchain, Rust toolchain)
- LSP server available in PATH

### Reference Integration Tests

- **C#:** `tests/integration/test_mcp_tools.py`, `tests/integration/test_cli_commands.py`
- **Python:** `tests/integration/test_mcp_tools_python.py`, `tests/integration/test_cli_commands_python.py`
- **TypeScript:** `tests/integration/test_mcp_tools_typescript.py`, `tests/integration/test_cli_commands_typescript.py`

The shared conftest at `tests/integration/conftest.py` provides fixtures for MCP and service setup.

### Acceptance Criteria

```bash
# Start Memgraph
docker compose up -d

# Run integration tests
pytest tests/integration/test_mcp_tools_{lang}.py -v -m integration
pytest tests/integration/test_cli_commands_{lang}.py -v -m integration
```

---

## Appendix A: Feature Parity Matrix

This matrix shows which features each existing language supports. When adding a new language, fill in the `{New Lang}` column. Mark each feature as **Y** (implemented), **N/A** (not applicable to this language, with justification), or **Planned** (will implement later).

Every **Y** in existing languages should be **Y** or **N/A** (with justification) in the new language.

| Feature | C# | Python | TypeScript | {New Lang} |
|---------|:--:|:------:|:----------:|:----------:|
| `call_extractor` | Y | Y | Y | |
| `import_extractor` | Y (`list[str]`) | Y (`list[tuple]`) | Y (`list[tuple]`) | |
| `base_type_extractor` | Y | Y | Y | |
| `attribute_extractor` | Y | Y | Y | |
| `type_ref_extractor` | Y | Y | Y | |
| `assignment_extractor` | N/A | Y | N/A | |
| ABC/Protocol promotion | N/A | Y | N/A | |
| Module nodes | N/A | Y | Y | |
| OverridesIndexer (graph-based) | N/A | Y | Y | |
| OverridesIndexer (LSP-based) | Y | N/A | N/A | |
| `const_object` promotion | N/A | N/A | Y | |
| `const_function` promotion | N/A | N/A | Y | |
| Metadata flags (`is_abstract`, etc.) | Y (LSP) | Y (decorators) | Y (modifiers) | |

**Notes:**
- `import_extractor` return type varies by language paradigm: module-based languages return `list[tuple[str, str|None]]`, package-based languages return `list[str]`. See Phase 3 for details.
- `assignment_extractor` is only needed for languages with constructor-injected field patterns (DI). Most languages can return `None`.
- ABC/Protocol promotion is Python-specific. Languages with explicit interface keywords (Go, TypeScript, C#, Java) do not need this.
- OverridesIndexer (graph-based) uses pure Cypher traversal; OverridesIndexer (LSP-based) relies on the LSP server providing override info. Use graph-based unless the LSP already provides this data.

---

## Appendix B: Integration Touchpoint Map

Every shared file that needs modification when adding a new language, with exact patterns and verification commands.

### File: `src/synapps/plugin/__init__.py`

```
Action:   Add lazy import + registry.register() in default_registry()
Pattern:  Follow existing CSharp/Python/TypeScript imports
Example:  from synapps.plugin.{lang} import {Lang}Plugin
          registry.register({Lang}Plugin())
Verify:   grep "{Lang}Plugin" src/synapps/plugin/__init__.py
```

### File: `src/synapps/indexer/indexer.py`

```
Action:   Add language to guard tuples where applicable (see Phase 4 for decision criteria)
Pattern:  if self._language in ("python", "typescript", "{lang}")
Guards:   8 guards at lines ~90, ~273, ~337, ~342, ~363, ~393, ~443-459, ~529
Verify:   grep '"{lang}"' src/synapps/indexer/indexer.py
```

### File: `pyproject.toml`

```
Action:   Add tree-sitter grammar to project dependencies
Pattern:  "tree-sitter-{lang}>=X.Y"
Section:  [project.dependencies]
Verify:   grep "tree-sitter-{lang}" pyproject.toml
```

### File: `src/synapps/service.py`

```
Action:   Review for language-specific behavior (currently none beyond plugin system)
Pattern:  No current language guards in service.py
Verify:   grep '"{lang}"' src/synapps/service.py  (should return 0 results unless you added one)
```

### File: `src/synapps/watcher/watcher.py`

```
Action:   No code change needed
Reason:   FileWatcher uses plugin.file_extensions automatically
Verify:   N/A -- automatic via LanguagePlugin.file_extensions
```

### New Files to Create

| File | Purpose |
|------|---------|
| `src/synapps/plugin/{lang}.py` | Plugin class |
| `src/synapps/lsp/{lang}.py` | LSP adapter |
| `src/synapps/indexer/{lang}/__init__.py` | Extractor package |
| `src/synapps/indexer/{lang}/{lang}_call_extractor.py` | Call site extractor |
| `src/synapps/indexer/{lang}/{lang}_import_extractor.py` | Import extractor |
| `src/synapps/indexer/{lang}/{lang}_base_type_extractor.py` | Inheritance extractor |
| `src/synapps/indexer/{lang}/{lang}_attribute_extractor.py` | Attribute/decorator extractor |
| `src/synapps/indexer/{lang}/{lang}_type_ref_extractor.py` | Type reference extractor |
| `src/synapps/indexer/{lang}/{lang}_assignment_extractor.py` | Assignment extractor (optional) |
| `tests/fixtures/Synapps{Lang}Test/` | Test fixture project |
| `tests/unit/indexer/test_{lang}_call_extractor.py` | Call extractor unit tests |
| `tests/unit/indexer/test_{lang}_import_extractor.py` | Import extractor unit tests |
| `tests/unit/indexer/test_{lang}_base_type_extractor.py` | Base type extractor unit tests |
| `tests/unit/indexer/test_{lang}_attribute_extractor.py` | Attribute extractor unit tests |
| `tests/unit/indexer/test_{lang}_type_ref_extractor.py` | Type ref extractor unit tests |
| `tests/integration/test_mcp_tools_{lang}.py` | MCP integration tests |
| `tests/integration/test_cli_commands_{lang}.py` | CLI integration tests |

---

## Appendix C: LSP Capability Checklist

### Required vs Optional LSP Capabilities

| Capability | Required | Used By | Notes |
|-----------|:--------:|---------|-------|
| `textDocument/documentSymbol` | **Required** | `get_document_symbols` | Structural indexing -- enumerates all symbols in a file |
| `textDocument/definition` | **Required** | `request_defining_symbol` | Phase 2 call resolution -- resolves callee identities |
| `textDocument/didOpen` | **Required** | `open_file` | File tracking -- notifies LSP of open files |
| `textDocument/didClose` | **Required** | `close_file` | File tracking -- notifies LSP of closed files |
| `textDocument/didChange` | Optional | Not currently used | Incremental file updates (Synapps re-reads from disk) |
| `callHierarchy/incomingCalls` | Optional | Not used | Stubs exist in LSPAdapter but are intentionally empty. Synapps uses tree-sitter + definition resolution instead. |
| `textDocument/references` | Optional | Not used | Could be used for find_usages but Synapps uses graph queries |
| `workspace/symbol` | Optional | Not used | Synapps enumerates per-file via documentSymbol |

### Testing an LSP Adapter Standalone

Follow this sequence to verify the adapter works before integrating:

1. **Start the LSP server:**
   ```python
   from synapps.lsp.{lang} import {Lang}LSPAdapter
   adapter = {Lang}LSPAdapter.create("/path/to/test/project")
   ```

2. **List workspace files:**
   ```python
   files = adapter.get_workspace_files("/path/to/test/project")
   print(f"Found {len(files)} source files")
   # Verify: list should contain only source files (no build artifacts, vendor dirs)
   ```

3. **Extract symbols from a test file:**
   ```python
   symbols = adapter.get_document_symbols(files[0])
   for sym in symbols:
       print(f"  {sym.kind.value}: {sym.full_name} (line {sym.line})")
   # Verify: symbols should include classes, methods, fields as expected
   ```

4. **Test definition resolution (for Phase 2):**
   ```python
   ls = adapter.language_server
   rel_path = os.path.relpath(files[0], "/path/to/test/project")
   with ls.open_file(rel_path):
       result = ls.request_defining_symbol(rel_path, line=5, column=10)
       print(f"Definition: {result}")
   # Verify: should return the symbol definition for the token at line 5, col 10
   ```

5. **Shut down:**
   ```python
   adapter.shutdown()
   ```

### solidlsp Language Server Implementation

If the target language does not have a server in `src/solidlsp/language_servers/`, create one following this pattern:

```python
# src/solidlsp/language_servers/{lang}_language_server.py
from solidlsp.ls_config import Language, ServerConfig

class {Lang}LanguageServer:
    """solidlsp wrapper for the {lang} LSP server."""

    @staticmethod
    def get_config() -> ServerConfig:
        return ServerConfig(
            language=Language.{LANG_UPPER},
            command=["{lsp-server-binary}", "--stdio"],  # e.g., "gopls", "rust-analyzer"
            initialization_options={},
        )
```

The exact structure depends on the solidlsp version. Reference existing implementations for the current API.

---

## Appendix D: Troubleshooting / Common Pitfalls

### Pitfall 1: Language Guard Semantics

**What goes wrong:** Blindly adding a new language to every `if language in (...)` tuple in `indexer.py`, causing incorrect graph structure or spurious edges.

**Why it happens:** Guards look mechanical but encode language-specific behavior decisions. For example, ABC/Protocol pre-scan (Guard 1) only makes sense for languages where the LSP does not distinguish interfaces from classes.

**How to avoid:** Read the Phase 4 documentation for each guard. Understand WHAT the guard does and WHEN a new language should opt in. Test each guard independently.

**Warning signs:** Test failures in structural indexing, unexpected `:Interface` labels, spurious OVERRIDES edges, or incorrect symbol kinds in the graph.

### Pitfall 2: Import Extractor Return Type Divergence

**What goes wrong:** The import extractor returns the wrong type. The indexer's `_index_file_imports` dispatches on `isinstance(item, tuple)` to decide between module-path imports and package-name imports. Wrong type = no IMPORTS edges in the graph.

**Why it happens:** C# returns `list[str]` (package names like `"System.Collections.Generic"`), while Python and TypeScript return `list[tuple[str, str|None]]` (module paths with optional imported symbol).

**How to avoid:** Decide early: is the language module-based (files are modules) or package-based (namespaces/packages are the unit)? Module-based -> tuples. Package-based -> strings.

**Warning signs:** `IMPORTS` edges missing entirely from the graph. `grep "IMPORTS" ...` returns no results after indexing.

### Pitfall 3: solidlsp Language Server Availability

**What goes wrong:** The `Language` enum lists the language, but no server implementation exists. The adapter fails at instantiation with `ImportError` or `AttributeError`.

**Why it happens:** The `Language` enum in `ls_config.py` lists 17+ languages, but only 3 have actual server implementations in `src/solidlsp/language_servers/` (C#, Python, TypeScript).

**How to avoid:** Always check `src/solidlsp/language_servers/` for an existing implementation BEFORE writing the LSP adapter. If none exists, creating one is part of Phase 0.

**Warning signs:** `ImportError` or `ModuleNotFoundError` when instantiating the LSP adapter.

### Pitfall 4: Full Name Construction Strategy

**What goes wrong:** Using the wrong qualified name format causes duplicate nodes, broken CONTAINS edges, and symbol lookup failures.

**Why it happens:** Each language has a different `_build_{lang}_full_name` function with a different naming convention:
- C#: `Namespace.Class.Method` (dot-separated namespace path)
- Python: `package.module.Class.method` (module-dotted path from source root)
- TypeScript: `src/path/file.Class.method` (forward-slash file path + dot-separated symbols)

**How to avoid:** Choose the naming convention most natural for the language. Document the decision. Test by verifying `full_name` uniqueness across the fixture project. The `full_name` is the graph node identity -- it must be globally unique within a project.

**Warning signs:** Duplicate nodes for the same symbol, CALLS edges pointing to non-existent nodes, `search_symbols` returning unexpected results.

### Pitfall 5: Source Root Detection

**What goes wrong:** Import paths resolve to wrong modules or produce no edges at all because the source root is incorrect.

**Why it happens:** The `_source_root` on the import extractor determines how absolute file paths are converted to module paths. Python walks up looking for `__init__.py` boundaries. TypeScript uses the repository root. A wrong source root means wrong module paths.

**How to avoid:** Determine the language's source root strategy during Phase 2:
- Does the language have a manifest file that defines the source root? (e.g., `go.mod`, `Cargo.toml`)
- Does the language use the repo root? (TypeScript)
- Does the language use package markers? (Python's `__init__.py`)
Add the appropriate logic as an `elif` branch in Guard 6 (line ~393 of `indexer.py`).

**Warning signs:** `IMPORTS` edges point to wrong module paths or are entirely missing.

### Pitfall 6: Missing pyproject.toml Dependency

**What goes wrong:** Tree-sitter grammar package is not installed, causing `ModuleNotFoundError` on first import of any extractor.

**Why it happens:** Forgetting to add `tree-sitter-{lang}` to `[project.dependencies]` in `pyproject.toml`.

**How to avoid:** Add the dependency as an explicit checklist item in Phase 4. Always run `pip install -e .` after modifying `pyproject.toml` to verify.

**Warning signs:** `ModuleNotFoundError: No module named 'tree_sitter_{lang}'` when running tests.

---

## Quick Reference Card

### Files to Create

| Category | Files |
|----------|-------|
| Plugin | `src/synapps/plugin/{lang}.py` |
| LSP Adapter | `src/synapps/lsp/{lang}.py` |
| Extractors (5-6) | `src/synapps/indexer/{lang}/{lang}_call_extractor.py`, `{lang}_import_extractor.py`, `{lang}_base_type_extractor.py`, `{lang}_attribute_extractor.py`, `{lang}_type_ref_extractor.py`, optionally `{lang}_assignment_extractor.py` |
| Package init | `src/synapps/indexer/{lang}/__init__.py` |
| Test fixture | `tests/fixtures/Synapps{Lang}Test/` with source files |
| Unit tests (5-6) | `tests/unit/indexer/test_{lang}_call_extractor.py`, etc. |
| Integration tests (2) | `tests/integration/test_mcp_tools_{lang}.py`, `tests/integration/test_cli_commands_{lang}.py` |

### Files to Modify

| File | Change |
|------|--------|
| `src/synapps/plugin/__init__.py` | Add import + `registry.register()` in `default_registry()` |
| `src/synapps/indexer/indexer.py` | Add language to applicable guard tuples (Phase 4) |
| `pyproject.toml` | Add `tree-sitter-{lang}` to dependencies |

### Verification Commands (All Phases)

```bash
# Phase 0: Prerequisites
python -c "from solidlsp.ls_config import Language; print(Language.{LANG_UPPER})"
python -c "import tree_sitter_{lang}"

# Phase 1: Plugin class
python -c "from synapps.plugin.{lang} import {Lang}Plugin; from synapps.plugin import LanguagePlugin; assert isinstance({Lang}Plugin(), LanguagePlugin)"

# Phase 2: LSP adapter (requires language SDK + LSP server)
python -c "from synapps.lsp.{lang} import {Lang}LSPAdapter; a = {Lang}LSPAdapter.create('/path/to/fixture'); print(len(a.get_workspace_files('/path/to/fixture'))); a.shutdown()"

# Phase 3: Extractors
python -c "from synapps.indexer.{lang}.{lang}_call_extractor import {Lang}CallExtractor; assert hasattr({Lang}CallExtractor, 'extract')"

# Phase 4: Integration wiring
grep '"{lang}"' src/synapps/indexer/indexer.py
grep "tree-sitter-{lang}" pyproject.toml
grep "{Lang}Plugin" src/synapps/plugin/__init__.py

# Phase 5: Fixture
test -d tests/fixtures/Synapps{Lang}Test/

# Phase 6: Unit tests
pytest tests/unit/indexer/test_{lang}_*.py -v

# Phase 7: Integration tests
pytest tests/integration/test_mcp_tools_{lang}.py tests/integration/test_cli_commands_{lang}.py -v -m integration
```
