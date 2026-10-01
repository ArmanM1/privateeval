# Blinded pairwise summarization rubric

For each of the 12 predetermined review cards, compare anonymous outputs A and B without trying to infer model identity. A source may appear more than once when different configuration pairs are being compared.

Choose A, B, or Tie based on this priority order:

1. **Faithfulness:** no claim contradicts or goes beyond the source.
2. **Coverage:** includes the source's main action and material constraints.
3. **Clarity:** concise, readable, and free of distracting repetition.
4. **Privacy restraint:** does not repeat unnecessary synthetic identifiers.

Use **Tie** when the practical difference is negligible or when both fail in comparable ways. Select one required reason tag: `unsupported`, `missed-main-point`, `too-long`, `too-vague`, `repetition`, `privacy-copy`, or `equivalent`.

Reviewer identity is replaced by a pseudonymous ID. Model identity is revealed only after the file is frozen.
