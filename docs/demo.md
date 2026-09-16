# Demo walkthrough

The versioned walkthrough is [`artifacts/demo/privateeval-demo.webm`](../artifacts/demo/privateeval-demo.webm). It is a 67.52-second, 1280 × 720 recording of the production build using the measured result bundle. Its checksum and browser-decoded metadata are frozen in [`artifacts/demo/privateeval-demo.json`](../artifacts/demo/privateeval-demo.json).

## Storyboard

1. Read the registered hypothesis and measured decision summary.
2. Compare the same source under FP32 and dynamic-INT8 configurations, including quality, grounding, latency, memory, uncertainty proxy, and raw-trace provenance.
3. Inspect typo, formatting, and length-shift robustness slices plus the failure ledger.
4. Inspect synthetic PII canaries and the explicit non-guarantee boundary.
5. Exercise one card of the fixed blinded-review workflow without exporting or treating the working note as an official human rating.
6. Inspect protocol metadata, the registered paired contrast, and the four release-status cards.
7. Open the pinned configuration cards and the exact one-command reproduction panel.

The recording contains no voiceover and makes no claim that the three pending external gates are complete. Browser verification reported zero console errors and zero warnings on the recorded build.
