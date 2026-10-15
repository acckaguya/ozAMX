# Fused max candidate

This candidate layers the next global maximum reduction into the projection loop on top of the packed-residual layout. Root reports CTest and frozen-v1 bitwise validation over 100 cases and 2,322,780 C slots.

At N=8192 FP64, five-repetition candidate wall medians were 28.8–39.1% below the mean of bracketed default control medians across p6/p10/p15/p21. Differences from packed-residual are small and noisy; four alternating packed/max runs with seven repetitions at p6/p21 are queued. Do not select a winner based on the current close comparison. Patch: [fused_max.patch](fused_max.patch); CSV and provenance are captured in the experiment metadata and comparison JSON.
