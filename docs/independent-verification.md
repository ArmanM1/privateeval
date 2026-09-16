# Independent verification protocol

This gate must be completed by a person other than the implementer. It verifies the committed artifact and its claims; it is not satisfied by rerunning commands in the original development checkout.

## Clean-room procedure

1. Clone the public repository into a new directory and check out the exact commit recorded in `data/public_repository.json`.
2. Create a fresh Python environment and install `requirements-lock.txt`.
3. Run the manifest check, test suites, measured experiment, and release audit:

   ```powershell
   python -m privateeval validate
   python -m pytest
   npm ci
   npm test
   python -m privateeval run --config configs/demo.json --output artifacts/runs/independent
   python -m privateeval release-audit --bundle artifacts/runs/independent/result_bundle.json
   ```

4. Compare model revisions, data checksums, record counts, metric definitions, and the direction of every reported comparison with the committed measured report. Efficiency numbers may vary by hardware and should be treated as a fresh machine-specific measurement.
5. Inspect at least one raw trace per configuration and confirm that the web demo does not label pending human or privacy evidence as a validated claim.
6. Populate `data/independent_verification.json` with the reviewer identifier, exact commit, reproduced run ID, UTC completion time, and notes. Set both boolean checks to `true` only after the work is complete.

The strict audit remains red if the repository is not public, the reviewed commit differs, or either inspection outcome is missing.
