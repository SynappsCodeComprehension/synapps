from __future__ import annotations

from typing import TYPE_CHECKING

from synapps.graph.connection import GraphConnection

if TYPE_CHECKING:
    from synapps.service import SynappsService
from synapps.graph.lookups import (
    get_symbol, get_symbol_source_info,
    get_containing_type, get_members_overview, get_implemented_interfaces,
    get_constructor, get_summary,
    find_callers_with_sites, find_callees,
    find_relevant_deps, find_all_deps, find_test_coverage,
    get_called_members,
    find_dependencies as query_find_dependencies,
)
from synapps.graph.analysis import find_interface_contract
from synapps.service.formatting import _p, _slim, _member_line


class ContextBuilder:
    _CALLER_LIMIT = 15
    _TYPE_CALLER_LIMIT = 10
    _TYPE_METHOD_LIMIT = 10

    def __init__(self, conn: GraphConnection, service: SynappsService | None = None) -> None:
        self._conn = conn
        self._service = service

    # --- Source retrieval ---

    def get_symbol_source(self, full_name: str, include_class_signature: bool = False) -> str | None:
        info = get_symbol_source_info(self._conn, full_name)
        if info is None:
            return None
        file_path = info["file_path"]
        line = info["line"]
        end_line = info["end_line"]
        if line is None or not end_line:
            return f"Symbol '{full_name}' was indexed without line ranges. Re-index the project to enable source retrieval."
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                all_lines = f.readlines()
        except OSError:
            return f"Source file not found: {file_path}"
        source_lines = all_lines[line:end_line + 1]
        result = f"// {file_path}:{line + 1}\n{''.join(source_lines)}"
        if include_class_signature:
            parent = self._get_parent_signature(full_name)
            if parent:
                result = parent + "\n\n" + result
        return result

    # --- Context entry point ---

    def get_context_for(self, full_name: str, scope: str | None = None, max_lines: int = 200) -> str | None:
        symbol = get_symbol(self._conn, full_name)
        if symbol is None:
            return None

        props = _p(symbol)
        labels = set(props.get("_labels", []))

        if scope == "impact":
            if self._service is None:
                return "Impact scope requires service reference"
            return self._service.analyze_change_impact(full_name)

        if scope == "structure":
            if not labels & {"Class", "Interface"}:
                return f"scope='structure' requires a type (class or interface), but '{full_name}' is a {props.get('kind', 'unknown')}."
            return self._context_structure(full_name)
        elif scope == "method":
            if not labels & {"Method", "Property"}:
                return f"scope='method' requires a method or property, but '{full_name}' is a {props.get('kind', 'unknown')}."
            return self._context_method(full_name, max_lines=max_lines)
        elif scope == "edit":
            if labels & {"Method"}:
                return self._context_edit_method(full_name, max_lines=max_lines)
            elif labels & {"Class", "Interface"}:
                return self._context_edit_type(full_name, is_interface=bool(labels & {"Interface"}), max_lines=max_lines)
            else:
                kind = props.get("kind", "unknown")
                return f"scope='edit' requires a method, class, or interface, but '{full_name}' is a {kind}."
        elif scope is not None:
            return f"Unknown scope '{scope}'. Valid values: 'structure', 'method', 'edit', 'impact'."

        return self._context_full(full_name, labels=labels, max_lines=max_lines)

    # --- Shared section builders ---

    def _target_section(self, full_name: str, max_lines: int = -1, labels: set[str] | None = None) -> str:
        source = self.get_symbol_source(full_name)
        if source is not None and max_lines >= 0:
            line_count = source.count("\n") + 1
            if line_count > max_lines:
                note = f"[Source exceeds {max_lines} lines — showing structure. Use scope='method' on individual methods for full source.]"
                if labels and labels & {"Class", "Interface"}:
                    members = get_members_overview(self._conn, full_name)
                    member_lines = "\n".join(_member_line(m) for m in members)
                    return f"## Target: {full_name}\n\n{note}\n\n{member_lines}"
                else:
                    sig_line = source.split("\n", 1)[0]
                    return f"## Target: {full_name}\n\n{note}\n\n{sig_line}"
        return f"## Target: {full_name}\n\n{source or 'Source not available (re-index may be required)'}"

    def _interfaces_section(self, type_full_name: str) -> str | None:
        interfaces = get_implemented_interfaces(self._conn, type_full_name)
        if not interfaces:
            return None
        iface_blocks = []
        for iface in interfaces:
            iface_fn = _p(iface)["full_name"]
            iface_members = get_members_overview(self._conn, iface_fn)
            lines = [_member_line(m) for m in iface_members]
            iface_blocks.append(f"### {iface_fn}\n" + "\n".join(lines))
        return "## Implemented Interfaces\n\n" + "\n\n".join(iface_blocks)

    def _interface_contract_section(self, full_name: str) -> str | None:
        contract = find_interface_contract(self._conn, full_name)
        if contract["interface"] is None:
            return None
        lines = [
            f"Interface: `{contract['interface']}`",
            f"Contract method: `{contract['contract_method']}`",
        ]
        if contract["sibling_implementations"]:
            siblings = ", ".join(
                f"{s['class_name']} ({s['file_path']})"
                for s in contract["sibling_implementations"]
            )
            lines.append(f"Other implementations: {siblings}")
        return "## Interface Contract\n\n" + "\n".join(lines)

    def _callers_section(self, full_name: str, limit: int = _CALLER_LIMIT) -> str | None:
        results = find_callers_with_sites(self._conn, full_name)
        if not results:
            return None
        lines = []
        for entry in results[:limit]:
            caller_props = _p(entry["caller"])
            sites = entry["call_sites"]
            line_str = self._format_call_sites(sites)
            fp = caller_props.get("file_path", "")
            fn = caller_props["full_name"]
            if line_str:
                lines.append(f"- `{fn}` — {fp} ({line_str})")
            else:
                lines.append(f"- `{fn}` — {fp}")
        if len(results) > limit:
            lines.append(f"... and {len(results) - limit} more callers")
        return "## Direct Callers\n\n" + "\n".join(lines)

    @staticmethod
    def _format_call_sites(sites: list) -> str:
        if not sites:
            return ""
        line_numbers = sorted({s[0] for s in sites if s and s[0] is not None})
        if not line_numbers:
            return ""
        if len(line_numbers) == 1:
            return f"line {line_numbers[0]}"
        return f"lines {', '.join(str(n) for n in line_numbers)}"

    def _test_coverage_section(self, full_name: str) -> str | None:
        tests = find_test_coverage(self._conn, full_name)
        if not tests:
            return None
        lines = [f"- `{t['full_name']}` — {t['file_path']}" for t in tests]
        return "## Test Coverage\n\n" + "\n".join(lines)

    def _relevant_deps_section(self, class_full_name: str, method_full_name: str) -> str | None:
        deps = find_relevant_deps(self._conn, class_full_name, method_full_name)
        if not deps:
            return None
        dep_lines = []
        for dep_node in deps:
            dep_fn = _p(dep_node)["full_name"]
            called = get_called_members(self._conn, method_full_name, dep_fn)
            if called:
                dep_lines.append(f"### {dep_fn}\n" + "\n".join(_member_line(m) for m in called))
            else:
                members = get_members_overview(self._conn, dep_fn)
                dep_lines.append(
                    f"### {dep_fn}\n*(all members shown — no direct method calls detected)*\n"
                    + "\n".join(_member_line(m) for m in members)
                )
        return "## Constructor Dependencies (used by this method)\n\n" + "\n\n".join(dep_lines)

    def _callees_section(self, full_name: str) -> str | None:
        raw = find_callees(self._conn, full_name, include_interface_dispatch=True)
        callees = [_slim(item, "full_name", "signature") for item in raw]
        if not callees:
            return None
        lines = [f"- `{c['full_name']}` — {c.get('signature', '')}" for c in callees]
        return "## Called Methods\n\n" + "\n".join(lines)

    def _dependencies_section(self, full_name: str) -> str | None:
        raw = query_find_dependencies(self._conn, full_name, depth=1)
        deps = [{"type": _slim(r["type"], "full_name", "file_path"), "depth": r["depth"]} for r in raw]
        if not deps:
            return None
        dep_lines = []
        seen_types: set[str] = set()
        for dep in deps:
            type_fn = dep["type"]["full_name"]
            if type_fn in seen_types:
                continue
            seen_types.add(type_fn)
            type_members = get_members_overview(self._conn, type_fn)
            dep_lines.append(f"### {type_fn}\n" + "\n".join(_member_line(m) for m in type_members))
        return "## Parameter & Return Types\n\n" + "\n\n".join(dep_lines)

    def _summaries_section(self, full_names: list[str]) -> str | None:
        entries = []
        for fn in full_names:
            s = get_summary(self._conn, fn)
            if s:
                entries.append(f"**{fn}:** {s}")
        if not entries:
            return None
        return "## Summaries\n\n" + "\n\n".join(entries)

    # --- Context composers ---

    def _context_full(self, full_name: str, labels: set[str] | None = None, max_lines: int = -1) -> str:
        sections: list[str] = []

        sections.append(self._target_section(full_name, max_lines=max_lines, labels=labels or set()))

        parent = get_containing_type(self._conn, full_name)
        if parent:
            parent_fn = _p(parent)["full_name"]
            members = get_members_overview(self._conn, parent_fn)
            sections.append(
                f"## Containing Type: {parent_fn}\n\n"
                + "\n".join(_member_line(m) for m in members)
            )

            iface_section = self._interfaces_section(parent_fn)
            if iface_section:
                sections.append(iface_section)

        callees_section = self._callees_section(full_name)
        if callees_section:
            sections.append(callees_section)

        deps_section = self._dependencies_section(full_name)
        if deps_section:
            sections.append(deps_section)

        # Summaries: symbol + parent + parent's interfaces, or symbol + own interfaces
        summary_fns = [full_name]
        if parent:
            parent_fn = _p(parent)["full_name"]
            summary_fns.append(parent_fn)
            for iface in get_implemented_interfaces(self._conn, parent_fn):
                summary_fns.append(_p(iface)["full_name"])
        else:
            for iface in get_implemented_interfaces(self._conn, full_name):
                summary_fns.append(_p(iface)["full_name"])
        summaries_section = self._summaries_section(summary_fns)
        if summaries_section:
            sections.append(summaries_section)

        return "\n\n---\n\n".join(sections)

    def _context_structure(self, full_name: str) -> str:
        sections: list[str] = []

        # Constructor source (if exists)
        ctor = get_constructor(self._conn, full_name)
        if ctor is not None:
            ctor_fn = _p(ctor)["full_name"]
            ctor_source = self.get_symbol_source(ctor_fn)
            if ctor_source:
                sections.append(f"## Constructor\n\n{ctor_source}")

        # Member signatures
        members = get_members_overview(self._conn, full_name)
        if members:
            sections.append(
                f"## Members: {full_name}\n\n"
                + "\n".join(_member_line(m) for m in members)
            )

        # Implemented interfaces
        iface_section = self._interfaces_section(full_name)
        if iface_section:
            sections.append(iface_section)

        # Summaries (type + interfaces only)
        interfaces = get_implemented_interfaces(self._conn, full_name)
        summary_fns = [full_name] + [_p(iface)["full_name"] for iface in interfaces]
        summaries_section = self._summaries_section(summary_fns)
        if summaries_section:
            sections.append(summaries_section)

        if not sections:
            return f"No structure information available for `{full_name}`."
        return "\n\n---\n\n".join(sections)

    def _context_method(self, full_name: str, max_lines: int = -1) -> str:
        sections: list[str] = []

        sections.append(self._target_section(full_name, max_lines=max_lines, labels={"Method"}))

        contract_section = self._interface_contract_section(full_name)
        if contract_section:
            sections.append(contract_section)

        callees_section = self._callees_section(full_name)
        if callees_section:
            sections.append(callees_section)

        deps_section = self._dependencies_section(full_name)
        if deps_section:
            sections.append(deps_section)

        # Summaries (method + containing type)
        summary_fns = [full_name]
        parent = get_containing_type(self._conn, full_name)
        if parent:
            summary_fns.append(_p(parent)["full_name"])
        summaries_section = self._summaries_section(summary_fns)
        if summaries_section:
            sections.append(summaries_section)

        return "\n\n---\n\n".join(sections)

    def _context_edit_method(self, full_name: str, max_lines: int = -1) -> str:
        sections: list[str] = []

        sections.append(self._target_section(full_name, max_lines=max_lines, labels={"Method"}))

        contract_section = self._interface_contract_section(full_name)
        if contract_section:
            sections.append(contract_section)

        # Direct callers
        callers_section = self._callers_section(full_name)
        if callers_section:
            sections.append(callers_section)

        # Relevant constructor deps
        parent = get_containing_type(self._conn, full_name)
        if parent:
            parent_fn = _p(parent)["full_name"]
            deps_section = self._relevant_deps_section(parent_fn, full_name)
            if deps_section:
                sections.append(deps_section)

        # Test coverage
        test_section = self._test_coverage_section(full_name)
        if test_section:
            sections.append(test_section)

        # Summaries
        summary_fns = [full_name]
        if parent:
            parent_fn = _p(parent)["full_name"]
            summary_fns.append(parent_fn)
            for iface in get_implemented_interfaces(self._conn, parent_fn):
                summary_fns.append(_p(iface)["full_name"])
        summaries_section = self._summaries_section(summary_fns)
        if summaries_section:
            sections.append(summaries_section)

        return "\n\n---\n\n".join(sections)

    def _context_edit_type(self, full_name: str, is_interface: bool = False, max_lines: int = -1) -> str:
        sections: list[str] = []

        labels = {"Interface"} if is_interface else {"Class"}
        sections.append(self._target_section(full_name, max_lines=max_lines, labels=labels))

        # Interface contracts (only for classes)
        if not is_interface:
            iface_section = self._interfaces_section(full_name)
            if iface_section:
                sections.append(iface_section)

        # Callers of public methods
        members = get_members_overview(self._conn, full_name)
        all_member_props = [_p(m) for m in members]
        methods = [mp for mp in all_member_props if "Method" in mp.get("_labels", [])]

        methods_with_callers = []
        for method in methods:
            method_fn = method["full_name"]
            results = find_callers_with_sites(self._conn, method_fn)
            if results:
                methods_with_callers.append((method, results))

        # Sort by caller count descending, limit to top N methods
        methods_with_callers.sort(key=lambda x: len(x[1]), reverse=True)
        omitted_methods = max(0, len(methods_with_callers) - self._TYPE_METHOD_LIMIT)
        callers_parts = []
        for method, results in methods_with_callers[:self._TYPE_METHOD_LIMIT]:
            sig = method.get("signature", method.get("name", "?"))
            method_lines = [f"### {method['full_name']} — {sig}"]
            for entry in results[:self._TYPE_CALLER_LIMIT]:
                caller_props = _p(entry["caller"])
                sites = entry["call_sites"]
                line_str = self._format_call_sites(sites)
                fp = caller_props.get("file_path", "")
                fn = caller_props["full_name"]
                if line_str:
                    method_lines.append(f"- `{fn}` — {fp} ({line_str})")
                else:
                    method_lines.append(f"- `{fn}` — {fp}")
            if len(results) > self._TYPE_CALLER_LIMIT:
                method_lines.append(f"... and {len(results) - self._TYPE_CALLER_LIMIT} more callers")
            callers_parts.append("\n".join(method_lines))

        if callers_parts:
            header = "## Callers of Public Methods"
            if omitted_methods > 0:
                header += f"\n\n(showing top {self._TYPE_METHOD_LIMIT} methods by caller count; {omitted_methods} more omitted)"
            sections.append(header + "\n\n" + "\n\n".join(callers_parts))
        elif methods:
            pass  # methods exist but none have callers — omit section
        else:
            sections.append("## Callers of Public Methods\n\nNo public methods found.")

        # Constructor dependencies (all, not filtered — skip for interfaces)
        if not is_interface:
            deps = find_all_deps(self._conn, full_name)
            if deps:
                dep_lines = []
                for dep_node in deps:
                    dep_fn = _p(dep_node)["full_name"]
                    dep_members = get_members_overview(self._conn, dep_fn)
                    dep_lines.append(f"### {dep_fn}\n" + "\n".join(_member_line(m) for m in dep_members))
                sections.append("## Constructor Dependencies\n\n" + "\n\n".join(dep_lines))

        # Test coverage (flat list across all methods)
        all_tests: list[dict] = []
        seen_tests: set[str] = set()
        for method in methods:
            for t in find_test_coverage(self._conn, method["full_name"]):
                if t["full_name"] not in seen_tests:
                    seen_tests.add(t["full_name"])
                    all_tests.append(t)
        if all_tests:
            test_lines = [f"- `{t['full_name']}` — {t['file_path']}" for t in all_tests]
            sections.append("## Test Coverage\n\n" + "\n".join(test_lines))

        # Summaries
        interfaces = get_implemented_interfaces(self._conn, full_name)
        summary_fns = [full_name] + [_p(iface)["full_name"] for iface in interfaces]
        summaries_section = self._summaries_section(summary_fns)
        if summaries_section:
            sections.append(summaries_section)

        return "\n\n---\n\n".join(sections)

    # --- Internal helpers ---

    def _get_parent_signature(self, full_name: str) -> str | None:
        """Get the declaration line of the containing class/interface."""
        rows = self._conn.query(
            "MATCH (parent)-[:CONTAINS]->(n {full_name: $full_name}) "
            "WHERE parent:Class OR parent:Interface "
            "RETURN parent.full_name, parent.line, parent.end_line",
            {"full_name": full_name},
        )
        if not rows:
            return None
        parent_full_name = rows[0][0]
        parent_line = rows[0][1]
        if parent_line is None:
            return f"// Containing type: {parent_full_name}"
        parent_info = get_symbol_source_info(self._conn, parent_full_name)
        if not parent_info or not parent_info["file_path"]:
            return f"// Containing type: {parent_full_name}"
        try:
            with open(parent_info["file_path"], encoding="utf-8", errors="ignore") as f:
                all_lines = f.readlines()
            return f"// {parent_info['file_path']}:{parent_line + 1}\n{all_lines[parent_line].rstrip()}"
        except (OSError, IndexError):
            return f"// Containing type: {parent_full_name}"
