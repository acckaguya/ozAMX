# Packed residual candidate

This variant preserves the existing floating-point decomposition order while writing residual elements in the packed-panel layout, reducing an intermediate materialization. The global maximum remains symmetric across components. Root reports CTest and frozen-v1 bitwise validation across 100 cases and 2,322,780 C slots.

At N=8192 FP64, candidate wall medians were 31.1–38.7% below the mean of bracketed default control medians across p6/p10/p15/p21. This is not evidence that the candidate beats fused-max; their differences are small and an alternating check is queued. Patch: [packed_residual.patch](packed_residual.patch). Raw CSVs and hashes are listed in the adjacent experiment JSON files.
