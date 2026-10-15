# Direct pack candidate

The candidate generates component slices directly into the packed panels, bypassing a full intermediate slice buffer for eligible aligned dimensions; other cases use the existing fallback. At N=8192 FP64, five-repetition medians reduced whole-call wall by 28.4–34.7% across p6/p10/p15/p21 versus the mean of bracketed default controls. Minor faults also fell substantially for these configurations. This is promising evidence, not a production adoption decision.

Patch: [direct_pack.patch](direct_pack.patch). CSVs: `../direct_pack/`. Per-config phases, raw fault counts, hashes, and reconstructed commands: [comparison.json](comparison.json), [experiment_metadata.json](experiment_metadata.json). CTest passed; no separate equivalence-gate report was archived in this snapshot.
