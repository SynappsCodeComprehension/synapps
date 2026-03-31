from __future__ import annotations

from pathlib import Path

from synapps.onboarding.agent_instructions import (
    _MD_START,
    _MD_END,
    _markdown_section,
    _cursor_mdc,
    _upsert_markdown,
    _write_cursor_mdc,
    install_agent_instructions,
)


# ---------------------------------------------------------------------------
# Markdown section generation
# ---------------------------------------------------------------------------

def test_markdown_section_has_markers():
    section = _markdown_section()
    assert section.startswith(_MD_START)
    assert section.endswith(_MD_END)
    assert "## Synapps MCP" in section


def test_markdown_section_contains_tool_guidance():
    section = _markdown_section()
    assert "get_context_for" in section
    assert "find_usages" in section
    assert "search_symbols" in section


# ---------------------------------------------------------------------------
# Cursor MDC generation
# ---------------------------------------------------------------------------

def test_cursor_mdc_has_frontmatter():
    mdc = _cursor_mdc()
    assert mdc.startswith("---\n")
    assert "alwaysApply: true" in mdc
    assert "description:" in mdc


def test_cursor_mdc_has_body():
    mdc = _cursor_mdc()
    assert "## Synapps MCP" in mdc
    assert "get_context_for" in mdc


# ---------------------------------------------------------------------------
# _upsert_markdown
# ---------------------------------------------------------------------------

def test_upsert_creates_new_file(tmp_path: Path):
    target = tmp_path / "CLAUDE.md"
    section = _markdown_section()
    _upsert_markdown(target, section)

    content = target.read_text()
    assert _MD_START in content
    assert _MD_END in content
    assert "## Synapps MCP" in content


def test_upsert_appends_to_existing_file(tmp_path: Path):
    target = tmp_path / "CLAUDE.md"
    target.write_text("# My Project\n\nSome existing content.\n")

    section = _markdown_section()
    _upsert_markdown(target, section)

    content = target.read_text()
    assert content.startswith("# My Project")
    assert "Some existing content." in content
    assert _MD_START in content
    assert _MD_END in content


def test_upsert_replaces_existing_section(tmp_path: Path):
    target = tmp_path / "CLAUDE.md"
    old_section = f"{_MD_START}\nold content\n{_MD_END}"
    target.write_text(f"# My Project\n\n{old_section}\n\nMore stuff.\n")

    section = _markdown_section()
    _upsert_markdown(target, section)

    content = target.read_text()
    assert "old content" not in content
    assert "## Synapps MCP" in content
    assert content.count(_MD_START) == 1
    assert content.count(_MD_END) == 1
    assert "# My Project" in content
    assert "More stuff." in content


def test_upsert_is_idempotent(tmp_path: Path):
    target = tmp_path / "CLAUDE.md"
    section = _markdown_section()

    _upsert_markdown(target, section)
    first = target.read_text()

    _upsert_markdown(target, section)
    second = target.read_text()

    assert first == second


def test_upsert_creates_parent_dirs(tmp_path: Path):
    target = tmp_path / "deep" / "nested" / "AGENTS.md"
    section = _markdown_section()
    _upsert_markdown(target, section)

    assert target.exists()
    assert _MD_START in target.read_text()


# ---------------------------------------------------------------------------
# _write_cursor_mdc
# ---------------------------------------------------------------------------

def test_write_cursor_mdc_creates_file(tmp_path: Path):
    target = tmp_path / ".cursor" / "rules" / "synapps.mdc"
    _write_cursor_mdc(target)

    content = target.read_text()
    assert content.startswith("---\n")
    assert "alwaysApply: true" in content
    assert "## Synapps MCP" in content


def test_write_cursor_mdc_overwrites_existing(tmp_path: Path):
    target = tmp_path / ".cursor" / "rules" / "synapps.mdc"
    target.parent.mkdir(parents=True)
    target.write_text("old stuff")

    _write_cursor_mdc(target)
    assert "old stuff" not in target.read_text()
    assert "## Synapps MCP" in target.read_text()


# ---------------------------------------------------------------------------
# install_agent_instructions (integration)
# ---------------------------------------------------------------------------

def test_install_writes_all_agent_files(tmp_path: Path):
    written = install_agent_instructions(tmp_path)

    assert "CLAUDE.md" in written
    assert "AGENTS.md" in written
    assert ".cursor/rules/synapps.mdc" in written
    assert ".github/copilot-instructions.md" in written

    assert (tmp_path / "CLAUDE.md").exists()
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".cursor" / "rules" / "synapps.mdc").exists()
    assert (tmp_path / ".github" / "copilot-instructions.md").exists()


def test_install_preserves_existing_claude_md(tmp_path: Path):
    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text("# My Project\n\nCustom instructions here.\n")

    install_agent_instructions(tmp_path)

    content = claude_md.read_text()
    assert "# My Project" in content
    assert "Custom instructions here." in content
    assert "## Synapps MCP" in content


def test_install_updates_existing_synapps_section(tmp_path: Path):
    claude_md = tmp_path / "CLAUDE.md"
    old = f"# Proj\n\n{_MD_START}\nold synapps stuff\n{_MD_END}\n\nUser notes.\n"
    claude_md.write_text(old)

    install_agent_instructions(tmp_path)

    content = claude_md.read_text()
    assert "old synapps stuff" not in content
    assert "## Synapps MCP" in content
    assert "# Proj" in content
    assert "User notes." in content
    assert content.count(_MD_START) == 1


def test_install_is_idempotent(tmp_path: Path):
    install_agent_instructions(tmp_path)
    first_claude = (tmp_path / "CLAUDE.md").read_text()
    first_cursor = (tmp_path / ".cursor" / "rules" / "synapps.mdc").read_text()

    install_agent_instructions(tmp_path)
    second_claude = (tmp_path / "CLAUDE.md").read_text()
    second_cursor = (tmp_path / ".cursor" / "rules" / "synapps.mdc").read_text()

    assert first_claude == second_claude
    assert first_cursor == second_cursor
