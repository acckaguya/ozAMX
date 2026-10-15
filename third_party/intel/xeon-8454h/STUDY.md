# Xeon Platinum 8454H / Sapphire Rapids study

Retrieved Intel source copies and a read-only machine snapshot are kept beside this note. `manifest.json` records each source URL, final URL, retrieval date, revision where stated, byte count, SHA-256, and reuse boundary. The HTML files are vendor page copies; PDFs are unmodified Intel-hosted documents. Text extractions used while reading are in `/tmp/ozamx-8454h/` and are not source documents.

## What the part number establishes

Intel ARK identifies Xeon Platinum 8454H as a 4th Gen Xeon Scalable part, formerly codenamed Sapphire Rapids. The SKU page specifies 32 cores / 64 threads, 2.10 GHz base, up to 3.40 GHz maximum turbo, 82.5 MB LLC, 270 W TDP, AMX support, two AVX-512 FMA units, up to four UPI links at 16 GT/s, eight DDR5 channels, and up to DDR5-4800 with one DIMM per channel or DDR5-4400 with two DIMMs per channel. ARK lists S8S scalability as a product capability; it does not describe this machine's socket count or active UPI topology.

The 8454H listing also reports 12 high-priority cores with a 2.20 GHz frequency and 20 low-priority cores with a 1.80 GHz frequency. These are Intel's SKU priority/frequency attributes. They do not imply a conventional heterogeneous P-core/E-core design, and the Linux topology snapshot does not identify a mapping between those priority groups and logical CPU IDs.

The historical Xeon Gold 6430 ARK page identifies the same 4th Gen/Sapphire Rapids family and the same 32-core / 64-thread, 2.10 GHz base, 3.40 GHz maximum turbo, and 270 W TDP. Its SKU-level differences include 60 MB cache, at most three UPI links, DDR5-4400 for 1DPC and 2DPC, and 2S scalability. The comparison is a model-specification comparison, not an explanation of the measured performance difference by itself: both processors share the Sapphire Rapids core generation, and measured runs still depend on configured platform, software, frequency, placement and trial conditions.

The family overview is explicitly generation-wide. Its maxima, tables and platform feature descriptions must be read alongside the SKU pages: family limits such as the top core count or accelerator list do not establish support on every part. Intel's family overview describes private 32 KiB L1 instruction / 48 KiB L1 data caches, 2 MiB private L2, and LLC organizations; the actual current CPU0 sysfs cache record and `lscpu` totals corroborate the 8454H cache sizes (48 KiB L1D, 32 KiB L1I, 2 MiB L2, 84,480 KiB / 82.5 MiB L3 per socket).

## Current machine snapshot

The snapshot was captured on 2026-10-13 UTC. `hardware-snapshot/snapshot.txt` preserves the full `lscpu`, `lscpu -e=CPU,CORE,SOCKET,NODE`, visible flags, selected sysfs values, cgroup ancestry, memory totals, and runtime xstate probes; the JSON form separates fields for later comparison.

Observed by Linux in this environment:

- Intel Xeon Platinum 8454H, family 6/model 143/stepping 8; two sockets, 32 cores per socket, two threads per core, 128 online logical CPUs (`0-127`). NUMA node 0 maps CPUs `0-31,64-95`; node 1 maps `32-63,96-127`.
- CPU0's cache sysfs reports 48 KiB L1D, 32 KiB L1I, 2,048 KiB L2, and 84,480 KiB L3. `lscpu` reports 165 MiB total L3 across two sockets.
- The first `/proc/cpuinfo` flags line exposes AVX, AVX2, AVX-512, AVX-512 BF16, AVX-512 FP16, AVX-VNNI, AMX-TILE, AMX-INT8, and AMX-BF16. A small read-only CPUID/XGETBV probe reports OSXSAVE, AVX-512F and all three AMX CPUID bits. XCR0 is `0x602e7`, with AVX, AVX-512 opmask/ZMM state, XTILECFG and XTILEDATA enabled.
- A fresh process initially reported `ARCH_GET_XCOMP_PERM=0x202e7`; after `ARCH_REQ_XCOMP_PERM` for XTILEDATA (component 18), it reported `0x602e7` and successfully executed `TILERELEASE`. A same-process pthread probe observed `0x202e7` in the main task and an already-created worker before the request; after the main task requested permission, both the existing worker and a subsequently-created worker observed `0x602e7`. This matches Linux's process-level AMX permission behavior (permissions are inherited by threads created with clone; fork inherits, while exec clears the permission). It did not change machine-wide settings. CPU feature flags alone do not establish that the current process has requested AMX permission.
- `taskset` and `/proc/self/status` show this shell may run on CPUs `0-127` and NUMA nodes `0-1`. The visible cgroup v2 path has no CPU quota file; its visible root `cpu.stat` counters report zero throttled periods at capture. The shell cgroup has `memory.max=max`. These describe only the observed cgroup namespace and capture time.
- `/proc/meminfo` reports 1,056,305,240 KiB total and 949,736,984 KiB available at the snapshot. This is OS-visible addressable memory, not a DIMM inventory.
- Kernel is `5.15.0-161-generic`. CPU0's instantaneous `scaling_cur_freq` read was about 2.70 GHz, `cpuinfo_max_freq` 3.40 GHz, driver `intel_pstate`, governor `powersave`. One sample is not sustained frequency evidence.
- DMI reports vendor `OEM`, product `S768G5`, board `BM-X13DEPS3`.

