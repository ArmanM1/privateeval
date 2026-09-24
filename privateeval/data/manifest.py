from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class ManifestError(ValueError):
    """Raised when a frozen data artifact does not match its manifest."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: str | Path = "data/manifest.json") -> dict[str, Any]:
    manifest_path = Path(path)
    with manifest_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_manifest(path: str | Path = "data/manifest.json") -> dict[str, Any]:
    manifest_path = Path(path)
    root = manifest_path.parent.parent
    manifest = load_manifest(manifest_path)
    verified: list[dict[str, str]] = []

    for entry in manifest.get("files", []):
        artifact = root / entry["path"]
        if not artifact.exists():
            raise ManifestError(f"Missing frozen artifact: {artifact}")
        actual = sha256_file(artifact)
        expected = entry["sha256"].lower()
        if actual != expected:
            raise ManifestError(
                f"Checksum mismatch for {entry['path']}: expected {expected}, got {actual}"
            )
        verified.append({"path": entry["path"], "sha256": actual})

    fixture_path = root / next(
        entry["path"]
        for entry in manifest["files"]
        if entry["role"] == "frozen_test_fixture"
    )
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    test_ids = {example["id"] for example in fixture["examples"]}
    adaptation_path = root / manifest["adaptation_ids"]
    adaptation_ids = {
        line.strip()
        for line in adaptation_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    overlap = sorted(test_ids.intersection(adaptation_ids))
    if overlap:
        raise ManifestError(f"Split leakage detected for IDs: {', '.join(overlap)}")

    return {
        "dataset": manifest["dataset"],
        "verified_files": verified,
        "fixture_examples": len(test_ids),
        "leakage_overlap": overlap,
    }


def load_examples(path: str | Path, limit: int | None = None) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    examples = payload["examples"]
    return examples[:limit] if limit else examples

