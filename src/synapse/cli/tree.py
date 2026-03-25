from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TreeNode:
    label: str
    children: list[TreeNode] = field(default_factory=list)
    annotation: str | None = None


def render_tree(root: TreeNode) -> str:
    lines: list[str] = []
    label = root.label
    if root.annotation:
        label += f" [{root.annotation}]"
    lines.append(label)
    _render_children(lines, root.children, prefix="")
    return "\n".join(lines)


def _render_children(lines: list[str], children: list[TreeNode], prefix: str) -> None:
    for i, child in enumerate(children):
        is_last = i == len(children) - 1
        connector = "└── " if is_last else "├── "
        label = child.label
        if child.annotation:
            label += f" [{child.annotation}]"
        lines.append(f"{prefix}{connector}{label}")
        extension = "    " if is_last else "│   "
        _render_children(lines, child.children, prefix + extension)
