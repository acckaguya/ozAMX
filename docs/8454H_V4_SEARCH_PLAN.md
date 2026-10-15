# 8454H V4 roofline search preparation

**Status:** this round is complete. V3 paper-alignment testing and the supplementary freeze are complete. V4 diagnostics, calibration, INT8 precision gates, 65 timed parameter configurations, interleaved comparisons and actual-main validation have executed. Current source 0.4.0 adopts only the bounded FP32 CompactWide path; this document records the original hypotheses. Final behavior, evidence and limitations are in [the round report](8454H_V4_ROUND_RESULTS.md), with the experiment sequence in [the search log](8454H_V4_SEARCH_LOG.md).

## Question and first experiment

V4 first asks where the gap between the observed production FP32 rate (about 47 TFLOP/s) and the hot AMX-register diagnostic (about 152 TFLOP/s) is spent. These are supplied working reference values; preserve the provenance/shape/thread count from the frozen V3 records when making the comparison. They are unlike-for-like unless dimensions, thread placement, warmup, timer, repetition, and work accounting are matched.

Build one diagnostic harness that uses the **same real production operand address ranges and strides**, and times three modes in a single run:

1. `no_recon`: production operand traversal, conversion/packing and AMX multiply; stop before output reconstruction.
2. `with_recon`: same traversal and multiply plus the production reconstruction stage.
3. `whole_api`: call the production API end to end.

Run the matching frozen V3 input and shape/thread configuration as a comparison row, not as a substitute for the live V3 paper run. Record stage timings, AMX operation counts and address-span/stride metadata. Compare with the hot register diagnostic while explicitly marking that it has different data residency and may have different useful-work accounting. Do not call its logical payload a DRAM rate. No PMU/counter evidence currently assigns these bytes to L1/L2/LLC/DRAM; the project's paranoid setting is 4. Report instruction-logical bytes and traffic hypotheses separately from physical traffic.

The first experiment is a diagnostic gate, not a tuning sweep. It should identify whether operand feeding/packing, tile math, reconstruction, or API overhead dominates before a kernel hypothesis is selected. Keep source and binary hashes, run order, frequencies/affinity, and raw samples. Do not modify the V3 checkout/artifact to construct this harness.

## Low-cost candidate after the diagnostic: Late32 non-finite scan

Before considering INT8, test whether the current FP32 production path's per-microblock non-finite classification is material. Inspection corrected the original design assumption: production FP32 checks the running `C+f` and the resulting microblock, rather than separately classifying every `f`. The hot FP32 calibration's plain reconstruction path omits that classification; it is a timing reference only and is not a correct production candidate.

Use one real-address diagnostic with three same-input modes: (1) `full`, preserving all production per-product checks; (2) `plainrecon-no-NF`, isolating reconstruction without classification, explicitly diagnostic/incorrect as a production candidate; and (3) `no-recon`, isolating operand supply and AMX work. Keep mode timing and whole-API timing distinct. If the measured classification cost warrants a candidate, implement `Late32` only for a declared large-shape range (initial hypothesis K≥4096): retain the same IEEE FP32 addition order and BK boundaries, defer classification, then scan the final private float C block once before commit. Do not commit caller C until this final scan passes.

The rationale is limited: with ordinary IEEE operations, once a computed value becomes Inf or NaN, later additions cannot turn it back into a finite value (`Inf + -Inf` becomes NaN, and NaN propagates). This does not replace validation. Require the normal full-buffer C gate byte-for-byte, plus explicit overflow, Inf/NaN, cancellation, and transactional `C`-unchanged rejection gates. Compile with `-ffp-contract=off` and without fast-math. A plain reconstruction result without the required final classification cannot be reported as a supported candidate. Late32 was subsequently implemented and passed the numerical gate, but did not show stable API benefit in the initial diagnostic batch; production remains unchanged. Later screen binaries retain the mode-3 flag, so final comparisons must state that build identity explicitly.

## Candidate numerical prototype after the diagnostics

After the Late32 test has either been rejected or completed and V3 remains frozen, if evidence still supports a high-precision compute-path experiment, start INT8 as an isolated, single-shape prototype behind an explicit experimental entry point. Its initial claim is **p21 accuracy target** only. It is not a V3-equivalent or general FP64 method. The algorithm outline and mandatory gate are in [`bench/8454h/roofline_v4/design_notes.md`](../bench/8454h/roofline_v4/design_notes.md).

The prototype must prove quantization error, signed-wide assembly safety, tile tails, and fallback behavior before timing. It must not silently lower precision on inputs outside its validated domain. A future FP32 signed-digit D4 method is lower priority and is not part of the first prototype.

## Exit criteria for this preparation phase

- V3 has completed and root has frozen its result hashes and status.
- The real-address-span diagnostic has comparable raw records and a clear limitation statement about absent physical-traffic counters.
- Late32 is evaluated before INT8; it must pass full correctness and non-finite transactional gates and show whole-API benefit to continue.
- Only then select one kernel prototype. Any speed result must include conversion, packing, all requested diagonal products, assembly/reconstruction, and whole-call overhead.
- Any numerical claim names the tested input domain and exact metric/tolerance. Failed accuracy or overflow gates stop the experiment or route to an explicit supported fallback.

## Primary references

Exact local revisions, SHA-256 values, Intel URLs, and the relevant section/page map are recorded in [`bench/8454h/roofline_v4/techrefs.json`](../bench/8454h/roofline_v4/techrefs.json). The principal sources are Intel Optimization Reference Manual Volume 1, 248966-050US (revision 50, April 2024), Chapter 20, and Intel SDM Volume 2B, 253667-093US (September 2026), AMX TDPB* instruction entries. Vol. 2C does not contain the TDPB* entries; they are in Vol. 2B (M–U).
