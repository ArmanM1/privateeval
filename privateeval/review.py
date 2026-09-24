from __future__ import annotations

import csv
import hashlib
import json
import random
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

from privateeval.analysis.stats import bootstrap_mean_ci

VALID_CHOICES = {"A", "B", "Tie"}
VALID_REASON_TAGS = {
    "unsupported",
    "missed-main-point",
    "too-long",
    "too-vague",
    "repetition",
    "privacy-copy",
    "equivalent",
}
RATING_COLUMNS = [
    "review_id",
    "card_id",
    "example_id",
    "left_blind_id",
    "right_blind_id",
    "choice",
    "reason_tag",
    "reviewer_id",
]


def build_review_cards(
    records: list[dict[str, Any]], sample_size: int, seed: int
) -> tuple[list[dict[str, Any]], dict[str, dict[str, str]]]:
    """Create a fixed, balanced, model-blinded review packet and private key."""
    clean = [record for record in records if record["slice"] == "clean"]
    model_ids = list(dict.fromkeys(record["model_id"] for record in clean))
    examples = list(dict.fromkeys(record["example_id"] for record in clean))
    record_index = {(record["example_id"], record["model_id"]): record for record in clean}
    if len(model_ids) < 2:
        return [], {}

    neural = [model_id for model_id in model_ids if "flan-t5" in model_id]
    primary_pair = tuple(neural[:2]) if len(neural) >= 2 else tuple(model_ids[:2])
    all_pairs = [primary_pair] + [
        pair for pair in combinations(model_ids, 2) if set(pair) != set(primary_pair)
    ]
    rng = random.Random(seed + 404)
    primary_candidates = [(example_id, primary_pair) for example_id in examples]
    rng.shuffle(primary_candidates)
    secondary_candidates = [
        (example_id, pair)
        for pair in all_pairs[1:]
        for example_id in examples
    ]
    rng.shuffle(secondary_candidates)
    selected = (primary_candidates + secondary_candidates)[:sample_size]

    cards: list[dict[str, Any]] = []
    key: dict[str, dict[str, str]] = {}
    for index, (example_id, pair) in enumerate(selected, 1):
        first, second = pair
        left_model, right_model = (second, first) if rng.random() < 0.5 else (first, second)
        left = record_index[(example_id, left_model)]
        right = record_index[(example_id, right_model)]
        card_id = f"review-{index:03d}"
        cards.append(
            {
                "card_id": card_id,
                "example_id": example_id,
                "title": left["title"],
                "topic": left["topic"],
                "source": left["source"],
                "output_a": left["output"],
                "output_b": right["output"],
                "blind_ids": ["A", "B"],
            }
        )
        key[card_id] = {"A": left_model, "B": right_model}
    return cards, key


