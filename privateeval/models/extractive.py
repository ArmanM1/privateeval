from __future__ import annotations

import math
import re
import time
from collections import Counter

from .base import Generation, ModelAdapter

TOKEN_RE = re.compile(r"[A-Za-z0-9$%+-]+")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "was",
    "were", "will", "with", "shall", "may", "under", "into", "after", "within",
}


def tokens(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


class ExtractiveAdapter(ModelAdapter):
    def load(self) -> None:
        started = time.perf_counter()
        self.load_time_ms = (time.perf_counter() - started) * 1000

    def summarize(self, text: str) -> Generation:
        sentences = [item.strip() for item in SENTENCE_RE.split(text) if item.strip()]
        if not sentences:
            sentences = [text.strip()] if text.strip() else []
        content = [word for word in tokens(text) if word not in STOPWORDS and len(word) > 2]
        frequencies = Counter(content)
        denominator = max(frequencies.values(), default=1)
        sentence_scores: list[tuple[float, int, str]] = []
        for index, sentence in enumerate(sentences):
            sentence_tokens = [word for word in tokens(sentence) if word not in STOPWORDS]
            lexical = sum(frequencies[word] / denominator for word in sentence_tokens)
            length_penalty = 1 / math.sqrt(max(8, len(sentence_tokens)))
            position_bonus = 0.8 / (index + 1)
            sentence_scores.append((lexical * length_penalty + position_bonus, index, sentence))
        keep = int(self.config.get("max_sentences", 3))
        selected = sorted(sorted(sentence_scores, reverse=True)[:keep], key=lambda item: item[1])
        summary = " ".join(item[2] for item in selected)
        if len(summary.split()) > 90:
            summary = " ".join(summary.split()[:90]).rstrip(" ,;:") + "."
        confidence = None
        if len(sentence_scores) >= 2:
            ranked = sorted((item[0] for item in sentence_scores), reverse=True)
            confidence = round(min(1.0, max(0.0, ranked[0] / (ranked[0] + ranked[1] + 1e-9))), 4)
        return Generation(
            text=summary,
            input_tokens=len(tokens(text)),
            output_tokens=len(tokens(summary)),
            confidence=confidence,
            metadata={"algorithm": "frequency-weighted extractive ranking"},
        )

    def model_size_mb(self) -> float:
        return 0.003


class MockOpenConfigAdapter(ExtractiveAdapter):
    """A deterministic contract fixture; never represented as a real model result."""

    def summarize(self, text: str) -> Generation:
        generated = super().summarize(text)
        generated.metadata["simulated"] = True
        generated.metadata["warning"] = "Smoke-test configuration, not an open-weight model run"
        return generated

    def model_size_mb(self) -> float:
        return 62.0 if "int8" in self.id else 248.0

