from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from privateeval.data.manifest import ManifestError, validate_manifest


def _check(name: str, passed: bool, evidence: str, required: bool = True) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "required": required, "evidence": evidence}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_release(
    bundle_path: str | Path,
    root: str | Path = ".",
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    bundle_file = Path(bundle_path)
    if not bundle_file.is_absolute():
        bundle_file = (root_path / bundle_file).resolve()
    bundle = json.loads(bundle_file.read_text(encoding="utf-8"))
    checks: list[dict[str, Any]] = []

    try:
        manifest = validate_manifest(root_path / "data" / "manifest.json")
        checks.append(_check("Frozen data checksums and leakage guard", True, f"{len(manifest['verified_files'])} files verified; overlap={manifest['leakage_overlap']}"))
    except ManifestError as error:
        checks.append(_check("Frozen data checksums and leakage guard", False, str(error)))

    models = bundle.get("models", [])
    extractive = [model for model in models if model.get("kind") == "extractive"]
    open_configs = [model for model in models if model.get("kind") == "transformers"]
    checks.append(_check("Transparent baseline plus two open configurations", len(extractive) >= 1 and len(open_configs) >= 2, f"extractive={len(extractive)}, open_configs={len(open_configs)}"))

    aggregates = bundle.get("aggregates", {}).get("models", [])
    quality_complete = bool(aggregates) and all(
        all(metric in model.get("quality", {}) for metric in ("semantic_similarity", "rouge_1", "rouge_2", "rouge_l", "source_support"))
        and all(key in model["quality"]["semantic_similarity"] for key in ("mean", "low", "high", "n"))
        for model in aggregates
    )
    checks.append(_check("Quality, grounding, and confidence intervals", quality_complete, f"aggregate_models={len(aggregates)}; semantic={bundle.get('protocol', {}).get('semantic_metric')}"))

    telemetry_complete = bool(aggregates) and all(
        model.get("efficiency", {}).get("warmup_runs", 0) >= 1
        and model.get("efficiency", {}).get("measurement_repetitions", 0) >= 2
        and model.get("efficiency", {}).get("peak_rss_mb") is not None
        and model.get("efficiency", {}).get("model_size_mb") is not None
        and model.get("efficiency", {}).get("median_output_tokens_per_second") is not None
        for model in aggregates
    ) and all(model.get("telemetry_isolation") == "fresh_process" for model in models)
    checks.append(_check("Isolated efficiency telemetry", telemetry_complete, "fresh process, warm-up, repeated latency, RSS, model bytes, throughput"))

    robustness = bundle.get("analysis", {}).get("robustness", [])
    perturbations = {row.get("perturbation") for row in robustness}
    checks.append(_check("Registered robustness slices", {"typos", "formatting", "length_shift"}.issubset(perturbations), f"perturbations={sorted(item for item in perturbations if item)}"))

    privacy = bundle.get("analysis", {}).get("privacy", [])
    checks.append(_check("Synthetic privacy canaries", bool(privacy) and all(row.get("n", 0) >= 3 for row in privacy), f"model_rows={len(privacy)}; real_personal_data=false"))

    comparison = bundle.get("analysis", {}).get("primary_comparison") or {}
    stats_complete = all(key in comparison for key in ("difference", "low", "high", "effect_size_dz", "common_language_probability", "n"))
    slices = bundle.get("analysis", {}).get("slices", [])
    dimensions = {row.get("dimension") for row in slices}
    checks.append(_check("Paired statistics, effect size, and slices", stats_complete and {"topic", "length"}.issubset(dimensions), f"paired_n={comparison.get('n')}; dimensions={sorted(item for item in dimensions if item)}"))

    spot_path = root_path / "data" / "manual_spot_checks.csv"
    spot_rows = []
    if spot_path.exists():
        with spot_path.open("r", encoding="utf-8", newline="") as handle:
            spot_rows = [row for row in csv.DictReader(handle) if row.get("judgment")]
    checks.append(_check("Manual grounding spot audit", len(spot_rows) >= 5, f"audited_claims={len(spot_rows)}; preference_study=false"))

    human = bundle.get("analysis", {}).get("human_review", {})
    human_ready = (
        human.get("status") == "complete"
        and human.get("completed", 0) >= human.get("target", 1)
        and human.get("cards_available", 0) >= human.get("target", 1)
        and bool(human.get("comparisons"))
        and not human.get("validation_errors")
    )
    checks.append(_check("Blinded human preference with uncertainty", human_ready, f"completed={human.get('completed', 0)}/{human.get('target', 0)}; comparisons={len(human.get('comparisons', []))}; errors={len(human.get('validation_errors', []))}"))

    evidence_path = root_path / "artifacts" / "demo-evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8")) if evidence_path.exists() else {}
    screenshot_paths = [root_path / path for path in evidence.get("screenshots", [])]
    video_metadata_path = root_path / "artifacts" / "demo" / "privateeval-demo.json"
    video_metadata = json.loads(video_metadata_path.read_text(encoding="utf-8")) if video_metadata_path.exists() else {}
    video = video_metadata.get("video", {})
    video_path = root_path / video.get("path", "missing-video")
    video_valid = (
        video_metadata.get("run_id") == bundle.get("run", {}).get("id")
        and video_path.is_file()
        and video_path.stat().st_size == video.get("bytes")
        and _sha256(video_path) == video.get("sha256")
        and video.get("duration_seconds", 0) >= 30
        and video.get("width", 0) >= 1280
        and video.get("height", 0) >= 720
        and video_metadata.get("result_bundle", {}).get("sha256") == _sha256(bundle_file)
        and video_metadata.get("verification", {}).get("browser_console_errors") == 0
        and video_metadata.get("verification", {}).get("browser_console_warnings") == 0
        and video_metadata.get("verification", {}).get("metadata_decode") == "passed"
    )
    demo_ready = (
        evidence.get("run_id") == bundle.get("run", {}).get("id")
        and len(screenshot_paths) >= 4
        and all(path.exists() for path in screenshot_paths)
        and evidence.get("verification", {}).get("browser_console_errors_or_warnings") == 0
        and video_valid
    )
    checks.append(_check("Interactive demo screenshots, video, and browser verification", demo_ready, f"screenshots={len(screenshot_paths)}; video={video.get('duration_seconds', 0)}s {video.get('width', 0)}x{video.get('height', 0)}; run_match={evidence.get('run_id') == bundle.get('run', {}).get('id')}"))

    required_files = [
        root_path / "README.md",
        root_path / "reports" / "MODEL_CARD.md",
        root_path / "reports" / "MEASURED_RESULTS.md",
        root_path / "docs" / "experiment-registration.md",
        root_path / "docs" / "reproduction.md",
        root_path / "docs" / "demo.md",
        root_path / "docs" / "independent-verification.md",
        root_path / ".github" / "workflows" / "ci.yml",
    ]
    checks.append(_check("Documentation, model card, one-command reproduction, and CI", all(path.exists() for path in required_files), f"present={sum(path.exists() for path in required_files)}/{len(required_files)}"))

    repository_path = root_path / "data" / "public_repository.json"
    repository = json.loads(repository_path.read_text(encoding="utf-8")) if repository_path.exists() else {}
    verification_path = root_path / "data" / "independent_verification.json"
    verification = json.loads(verification_path.read_text(encoding="utf-8")) if verification_path.exists() else {}
    independent_ready = (
        verification.get("status") == "complete"
        and bool(verification.get("reviewer_id"))
        and verification.get("run_id") == bundle.get("run", {}).get("id")
        and verification.get("core_run_reproduced") is True
        and verification.get("claims_match_artifacts") is True
        and bool(verification.get("completed_at"))
        and verification.get("commit_sha") == repository.get("commit_sha")
    )
    checks.append(_check("Independent reproduction and claim inspection", independent_ready, f"status={verification.get('status', 'missing')}; reviewer={verification.get('reviewer_id') or 'none'}"))

    public_repo_ready = (
        repository.get("visibility") == "public"
        and str(repository.get("url", "")).startswith("https://")
        and bool(repository.get("verified_at"))
        and len(str(repository.get("commit_sha", ""))) == 40
    )
    checks.append(_check("Versioned public repository", public_repo_ready, f"visibility={repository.get('visibility', 'missing')}; url={repository.get('url') or 'none'}"))

    required_checks = [check for check in checks if check["required"]]
    blockers = [check for check in required_checks if not check["passed"]]
    return {
        "status": "ready" if not blockers else "not_ready",
        "run_id": bundle.get("run", {}).get("id"),
        "checks_passed": sum(check["passed"] for check in required_checks),
        "checks_total": len(required_checks),
        "checks": checks,
        "blockers": [check["name"] for check in blockers],
        "claim_policy": "Resume or portfolio claims are allowed only when status is ready.",
    }
