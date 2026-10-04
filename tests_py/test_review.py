import csv
import json
from copy import deepcopy
from pathlib import Path

import pytest

from privateeval.review import (
    RATING_COLUMNS,
    analyze_human_review,
    build_review_cards,
    import_blinded_ratings,
    packet_checksum,
)


def _records():
    records = []
    for example_index in range(8):
        for model_id in ("lead-3", "flan-t5-small-fp32", "flan-t5-small-int8"):
            records.append(
                {
                    "record_id": f"clean::example-{example_index}",
                    "example_id": f"example-{example_index}",
                    "slice": "clean",
                    "title": f"Example {example_index}",
                    "topic": "test",
                    "source": f"Public source {example_index}",
                    "output": f"Output from {model_id} for {example_index}",
                    "model_id": model_id,
                    "model_label": model_id,
                }
            )
    return records


def test_review_packet_is_deterministic_blinded_and_reaches_target():
    first, first_key = build_review_cards(_records(), 12, 20260807)
    second, second_key = build_review_cards(_records(), 12, 20260807)
    assert first == second
    assert first_key == second_key
    assert len(first) == 12
    assert len({card["card_id"] for card in first}) == 12
    assert all("model_id" not in json.dumps(card) for card in first)
    assert packet_checksum(first) == packet_checksum(second)


def test_ratings_unblind_to_pairwise_preference_intervals(tmp_path: Path):
    records = _records()
    cards, key = build_review_cards(records, 12, 20260807)
    ratings_path = tmp_path / "ratings.csv"
    with ratings_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "review_id", "card_id", "example_id", "left_blind_id",
                "right_blind_id", "choice", "reason_tag", "reviewer_id",
            ],
        )
        writer.writeheader()
        for index, card in enumerate(cards, 1):
            canonical_first = sorted(key[card["card_id"]].values())[0]
            choice = next(blind for blind, model in key[card["card_id"]].items() if model == canonical_first)
            writer.writerow(
                {
                    "review_id": f"rating-{index}",
                    "card_id": card["card_id"],
                    "example_id": card["example_id"],
                    "left_blind_id": "A",
                    "right_blind_id": "B",
                    "choice": choice,
                    "reason_tag": "missed-main-point",
                    "reviewer_id": "reviewer-test",
                }
            )
    config = deepcopy(json.loads(Path("configs/demo.json").read_text(encoding="utf-8")))
    config["human_review"]["ratings_path"] = str(ratings_path)
    result = analyze_human_review(config, records)
    assert result["status"] == "complete"
    assert result["completed"] == 12
    assert result["validation_errors"] == []
    assert result["comparisons"]
    assert all(comparison["left_preference_rate"] == 1.0 for comparison in result["comparisons"])


def _write_export(path: Path, cards: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RATING_COLUMNS)
        writer.writeheader()
        for index, card in enumerate(cards, 1):
            writer.writerow(
                {
                    "review_id": f"rating-{index}",
                    "card_id": card["card_id"],
                    "example_id": card["example_id"],
                    "left_blind_id": "A",
                    "right_blind_id": "B",
                    "choice": "Tie",
                    "reason_tag": "equivalent",
                    "reviewer_id": "reviewer-test",
                }
            )


def test_importer_freezes_only_a_complete_matching_packet(tmp_path: Path):
    packet_path = Path("artifacts/human-review/review_packet.json")
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    source = tmp_path / "export.csv"
    destination = tmp_path / "ratings.csv"
    _write_export(source, packet["cards"])

    result = import_blinded_ratings(source, packet_path, destination)

    assert result["status"] == "imported"
    assert result["ratings"] == 12
    assert result["reviewers"] == ["reviewer-test"]
    assert len(list(csv.DictReader(destination.open(encoding="utf-8")))) == 12


def test_importer_rejects_partial_or_duplicate_packets(tmp_path: Path):
    packet_path = Path("artifacts/human-review/review_packet.json")
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    source = tmp_path / "partial.csv"
    _write_export(source, packet["cards"][:-1])

    with pytest.raises(ValueError, match="missing 1 packet cards"):
        import_blinded_ratings(source, packet_path, tmp_path / "ratings.csv")

    duplicate = tmp_path / "duplicate.csv"
    _write_export(duplicate, packet["cards"][:-1] + [packet["cards"][0]])
    with pytest.raises(ValueError, match="duplicate card_id"):
        import_blinded_ratings(duplicate, packet_path, tmp_path / "ratings.csv")
