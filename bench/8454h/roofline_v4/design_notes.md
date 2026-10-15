# V4 design notes: bounded INT8 signed-digit GEMM candidate

**Prepared only; do not build/run before V3 is complete and frozen and the real-address-span diagnostic justifies proceeding.** This is an algorithm hypothesis, not a correctness or performance result.

## Candidate encoding

For each input matrix independently, find `absmax` over the agreed quantization group and choose a shared exponent `e = frexp(absmax).exponent`. Zero groups need a separate zero path. Form the integer target

`y = RNE(x * 2^(55-e))`, with a proved guard that `|y| < 2^55` for all finite values admitted by the input contract. Decompose by balanced radix 128, eight signed digits:

`d_i = ((y_i + 64) mod 128) - 64`, `y_(i+1) = (y_i-d_i)/128`, for `i=0..7`.

At each step, `d_i` is in `[-64,63]`. If a quotient remains after seven divisions, the eighth digit may also be `+64`; for valid input `|y|<2^55`, the residual after seven divisions has magnitude strictly less than 128, so the final digit lies in `[-64,64]` and the residual becomes zero. Thus every digit is representable as signed INT8 and `|d_i|≤64`. The exact integer reconstructs as `y = sum_i d_i 128^i`, subject to the initial representability and rounding conditions. Implement Euclidean modulo for negative values; language remainder behavior must not change the digit rule.

For `A ≈ 2^(eA-55) Σ_i 128^i A_i` and similarly B, products are grouped by diagonal `q=i+j`, retaining only `i+j<8` (36 of 64 products). The scale for diagonal q is `2^(eA+eB-110) * 128^q`. Compute each diagonal's full-K products into a fresh INT32 AMX accumulator, then export and add that diagonal into a sufficiently wide reconstruction representation. Never combine distinct diagonals in a shared INT32 accumulator: their binary weights differ.

At K≤32768, one digit product's conservative absolute bound is `K*64*64 = 2^27`. At most eight products occur in one diagonal, giving `2^30`, strictly below signed INT32 max. This proof depends on each product being accumulated separately within a zeroed fresh tile and on K actually being bounded as stated. AMX INT8 tiles have at most K=64 per tile multiply; larger K must be looped in chunks, and full-K denotes a software accumulation of chunks into that diagonal's same bounded accumulator. Tail bytes are zero-filled. For the production shape, re-derive the bound from the actual K and tile schedule before use.

## Wide result assembly: conditional signed-128 proof

For one encoded operand, the weighted absolute digit sum satisfies

`E = Σ_i |d_i|·2^(7i) ≤ 64·(2^56−1)/127 < (128/127)·2^55`.

Therefore, for one output dot product with K≤32768,

`Σ_k E_A E_B < 32768·(128/127)^2·2^110 = (128/127)^2·2^125 < 2^126`.

This bounds the sum of absolute values of **all** weighted digit-pair terms in the dot product. Any sequential signed `__int128` partial sum, in any order, is bounded by the same absolute sum, so each partial sum remains within signed 128-bit range with more than one bit of headroom. The largest digit-pair weight is `2^(7·7+7·7)=2^98`; with the per-pair dot-product bound `K·64²≤2^27`, its weighted magnitude is at most `2^125`, consistent with the aggregate proof. This proof requires eight digits with `|d|≤64`, finite inputs successfully represented by the stated quantizer, exact digit extraction, no extra scale factors folded into the integer sum, and K≤32768. Re-derive it if any condition changes. Unsupported K or input domains must use an explicit fallback or report unsupported input; do not wrap or silently narrow.

Form the integer sum in scalar signed `__int128`, then convert once to binary64 with a correctly rounded conversion and scale by an exact power of two. Before using a compiler helper such as `__floattidf`, inspect generated behavior and rounding under the actual compiler and flags; this note does not certify a particular compiler implementation. Avoid early per-diagonal floating conversions or hand-built double assembly unless a separate error analysis shows they preserve the accuracy gate.

