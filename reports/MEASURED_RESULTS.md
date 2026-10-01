# PrivateEval report — privateeval-billsum-cpu-v1

**Artifact status:** `provisional_measured_unverified`
**Created:** 2026-08-08T05:52:27.187369+00:00
**Primary metric:** semantic_similarity

> Results are fresh-process local measurements on the recorded hardware unless marked simulated. They are not production, Apple Silicon, privacy-security, or independent-verification claims.

## Aggregate results

| Configuration | Semantic similarity (95% CI) | ROUGE-L | Support proxy | Median latency | Peak RSS | Model bytes |
|---|---:|---:|---:|---:|---:|---:|
| Lead-3 extractive | 0.724 [0.649, 0.791] | 0.222 | 1.000 | 0.2 ms | 22.3 MB | 0.0 MB |
| FLAN-T5 small · FP32 | 0.607 [0.502, 0.709] | 0.180 | 0.782 | 535.7 ms | 653.8 MB | 419.1 MB |
| FLAN-T5 small · dynamic INT8 | 0.266 [0.151, 0.390] | 0.087 | 0.280 | 640.7 ms | 818.4 MB | 246.0 MB |

## Paired comparison

`flan-t5-small-int8 − flan-t5-small-fp32`: -0.341 (95% CI -0.528 to -0.175); paired dz=-1.29, n=8.

## Robustness

Deltas are relative to each model's clean score on the paired source.

| Configuration | Perturbation | Δ semantic similarity | n |
|---|---|---:|---:|
| Lead-3 extractive | typos | -0.009 | 2 |
| Lead-3 extractive | formatting | 0.001 | 2 |
| Lead-3 extractive | length_shift | 0.000 | 2 |
| FLAN-T5 small · FP32 | typos | 0.032 | 2 |
| FLAN-T5 small · FP32 | formatting | -0.001 | 2 |
| FLAN-T5 small · FP32 | length_shift | -0.413 | 2 |
| FLAN-T5 small · dynamic INT8 | typos | 0.327 | 2 |
| FLAN-T5 small · dynamic INT8 | formatting | -0.128 | 2 |
| FLAN-T5 small · dynamic INT8 | length_shift | -0.025 | 2 |

## Synthetic privacy canaries

| Configuration | Exact copy rate | Normalized copy rate |
|---|---:|---:|
| Lead-3 extractive | 33.3% | 33.3% |
| FLAN-T5 small · FP32 | 100.0% | 100.0% |
| FLAN-T5 small · dynamic INT8 | 0.0% | 0.0% |

## Human preference

Official ratings complete: **0 / 12**; status: `pending`; fixed packet: `4decaef5218b55902b3ee1d5b55a99d1cfd9a4aa5a00ad96c94eda36cf38abe0`.
No human-preference conclusion is made until all predetermined cards are validly rated.

## Limitations and threats to validity

- The frozen BillSum fixture is small and legislation-specific; confidence intervals reflect only this sample.
- Inputs are deliberately bounded and may omit material later sections of long bills.
- MiniLM cosine and the lexical source-support score are proxies, not factuality or entailment guarantees.
- Process RSS contains runtime allocations and is not directly comparable across different hardware runs.
- Synthetic PII copying behavior is not a privacy or security guarantee.
- The neural comparison uses one open model family in two configurations, limiting architectural generalization.
- Human preference and independent reproduction remain pending until separately completed.

## Reproduction

See `docs/reproduction.md` and the exact config embedded in the bundle.
