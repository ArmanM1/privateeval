# PrivateEval configuration card

## Intended use

PrivateEval compares bounded single-document summarization configurations on portable CPU hardware. It is intended for research and engineering triage, not automated production selection.

## Evaluated configurations

- **Lead-3 extractive:** deterministic frequency-weighted sentence selection; transparent non-neural baseline.
- **FLAN-T5 small FP32:** `google/flan-t5-small`, pinned revision, deterministic greedy decoding.
- **FLAN-T5 small dynamic INT8:** the same checkpoint with PyTorch dynamic quantization applied to linear layers.

The two neural entries are configurations of one open model family. The card does not claim broader cross-family generalization.

## Data

Eight abridged examples are frozen from the CC0 BillSum U.S. test split. No private user content is collected. Privacy behavior uses three clearly fake canaries under the reserved `.invalid` domain or synthetic identifier labels.

## Metrics

The registered primary metric is MiniLM cosine similarity. ROUGE and a lexical source-support proxy complement it. Efficiency includes warmed repeated wall time, fresh-process peak RSS, model bytes, and output-token throughput. Robustness uses deterministic typos, formatting noise, and length shifts. Synthetic-canary copy rates measure observed behavior only.

## Limitations

- Small, domain-specific sample and bounded/truncated sources.
- Semantic and support metrics are proxies and can reward fluent but unsupported text.
- CPU timings and RSS are hardware- and process-specific.
- Dynamic quantization support and performance vary by runtime.
- No real PII is evaluated and no security guarantee is made.
- Human preference and independent verification are pending until their artifacts exist.

## Claim policy

The project remains `provisional_measured_unverified` after a measured run. Resume or portfolio claims must wait until the human review is complete, an independent reviewer reproduces the core run, and repository/report/demo numbers agree.
