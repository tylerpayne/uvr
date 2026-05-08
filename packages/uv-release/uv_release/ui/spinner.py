"""Spinner: ASCII `| / - \\` cycling in magenta for indeterminate work.

Use only when you can't measure progress (network, subprocess, polling).
For unit-counted work, use ProgressLine instead. Never run two spinners
at once — only one Live region should be active at a time.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from rich.spinner import SPINNERS
from rich.status import Status

from .console import console


# Register the uvr spinner once at import time. ASCII frames so they survive
# CI logs, screenshots, and README code fences without box-drawing artifacts.
SPINNERS["uvr"] = {
    "interval": 80,
    "frames": ["|", "/", "-", "\\"],
}


@contextmanager
def spinner(label: str, subtitle: str | None = None) -> Iterator[Status]:
    """Run an indeterminate spinner. Auto-clears on context exit.

    Yields the underlying `Status` so callers can swap the label live via
    `s.update("...")` as the work progresses through phases. Both label
    and subtitle render in default fg — content the user reads, not chrome.
    """
    text = label if subtitle is None else f"{label}     {subtitle}"
    status = console.status(text, spinner="uvr", spinner_style="uvr.accent")
    with status:
        yield status


def spinner_done(label: str, elapsed_ms: float | None = None) -> None:
    """Print the post-spinner completion line.

    Convention: green `[ok]` token, label and elapsed in default fg. Call
    this right after the `with spinner(...)` block exits so the line takes
    the place of the cleared spinner. ASCII `[ok]` (not unicode `✓`) so
    the line survives screenshots, CI logs, and pasted README blocks.
    """
    # Escape the brackets so Rich markup doesn't try to parse `[ok]` as a tag.
    if elapsed_ms is None:
        console.print(rf"[uvr.ok]\[ok][/] {label}")
        return
    console.print(rf"[uvr.ok]\[ok][/] {label}  {elapsed_ms:.0f}ms")
