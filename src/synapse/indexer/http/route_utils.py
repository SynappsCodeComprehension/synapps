from __future__ import annotations

import re

# Matches {name:constraint} or {name:regex} patterns — captures just the name
_PARAM_CONSTRAINT_RE = re.compile(r"\{(\w+):[^}]+\}")


def normalize_route(class_route: str, method_route: str = "") -> str:
    """Combine and normalize a server-side route pattern.

    Handles ASP.NET conventions:
    - Tilde prefix on method_route overrides the class route
    - Type constraints are stripped: {id:guid} -> {id}
    - Leading / ensured, trailing / stripped, // collapsed
    """
    if method_route.startswith("~"):
        raw = method_route.lstrip("~").lstrip("/")
    elif class_route and method_route:
        raw = class_route.strip("/") + "/" + method_route.strip("/")
    elif class_route:
        raw = class_route.strip("/")
    elif method_route:
        raw = method_route.strip("/")
    else:
        return "/"

    # Strip type/regex constraints from route parameters
    raw = _PARAM_CONSTRAINT_RE.sub(r"{\1}", raw)

    # Ensure leading slash, strip trailing, collapse doubles
    raw = "/" + raw.lstrip("/")
    raw = raw.rstrip("/") or "/"
    while "//" in raw:
        raw = raw.replace("//", "/")

    return raw