The snapshot does **not** establish the installed DIMM make/count, actual memory data rate, rank or per-channel population, configured BIOS SNC/UMA mode, active UPI link arrangement, HBM presence/configuration, or sustained clocks. The two visible NUMA nodes are consistent with a two-socket machine using one exposed NUMA node per socket, but this is an observation/inference about the current OS view, not a readout of BIOS policy. ARK's 4800/4400 MT/s rates and eight-channel capability are maxima conditional on SKU and DIMM population, not measured memory settings. No STREAM or other performance experiment was run and no BIOS, kernel, governor, or machine settings were changed.

## ISA and numerical reading notes

`pdfs/intel-architecture-instruction-set-extensions-programming-reference-dec24.pdf` is Intel's December 2024 extension reference; this study does not claim it is Intel's latest revision. It includes then-current and future extensions, so applicability annotations matter: its broad CPUID tables include Sapphire Rapids tags for AMX, while the same volume also documents later extensions that must not be attributed to 8454H. Use the Sapphire Rapids tags and the shared Intel SDM copies under `../manuals/`, not the mere presence of an instruction in this combined extension document, to decide target applicability.

The shared Intel SDM Vol. 1 (`../manuals/sdm-vol1-v093.pdf`) covers basic architecture and XSAVE state; its AMX state section (printed Vol. 1 pages 13-17 onward) says AMX execution requires OSXSAVE and XCR0 bits 17:18. The shared Vol. 2B (`../manuals/sdm-vol2b-v093.pdf`) entry for `TDPBF16PS` (printed pages 4-715/716) defines pairs of BF16 inputs, packed FP32 accumulation, round-to-nearest-even at each FMA accumulation, and DAZ/FTZ behavior. This is directly relevant to BF16 numerical interpretation; compare the instruction's round points and denormal behavior with the kernel's grouping, conversion and scalar reference rather than assuming exact FP32-equivalent results.

The AVX-512 FP16 Technology Guide (revision 004, March 2024) explicitly describes FP16 vector ISA added to 4th Gen Xeon Scalable. Its distinction is important: IEEE binary16/FP16 has 5 exponent bits and 10 fraction bits, while BF16 has 8 exponent bits and 7 fraction bits. The guide's FP16 arithmetic and embedded rounding provisions apply to its FP16 operations and must not be conflated with AMX-BF16 dot products. The CPU advertises `avx512_fp16`, but the ozAMX path of interest is BF16 AMX plus FP32 accumulation; FP16 guide behavior is context for SIMD alternatives, not proof that FP16 is interchangeable with BF16.

Visual review of the rendered PDF pages found three source-guide errata (the printed page numbers match the PDF page numbers):

