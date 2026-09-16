# Architecture

```text
BillSum fixture + checksums ─┬─> fixed test examples
                            ├─> deterministic perturbations
                            └─> synthetic PII canaries

adapter contract ─> generation + warm telemetry ─> raw records
                                                ├─> quality / support
                                                ├─> privacy / robustness
                                                └─> bootstrap + slices

versioned result bundle ─> report generator ─> interactive results lab
```

The Python package owns data validation, adapters, telemetry, metrics, statistics, and report generation. The web application is a read-only browser over the generated JSON bundle, except for a device-local blinded-review workflow that exports ratings for later import. Every displayed measurement retains an example ID, model ID, run ID, and artifact status.

