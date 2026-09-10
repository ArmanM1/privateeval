# PrivateEval

PrivateEval is a reproducible evaluation lab for small summarization models on local or CPU-constrained hardware. It compares quality, latency, memory, robustness, synthetic privacy behavior, and—once real ratings are imported—blinded human preference in one traceable result bundle.

> **Evidence status:** under construction / not independently verified. Do not cite this repository as a completed result or resume accomplishment until the release checklist passes.

## One-command paths

Deterministic pipeline smoke test (no model download):

```powershell
python -m privateeval run --config configs/smoke.json --output artifacts/runs/smoke
```

Measured portable CPU run after installing `requirements-lock.txt`:

```powershell
python -m privateeval run --config configs/demo.json --output artifacts/runs/cpu-v1
```

The full run uses BillSum (CC0-1.0), a Lead-3 extractive baseline, and pinned FLAN-T5-small FP32 and dynamic-INT8 configurations. It registers MiniLM cosine as the primary metric and uses paired bootstrap confidence intervals.

## Repository map

- `privateeval/`: adapters, data validation, metrics, telemetry, statistics, runner, reports
- `configs/`: frozen smoke and measured experiment configurations
- `data/`: checksummed public fixtures, synthetic canaries, review protocol
- `docs/`: preregistration, architecture, demo, reproduction, and independent-verification guides
- `app/`: interactive traceable result browser
- `reports/`: model/configuration card
- `tests_py/` and `tests/`: pipeline and interface tests

## Evidence boundaries

Numbers from `configs/smoke.json` are explicitly simulated contract checks. Numbers from `configs/demo.json` are local measurements on the recorded machine, not Apple Silicon or production estimates. Synthetic canary behavior is not a privacy guarantee. Human preference and independent reproduction remain pending until separate people complete those steps.

The [versioned demo walkthrough](artifacts/demo/privateeval-demo.webm) follows the PRD path from paired outputs through failure slices, privacy canaries, blinded review, model cards, and the exact reproduction command. Its dimensions, duration, checksum, and console status are recorded in `artifacts/demo/privateeval-demo.json`.

## Release gate

Generate the fixed 12-card review packet and run the complete M5 audit:

```powershell
python -m privateeval review-packet --bundle public/results/result_bundle.json --output artifacts/human-review
python -m privateeval import-ratings --source privateeval-blinded-ratings.csv
python -m privateeval release-audit --bundle public/results/result_bundle.json --strict
```

The importer refuses partial packets, duplicate cards, mismatched examples, invalid choices or reason tags, changed blind IDs, and missing reviewer IDs before replacing the canonical ratings file. The strict audit intentionally exits nonzero until blinded ratings with preference confidence intervals, independent reproduction, and a verified public repository are all present. Passing unit tests or deploying the demo cannot override that evidence gate.
