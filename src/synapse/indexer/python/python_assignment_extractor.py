from __future__ import annotations

from synapse.indexer.assignment_ref import AssignmentRef


class PythonAssignmentExtractor:
    def __init__(self) -> None:
        pass

    def extract(
        self,
        file_path: str,
        source: str,
        symbol_map: dict[tuple[str, int], str],
        class_lines: list[tuple[int, str]] | None = None,
        module_name_resolver=None,
    ) -> list[AssignmentRef]:
        raise NotImplementedError