For the stated lattice, `eA,eB` from `frexp` are integers. The unscaled product lattice is `2^(eA+eB-110)`. For normal finite binary32 inputs, `e≥−125`, so the least lattice exponent is at least `−360`, above the binary64 subnormal threshold `−1022`. Also `e≤128`, giving a conservative exact-product magnitude below `2^271`, far below binary64 overflow. Thus power-of-two scaling alone does not underflow into binary64 subnormals or overflow, provided conversion to binary64 is correctly rounded and the normal-binary32 input domain is enforced. Binary32 subnormals need a separate proof/handling policy; NaN/Inf must be rejected or explicitly handled. These range facts do not prove the quantization and dropped-diagonal error meets the target.

## Accuracy/coverage gate

The initial label is **p21 accuracy target**. It must not be described as V3 p21 matching until it passes a direct, preregistered comparator against the frozen V3 path with identical inputs and output metric. Before timing, validate at minimum:

- float128 reference sampling covering exponent boundaries and values near each RNE transition;
- the V3 matching inputs and its exact output acceptance metric;
- Gaussian, scaled, cancellation-heavy, sparse, near-zero, and adversarial exponent mixtures;
- positive/negative values, signed-zero/zero groups, finite extremes, subnormals if admitted, NaN/Inf rejection or defined handling;
- K boundaries around 64 and the declared maximum, plus non-multiple tails;
- reconstruction overflow, underflow, and cancellation behavior.

Record per-case max absolute, relative where meaningful, and ULP/error metric agreed with V3. Aggregate averages cannot waive a bad case. The algorithm has shared-exponent quantization and discarded higher diagonals, so its error is input dependent; this experimental candidate offers no universal accuracy guarantee. If the required domain fails, stop or implement an explicit, observable fallback. Do not silently change precision or narrow the supported domain after seeing results.

## Upper-level review note and sequence

The one-time upper-level review recommendation is to proceed in this order: (1) diagnose operand supply using actual production packed address spans and the matched no-reconstruction / with-reconstruction / whole-API stages; (2) only if that evidence supports a compute-path experiment, prototype high-precision INT8 with the accuracy and range stop conditions above; (3) after V3 is frozen and the first two stages justify further work, inspect and remove any partial intermediate-buffer traffic that still exists in the then-current path. This does not assert that such a partial intermediate remains: verify it before acting. Existing batch2 reconstruction savings were already measured/accounted for in V3 and must not be counted again as new V4 benefit.

## Other design constraints

- Query and validate hardware AMX_INT8 support and OS-enabled tile state before dispatch. The SDM instruction feature flags alone are not a complete OS permission check. On Linux, use the documented XSTATE/permission flow in the repository runtime; keep scalar-safe dispatch outside any AMX-targeted function.
- Set up tile configuration outside the K loop and amortize it; manual Table 20-2 reports high `LDTILECFG` latency and recommends one setup/release pair per AMX layer.
- Use 64-byte base alignment as the manual's performance recommendation, but do not infer a 64-byte instruction precondition from that recommendation. Respect tile row-byte/stride and address-range requirements from the SDM; test odd tails and valid allocation extents.
- The manual gives design examples for B re-layout, minimizing tile loads, pipelining, cache blocking, software prefetch and multicore partitioning. These are hypotheses to measure. It does not establish a universal panel size or guarantee that a B panel fits L2 on this host. Calculate candidate footprints, then measure; do not label instruction-logical bytes as DRAM traffic.
- For first comparison, use the same real production address spans, with no-reconstruction, with-reconstruction, and whole-API timings. Include conversion and digit generation in whole API time.

## Deferred FP32 alternative

A possible later branch is four signed balanced radix-128 digits for FP32 integers formed as `RNE(x*2^(27-e))`, which suggests ten `i+j<4` products. The proposed seven-bin/fused-diagonal count and precision are unvalidated. Do not implement until the V3 freeze, the first diagnostic, and a separately written error/overflow proof.
