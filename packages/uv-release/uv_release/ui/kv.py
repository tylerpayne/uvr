"""KV: two-column aligned key/value pairs.

Both keys and values are default fg — keys are content the user reads,
not chrome to skim past. Padded to the widest key so values form a
vertical column.
"""

from __future__ import annotations

from collections.abc import Mapping

from .console import console


def kv(pairs: Mapping[str, str]) -> None:
    if not pairs:
        return
    w = max(len(k) for k in pairs)
    for k, v in pairs.items():
        console.print(f"  {k:<{w}}  {v}")
