from __future__ import annotations

import json
import os
import platform
import random
import statistics
import subprocess
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from privateeval.analysis.stats import bootstrap_mean_ci, paired_bootstrap_difference, p95
from privateeval.data.manifest import load_examples, validate_manifest
from privateeval.data.perturb import apply_perturbation
from privateeval.eval.quality import make_semantic_scorer
from privateeval.reporting import write_bundle
from privateeval.review import analyze_human_review


def _truncate_words(text: str, maximum: int) -> str:
    return " ".join(text.split()[:maximum])


def _hardware() -> dict[str, Any]:
    memory_gb = None
    try:
        import psutil
        memory_gb = round(psutil.virtual_memory().total / (1024**3), 2)
    except ImportError:
        pass
    packages = {}
    for name in ("torch", "transformers", "sentence_transformers", "psutil"):
        try:
            module = __import__(name)
            packages[name] = getattr(module, "__version__", "unknown")
        except ImportError:
            packages[name] = None
    return {
        "os": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or os.environ.get("PROCESSOR_IDENTIFIER", "unknown"),
        "logical_cpu_count": os.cpu_count(),
        "memory_gb": memory_gb,
        "python": sys.version.split()[0],
        "packages": packages,
        "hardware_label": f"{platform.system()} CPU · {platform.machine()}",
    }


def _tasks(config: dict, examples: list[dict]) -> list[dict]:
    maximum = int(config["dataset"]["max_input_words"])
    tasks = []
    for example in examples:
        tasks.append(
            {
                "record_id": f"clean::{example['id']}",
                "example_id": example["id"],
                "slice": "clean",
                "perturbation": None,
                "title": example["title"],
                "topic": example["topic"],
                "source": _truncate_words(example["source"], maximum),
                "reference": example["reference"],
                "canary": None,
            }
        )
    robustness = config["robustness"]
    for example_index, example in enumerate(examples[: int(robustness["examples"])]):
        for perturbation in robustness["perturbations"]:
            perturbed = apply_perturbation(
                perturbation, example["source"], config["seed"] + example_index
            )
            tasks.append(
                {
                    "record_id": f"{perturbation}::{example['id']}",
                    "example_id": example["id"],
                    "slice": "robustness",
                    "perturbation": perturbation,
                    "title": example["title"],
                    "topic": example["topic"],
                    "source": _truncate_words(perturbed, maximum),
                    "reference": example["reference"],
                    "canary": None,
                }
            )
    privacy_payload = json.loads(Path(config["privacy"]["fixture"]).read_text(encoding="utf-8"))
    for canary in privacy_payload["canaries"]:
        tasks.append(
            {
                "record_id": f"privacy::{canary['id']}",
                "example_id": canary["id"],
                "slice": "privacy",
                "perturbation": None,
                "title": f"Synthetic {canary['type']} canary",
                "topic": "synthetic_privacy",
                "source": _truncate_words(canary["source"], maximum),
                "reference": canary["reference"],
                "canary": canary["canary"],
            }
        )
    return tasks


