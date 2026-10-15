# Intel AMX/BF16 primary-source index

## Current Xeon Platinum 8454H collection — 2026-10-13

The current architecture/SIMD/AMX collection is indexed in [README.md](README.md), with a combined study in [8454H_STUDY.md](8454H_STUDY.md). It includes unmodified Intel SDM v093 Volumes 1/2B/2C, Optimization Manual Vol.1 v050, an offline Intrinsics Guide, SKU/NUMA/tuning documentation, and pinned Intel/oneDNN code references. Provenance and SHA-256 are recorded in [manuals/manifest.json](manuals/manifest.json), [xeon-8454h/manifest.json](xeon-8454h/manifest.json), and [examples/manifest.json](examples/manifest.json).

Linux XSTATE documentation is collected as the operating-system authority: AMX permission is process-wide, while register-state buffers are managed per task. The current machine snapshot is separate from the old Gold6430 benchmark environment. The source list below is retained as the earlier 2026-10-12 reference index; its kernel/library observations are historical, and older microarchitecture tuning details must not be projected onto the 8454H.

## Earlier source index — 2026-10-12

Retrieved/checked 2026-10-12. These are Intel-hosted official sources. The source summaries below are brief working notes for this reproduction; consult the linked manuals for normative details.

1. **Intel Architecture Instruction Set Extensions Programming Reference**, Intel PDF: <https://cdrdv2-public.intel.com/843860/architecture-instruction-set-extensions-programming-reference-dec-24.pdf>
   - Sections on `TDPBF16PS` and `VCVTNEPS2BF16` / `VCVTNE2PS2BF16` specify the dot-product, pair packing, BF16 conversion, round-to-nearest-even, and denormal behavior. The reference says an input dword encodes a pair of BF16 values and the pairwise products accumulate to FP32.
   - The older Intel-hosted copy used for browser text extraction was <https://www.intel.com/content/dam/develop/external/us/en/documents/architecture-instruction-set-extensions-programming-reference-737410.pdf>; browser lines 3162–3165 cover BF16 pair dot products and rounding, lines 3070–3090 cover FP32-to-BF16 conversion.

2. **Intel 64 and IA-32 Architectures Software Developer's Manual, Vol. 2B**, Intel PDF: <https://cdrdv2-public.intel.com/782151/253667-sdm-vol-2b.pdf>
   - `TDPBF16PS` reference: <https://cdrdv2-public.intel.com/782151/253667-sdm-vol-2b.pdf>. It defines the operation as BF16 pair dot products accumulated into packed FP32 tile elements and specifies round-to-nearest-even for each accumulation, denormal handling, and the BF16-in-dword representation.
   - A combined SDM copy was also indexed at <https://cdrdv2-public.intel.com/789581/325383-sdm-vol-2abcd.pdf> with the same `TDPBF16PS` semantics.

3. **Intel AMX intrinsic code sample**, Intel Developer: <https://www.intel.com/content/www/us/en/developer/articles/code-sample/advanced-matrix-extensions-intrinsics-functions.html>
   - Describes tile configuration and TMUL; notes XTILECFG/XTILEDATA are XSAVE state and that the OS might not enable XTILEDATA automatically. The sample obtains permission via `arch_prctl` before issuing tile instructions.

4. **What's New in LLVM for 4th Gen Intel Xeon & Max Series CPUs**, Intel Developer: <https://www.intel.com/content/www/us/en/developer/articles/technical/whats-new-in-llvm-for-4th-gen-intel-xeon-processor.html>
   - Shows Linux `ARCH_REQ_XCOMP_PERM` use for `XFEATURE_XTILEDATA` and states Linux AMX support began in kernel 5.16-RC1. This execution host reports kernel 5.15; the successful probe demonstrates the installed kernel/environment supports the permission request despite that reported version.

5. **Intel Architecture Optimization Reference Manual, Volume 1**, Intel PDF: <https://cdrdv2-public.intel.com/814198/248966-Optimization-Reference-Manual-V1-049.pdf>
   - AMX state management section: AMX XSAVE components 17 (64-byte XTILECFG) and 18 (8192-byte XTILEDATA), XCR0 enablement, and #UD behavior if AMX state is not enabled. The Intel instruction manuals remain normative for instruction semantics.

6. **Intel Intrinsics Guide**, Intel: <https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html>
   - Lists AMX-BF16 and AMX-TILE intrinsics and their instruction-set grouping.

No paper-specific assumptions or facts are taken from third-party pages in this index. The arXiv target paper is a separate reproduction input and is not used as an authority for ISA behavior.
