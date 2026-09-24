from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from typing import Iterable, Protocol

TOKEN_RE = re.compile(r"[a-z0-9$%+-]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def _f1(overlap: int, predicted: int, reference: int) -> float:
    if not predicted or not reference or not overlap:
        return 0.0
    precision = overlap / predicted
    recall = overlap / reference
    return 2 * precision * recall / (precision + recall)


def rouge_n(prediction: str, reference: str, n: int) -> float:
    pred_tokens = tokenize(prediction)
    ref_tokens = tokenize(reference)
    pred_ngrams = Counter(tuple(pred_tokens[i : i + n]) for i in range(len(pred_tokens) - n + 1))
    ref_ngrams = Counter(tuple(ref_tokens[i : i + n]) for i in range(len(ref_tokens) - n + 1))
    overlap = sum((pred_ngrams & ref_ngrams).values())
    return _f1(overlap, sum(pred_ngrams.values()), sum(ref_ngrams.values()))


def rouge_l(prediction: str, reference: str) -> float:
    left = tokenize(prediction)
    right = tokenize(reference)
    previous = [0] * (len(right) + 1)
    for token in left:
        current = [0]
        for index, ref_token in enumerate(right, 1):
            if token == ref_token:
                current.append(previous[index - 1] + 1)
            else:
                current.append(max(current[-1], previous[index]))
        previous = current
    return _f1(previous[-1], len(left), len(right))


class SemanticScorer(Protocol):
    name: str

    def score_pairs(self, pairs: Iterable[tuple[str, str]]) -> list[float]: ...


class HashingSemanticScorer:
    """Deterministic dependency-free semantic proxy used only by smoke tests."""

    name = "hashing-semantic-proxy"

    def __init__(self, dimensions: int = 512) -> None:
        self.dimensions = dimensions

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        words = tokenize(text)
        features = words + [f"{a}_{b}" for a, b in zip(words, words[1:])]
        for feature in features:
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            value = int.from_bytes(digest, "big")
            index = value % self.dimensions
            sign = 1.0 if value & 1 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(item * item for item in vector)) or 1.0
        return [item / norm for item in vector]

    def score_pairs(self, pairs: Iterable[tuple[str, str]]) -> list[float]:
        scores = []
        for prediction, reference in pairs:
            left = self._vector(prediction)
            right = self._vector(reference)
            scores.append(max(-1.0, min(1.0, sum(a * b for a, b in zip(left, right)))))
        return scores


class MiniLMSemanticScorer:
    name = "sentence-transformers/all-MiniLM-L6-v2 cosine"

    def __init__(self, model_name: str) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise RuntimeError("MiniLM scoring requires requirements-lock.txt") from error
        self.model = SentenceTransformer(model_name, device="cpu")

    def score_pairs(self, pairs: Iterable[tuple[str, str]]) -> list[float]:
        pair_list = list(pairs)
        if not pair_list:
            return []
        texts = [text for pair in pair_list for text in pair]
        embeddings = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        scores: list[float] = []
        for index in range(0, len(embeddings), 2):
            scores.append(float(embeddings[index] @ embeddings[index + 1]))
        return scores


def make_semantic_scorer(config: dict) -> SemanticScorer:
    backend = config.get("semantic_backend", "hashing")
    if backend == "minilm":
        return MiniLMSemanticScorer(config["semantic_model"])
    if backend == "hashing":
        return HashingSemanticScorer()
    raise ValueError(f"Unknown semantic backend: {backend}")


def lexical_quality(prediction: str, reference: str) -> dict[str, float]:
    return {
        "rouge_1": round(rouge_n(prediction, reference, 1), 6),
        "rouge_2": round(rouge_n(prediction, reference, 2), 6),
        "rouge_l": round(rouge_l(prediction, reference), 6),
    }