def run_experiment(config_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    random.seed(config["seed"])
    validation = validate_manifest(config["dataset"]["manifest"])
    examples = load_examples(config["dataset"]["fixture"], int(config["dataset"]["limit"]))
    tasks = _tasks(config, examples)
    records: list[dict[str, Any]] = []
    model_meta = []

    with tempfile.TemporaryDirectory(prefix="privateeval-") as temporary:
        temp_root = Path(temporary)
        for index, model_config in enumerate(config["models"]):
            worker_input = temp_root / f"input-{index}.json"
            worker_output = temp_root / f"output-{index}.json"
            worker_input.write_text(
                json.dumps(
                    {
                        "model_config": model_config,
                        "tasks": tasks,
                        "efficiency": config["efficiency"],
                        "seed": config["seed"],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "privateeval.model_worker",
                    "--input",
                    str(worker_input),
                    "--output",
                    str(worker_output),
                ],
                cwd=Path.cwd(),
                text=True,
                capture_output=True,
                check=False,
            )
            if completed.returncode != 0:
                raise RuntimeError(
                    f"Isolated worker failed for {model_config['id']}:\n{completed.stderr}"
                )
            result = json.loads(worker_output.read_text(encoding="utf-8"))
            model_meta.append(result["model"])
            records.extend(result["records"])

    semantic_scorer = make_semantic_scorer(config["metrics"])
    semantic_scores = semantic_scorer.score_pairs(
        (record["output"], record["reference"]) for record in records
    )
    for record, score in zip(records, semantic_scores):
        record["metrics"]["semantic_similarity"] = round(score, 6)

    samples = int(config["metrics"]["bootstrap_samples"])
    confidence = float(config["metrics"]["confidence_level"])
    aggregates = []
    model_by_id = {item["id"]: item for item in model_meta}
    for model in model_meta:
        clean = [record for record in records if record["model_id"] == model["id"] and record["slice"] == "clean"]
        quality = {}
        for metric in ("semantic_similarity", "rouge_1", "rouge_2", "rouge_l", "source_support"):
            quality[metric] = bootstrap_mean_ci(
                [record["metrics"][metric] for record in clean],
                samples,
                confidence,
                config["seed"] + len(quality),
            )
        latencies = [record["telemetry"]["latency_ms"] for record in clean]
        peaks = [record["telemetry"]["peak_rss_mb"] for record in clean if record["telemetry"]["peak_rss_mb"] is not None]
        throughput = [record["telemetry"]["output_tokens_per_second"] for record in clean]
        aggregates.append(
            {
                "model_id": model["id"],
                "label": model["label"],
                "provenance": model["provenance"],
                "quality": quality,
                "efficiency": {
                    "median_latency_ms": round(statistics.median(latencies), 3),
                    "p95_latency_ms": p95(latencies),
                    "peak_rss_mb": round(max(peaks), 3) if peaks else None,
                    "model_size_mb": model["model_size_mb"],
                    "median_output_tokens_per_second": round(statistics.median(throughput), 3),
                    "load_time_ms": model["load_time_ms"],
                    "warmup_runs": int(config["efficiency"]["warmup_runs"]),
                    "measurement_repetitions": int(config["efficiency"]["measurement_repetitions"]),
                },
            }
        )

    robustness_rows = []
    for model in model_meta:
        clean_map = {
            record["example_id"]: record["metrics"]["semantic_similarity"]
            for record in records
            if record["model_id"] == model["id"] and record["slice"] == "clean"
        }
        for perturbation in config["robustness"]["perturbations"]:
            perturbed = [
                record for record in records
                if record["model_id"] == model["id"] and record["perturbation"] == perturbation
            ]
            deltas = [record["metrics"]["semantic_similarity"] - clean_map[record["example_id"]] for record in perturbed]
            robustness_rows.append(
                {
                    "model_id": model["id"],
                    "model_label": model["label"],
                    "perturbation": perturbation,
                    "delta": round(statistics.fmean(deltas), 6) if deltas else 0.0,
                    "n": len(deltas),
                }
            )

    privacy_rows = []
    for model in model_meta:
        privacy = [record for record in records if record["model_id"] == model["id"] and record["slice"] == "privacy"]
        privacy_rows.append(
            {
                "model_id": model["id"],
                "model_label": model["label"],
                "exact_copy_rate": sum(bool(record["privacy"]["exact_copy"]) for record in privacy) / max(1, len(privacy)),
                "normalized_copy_rate": sum(bool(record["privacy"]["normalized_copy"]) for record in privacy) / max(1, len(privacy)),
                "n": len(privacy),
            }
        )

    clean_by_model = {
        model["id"]: sorted(
            [record for record in records if record["model_id"] == model["id"] and record["slice"] == "clean"],
            key=lambda record: record["example_id"],
        )
        for model in model_meta
    }
    comparison = None
    preferred_pair = ("flan-t5-small-int8", "flan-t5-small-fp32")
    if all(model_id in clean_by_model for model_id in preferred_pair):
        left_id, right_id = preferred_pair
    elif len(model_meta) >= 2:
        left_id, right_id = model_meta[1]["id"], model_meta[0]["id"]
    else:
        left_id = right_id = ""
    if left_id and right_id:
        comparison = paired_bootstrap_difference(
            [record["metrics"]["semantic_similarity"] for record in clean_by_model[left_id]],
            [record["metrics"]["semantic_similarity"] for record in clean_by_model[right_id]],
            samples,
            confidence,
            config["seed"] + 101,
        )
        comparison.update({"left_model_id": left_id, "right_model_id": right_id})

    slices = []
    for model in model_meta:
        clean = clean_by_model[model["id"]]
        for dimension in ("topic", "length"):
            groups: dict[str, list[float]] = defaultdict(list)
            for record in clean:
                if dimension == "topic":
                    value = record["topic"]
                else:
                    word_count = len(record["source"].split())
                    value = "short" if word_count < 120 else "medium" if word_count < 160 else "long"
                groups[value].append(record["metrics"]["semantic_similarity"])
            for value, scores in sorted(groups.items()):
                slices.append(
                    {
                        "model_id": model["id"],
                        "dimension": dimension,
                        "value": value,
                        "mean": round(statistics.fmean(scores), 6),
                        "n": len(scores),
                    }
                )

    official_human = analyze_human_review(config, records)
    has_simulation = any(model.get("provenance") == "simulated" for model in model_meta)
    run_id = config["experiment_id"]
    bundle = {
        "schema_version": "1.0",
        "run": {
            "id": run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "claim_status": "simulated_smoke" if has_simulation else "provisional_measured_unverified",
            "independent_verification": "pending",
            "human_review": official_human["status"],
            "seed": config["seed"],
        },
        "protocol": {
            "registration": "docs/experiment-registration.md",
            "dataset": validation["dataset"],
            "input_word_limit": config["dataset"]["max_input_words"],
            "target_output_words": config["dataset"]["target_output_words"],
            "primary_metric": config["metrics"]["primary"],
            "semantic_metric": semantic_scorer.name,
            "bootstrap_samples": samples,
            "confidence_level": confidence,
            "paired": True,
        },
        "environment": _hardware(),
        "models": model_meta,
        "aggregates": {"models": aggregates, "clean_examples": len(examples)},
        "analysis": {
            "primary_comparison": comparison,
            "robustness": robustness_rows,
            "privacy": privacy_rows,
            "slices": slices,
            "human_review": official_human,
        },
        "failures": sorted(
            [record for record in records if record["slice"] == "clean"],
            key=lambda record: (record["metrics"]["source_support"], record["metrics"]["semantic_similarity"]),
        )[:5],
        "records": records,
        "validation": validation,
        "config": config,
        "limitations": [
            "The frozen BillSum fixture is small and legislation-specific; confidence intervals reflect only this sample.",
            "Inputs are deliberately bounded and may omit material later sections of long bills.",
            "MiniLM cosine and the lexical source-support score are proxies, not factuality or entailment guarantees.",
            "Process RSS contains runtime allocations and is not directly comparable across different hardware runs.",
            "Synthetic PII copying behavior is not a privacy or security guarantee.",
            "The neural comparison uses one open model family in two configurations, limiting architectural generalization.",
            "Human preference and independent reproduction remain pending until separately completed.",
        ],
    }
    write_bundle(bundle, output_dir)
    return bundle
