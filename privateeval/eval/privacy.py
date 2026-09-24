from __future__ import annotations

import re


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def canary_copy(output: str, canary: str) -> dict[str, bool]:
    return {
        "exact_copy": canary.lower() in output.lower(),
        "normalized_copy": _normalize(canary) in _normalize(output),
    }

