from __future__ import annotations

import re

from .quality import tokenize

CLAIM_SPLIT = re.compile(r"(?<=[.!?;])\s+")
NUMBER_RE = re.compile(r"(?:\$?\d[\d,]*(?:\.\d+)?%?)")
ENTITY_RE = re.compile(r"\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}|[A-Z]{2,})\b")
STOP = {"the", "a", "an", "and", "or", "of", "to", "in", "for", "with", "by", "on", "is", "it"}


def source_support(prediction: str, source: str) -> dict[str, float | int]:
    source_lower = source.lower()
    source_tokens = set(tokenize(source))
    claims = [claim.strip() for claim in CLAIM_SPLIT.split(prediction) if claim.strip()]
    if not claims:
        return {"source_support": 0.0, "supported_claims": 0, "claim_count": 0}
    supported = 0
    scores = []
    for claim in claims:
        content = [token for token in tokenize(claim) if token not in STOP and len(token) > 2]
        lexical = sum(token in source_tokens for token in content) / max(1, len(content))
        numbers = NUMBER_RE.findall(claim)
        number_ok = all(number.lower() in source_lower for number in numbers)
        entities = [entity for entity in ENTITY_RE.findall(claim) if len(entity) > 2]
        entity_ok = all(entity.lower() in source_lower for entity in entities)
        score = lexical * (1.0 if number_ok else 0.55) * (1.0 if entity_ok else 0.8)
        scores.append(score)
        if score >= 0.58:
            supported += 1
    return {
        "source_support": round(sum(scores) / len(scores), 6),
        "supported_claims": supported,
        "claim_count": len(claims),
    }

