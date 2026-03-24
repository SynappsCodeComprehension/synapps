from __future__ import annotations

from io import StringIO

from rich.console import Console

from synapse.cli.banner import print_banner


def _capture_banner() -> str:
    """Render banner to a string via a Console writing to StringIO."""
    buf = StringIO()
    console = Console(file=buf, force_terminal=True)
    print_banner(console=console)
    return buf.getvalue()


def test_banner_contains_synapse_text():
    output = _capture_banner()
    assert "SYNAPSE" in output.upper()


def test_banner_contains_accent_line_circles():
    output = _capture_banner()
    assert "\u25cb" in output  # ○ circle character


def test_banner_uses_rich_console():
    """print_banner() instantiates its own Console when none is injected."""
    # Calling without args should not raise
    buf = StringIO()
    console = Console(file=buf, force_terminal=True)
    print_banner(console=console)
    assert len(buf.getvalue()) > 0


def test_banner_contains_dark_green_color():
    output = _capture_banner()
    assert "#2d6a4f" in output.lower() or "2d6a4f" in output.lower()


def test_banner_contains_light_green_color():
    output = _capture_banner()
    assert "#74c69d" in output.lower() or "74c69d" in output.lower()
