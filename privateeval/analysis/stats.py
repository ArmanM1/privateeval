from __future__ import annotations

import math
import random
import statistics
from collections.abc import Iterable


def percentile(values: list[float], probability: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def bootstrap_mean_ci(
    values: Iterable[float], samples: int, confidence: float, seed: int
) -> dict[str, float | int]:
    observed = list(values)
    if not observed:
        return {"mean": float("nan"), "low": float("nan"), "high": float("nan"), "n": 0}
    rng = random.Random(seed)
    means = []
    for _ in range(samples):
        draw = [observed[rng.randrange(len(observed))] for _ in observed]
        means.append(statistics.fmean(draw))
    alpha = (1 - confidence) / 2
    return {
        "mean": round(statistics.fmean(observed), 6),
        "low": round(percentile(means, alpha), 6),
        "high": round(percentile(means, 1 - alpha), 6),
        "n": len(observed),
    }


def paired_bootstrap_difference(
    left: Iterable[float],
    right: Iterable[float],
    samples: int,
    confidence: float,
    seed: int,
) -> dict[str, float | int]:
    pairs = list(zip(left, right))
    if not pairs:
        return {"difference": float("nan"), "low": float("nan"), "high": float("nan"), "n": 0}
    differences = [a - b for a, b in pairs]
    rng = random.Random(seed)
    boot = []
    for _ in range(samples):
        draw = [differences[rng.randrange(len(differences))] for _ in differences]
        boot.append(statistics.fmean(draw))
    alpha = (1 - confidence) / 2
    mean = statistics.fmean(differences)
    standard_deviation = statistics.stdev(differences) if len(differences) > 1 else 0.0
    effect_dz = mean / standard_deviation if standard_deviation else 0.0
    common_language = sum(value > 0 for value in differences) / len(differences)
    return {
        "difference": round(mean, 6),
        "low": round(percentile(boot, alpha), 6),
        "high": round(percentile(boot, 1 - alpha), 6),
        "effect_size_dz": round(effect_dz, 6),
        "common_language_probability": round(common_language, 6),
        "n": len(differences),
    }


def p95(values: Iterable[float]) -> float:
    return round(percentile(list(values), 0.95), 3)

