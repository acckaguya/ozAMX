# Isolated INT8-36 FP64 prototype

This directory contains a source-only experimental backend for the V4 INT8-36 idea. It is not part of the public ozAMX API or production dispatch. **Do not configure, compile, link, or execute it until the V3 paper campaign is complete, the V3 release is frozen, and root authorizes the first prototype build.** No CPU benchmark or accuracy result exists yet.

The implementation targets FP64-shaped inputs encoded as eight signed balanced-radix-128 digits per operand. Each matrix gets one exponent from its finite nonzero maximum. For each value it rounds `x * 2^(55-e)` to nearest-even, extracts low-order digits using Euclidean modulo, then stores them high-digit first. It computes pairs with high-first indices `i+j<8`; diagonal `q=i+j` is weighted by `2^(7*(14-q))` after all K contributions are accumulated. This is 36 INT8 products, not the V3 p21 product budget.

AMX_INT8 uses signed `TDPBSSD`. Within each diagonal, products remain in an INT32 output plane through every BK block. The bound `8*K*64^2 <= 2^30` is required for `K<=32768`; differently weighted diagonals are never combined in INT32. The final eight weighted plane sums use signed `__int128`, multiply by positive powers of two, then use an explicit integer-to-binary64 nearest-even conversion before exact `scalbn` scaling. No FP32 or long-double intermediate is used.

The initial domain is deliberately narrow: `M` and `N` must be multiples of 32; positive `K` may have a tail and is zero padded to K64; `K<=32768`; each input is either zero or a finite value in the normal BF16 magnitude range `[2^-126, (2-2^-7)*2^127]`. Binary64 subnormals, values outside that range, NaN and infinity are rejected. K=0 returns a zero matrix. Leading dimensions are measured in double elements and may exceed the logical width. C row padding is preserved.

Both full inputs are scanned and completely packed before caller C is modified. The full output is also staged, so C may overlap A or B and remains unchanged on any C++ exception. Invalid shape/domain throws `std::invalid_argument`; size/address arithmetic overflow throws `std::overflow_error`; missing AMX_INT8 or V3-runtime tile permission throws `std::runtime_error`; scratch allocation can throw `std::bad_alloc`. As with other raw-pointer APIs, callers must provide valid readable/writable address spans. The prototype reuses the frozen V3 permission entry point, which also retains V3's existing AMX-BF16/AVX-512 host checks.

## Layout and workspace

A panels are ordered `[M32][K64][digit8][32x64 bytes]`; each digit panel's top and bottom 16-row tiles start at byte offsets 0 and 1024. B panels use `[N32][K64][digit8][64x32 bytes]`, with VNNI4 K groups and left/right N16 halves at offsets 0 and 1024. SIMD code validates/quantizes eight doubles and extracts all eight digits together; initial panel scatter is scalar. Tail K bytes are zero because packed buffers start cleared.

The output macroblock defaults to 128x128 and BK defaults to 256. Compile-time choices are BM/BN in `{64,128,256}` and BK in `{64,128,256,512}`. Each worker keeps eight INT32 planes; every row has an extra 64-byte pad and each plane has another 64-byte gap. At BM=BN=128, the planes occupy about 0.56 MiB; the active A/B panels add about 0.5 MiB at BK=256, keeping this working set near 1 MiB before other scratch. The copied V3-style per-thread workspace pool defaults to a 2 GiB retention cap controlled by `OZAMX_WORKSPACE_CACHE_BYTES`. API timings include scan, packing, computation, reconstruction, allocations, and workspace-pool release.

The GAS kernel takes A/B pointer arrays, an INT32 C plane tile, actual C row stride, K64 panel-step byte stride, K64 step count, and pair count. It loads the four existing C quadrants, loops K64 outer and diagonal products inner, issues four `TDPBSSD`s per product, and stores the updated C tile. Tile configuration is loaded once per worker region and released after that region. The dispatcher checks the AMX-TILE and AMX-INT8 CPUID bits and then asks the frozen V3 runtime for Linux XTILEDATA permission; BF16 support is never used as a proxy for INT8 support.

