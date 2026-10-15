# Roofline study notes for the 8454H campaign

These are original notes from the Intel Integrated Roofline article and the Berkeley Lab paper, applied to the saved ozAMX measurements. They summarize the model and its limits rather than reproducing source text. Bibliographic records, URLs and the downloaded PDF hash are in [`SOURCES.md`](SOURCES.md).

## Model and measurement meaning

The classical roofline bound is

\[
P \leq \min(P_{\text{peak}}, I\,B),
\]

where performance and bandwidth use consistent units, and arithmetic intensity is operations divided by bytes moved at the traffic boundary being modeled. Every input to the bound must describe the same workload and boundary. A logical byte count from source or an instruction loop is an operation count model; it is not automatically a count of bytes transferred from DRAM.

Intel describes its CARM view as cumulative code traffic, counted from instructions that move data to registers. It is useful for algorithm-level comparison, but does not say which memory level supplied those bytes. The Integrated Roofline analysis adds cache-simulation-derived traffic at individual hierarchy boundaries and computes a separate intensity for each level. Those intensities are matched to the corresponding level bandwidths. Since line fills, evictions, write allocation, reuse, and non-temporal stores affect traffic differently at each boundary, the per-level points need not appear in a fixed order.

The 2018 multi-level work makes the measurement distinction operational: detailed instruction/traffic instrumentation and application timing are separate activities because instrumentation perturbs execution. It profiles several levels and loops, then compares each level's traffic intensity with the matching bandwidth roof. For mixed kernels, a single aggregate point can hide distinct compute stages; AMX dot products and SIMD reconstruction should be analyzed as separate stages, with stage-appropriate operation counts and compute ceilings. The highest possible performance is constrained by the tightest applicable compute or data-movement bound, not by the sum of peaks for different ISAs.

## Implications for this AMX GEMM search

The calibration reports a directly measured AMX register-resident ceiling and several tileload rates computed from hand-counted logical payload bytes. The triad probes likewise report logical bytes per second. None used Intel Advisor cache simulation or hardware PMU cache/DRAM traffic counters. Therefore the plots label their diagonal lines as logical-payload rate references, not L1/L2/LLC/DRAM roofs. The per-worker 2.25 MiB tileload footprint is only an LLC residency hypothesis, and the larger 24 MiB/worker triad does not establish physical DRAM traffic by itself.

The integrated roofline perspective motivates measuring stages and recording working-set shape, batch size, data layout, thread placement, and NUMA first-touch policy together. It does not justify mapping a footprint label to a cache level without observed traffic. Nor should an AMX peak and SIMD peak be added to claim a mixed-kernel roof: dependencies, port sharing, conversion/reconstruction work, and data movement decide the combined limit.

This leads to a staged interpretation of the saved experiments:

- The register-only AMX case supplies a benchmark-shape-specific compute ceiling, excluding operand supply and reconstruction.
- TILELOAD and TILELOADT1 cases establish instruction-loop logical throughput under four footprint sizes; they do not identify a cache source.
- P6/P21 no-reconstruction and with-reconstruction points isolate useful product work from the widening/add stage. No-reconstruction remains diagnostic because it omits required numerical output work.
- Standalone FP32/FP64 reconstruction points are low-intensity SIMD diagnostics. The plain-add FP32 probe omits production nonfinite checks and the rest of GEMM.
- API-level scout measurements retain frozen controls and per-process noise/outliers. They guide follow-up selection but are not memory-level roof measurements.

Useful next measurements would pair a low-overhead timing run with appropriate PMU traffic/counter collection, document event semantics and multiplexing, and repeat on the same 64-core/NUMA placement. Cache simulation can provide another model, but its instrumentation and cache assumptions must be recorded separately from timing. Until then, keep algorithmic logical intensity, observed cache-level intensity, and measured API time as distinct quantities.

## Search-design notes

The scout results support several bounded hypotheses rather than a universal winning tile. Reconstruction batching changes scratch and live-state footprint, so any compute-stage gain should be checked against stack/cache pressure and complete API wall time. Rectangular output geometry changes B-panel access and active C footprint. THP's `smaps` evidence confirms backing for the probe allocation, but one probe is not a causal performance result. Adaptive geometry was added for large shapes after full-output equivalence passed; the remaining noisy smaller-shape cases and formal V3 oneMKL comparison still determine the performance interpretation.

An exploratory 16×32 AMX pair layout was not implemented: it would increase the B load volume in the proposed pairing, with no measured evidence that the wider tile reuse offsets that cost. NUMA-local allocation/first touch and explicit CPU affinity remain part of future controlled experiments because aggregate traffic and bandwidth can conceal socket imbalance.

Related local records: [calibration](../../docs/8454H_ROOFLINE_CALIBRATION.md), [search log](../../docs/8454H_ROOFLINE_SEARCH_LOG.md), [AMX total-intensity figure](../../docs/figures/8454H_ROOFLINE_AMX_LOGICAL_AI.svg), and [stage diagnostic figure](../../docs/figures/8454H_ROOFLINE_STAGE_DIAGNOSTIC.svg).

