from __future__ import annotations

import random
import re


def typos(text: str, seed: int) -> str:
    """Swap adjacent internal characters in a deterministic 3% word sample."""
    rng = random.Random(seed)
    words = text.split()
    candidates = [index for index, word in enumerate(words) if len(re.sub(r"\W", "", word)) >= 6]
    count = max(1, round(len(words) * 0.03))
    for index in rng.sample(candidates, min(count, len(candidates))):
        word = words[index]
        positions = [i for i in range(1, len(word) - 2) if word[i : i + 2].isalpha()]
        if positions:
            pos = rng.choice(positions)
            words[index] = word[:pos] + word[pos + 1] + word[pos] + word[pos + 2 :]
    return " ".join(words)


def formatting(text: str, seed: int) -> str:
    """Add deterministic headings, bullets, repeated whitespace, and line breaks."""
    del seed
    sentences = re.split(r"(?<=[.!?])\s+", text)
    decorated = []
    for index, sentence in enumerate(sentences):
        prefix = "\n\n### SOURCE NOTE\n" if index == 0 else ("\n  •  " if index % 2 else "\n\t")
        decorated.append(prefix + sentence)
    return "".join(decorated)


def length_shift(text: str, seed: int) -> str:
    """Add irrelevant but benign boilerplate to exercise the input boundary."""
    del seed
    prefix = (
        "DOCUMENT ROUTING NOTICE. This public legislative text was normalized for a "
        "summarization evaluation. Headings, citations, dates, agencies, conditions, and "
        "amounts may be material. Do not treat this notice as part of the bill's policy. "
    )
    suffix = (
        " Administrative note: the evaluator will truncate inputs at the registered word "
        "limit and will compare every model on the same bounded text."
    )
    return prefix + text + suffix


PERTURBATIONS = {
    "typos": typos,
    "formatting": formatting,
    "length_shift": length_shift,
}


def apply_perturbation(name: str, text: str, seed: int) -> str:
    if name not in PERTURBATIONS:
        raise KeyError(f"Unknown perturbation: {name}")
    return PERTURBATIONS[name](text, seed)

