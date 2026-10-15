# Roofline source register

Retrieval/check date: 2026-10-13 UTC. This directory keeps one lightweight primary-paper PDF and original study notes. It does not vendor Intel Advisor, cache simulators, or benchmark dependencies. The saved PDF is included for local research reference; cite the publisher/author record when reusing the work.

## Intel Integrated Roofline / Cache Aware Roofline Model

- **Publisher:** Intel Corporation.
- **Article:** [Integrated Roofline Model with Intel Advisor](https://www.intel.com/content/www/us/en/developer/articles/technical/integrated-roofline-model-with-intel-advisor.html), article ID 659622, page identifies update date 2018-08-29 (checked 2026-10-13).
- **Relevant distinction:** Intel describes CARM as cumulative instruction-level traffic (L1+L2+LLC+DRAM) with arithmetic intensity invariant for a given code/platform. Its Integrated Roofline extends this with cache-simulation-based transfer counts and a distinct intensity for each memory level. These level-specific traffic quantities cannot be inferred from a source-level logical byte count.
- **Local copy:** none. The page is linked rather than mirrored.

## Original Roofline model

- **Authors:** Samuel Williams, Andrew Waterman, David Patterson.
- **Title:** “Roofline: An Insightful Visual Performance Model for Multicore Architectures.”
- **Publication:** *Communications of the ACM*, 52(4), 65–76, 2009.
- **DOI:** [10.1145/1498765.1498785](https://doi.org/10.1145/1498765.1498785).
- **Berkeley Lab bibliography:** [Roofline performance-model publications](https://amcr.lbl.gov/departments/computer-science-department/ppan/roofline-performance-model/ppan-roofline-publications/).
- **Local copy:** none.

## Multi-level Integrated Roofline

- **Authors:** Tuomas Koskela, Zakhar Matveev, Charlene Yang, Adetokunbo Adedoyin, Roman Belenov, Philippe Thierry, Zhengji Zhao, Rahulkumar Gayatri, Hongzhang Shan, Leonid Oliker, Jack Deslippe, Ron Green, and Samuel Williams.
- **Title:** “A Novel Multi-Level Integrated Roofline Model Approach for Performance Characterization.”
- **Publication:** ISC High Performance 2018, LNCS 10876, pages 226–245.
- **DOI:** [10.1007/978-3-319-92040-5_12](https://doi.org/10.1007/978-3-319-92040-5_12).
- **Berkeley Lab official PDF URL:** <https://amcr.lbl.gov/wp-content/uploads/2025/11/ISC18-RooflineAdvisor-final.pdf>.
- **Institutional record:** [UC eScholarship item](https://escholarship.org/uc/item/8jx3m244), which identifies the 2018 publication and CC BY 4.0 terms.
- **Local file:** [`ISC18-RooflineAdvisor-final.pdf`](ISC18-RooflineAdvisor-final.pdf), 989,209 bytes.
- **SHA-256:** `2fddb09d2b93440f84ca8090af0ebe33bd60bb7b4ffded46aa0c669c119d27b5`.
- **Retrieved:** 2026-10-13 UTC from the Berkeley Lab AMCR URL above over HTTPS. The original paper is retained without extracted/copied text; an original-language summary is in [`study.md`](study.md).

## Project analyses informed by these sources

- [Kernel and memory calibration](../../docs/8454H_ROOFLINE_CALIBRATION.md): measured AMX register ceiling and logical tileload/triad references, with explicit limits on physical-traffic interpretation.
- [Roofline-guided search log](../../docs/8454H_ROOFLINE_SEARCH_LOG.md): batch, pad, THP, rectangular, adaptive, and staged-kernel explorations.
- [Calibration figures](../../docs/figures/8454H_ROOFLINE_AMX_LOGICAL_AI.svg) and [stage view](../../docs/figures/8454H_ROOFLINE_STAGE_DIAGNOSTIC.svg): logical-payload AI and hand-counted byte-rate reference slopes; neither depicts measured cache-level traffic.

