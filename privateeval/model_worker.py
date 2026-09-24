from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

from privateeval.eval.efficiency import measure, summarize_measurements
from privateeval.eval.grounding import source_support
from privateeval.eval.privacy import canary_copy
from privateeval.eval.quality import lexical_quality
from privateeval.models import ExtractiveAdapter, MockOpenConfigAdapter, TransformersAdapter


def make_adapter(config: dict[str, Any]):
    kind = config["kind"]
    if kind == "extractive":
        return ExtractiveAdapter(config)
    if kind == "mock-open-config":
        return MockOpenConfigAdapter(config)
    if kind == "transformers":
        return TransformersAdapter(config)
    raise ValueError(f"Unsupported adapter kind: {kind}")


def run_model(
    model_config: dict[str, Any],
    tasks: list[dict[str, Any]],
    efficiency: dict[str, Any],
    seed: int,
) -> dict[str, Any]:
    random.seed(seed)
    adapter = make_adapter(model_config)
    adapter.load()
    warmups = int(efficiency["warmup_runs"])
    if warmups and tasks:
        for _ in range(warmups):
            adapter.summarize(tasks[0]["source"])
    records = []
    for task in tasks:
        repetitions = int(efficiency["measurement_repetitions"])
        measured = [
            measure(
                lambda current=task: adapter.summarize(current["source"]),
                int(efficiency["memory_poll_ms"]),
            )
            for _ in range(repetitions)
        ]
        telemetry = summarize_measurements(measured)
        generation = telemetry.pop("generation")
        if any(item.generation.text != generation.text for item in measured):
            raise RuntimeError(f"Non-deterministic output from {adapter.id} on {task['record_id']}")
        records.append(
            {
                **task,
                "model_id": adapter.id,
                "model_label": adapter.label,
                "output": generation.text,
                "confidence": generation.confidence,
                "generation_metadata": generation.metadata,
                "input_tokens": generation.input_tokens,
                "output_tokens": generation.output_tokens,
                "telemetry": telemetry,
                "metrics": {
                    **lexical_quality(generation.text, task["reference"]),
                    **source_support(generation.text, task["source"]),
                },
                "privacy": canary_copy(generation.text, task["canary"]) if task["canary"] else None,
                "provenance": "simulated" if model_config.get("simulated") else "measured_local",
            }
        )
    model_meta = {
        "id": adapter.id,
        "label": adapter.label,
        "kind": model_config["kind"],
        "revision": model_config.get("revision"),
        "quantization": model_config.get("quantization", "none"),
        "load_time_ms": round(adapter.load_time_ms, 3),
        "model_size_mb": adapter.model_size_mb(),
        "provenance": "simulated" if model_config.get("simulated") else "measured_local",
        "telemetry_isolation": "fresh_process",
    }
    adapter.close()
    return {"model": model_meta, "records": records}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = run_model(
        payload["model_config"], payload["tasks"], payload["efficiency"], payload["seed"]
    )
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()