## Build integration after authorization

CMake links the frozen V3 static library for its permission/runtime entry point. By default it uses the V3 archive library at `bench/8454h/versions/v3_release/artifacts/libozamx_v3.a`. The standalone target can be configured later with:

```sh
cmake -S bench/8454h/roofline_v4/int8_proto \
  -B /tmp/ozamx-int8-36-build -DCMAKE_BUILD_TYPE=Release \
  -DOZAMX_V3_ROOT="$PWD" \
  -DOZAMX_V3_LIBRARY="$PWD/bench/8454h/versions/v3_release/artifacts/libozamx_v3.a"
cmake --build /tmp/ozamx-int8-36-build -j8
```

The prepared build exposes `ozamx_int8_36`, `int8_quality_gate`, and `int8_benchmark_driver`. These targets have not been configured or built. The macroblock and TILELOADDT1 settings are standalone CMake cache options. Compilation, gate execution, and CPU timing remain forbidden until the frozen-completion marker exists and root authorizes the post-V3 prototype phase.

## Prepared post-freeze gate and comparison

`quality_gate.cpp` is the separate full-binary128 and semantic gate. It exercises the INT8-36 prototype against the independent V3 p21 path and rejects failing accuracy, padding, transaction, or alias checks. A successful gate is a prerequisite in `run_after_freeze.sh`; the script holds `/tmp/ozamx-perf.lock` across configure/build, gate, and the complete timing sequence. It requires `bench/8454h/v3_paper_alignment/FROZEN_COMPLETE` to match the schema emitted by `create_v3_paper_release.py`: `complete: true`, `archive: "bench/8454h/versions/v3_paper_release"`, `manifest_sha256`, `configurations: 66`, and the frozen library SHA-256. The runner resolves and restricts the archive path, checks the supplemental archive manifest hash against the marker, checks the archived V3 library hash, and validates every entry in the supplemental `MANIFEST.sha256` before building. Result files go into a unique timestamped directory so failed gate output is retained across retries.

The standalone driver accepts `--n`, `--threads`, `--reps`, `--seed`, and `--output`. It creates one shared uniform `[-1,1]` input pair, warms each implementation once, alternates INT8-36 and frozen V3 p21 call order, and records each raw sample to an atomic JSON checkpoint after every repetition. API wall time surrounds each complete ozAMX profiled call; the phase fields and profile total are diagnostic only. oneMKL timings surround `cblas_dgemm` only. After all timed samples, it computes full-matrix `eF` and elementwise `e_scaled = max_ij(|C_ij - Cref_ij| / sum_k(|A_ik| |B_kj|))` against oneMKL using an untimed `DGEMM(abs(A),abs(B))` denominator. The record states that the two ozAMX methods use 36 and 21 integer products respectively, so this is a matched-input comparison rather than equal-work arithmetic.

The runner stores source/archive/executable and oneMKL runtime SHA-256 identities plus `ldd` output, then runs the gate and (only after a pass) N=1024, 4096, and 8192 with 64 threads and five timed repetitions. Standard output and error logs are retained per gate and matrix size. No benchmark, build, or numerical validation has yet been run for this prototype.

## Correctness obligations before any performance claim

This encoding drops 28 of the 64 digit pairs and has input-dependent quantization error. The magnitude proof prevents INT32/INT128 overflow and final binary64 range failure under the stated assumptions; it is not a precision proof. Before any timing, a separately reviewed harness must compare against the frozen V3 p21 path on identical data using the agreed output metric. Required cases include float128 reference samples near RNE transitions and exponent boundaries; uniform, Gaussian, scaled, sparse and cancellation-heavy inputs; zero groups; positive/negative values; finite extremes; K boundaries around 64 and 32768; padded K tails; aliasing and row strides; and rejection/handling checks for subnormals, NaN and infinity. Report max absolute, relative where meaningful, and ULP errors per case. Passing averages cannot waive a failing case.
