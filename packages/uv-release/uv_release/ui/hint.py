"""Hint: trailing line that points at the next command.

Every successful command should end with a hint or a blank line. The
text is default fg (not dim — content the user reads); only the literal
command is colored magenta so the user can copy-paste it.
"""

from __future__ import annotations

from .console import console


def hint(text: str, cmd: str | None = None) -> None:
    if cmd is None:
        console.print(f"  {text}")
        return
    # Split text on the placeholder if present, else append cmd at the end.
    if "{cmd}" in text:
        before, _, after = text.partition("{cmd}")
        console.print(f"  {before}[uvr.cmd]{cmd}[/]{after}")
    else:
        console.print(f"  {text} [uvr.cmd]{cmd}[/]")
