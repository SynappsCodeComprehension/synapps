from __future__ import annotations


def symbol_suffix(raw: dict) -> str:
    """Build dotted suffix from a symbol's parent chain (no file-path prefix)."""
    name = raw.get("name", "")
    parent = raw.get("parent")
    if parent:
        return f"{symbol_suffix(parent)}.{name}"
    return name


def build_full_name(raw: dict) -> str:
    """Build a fully-qualified dotted name by walking the parent chain of a UnifiedSymbolInformation dict."""
    name = raw.get("name", "")
    parent = raw.get("parent")
    base = f"{build_full_name(parent)}.{name}" if parent is not None else name
    if "overload_idx" in raw:
        detail = raw.get("detail", "") or ""
        if "(" in detail:
            return f"{base}{detail[detail.index('('):]}"
    return base
