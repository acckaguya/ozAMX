# Roofline V4 compile-time search tree

This isolated tree is a selective copy of the frozen-V3 diagnostic implementation. It contains the mode-capable GEMM core, matching headers and AMX assembly, the existing benchmark and validation drivers, and an extended copied binary gate. It excludes all `build/`, prior search `results/`, vendor files and the INT8 prototype. It does not modify `diagnostic_src/`, the frozen V3 release, or the production core. See `SOURCE_ORIGIN.json` for copy-source and current-file hashes.

No CMake configure, compile, test, binary gate or performance run was performed while preparing this tree. The search runner refuses all execution unless explicitly passed `--execute`, checks the V3 freeze marker and library SHA, and serializes run phases under `/tmp/ozamx-perf.lock`.

## Controls and defaults

The default knobs preserve the already-gated V3 wide-call behavior:

| CMake option | Default | Search values | Meaning |
|---|---:|---|---|
| `OZV4_FP64_BATCH` | 2 | 2, 4, 8, 12, 21 | Number of FP64 float microproducts buffered before ordered FP64 reconstruction. Product order and each output's addition order remain fixed. |
| `OZV4_WIDE_CBM` | 128 | 64, 128, 256 | Wide output rows per worker block. Small-call CBM remains 32. |
| `OZV4_WIDE_CBN` | 0 (automatic) | 0, 128, 256, 512, 1024 | Wide output columns per block. Automatic means 512 for FP32 and FP64 depths 3/4, and 256 for FP64 depths 5/6, matching V3. |
| `OZV4_WIDE_PAD_BYTES` | 64 | 0, 64, 128 | Extra bytes between output rows in each private wide C block. All choices preserve 64-byte row alignment. |
| `OZAMX_TILELOAD_HINT` | 1 | 0, 1 | Selects the already-supported `tileloaddt1` (1) or `tileloadd` (0) assembly spelling. |
| `OZV4_FP32_LATE32` | 1 | 0, 1 | Only affects mode 3. Enables the existing FP32 K>=4096 late scan when 1; mode 0 always retains eager V3 checks. |

BK remains 256. The small path and the six FP64 component-product order are unchanged. The default mode 0/3 binaries must pass all three CTests and the strict full-output/transaction comparison against the immutable V3 static library before timing. Mode 1 remains finite-input diagnostic-only; mode 2 remains `diagnostic_no_reconstruction_non_numeric` and is never used as an accuracy result.

CBN must be a multiple of 16 elements; this also satisfies double's 8-element ZMM alignment. Private C-block storage is 64-byte aligned, and row byte stride is `CBN*sizeof(T)+pad_bytes`, always a multiple of 64. The implementation sizes each compile-time block for the selected maximum CBM/CBN/padding, zeroes the entire active block, and checks/copies only through the active stride.

For one active BK=256 panel step, the packed A+B footprint estimate is
`256*256*2*S + 256*CBN*2*S` bytes, where S=3 for FP32 and S is the FP64 product depth. Add `CBM*(CBN+pad_bytes/sizeof(T))*sizeof(T)` bytes for the private C block and `4*FP64_BATCH*32*32` bytes of FP64 product scratch. These estimates exclude shared packed panels, allocator/cache metadata and other worker state, and do not imply a cache-fit guarantee. With defaults, FP32 at CBN512 is 1.125 MiB of A+B panels plus 264 KiB C block. FP64 depth 4 at CBN512 is 1.5 MiB of panels plus 520 KiB C block; depth 6 at CBN256 is 1.5 MiB of panels plus 264 KiB C block. The batch-2 scratch is 8 KiB. CMake writes the selected knobs, compiler identity and GEMM/kernel/header/driver/MKL-runtime SHA-256 values into each build's `build_identity.json`; each CSV row also has a 37th `build_identity` field.

## Search stages

`tools/search.py --plan` prints the deterministic candidate matrix without compiling or running anything. Stage 1 uses 30 unique FP64-batch / CBM / CBN combinations at N=8192, with tile-load hint 1 and 64-byte padding held at their defaults; one matched mode-3 configuration toggles Late32 off. Every stage-1 candidate is built separately, passes three CTests and the quick strict-bit gate (`17,18,19,20,11,12`) before a three-repetition N=8192 API screen over FP32 and FP64 budgets 6/10/15/21. The short-K wide-shape gate cases 19/20 exercise wide FP32 and high-depth FP64 geometry, while 11/12 exercise wide FP64 alias transactions and 17/18 exercise long-K FP32 late-path transaction semantics. Full gate remains mandatory for finalists.

The screen invocation also records initial V3 and modes 0–3 default controls at N=8192 with seven repetitions. Modes 0 and 3 pass the full binary gate first. A separate layout stage accepts a screened base candidate and tests the six pad/hint combinations (0/64/128 bytes × 0/1 tile-load hint) with the same quick gate then three-repetition screen. Candidate values and all raw measurements remain in the dataset; there is no outlier removal.

For a finalist, `tools/search.py --phase final --candidate-id ID --execute --result-dir DIR` builds gated mode 0 and mode 3 variants and records 18 matched rechecks at seven repetitions: for each N=1024/4096/8192, FP32 mode 0, FP32 mode 3, and FP64 budgets 6/10/15/21. Every candidate case is paired with an immutable-V3 invocation using the same seed, CPU affinity, thread/runtime settings, repetitions and driver. The full 20-case strict binary gate and three CTests are required before any finalist timings. The phase finishes with a V3 control run to bracket drift. It preserves every result and records measured timing scope (full API wall versus oneMKL GEMM-only); diagnostics are explicitly tagged and not compared as numerical candidates.

All executable phases require explicit `--execute`, a fresh non-existing result directory, the frozen marker and the library SHA-256 `73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c`. CPU work remains scheduled by the root agent; during preparation only the non-executing `--plan` path was invoked.

The runner's explicit entry points are:

```sh
python3 bench/8454h/roofline_v4/search_src/tools/search.py --plan
python3 bench/8454h/roofline_v4/search_src/tools/search.py --phase screen --execute --result-dir /tmp/ozamx-v4-screen-RUNID
python3 bench/8454h/roofline_v4/search_src/tools/search.py --phase layout --execute --base-candidate CANDIDATE_ID --screen-dir /tmp/ozamx-v4-screen-RUNID --result-dir /tmp/ozamx-v4-layout-RUNID
python3 bench/8454h/roofline_v4/search_src/tools/search.py --phase final --execute --candidate-id CANDIDATE_ID --screen-dir /tmp/ozamx-v4-screen-RUNID --result-dir /tmp/ozamx-v4-final-RUNID
```
