from privateeval.release_audit import audit_release


def test_release_audit_stays_red_for_missing_external_evidence():
    result = audit_release("public/results/result_bundle.json")
    assert result["status"] == "not_ready"
    assert "Blinded human preference with uncertainty" in result["blockers"]
    assert "Independent reproduction and claim inspection" in result["blockers"]
    assert "Versioned public repository" not in result["blockers"]
    repository_check = next(check for check in result["checks"] if check["name"] == "Versioned public repository")
    assert repository_check["passed"] is True
    demo_check = next(check for check in result["checks"] if "screenshots, video" in check["name"])
    assert demo_check["passed"] is True
    assert "67.52s 1280x720" in demo_check["evidence"]
    assert result["checks_passed"] == 11