def packet_checksum(cards: list[dict[str, Any]]) -> str:
    payload = json.dumps(cards, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_ratings(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.exists():
        return [], []
    errors: list[str] = []
    valid: list[dict[str, str]] = []
    seen_review_ids: set[str] = set()
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row_number, row in enumerate(csv.DictReader(handle), 2):
            if not row.get("choice"):
                continue
            review_id = row.get("review_id", "").strip()
            choice = row.get("choice", "").strip()
            reason = row.get("reason_tag", "").strip()
            if not review_id or review_id in seen_review_ids:
                errors.append(f"row {row_number}: missing or duplicate review_id")
                continue
            if choice not in VALID_CHOICES:
                errors.append(f"row {row_number}: invalid choice {choice!r}")
                continue
            if reason not in VALID_REASON_TAGS:
                errors.append(f"row {row_number}: invalid reason_tag {reason!r}")
                continue
            seen_review_ids.add(review_id)
            valid.append({key: (value or "").strip() for key, value in row.items()})
    return valid, errors


def analyze_human_review(
    config: dict[str, Any], records: list[dict[str, Any]]
) -> dict[str, Any]:
    review_config = config["human_review"]
    target = int(review_config["sample_size"])
    cards, key = build_review_cards(records, target, int(config["seed"]))
    ratings, errors = _load_ratings(Path(review_config["ratings_path"]))
    card_index = {card["card_id"]: card for card in cards}
    model_labels = {
        record["model_id"]: record["model_label"]
        for record in records
    }
    scored: dict[tuple[str, str], list[float]] = defaultdict(list)
    completed_cards: set[str] = set()
    choice_counts: dict[str, int] = defaultdict(int)
    unblind_errors = list(errors)
    for row_number, row in enumerate(ratings, 2):
        card_id = row.get("card_id", "")
        if card_id not in card_index or card_id not in key:
            unblind_errors.append(f"rating {row_number}: unknown card_id {card_id!r}")
            continue
        if row.get("example_id") != card_index[card_id]["example_id"]:
            unblind_errors.append(f"rating {row_number}: example/card mismatch")
            continue
        left_model = key[card_id]["A"]
        right_model = key[card_id]["B"]
        canonical = tuple(sorted((left_model, right_model)))
        choice = row["choice"]
        if choice == "Tie":
            score = 0.5
        else:
            chosen = key[card_id][choice]
            score = 1.0 if chosen == canonical[0] else 0.0
        scored[canonical].append(score)
        completed_cards.add(card_id)
        choice_counts[choice] += 1

    comparisons = []
    for pair, scores in sorted(scored.items()):
        interval = bootstrap_mean_ci(
            scores,
            int(config["metrics"]["bootstrap_samples"]),
            float(config["metrics"]["confidence_level"]),
            int(config["seed"]) + 909,
        )
        comparisons.append(
            {
                "left_model_id": pair[0],
                "left_model_label": model_labels[pair[0]],
                "right_model_id": pair[1],
                "right_model_label": model_labels[pair[1]],
                "left_preference_rate": interval["mean"],
                "low": interval["low"],
                "high": interval["high"],
                "effect_vs_chance": round(float(interval["mean"]) - 0.5, 6),
                "n": interval["n"],
            }
        )

    completed = len(completed_cards)
    return {
        "status": "complete" if completed >= target and not unblind_errors else "pending",
        "completed": completed,
        "target": target,
        "cards_available": len(cards),
        "packet_checksum": packet_checksum(cards),
        "choices": dict(choice_counts),
        "comparisons": comparisons,
        "validation_errors": unblind_errors,
        "provenance": "human" if completed else "pending_external_input",
        "cards": cards,
    }


def write_review_packet(bundle: dict[str, Any], output_dir: str | Path) -> dict[str, Path]:
    config = bundle["config"]
    target = int(config["human_review"]["sample_size"])
    cards, key = build_review_cards(bundle["records"], target, int(config["seed"]))
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    packet_path = output / "review_packet.json"
    key_path = output / "review_key.json"
    ratings_path = output / "ratings-template.csv"
    packet_path.write_text(
        json.dumps(
            {
                "review_protocol": config["human_review"],
                "packet_checksum": packet_checksum(cards),
                "cards": cards,
            },
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )
    key_path.write_text(
        json.dumps({"packet_checksum": packet_checksum(cards), "key": key}, indent=2) + "\n",
        encoding="utf-8",
    )
    ratings_path.write_text(
        "review_id,card_id,example_id,left_blind_id,right_blind_id,choice,reason_tag,reviewer_id\n",
        encoding="utf-8",
    )
    return {"packet": packet_path, "key": key_path, "ratings": ratings_path}


def import_blinded_ratings(
    source_path: str | Path,
    packet_path: str | Path,
    destination_path: str | Path,
) -> dict[str, Any]:
    """Validate and atomically freeze one complete blinded rating per packet card."""
    source = Path(source_path)
    packet_file = Path(packet_path)
    destination = Path(destination_path)
    packet = json.loads(packet_file.read_text(encoding="utf-8"))
    cards = {card["card_id"]: card for card in packet.get("cards", [])}
    if not cards:
        raise ValueError("review packet contains no cards")
    if packet.get("packet_checksum") != packet_checksum(list(cards.values())):
        raise ValueError("review packet checksum mismatch")

    errors: list[str] = []
    rows: list[dict[str, str]] = []
    seen_review_ids: set[str] = set()
    seen_card_ids: set[str] = set()
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != RATING_COLUMNS:
            raise ValueError(f"rating columns must be exactly {RATING_COLUMNS}")
        for row_number, raw in enumerate(reader, 2):
            row = {key: (raw.get(key) or "").strip() for key in RATING_COLUMNS}
            review_id = row["review_id"]
            card_id = row["card_id"]
            card = cards.get(card_id)
            if not review_id or review_id in seen_review_ids:
                errors.append(f"row {row_number}: missing or duplicate review_id")
            if not card or card_id in seen_card_ids:
                errors.append(f"row {row_number}: unknown or duplicate card_id {card_id!r}")
            elif row["example_id"] != card["example_id"]:
                errors.append(f"row {row_number}: example/card mismatch")
            if row["left_blind_id"] != "A" or row["right_blind_id"] != "B":
                errors.append(f"row {row_number}: blind IDs must remain A and B")
            if row["choice"] not in VALID_CHOICES:
                errors.append(f"row {row_number}: invalid choice {row['choice']!r}")
            if row["reason_tag"] not in VALID_REASON_TAGS:
                errors.append(f"row {row_number}: invalid reason_tag {row['reason_tag']!r}")
            if not row["reviewer_id"]:
                errors.append(f"row {row_number}: reviewer_id is required")
            if review_id:
                seen_review_ids.add(review_id)
            if card:
                seen_card_ids.add(card_id)
            rows.append(row)

    missing_cards = sorted(set(cards) - seen_card_ids)
    if missing_cards:
        errors.append(f"missing {len(missing_cards)} packet cards: {', '.join(missing_cards)}")
    if len(rows) != len(cards):
        errors.append(f"expected exactly {len(cards)} ratings, found {len(rows)}")
    if errors:
        raise ValueError("; ".join(errors))

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RATING_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(destination)
    return {
        "status": "imported",
        "ratings": len(rows),
        "reviewers": sorted({row["reviewer_id"] for row in rows}),
        "packet_checksum": packet["packet_checksum"],
        "destination": str(destination),
    }
