# PrivateEval experiment registration

Status: **locked before the measured CPU run**  
Registration ID: `privateeval-billsum-cpu-v1`  
Seed: `20260807`

## Decision question

For an interactive, privacy-sensitive summarization product constrained to a CPU, does dynamic INT8 quantization of FLAN-T5 small materially reduce latency or memory while retaining useful semantic quality relative to its FP32 configuration and a transparent extractive baseline?

## Primary hypothesis and metric

**Hypothesis.** Dynamic INT8 will reduce resident memory and median warm latency relative to FP32. Its paired mean semantic-similarity loss will remain below 0.05 on the frozen BillSum fixture, but the loss may be larger on long-input and perturbed slices.

**Primary metric.** Cosine similarity between the generated and reference summaries using pinned `sentence-transformers/all-MiniLM-L6-v2` embeddings. This metric is complementary evidence, not a human judgment.

Secondary metrics are ROUGE-1/2/L, source-support proxy, median and p95 latency, peak process RSS, approximate model bytes, throughput, controlled-perturbation deltas, exact synthetic-canary copy rate, and blinded pairwise preference once human ratings exist.

## Fixed protocol

- Public data: `FiscalNote/billsum`, CC0-1.0, test rows identified in `data/fixtures/billsum_test.json`.
- Input bound: first 360 whitespace-delimited words. Output target: 45–90 words, maximum 72 generated tokens for neural configurations.
- Adapters: Lead-3 extractive; `google/flan-t5-small` FP32; the same pinned revision with PyTorch dynamic INT8 linear-layer quantization.
- Runtime: portable PyTorch CPU path. This registration makes no Apple Silicon or on-device production claim.
- Paired design: every configuration receives the same source examples and perturbations.
- Efficiency: each configuration runs in a fresh process, with one warm-up followed by two measured repetitions. Model load time is reported separately from warm generation latency.
- Robustness: deterministic typos, formatting noise, and length-shift fixtures for the first two frozen test examples.
- Privacy: synthetic, unmistakably fake canaries only. Exact and normalized copying are measured; this is not a security guarantee.
- Statistics: 2,000 paired bootstrap resamples, percentile 95% confidence intervals, paired standardized mean difference, and common-language effect.
- Human review: 12 examples, randomized A/B identity, written rubric, ties allowed. No human result is displayed as complete until ratings are imported.

## Stopping rule

Run the frozen test fixture once after a smoke run validates instrumentation. Do not tune prompts, generation parameters, or perturbations on the resulting test scores. Stop after the registered run, report failures, and leave external human review and independent reproduction explicitly pending if they have not occurred.

## Threats known in advance

The fixture is small, BillSum is domain-specific, source inputs are truncated, MiniLM is not a factuality judge, RSS includes shared runtime allocations, dynamic quantization support is runtime-dependent, and the same model family is compared across configurations. Possible pretraining exposure cannot be ruled out.
