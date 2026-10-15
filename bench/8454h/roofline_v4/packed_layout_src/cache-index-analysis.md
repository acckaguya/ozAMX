# FP64 packed-slab gap and rotation study: address/cache-index model

This isolated source tree varies inter-slab padding and, at zero gap, the
physical order of FP64 M32/N32 slabs by product part. A and B have independent
gap and rotation knobs. Each slab retains its contiguous K32 payload sequence,
its 2,048-byte K32 step, the original BF16-product ordering, and BK=256. FP32
uses zero gap and its existing layout. Gaps are allocation holes: pack and
residual-projection loops write and scan payload only. Rotation permutes the
eight slab slots in each 256-wide macro-panel:

```
physicalSlab = (logicalSlab + part * rotation) & 7
```

`part` is the FP64 component/slice number; A and B have independent rotation
values chosen from 0, 1, or 3. Rotation is a bijection over eight physical
slots, so it adds no storage. `rotation=0` preserves the former gap-only
layout.

## Verified layout arithmetic

A or B slab payload is `32 * 256 = 8192` BF16 words = 16 KiB. One K32 tile is
`32 * 32` BF16 words = 2,048 bytes. The slab pitch remains `16 KiB + gap` and a
256-wide panel occupies eight pitches. The same-numbered slab in the next panel
advances by `128 KiB + 8*gap`. A rotation permutes only slab slots within each
panel; K32 tiles within a slab remain contiguous, with no inserted padding.
Allocation count and total bytes do not change with rotation.

The packed-residual FP64 path first scatters inputs into logical, unrotated
residual slab order. Every projection pass reads and updates that same logical
residual order, then writes the component to its rotated physical slab slot.
The generic slice packer applies the identical per-component permutation. The
zero and normal paths leave gap bytes unwritten, and AMX readers start each A/B
slab from the corresponding component's physical slot. Projection traversal,
pack writers, and AMX readers therefore share one mapping while the
floating-point projection and product order remain unchanged.

## Conditional L2 set-index hypothesis

CPU0 sysfs reports L2 as 2,048 KiB, 16-way, 2,048 sets, 64-byte lines. The
conventional index period is 128 KiB and `set(PA)=(PA>>6) mod 2048`. For
physically contiguous panels and equal physical colors of corresponding slab
starts, gap-only panel advances are `(8*gap_bytes/64) mod 2048`:

| Gap | Conditional panel set advance |
|---:|---:|
| 0 B | 0 sets |
| 64 B | 8 sets |
| 4 KiB | 512 sets |
| 8 KiB | 1,024 sets |
| 16 KiB | 0 sets (one full period) |
| 32 KiB | 0 sets (two periods) |
| 64 KiB | 0 sets (four periods) |

At zero gap, rotation instead shifts the logical slab-to-physical-slot mapping
by `part*rotation mod 8`. This tests whether changing which component's slab
occupies each physical slot affects concurrent A/B working-set behavior. It
is only a mapping hypothesis: the component arrays have independent base
addresses, physical page placement and cache hashing are not controlled, and
rotation cannot guarantee distinct L2 colors or reduce conflicts.

Neither gap nor rotation reasoning proves cache misses or residency. With
ordinary 4 KiB pages, virtual addresses expose only page-offset bits directly;
physical indexing, page placement, huge pages, allocation reuse, cache hashing,
shared-L2 activity and prefetch behavior may change mappings. Larger gaps also
change TLB pressure, footprint and packed-stream prefetching. PMU traffic data
are not available here.

## Prepared scan protocol

The scan includes the original eleven gap pairs and five zero-gap rotations:
`(1,0)`, `(0,1)`, `(1,1)`, `(1,3)`, `(3,1)`. It runs an all-mode N=256
one-repetition preflight, then a full 20-case zero-gap gate before candidate
collection. Every candidate runs CTest and the full 20-case numerical gate
before N=8192 FP64 p6/p10/p15/p21, three-repetition timings. Frozen V3 controls
at seven repetitions bracket the scan; three-repetition V3 drift controls run
after every four candidates. All raw samples and failed attempts are retained,
with no outlier removal. Screen leaders are descriptive only, not validated
winners.
