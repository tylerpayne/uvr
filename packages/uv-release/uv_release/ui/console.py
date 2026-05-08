"""Singleton Console + named theme.

Every other ui module imports `console` from here so styling stays in one
place. Names map to the design grammar in the spec — anywhere you'd reach
for a literal color (`bright_magenta`, `bright_yellow`), use the named style
instead so we can retune all of uvr at once.
"""

from __future__ import annotations

from rich.console import Console
from rich.theme import Theme


THEME = Theme(
    {
        # Six semantic colors, one job each. See the design spec's "Color
        # language" section: meaning before decoration. Default fg is the
        # workhorse — color is the exception, applied only where it earns
        # meaning. Pair color with a word so meaning survives NO_COLOR.
        #
        # Hero / brand — magenta marks "things the user types or follows":
        # section titles, commands, progress fill, prompt cursor, spinner.
        "uvr.title": "bold bright_magenta",
        "uvr.accent": "bright_magenta",
        "uvr.cmd": "bright_magenta",
        # Ok — completion / "this is good".
        "uvr.ok": "green",
        "uvr.clean": "green",
        "uvr.created": "green",
        "uvr.updated": "green",
        # Warn — "look here, nothing broken": review-me state.
        "uvr.changed": "bright_yellow",
        # Error — "something is wrong, act."
        "uvr.error": "red",
        "uvr.err": "bold red",
        "uvr.stale": "red",
        # Ref — names that point at stable things: tags, branches, package
        # names being acted on, pipeline step names. Cyan for "noun the
        # system tracks", distinct from magenta "verb the user runs".
        "uvr.value": "cyan",
        "uvr.path": "cyan",
        # Dim — chrome only, never content. Hyphen rules, empty progress
        # cells, the `/` banner separator, the `$` shell prompt, dim arrows.
        "uvr.dim": "dim",
        "uvr.rule": "dim",
        # Default fg — explicit non-style for clarity. `unchanged` badges
        # carry meaning via the word, no color decoration needed.
        "uvr.unchanged": "",
    }
)


# Single shared console. Don't instantiate Rich's Console anywhere else;
# multiple consoles fight over the terminal during Live/Status renders.
console = Console(theme=THEME, highlight=False, soft_wrap=False)

# Dedicated stderr console for error blocks. Rich shares a single Live
# region across calls, so a separate Console keeps stderr isolated from
# stdout's status/progress widgets.
err_console = Console(theme=THEME, highlight=False, soft_wrap=False, stderr=True)
