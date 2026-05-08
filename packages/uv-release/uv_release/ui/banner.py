"""Banner: one-line opener for `uvr` (no args) or `uvr --help`.

One bold word + a tagline. No ASCII art logo, no figlet — those age badly
and make the tool feel hobbyist.
"""

from __future__ import annotations

from .console import console


def banner(version: str, tagline: str = "Release management for uv workspaces") -> None:
    # `uvr` is brand (bold magenta). The version is a ref/identifier (cyan).
    # Dim `/` separator is chrome. ASCII glyphs only — no `·` or unicode.
    console.print(f"[uvr.title]uvr[/] [uvr.value]{version}[/] [uvr.dim]/[/] {tagline}")
