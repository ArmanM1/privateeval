import json
from pathlib import Path

import pytest

from privateeval.data.manifest import ManifestError, validate_manifest


def test_frozen_manifest_validates():
    result = validate_manifest("data/manifest.json")
    assert result["fixture_examples"] == 8
    assert result["leakage_overlap"] == []
    assert len(result["verified_files"]) == 2


def test_leakage_guard_rejects_test_ids(tmp_path: Path):
    manifest = json.loads(Path("data/manifest.json").read_text(encoding="utf-8"))
    fixture = json.loads(Path("data/fixtures/billsum_test.json").read_text(encoding="utf-8"))
    canaries = json.loads(Path("data/fixtures/pii_canaries.json").read_text(encoding="utf-8"))
    (tmp_path / "data" / "fixtures").mkdir(parents=True)
    (tmp_path / "data" / "human_review").mkdir(parents=True)
    fixture_path = tmp_path / "data" / "fixtures" / "billsum_test.json"
    canary_path = tmp_path / "data" / "fixtures" / "pii_canaries.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
    canary_path.write_text(json.dumps(canaries), encoding="utf-8")
    from privateeval.data.manifest import sha256_file
    manifest["files"][0]["sha256"] = sha256_file(fixture_path)
    manifest["files"][1]["sha256"] = sha256_file(canary_path)
    (tmp_path / "data" / "human_review" / "adaptation_ids.txt").write_text(
        "billsum-test-0000\n", encoding="utf-8"
    )
    manifest_path = tmp_path / "data" / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ManifestError, match="Split leakage"):
        validate_manifest(manifest_path)

