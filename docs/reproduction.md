# Reproduction

## Fast deterministic smoke run

```powershell
python -m privateeval validate
python -m privateeval run --config configs/smoke.json --output artifacts/runs/smoke
python -m pytest
```

This path uses deterministic local adapters and verifies the full result contract without downloading model weights. Its neural-looking configurations are explicitly marked simulated and must never be cited as model results.

## Measured portable CPU run

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-lock.txt
.venv\Scripts\python -m privateeval run --config configs/demo.json --output artifacts/runs/cpu-v1
```

The command validates the manifest and split boundary, loads pinned public model revisions, warms each adapter, records repeated latency/RSS measurements, evaluates every paired example, and writes a traceable bundle plus Markdown report. The first run downloads public weights to the local Hugging Face cache.

## Human review

Generate the frozen packet with `python -m privateeval review-packet --bundle public/results/result_bundle.json --output artifacts/human-review`. Give reviewers `review_packet.json` and the rubric, but keep `review_key.json` separate until ratings are frozen. Alternatively, use the demo's **Blind review** view. Place the completed export at `data/human_review/ratings.csv` and rerun the registered experiment to unblind, validate, and bootstrap pairwise preference intervals. A zero-row template is intentional: until real reviewers complete all 12 cards, the report remains honest about the missing evidence.

## Independent verification

Follow [`docs/independent-verification.md`](independent-verification.md) from a clean checkout. The verifier records their evidence in `data/independent_verification.json`; the public repository identity is recorded separately in `data/public_repository.json`.
