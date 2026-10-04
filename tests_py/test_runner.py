import json
from pathlib import Path

from privateeval.runner import run_experiment


def test_smoke_bundle_has_traceable_contract(tmp_path: Path):
    bundle = run_experiment("configs/smoke.json", tmp_path)
    assert bundle["run"]["claim_status"] == "simulated_smoke"
    assert bundle["protocol"]["paired"] is True
    assert len(bundle["aggregates"]["models"]) == 3
    assert bundle["analysis"]["human_review"]["cards_available"] == 4
    assert len(bundle["analysis"]["human_review"]["cards"]) == 4
    assert all(record["record_id"] for record in bundle["records"])
    persisted = json.loads((tmp_path / "result_bundle.json").read_text(encoding="utf-8"))
    assert persisted["run"]["id"] == "privateeval-smoke-v1"
    assert (tmp_path / "REPORT.md").exists()