- Page 11, Figure 9 labels BF16 as “Significand (5)”; BF16 has 7 fraction/significand bits. The authoritative Intel ISA reference Vol. 1 v093 also lists BF16 as exponent 8 and significand 7 (printed p. 1-56). This is an error in the guide artwork, not a text-extraction artifact.
- Page 14, Table 7 reverses the descriptions for `roundTowardPositive` and `roundTowardNegative`: the positive row says negative infinity and the negative row says positive infinity. The selector constants on those rows correspond to the opposite named directions. Intel's Intrinsics Guide offline data defines `_MM_FROUND_TO_POS_INF` as round up / toward positive infinity and `_MM_FROUND_TO_NEG_INF` as round down / toward negative infinity.
- Page 14 shows `_mm512_add_round_ph` with a `__m128h` return and `__m128h` operands. The 512-bit intrinsic takes and returns `__m512h`; Intel's Intrinsics Guide offline data confirms those types.

Rendered inspection images are in `/tmp/ozamx-8454h/fp16-guide-pdfpage11.png` and `/tmp/ozamx-8454h/fp16-guide-pdfpage14.png`. The vendor PDF is preserved unchanged; these corrections are recorded here as errata only.

AVX-512 remains relevant as a SIMD comparison and fallback path: this host advertises AVX-512F and AVX-512 BF16. The SKU page lists two AVX-512 FMA units. BF16 vector support is separately enumerated in CPUID (`AVX512_BF16`) from AMX-BF16. Software can use vector BF16 dot products or AMX tile dot products, but must choose the implementation based on CPU support, process-level AMX permission, shape, layout/conversion cost, and the actual kernel. Do not infer an AMX speedup from AMX presence alone.

## NUMA, memory and tuning implications

Intel's Sapphire Rapids overview explains that SNC splits a socket into domains with local core/LLC/memory-controller affinity, while UMA provides one interleaved domain. The media tuning article and 4th Gen AI tuning guide recommend balanced channel population and locality for their stated workloads. Those are useful hypotheses for a large GEMM, not evidence that this host has SNC enabled or its channels balanced. The AI guide's example machine is a Xeon Platinum 8480 with DDR5-4800 and its BIOS/OS choices target AI toolkits; media-specific BIOS recommendations likewise should not be copied blindly into a reproducibility setup.

For interpreting ozAMX timing, retain per-stage split/pack/compute/reconstruction timing and distinguish compute throughput from end-to-end time. At small matrices, transformation/setup overhead can dominate even with AMX available. For large matrices, compare physical-core versus SMT placement, one versus both NUMA nodes, first-touch memory placement, observed thread frequencies and memory/channel configuration before attributing residual differences to ISA throughput. This note records those as follow-up measurement variables only; none were changed or benchmarked here.

## Source inventory and boundaries

- `source-html/ark-8454h.html` and `ark-gold6430.html`: model-specific product specifications used for SKU-level comparison.
- `source-html/4th-gen-family-overview.html`: Intel's family technical overview. It discusses NUMA locality/SNC, caches, DDR, UPI, AVX-512, and AMX; family-level values are not per-SKU guarantees.
- `source-html/ai-tuning-4th-gen.html`: workload-specific AI tuning guidance, AMX layout/instructions, memory population, NUMA/thread affinity; its validated system is an 8480 and the recommendations are not a prescription for this machine.
- `source-html/media-tuning-4th-gen.html`: media-specific tuning guidance with transferable discussion of memory/NUMA and actual runtime setting checks; media workload choices are not GEMM measurements.
- `pdfs/intel-architecture-instruction-set-extensions-programming-reference-dec24.pdf`: broad extension reference, includes future/other-generation instructions; use target applicability annotations.
- `../manuals/sdm-vol1-v093.pdf` and `../manuals/sdm-vol2b-v093.pdf`: shared, unmodified official Intel SDM Vol. 1 and Vol. 2B copies for state and instruction semantics. This directory intentionally does not duplicate those files.
- `pdfs/intel-avx512-fp16-technology-guide.pdf`: 4th Gen Xeon AVX-512 FP16 feature/numerical guide; FP16 is distinct from BF16.
- `pdfs/4th-gen-xeon-product-brief.pdf`: generation-level product brief for context, not an exact 8454H datasheet. ARK is the source for exact SKU limits.

Intel pages and PDFs remain copyrighted Intel material. The downloaded PDFs are unchanged. The SDM notice allows publishing an unmodified copy but grants no right to modify or make derivative copies; the other Intel pages/PDFs do not state an open license in these source files, so this collection preserves attribution and URLs and makes no broader redistribution or derivative-work claim. The code and notes in this repository are separate from those vendor documents.
