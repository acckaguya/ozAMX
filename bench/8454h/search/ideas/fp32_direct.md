# Direct FP32 panel generation candidate

The isolated candidate directly emits three FP32 components to packed panels and uses masked interleaving for SIMD B loads. Its N=8192 p6 CSV has a 202.43 ms median whole-call wall, 37.8% below its bracketing default controls. This is a candidate measurement only; it does not establish a general FP32 speedup or production suitability.

Patch: [fp32_direct.patch](fp32_direct.patch). Raw before/after/candidate CSVs are in `../fp32_direct/`; build/source/patch hashes and gate scope are recorded in `experiment_metadata.json` and `comparison.json`.
