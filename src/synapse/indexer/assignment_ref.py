from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AssignmentRef:
    class_full_name: str   # enclosing class or module full_name
    field_name: str        # e.g., "_handler"
    source_file: str       # absolute path
    source_line: int       # 0-indexed line of the source expression
    source_col: int        # 0-indexed column of the source expression
