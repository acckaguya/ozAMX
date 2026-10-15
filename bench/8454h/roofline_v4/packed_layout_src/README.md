# Isolated V4 FP64 packed-layout and slab-rotation study

This source tree is based on the frozen-V3 V4 search implementation. FP64
packing, packed-residual projection, and AMX address traversal now share an
optional per-component slab-slot permutation within each eight-slab 256×256
panel: `physical=(logical+part*rotation)&7`. A/B rotations are independent;
choices are 0, 1, or 3. Rotation changes no allocation size, FP operation
order, K32 tile order, BK=256, or FP32 behavior. Existing independent FP64 gap
parameters remain supported.

`tools/packed_layout_search.py --plan` prints the original eleven gap pairs
and five zero-gap rotation pairs. `--phase scan --execute` builds four modes
for N=256 one-repetition preflight, then runs a 20-case zero-gap gate. Every
candidate receives CTest and its full 20-case V3 numeric gate before its
N=8192 FP64 p6/p10/p15/p21 three-repetition timings. The immutable V3
library provides initial/final seven-repetition controls plus a three-rep
drift control after every four candidates. All work queues on
`/tmp/ozamx-perf.lock`; builds use at most `-j2`. Screen leaders are not
statistically established winners. Every raw sample, checkpoint, hash and
failed gate is retained.

`records/*/metadata.json` includes the selected gap/rotation, output allocation
estimate, gap-added bytes, API and phase samples, and build/library/MKL hashes.
The packed output allocation estimate covers persistent uint16 component
panels and excludes temporary residual buffers and public input/output. See
[`cache-index-analysis.md`](cache-index-analysis.md) for the address model and
its limitations.
