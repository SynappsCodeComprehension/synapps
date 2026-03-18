class _MockNode:
    """Minimal neo4j graph.Node stand-in for unit tests."""
    def __init__(self, labels: list[str], props: dict, element_id: str | None = None) -> None:
        self._props = props
        self.labels = frozenset(labels)
        self.element_id = element_id or str(id(self))

    def keys(self): return list(self._props.keys())
    def values(self): return list(self._props.values())
    def items(self): return list(self._props.items())
    def __getitem__(self, key): return self._props[key]
    def __iter__(self): return iter(self._props)
    def __len__(self): return len(self._props)
    def get(self, key, default=None): return self._props.get(key, default)
