from __future__ import annotations

import json
from pathlib import Path


def render_report(bundle: dict) -> str:
    lines = [
        f"# PrivateEval report — {bundle['run']['id']}",
        "",
        f"**Artifact status:** `{bundle['run']['claim_status']}`  ",
        f"**Created:** {bundle['run']['created_at']}  ",
        f"**Primary metric:** {bundle['protocol']['primary_metric']}",
        "",
        "> Results are fresh-process local measurements on the recorded hardware unless marked simulated. "
        "They are not production, Apple Silicon, privacy-security, or independent-verification claims.",
        "",
        "## Aggregate results",
        "",
        "| Configuration | Semantic similarity (95% CI) | ROUGE-L | Support proxy | Median latency | Peak RSS | Model bytes |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for model in bundle["aggregates"]["models"]:
        primary = model["quality"]["semantic_similarity"]
        lines.append(
            f"| {model['label']} | {primary['mean']:.3f} [{primary['low']:.3f}, {primary['high']:.3f}] "
            f"| {model['quality']['rouge_l']['mean']:.3f} | {model['quality']['source_support']['mean']:.3f} "
            f"| {model['efficiency']['median_latency_ms']:.1f} ms | {model['efficiency']['peak_rss_mb'] or 0:.1f} MB "
            f"| {model['efficiency']['model_size_mb']:.1f} MB |"
        )
    lines.extend(["", "## Paired comparison", ""])
    comparison = bundle["analysis"].get("primary_comparison")
    if comparison:
        lines.append(
            f"`{comparison['left_model_id']} − {comparison['right_model_id']}`: "
            f"{comparison['difference']:.3f} (95% CI {comparison['low']:.3f} to {comparison['high']:.3f}); "
            f"paired dz={comparison['effect_size_dz']:.2f}, n={comparison['n']}."
        )
    else:
        lines.append("No registered model pair was available.")
    lines.extend(["", "## Robustness", ""])
    lines.append("Deltas are relative to each model's clean score on the paired source.")
    lines.append("")
    lines.append("| Configuration | Perturbation | Δ semantic similarity | n |")
    lines.append("|---|---|---:|---:|")
    for row in bundle["analysis"]["robustness"]:
        lines.append(f"| {row['model_label']} | {row['perturbation']} | {row['delta']:.3f} | {row['n']} |")
    lines.extend(["", "## Synthetic privacy canaries", ""])
    lines.append("| Configuration | Exact copy rate | Normalized copy rate |")
    lines.append("|---|---:|---:|")
    for row in bundle["analysis"]["privacy"]:
        lines.append(
            f"| {row['model_label']} | {row['exact_copy_rate']:.1%} | {row['normalized_copy_rate']:.1%} |"
        )
    human = bundle["analysis"]["human_review"]
    lines.extend(
        [
            "",
            "## Human preference",
            "",
            f"Official ratings complete: **{human['completed']} / {human['target']}**; "
            f"status: `{human['status']}`; fixed packet: `{human['packet_checksum']}`.",
        ]
    )
    if human.get("comparisons"):
        lines.extend(
            [
                "",
                "| Preferred configuration | Comparator | Preference rate (95% CI) | n |",
                "|---|---|---:|---:|",
            ]
        )
        for row in human["comparisons"]:
            lines.append(
                f"| {row['left_model_label']} | {row['right_model_label']} | "
                f"{row['left_preference_rate']:.1%} [{row['low']:.1%}, {row['high']:.1%}] | {row['n']} |"
            )
    else:
        lines.append(
            "No human-preference conclusion is made until all predetermined cards are validly rated."
        )
    if human.get("validation_errors"):
        lines.extend(["", "Validation errors:"])
        lines.extend(f"- {error}" for error in human["validation_errors"])
    lines.extend(["", "## Limitations and threats to validity", ""])
    lines.extend(f"- {item}" for item in bundle["limitations"])
    lines.extend(["", "## Reproduction", "", "See `docs/reproduction.md` and the exact config embedded in the bundle."])
    return "\n".join(lines) + "\n"


def write_bundle(bundle: dict, output_dir: str | Path) -> tuple[Path, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    bundle_path = output / "result_bundle.json"
    report_path = output / "REPORT.md"
    bundle_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_path.write_text(render_report(bundle), encoding="utf-8")
    return bundle_path, report_path
