from __future__ import annotations

from synapse.cli.tree import TreeNode, render_tree


class TestRenderTree:
    def test_single_node_no_children(self) -> None:
        root = TreeNode(label="Root", children=[])
        assert render_tree(root) == "Root"

    def test_single_node_with_annotation(self) -> None:
        root = TreeNode(label="Root", children=[], annotation="info")
        assert render_tree(root) == "Root [info]"

    def test_flat_children(self) -> None:
        root = TreeNode(label="Root", children=[
            TreeNode(label="A", children=[]),
            TreeNode(label="B", children=[]),
            TreeNode(label="C", children=[]),
        ])
        expected = "\n".join([
            "Root",
            "├── A",
            "├── B",
            "└── C",
        ])
        assert render_tree(root) == expected

    def test_nested_children(self) -> None:
        root = TreeNode(label="Root", children=[
            TreeNode(label="A", children=[
                TreeNode(label="A1", children=[]),
            ]),
            TreeNode(label="B", children=[]),
        ])
        expected = "\n".join([
            "Root",
            "├── A",
            "│   └── A1",
            "└── B",
        ])
        assert render_tree(root) == expected

    def test_deep_nesting(self) -> None:
        root = TreeNode(label="Root", children=[
            TreeNode(label="A", children=[
                TreeNode(label="B", children=[
                    TreeNode(label="C", children=[
                        TreeNode(label="D", children=[]),
                    ]),
                ]),
            ]),
        ])
        expected = "\n".join([
            "Root",
            "└── A",
            "    └── B",
            "        └── C",
            "            └── D",
        ])
        assert render_tree(root) == expected

    def test_child_with_annotation(self) -> None:
        root = TreeNode(label="Root", children=[
            TreeNode(label="A", children=[], annotation="depth 2"),
        ])
        expected = "\n".join([
            "Root",
            "└── A [depth 2]",
        ])
        assert render_tree(root) == expected

    def test_complex_tree(self) -> None:
        root = TreeNode(label="Service.Process()", children=[
            TreeNode(label="Repo.Query()", children=[
                TreeNode(label="Db.Execute()", children=[]),
            ]),
            TreeNode(label="Logger.Info()", children=[]),
            TreeNode(label="Cache.Get()", children=[
                TreeNode(label="Redis.Connect()", children=[]),
                TreeNode(label="Redis.Read()", children=[]),
            ]),
        ])
        expected = "\n".join([
            "Service.Process()",
            "├── Repo.Query()",
            "│   └── Db.Execute()",
            "├── Logger.Info()",
            "└── Cache.Get()",
            "    ├── Redis.Connect()",
            "    └── Redis.Read()",
        ])
        assert render_tree(root) == expected
