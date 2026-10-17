# 文档覆盖与路径核验

范围：`docs/` 下全部 Markdown（排除本报告和 `FILE_INVENTORY.md`），以及 `third_party/` 下 basename 为 README.md、STUDY.md、SOURCES.md 的文件。跳过 `.git/`、`.aws/`、`.codex/`、`.agents/`。只记录文档显式内容和路径/哈希存在性，不评价算法主张。

文档 **53** 个；Markdown 本地相对链接 **331** 个（缺失 **9**）；引用结果路径 **156** 个（缺失 **0**）；校验和文件 **23** 个。

下表元数据仅提取明确标为 Version/版本、Machine/机器/CPU/硬件、Date/日期的行；空值记为 —。

| 文档 | 主题（首标题） | 版本标注 | 机器标注 | 日期标注 | 路径存在/总数 | 本地链接有效/总数 |
|---|---|---|---|---|---:|---:|
| `docs/8454H_CURRENT_BASELINE.md` | Xeon 8454H current machine baseline | — | — | — | 7/7 | 15/15 |
| `docs/8454H_FINAL_PERFORMANCE_REPORT.md` | 8454H final production performance report | — | — | — | 9/9 | 17/17 |
| `docs/8454H_KERNEL_IDEAS.md` | 8454H kernel experiments (not adopted by default) | — | — | — | 12/12 | 17/17 |
| `docs/8454H_PERFORMANCE_BASELINE.md` | Xeon 8454H：匹配基线与优化结果 | — | — | — | 16/16 | 26/26 |
| `docs/8454H_ROOFLINE_CALIBRATION.md` | 8454H roofline kernel calibration analysis | — | — | — | 7/7 | 15/15 |
| `docs/8454H_ROOFLINE_MODEL.md` | 8454H：用于本轮搜索的分层 Roofline 模型 | — | — | — | 1/1 | 4/4 |
| `docs/8454H_ROOFLINE_RESULTS.md` | 8454H roofline-guided production results | — | — | — | 13/13 | 11/11 |
| `docs/8454H_ROOFLINE_SEARCH_LOG.md` | 8454H roofline-guided search log | — | — | — | 9/9 | 20/20 |
| `docs/8454H_ROOFLINE_TRAFFIC.md` | 8454H Roofline Traffic Ledger: Immutable V2 and Adaptive V3 | — | — | — | 4/4 | 2/2 |
| `docs/8454H_SEARCH_LOG.md` | 8454H kernel tuning search log | — | — | — | 1/1 | 1/1 |
| `docs/8454H_SEARCH_RESULTS.md` | 8454H tuning search results | — | — | — | 2/2 | 1/1 |
| `docs/8454H_V1_ARCHIVE.md` | 8454H 优化版 v1 冻结归档 | — | — | — | 2/2 | 1/1 |
| `docs/8454H_V3_PAPER_ALIGNMENT.md` | V3 paper alignment campaign | — | — | — | 7/7 | 11/11 |
| `docs/8454H_V4_ADAPTIVE_RC_MATCHED.md` | Adaptive V4 release candidate matched checks | — | — | — | 0/0 | 0/0 |
| `docs/8454H_V4_COST_MODEL.md` | V4 搜索的成本模型 | — | — | — | 0/0 | 0/0 |
| `docs/8454H_V4_CURRENT_MAIN_VALIDATION.md` | Current main candidate validation | — | — | — | 1/1 | 0/0 |
| `docs/8454H_V4_DIAGNOSTIC_RESULTS.md` | 8454H V4 diagnostic campaign results | — | — | — | 1/1 | 0/0 |
| `docs/8454H_V4_INT8_EXPERIMENT.md` | V4 INT8-36 原型：实现验证与精度失败 | — | — | — | 0/0 | 0/0 |
| `docs/8454H_V4_KERNEL_SCHEDULE_RESULTS.md` | V4 AMX load schedule experiment results | — | — | — | 4/4 | 7/7 |
| `docs/8454H_V4_LAYOUT_RESULTS.md` | V4 padding and tile-load layout screen | — | — | — | 1/1 | 5/7 |
| `docs/8454H_V4_MATCHED_RESULTS.md` | V4 matched-call geometry results | — | — | — | 0/0 | 0/0 |
| `docs/8454H_V4_PACKED_LAYOUT_RESULTS.md` | V4 packed-layout screen results | — | — | — | 0/0 | 2/2 |
| `docs/8454H_V4_PAGE_LAYOUT_RESULTS.md` | V4 large-workspace page alignment and THP hint screen | — | — | — | 13/13 | 2/6 |
| `docs/8454H_V4_PAGE_MATCHED_RESULTS.md` | V4 page-layout matched-call results | — | — | — | 2/2 | 0/3 |
| `docs/8454H_V4_RC_CONFIRMATION.md` | Independent RC1 runtime confirmation | — | — | — | 1/1 | 0/0 |
| `docs/8454H_V4_RECON_ILP_RESULTS.md` | V4 ordered reconstruction ILP4 results | — | — | — | 2/2 | 0/0 |
| `docs/8454H_V4_ROOFLINE_CALIBRATION.md` | 8454H roofline calibration rerun for the V4 phase | — | — | — | 1/1 | 3/3 |
| `docs/8454H_V4_ROUND_RESULTS.md` | 8454H：V3 冻结后的 V4 roofline 搜索结果 | — | — | — | 3/3 | 8/8 |
| `docs/8454H_V4_SEARCH_LOG.md` | V4 搜索记录 | — | — | — | 0/0 | 12/12 |
| `docs/8454H_V4_SEARCH_PLAN.md` | 8454H V4 roofline search preparation | — | — | — | 2/2 | 4/4 |
| `docs/CODE_READABILITY.md` | 代码排版与注释整理 | — | — | — | 0/0 | 1/1 |
| `docs/CPU_LIMITS.md` | 本次执行的 CPU quota 可见性检查 | — | — | — | 0/0 | 1/1 |
| `docs/ENVIRONMENT.md` | 复现环境记录 | — | — | — | 1/1 | 2/2 |
| `docs/FP64_DIAGNOSTIC.md` | FP64 六片算法数值诊断 | — | — | — | 1/1 | 1/1 |
| `docs/NATIVE_ALTERNATIVE_ACCURACY.md` | 三种 FP64 六层分解的原生 AMX 对照诊断 | — | — | — | 0/0 | 1/1 |
| `docs/NATIVE_KERNEL_AUDIT.md` | AMX 原生乘积与面板验收 | — | — | — | 1/1 | 2/2 |
| `docs/PAPER_SECTION_6_3_IMPLEMENTATION.md` | 论文第 6.3 节：目标精度重建与并行化 | — | — | — | 1/1 | 10/10 |
| `docs/PAPER_STUDY.md` | 论文研读记录：BF16 Component-Product Emulation of FP32 and FP64 GEMM on Intel AMX | — | — | — | 2/2 | 1/1 |
| `docs/PROJECT_SUMMARY.md` | ozAMX 项目总结：论文复现、平台优化与现阶段结论 | — | — | — | 8/8 | 59/59 |
| `docs/PUBLICATION_PACKAGE.md` | 公开仓库文件范围 | — | — | — | 3/3 | 0/0 |
| `docs/REPRODUCTION_RESULTS.md` | ozAMX 论文复现实验结果 | — | — | — | 4/4 | 9/9 |
| `docs/REPRODUCTION_SPEC.md` | 复现规范：AMX 上以 BF16 component products 模拟 FP32/FP64 GEMM | — | — | — | 1/1 | 2/2 |
| `docs/SIGNED_SHIFT_DIAGNOSTIC.md` | N=256 signed-shift 单点诊断 | — | — | — | 0/0 | 5/5 |
| `docs/WORKSPACE_CLEANUP.md` | 工作区整理与 Git 管理 | — | — | — | 0/0 | 1/1 |
| `third_party/SOURCES.md` | 第三方来源登记 | — | — | — | 2/2 | 12/12 |
| `third_party/intel/README.md` | Xeon Platinum 8454H / Sapphire Rapids 资料库 | — | — | — | 2/2 | 13/13 |
| `third_party/intel/SOURCES.md` | Intel AMX/BF16 primary-source index | — | — | — | 0/0 | 5/5 |
| `third_party/intel/examples/STUDY.md` | Intel AMX and SIMD example study | — | — | — | 0/0 | 0/0 |
| `third_party/intel/simd/STUDY.md` | Intel ISA and SIMD reading notes for Sapphire Rapids / Xeon Platinum 8454H | — | — | — | 1/1 | 2/2 |
| `third_party/intel/xeon-8454h/STUDY.md` | Xeon Platinum 8454H / Sapphire Rapids study | — | — | — | 0/0 | 0/0 |
| `third_party/intel/xeon-8454h/hardware-snapshot/local-probes/README.md` | Local AMX/xstate validation probes | — | — | — | 0/0 | 0/0 |
| `third_party/roofline/SOURCES.md` | Roofline source register | — | — | — | 4/4 | 6/6 |
| `third_party/roofline/study.md` | Roofline study notes for the 8454H campaign | — | — | — | 4/4 | 5/5 |

## 逐文档引用的结果路径

**`docs/8454H_CURRENT_BASELINE.md`**
- 存在：`bench/8454h/roofline_v4/calibration_20261014/raw/kernels.csv`（解析为 `bench/8454h/roofline_v4/calibration_20261014/raw/kernels.csv`）
- 存在：`bench/8454h/roofline_v4/calibration_20261014/analysis.json`（解析为 `bench/8454h/roofline_v4/calibration_20261014/analysis.json`）
- 存在：`bench/8454h/roofline_v4/calibration_20261014/environment.json`（解析为 `bench/8454h/roofline_v4/calibration_20261014/environment.json`）
- 存在：`bench/8454h/roofline_v4/calibration_20261014/README.md`（解析为 `bench/8454h/roofline_v4/calibration_20261014/README.md`）
- 存在：`bench/8454h/v3_paper_alignment/analysis.json`（解析为 `bench/8454h/v3_paper_alignment/analysis.json`）
- 存在：`bench/8454h/v3_paper_alignment/machine_lscpu.txt`（解析为 `bench/8454h/v3_paper_alignment/machine_lscpu.txt`）
- 存在：`bench/8454h/v3_paper_alignment/campaign_completion.json`（解析为 `bench/8454h/v3_paper_alignment/campaign_completion.json`）
**`docs/8454H_FINAL_PERFORMANCE_REPORT.md`**
- 存在：`bench/8454h/versions/v2_release/README.md`（解析为 `bench/8454h/versions/v2_release/README.md`）
- 存在：`bench/8454h/mkl_production/README.md`（解析为 `bench/8454h/mkl_production/README.md`）
- 存在：`bench/8454h/versions/v2/README.md`（解析为 `bench/8454h/versions/v2/README.md`）
- 存在：`bench/8454h/mkl_production/provenance.json`（解析为 `bench/8454h/mkl_production/provenance.json`）
- 存在：`bench/8454h/V2_VALIDATION.md`（解析为 `bench/8454h/V2_VALIDATION.md`）
- 存在：`bench/8454h/mkl_production/production_comparison.md`（解析为 `bench/8454h/mkl_production/production_comparison.md`）
- 存在：`bench/8454h/mkl_production/full_production.csv`（解析为 `bench/8454h/mkl_production/full_production.csv`）
- 存在：`bench/8454h/search/source_base/README.md`（解析为 `bench/8454h/search/source_base/README.md`）
- 存在：`bench/8454h/search/ideas/amx_int8_exact_accumulation.md`（解析为 `bench/8454h/search/ideas/amx_int8_exact_accumulation.md`）
**`docs/8454H_KERNEL_IDEAS.md`**
- 存在：`bench/8454h/search/ideas/comparison.json`（解析为 `bench/8454h/search/ideas/comparison.json`）
- 存在：`bench/8454h/search/ideas/experiment_metadata.json`（解析为 `bench/8454h/search/ideas/experiment_metadata.json`）
- 存在：`bench/8454h/search/ideas/fp32_direct_gate_summary.json`（解析为 `bench/8454h/search/ideas/fp32_direct_gate_summary.json`）
- 存在：`bench/8454h/search/packed_vs_max/comparison.json`（解析为 `bench/8454h/search/packed_vs_max/comparison.json`）
- 存在：`bench/8454h/mkl_v2/README.md`（解析为 `bench/8454h/mkl_v2/README.md`）
- 存在：`bench/8454h/mkl_v2/comparison_v1_v2.md`（解析为 `bench/8454h/mkl_v2/comparison_v1_v2.md`）
- 存在：`bench/8454h/search/v2_cache/comparison.json`（解析为 `bench/8454h/search/v2_cache/comparison.json`）
- 存在：`bench/8454h/search/ideas/v2_late64.md`（解析为 `bench/8454h/search/ideas/v2_late64.md`）
- 存在：`bench/8454h/search/ideas/v2_late64_gate_summary.json`（解析为 `bench/8454h/search/ideas/v2_late64_gate_summary.json`）
- 存在：`bench/8454h/search/v2_late64/comparison.json`（解析为 `bench/8454h/search/v2_late64/comparison.json`）
- 存在：`bench/8454h/search/v2_late64_confirm/comparison.json`（解析为 `bench/8454h/search/v2_late64_confirm/comparison.json`）
- 存在：`bench/8454h/search/ideas/amx_int8_exact_accumulation.md`（解析为 `bench/8454h/search/ideas/amx_int8_exact_accumulation.md`）
**`docs/8454H_PERFORMANCE_BASELINE.md`**
- 存在：`bench/8454h/versions/v2_release/README.md`（解析为 `bench/8454h/versions/v2_release/README.md`）
- 存在：`bench/8454h/final_before.csv`（解析为 `bench/8454h/final_before.csv`）
- 存在：`bench/8454h/final_optimized.csv`（解析为 `bench/8454h/final_optimized.csv`）
- 存在：`bench/8454h/final_before_8192.csv`（解析为 `bench/8454h/final_before_8192.csv`）
- 存在：`bench/8454h/final_optimized_8192.csv`（解析为 `bench/8454h/final_optimized_8192.csv`）
- 存在：`bench/8454h/final_run_metadata.txt`（解析为 `bench/8454h/final_run_metadata.txt`）
- 存在：`bench/8454h/platform_baseline.csv`（解析为 `bench/8454h/platform_baseline.csv`）
- 存在：`bench/8454h/platform_instruction_audit.txt`（解析为 `bench/8454h/platform_instruction_audit.txt`）
- 存在：`bench/8454h/mkl_production/README.md`（解析为 `bench/8454h/mkl_production/README.md`）
- 存在：`bench/8454h/mkl_v2/README.md`（解析为 `bench/8454h/mkl_v2/README.md`）
- 存在：`bench/optimization_benchmark.cpp`（解析为 `bench/optimization_benchmark.cpp`）
- 存在：`bench/8454h/supplemental_default_8192.csv`（解析为 `bench/8454h/supplemental_default_8192.csv`）
- 存在：`bench/8454h/supplemental_cache4g_8192.csv`（解析为 `bench/8454h/supplemental_cache4g_8192.csv`）
- 存在：`bench/8454h/validation_results.json`（解析为 `bench/8454h/validation_results.json`）
- 存在：`bench/8454h/baseline_original.csv`（解析为 `bench/8454h/baseline_original.csv`）
- 存在：`bench/8454h/mkl_v1/README.md`（解析为 `bench/8454h/mkl_v1/README.md`）
**`docs/8454H_ROOFLINE_CALIBRATION.md`**
- 存在：`bench/8454h/roofline/calibration/kernels.csv`（解析为 `bench/8454h/roofline/calibration/kernels.csv`）
- 存在：`bench/8454h/roofline/calibration/kernel_metadata.json`（解析为 `bench/8454h/roofline/calibration/kernel_metadata.json`）
- 存在：`bench/8454h/roofline/calibration/kernel_disassembly.txt`（解析为 `bench/8454h/roofline/calibration/kernel_disassembly.txt`）
- 存在：`bench/8454h/roofline/calibration/kernel_summary.json`（解析为 `bench/8454h/roofline/calibration/kernel_summary.json`）
- 存在：`bench/8454h/platform_baseline.csv`（解析为 `bench/8454h/platform_baseline.csv`）
- 存在：`bench/8454h/roofline/memory_calibration_20261013.csv`（解析为 `bench/8454h/roofline/memory_calibration_20261013.csv`）
- 存在：`bench/8454h/roofline/memory_calibration_20261013.json`（解析为 `bench/8454h/roofline/memory_calibration_20261013.json`）
**`docs/8454H_ROOFLINE_MODEL.md`**
- 存在：`bench/8454h/roofline/search_adaptive/summary.json`（解析为 `bench/8454h/roofline/search_adaptive/summary.json`）
**`docs/8454H_ROOFLINE_RESULTS.md`**
- 存在：`bench/8454h/versions/v3_release/README.md`（解析为 `bench/8454h/versions/v3_release/README.md`）
- 存在：`bench/8454h/mkl_roofline_v3/full_roofline_v3.csv`（解析为 `bench/8454h/mkl_roofline_v3/full_roofline_v3.csv`）
- 存在：`bench/8454h/mkl_roofline_v3/provenance.json`（解析为 `bench/8454h/mkl_roofline_v3/provenance.json`）
- 存在：`bench/benchmark.cpp`（解析为 `bench/benchmark.cpp`）
- 存在：`bench/8454h/mkl_v2/full_candidate.csv`（解析为 `bench/8454h/mkl_v2/full_candidate.csv`）
- 存在：`bench/8454h/mkl_production/full_production.csv`（解析为 `bench/8454h/mkl_production/full_production.csv`）
- 存在：`bench/8454h/mkl_roofline_v3/matched_recheck/README.md`（解析为 `bench/8454h/mkl_roofline_v3/matched_recheck/README.md`）
- 存在：`bench/8454h/mkl_roofline_v3/matched_recheck/comparison.json`（解析为 `bench/8454h/mkl_roofline_v3/matched_recheck/comparison.json`）
- 存在：`bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/full.csv`（解析为 `bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/full.csv`）
- 存在：`bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/full.csv`（解析为 `bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/full.csv`）
- 存在：`bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/full.csv`（解析为 `bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/full.csv`）
- 存在：`bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/full.csv`（解析为 `bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/full.csv`）
- 存在：`bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/full.csv`（解析为 `bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/full.csv`）
**`docs/8454H_ROOFLINE_SEARCH_LOG.md`**
- 存在：`bench/8454h/versions/v2_release/README.md`（解析为 `bench/8454h/versions/v2_release/README.md`）
- 存在：`bench/8454h/versions/v2/README.md`（解析为 `bench/8454h/versions/v2/README.md`）
- 存在：`bench/8454h/roofline/search_numa_b/RESULTS.md`（解析为 `bench/8454h/roofline/search_numa_b/RESULTS.md`）
- 存在：`bench/8454h/roofline/search_numa_half/2g/RESULTS.md`（解析为 `bench/8454h/roofline/search_numa_half/2g/RESULTS.md`）
- 存在：`bench/8454h/roofline/search_numa_half/4g/RESULTS.md`（解析为 `bench/8454h/roofline/search_numa_half/4g/RESULTS.md`）
- 存在：`bench/8454h/roofline/search_numa_half/README.md`（解析为 `bench/8454h/roofline/search_numa_half/README.md`）
- 存在：`bench/8454h/roofline/search_batch64/comparison.json`（解析为 `bench/8454h/roofline/search_batch64/comparison.json`）
- 存在：`bench/8454h/roofline/search_commands.md`（解析为 `bench/8454h/roofline/search_commands.md`）
- 存在：`bench/8454h/roofline/binary_gate.json`（解析为 `bench/8454h/roofline/binary_gate.json`）
**`docs/8454H_ROOFLINE_TRAFFIC.md`**
- 存在：`bench/8454h/roofline/traffic_model.json`（解析为 `bench/8454h/roofline/traffic_model.json`）
- 存在：`bench/8454h/mkl_production/full_production.csv`（解析为 `bench/8454h/mkl_production/full_production.csv`）
- 存在：`bench/8454h/roofline/production_validation.json`（解析为 `bench/8454h/roofline/production_validation.json`）
- 存在：`bench/8454h/roofline/binary_gate.json`（解析为 `bench/8454h/roofline/binary_gate.json`）
**`docs/8454H_SEARCH_LOG.md`**
- 存在：`bench/8454h/search/variants.json`（解析为 `bench/8454h/search/variants.json`）
**`docs/8454H_SEARCH_RESULTS.md`**
- 存在：`bench/8454h/search/selection_final_c0eafaa4c07f9445.json`（解析为 `bench/8454h/search/selection_final_c0eafaa4c07f9445.json`）
- 存在：`bench/8454h/search/DEEP_EXPERIMENT_INDEX.json`（解析为 `bench/8454h/search/DEEP_EXPERIMENT_INDEX.json`）
**`docs/8454H_V1_ARCHIVE.md`**
- 存在：`bench/8454h/validation_results.json`（解析为 `bench/8454h/validation_results.json`）
- 存在：`docs/8454H_PERFORMANCE_BASELINE.md`（解析为 `docs/8454H_PERFORMANCE_BASELINE.md`）
**`docs/8454H_V3_PAPER_ALIGNMENT.md`**
- 存在：`third_party/papers/2609.04663v1.pdf`（解析为 `third_party/papers/2609.04663v1.pdf`）
- 存在：`bench/8454h/v3_paper_alignment/paper_reference.json`（解析为 `bench/8454h/v3_paper_alignment/paper_reference.json`）
- 存在：`bench/8454h/v3_paper_alignment/analysis.json`（解析为 `bench/8454h/v3_paper_alignment/analysis.json`）
- 存在：`bench/8454h/v3_paper_alignment/plots/ef_ratio_vs_size.png`（解析为 `bench/8454h/v3_paper_alignment/plots/ef_ratio_vs_size.png`）
- 存在：`bench/8454h/v3_paper_alignment/plots/fp32_speedup_vs_size.png`（解析为 `bench/8454h/v3_paper_alignment/plots/fp32_speedup_vs_size.png`）
- 存在：`bench/8454h/v3_paper_alignment/plots/fp32_thread_scaling_api_vs_mkl.png`（解析为 `bench/8454h/v3_paper_alignment/plots/fp32_thread_scaling_api_vs_mkl.png`）
- 存在：`bench/8454h/v3_paper_alignment/plots/raw_bf16_measured_gflops.png`（解析为 `bench/8454h/v3_paper_alignment/plots/raw_bf16_measured_gflops.png`）
**`docs/8454H_V4_CURRENT_MAIN_VALIDATION.md`**
- 存在：`bench/benchmark.cpp`（解析为 `bench/benchmark.cpp`）
**`docs/8454H_V4_DIAGNOSTIC_RESULTS.md`**
- 存在：`bench/8454h/roofline_v4/diagnostic_src/results/20261014T091717Z-3/analysis.json`（解析为 `bench/8454h/roofline_v4/diagnostic_src/results/20261014T091717Z-3/analysis.json`）
**`docs/8454H_V4_KERNEL_SCHEDULE_RESULTS.md`**
- 存在：`bench/8454h/roofline_v4/kernel_schedule_src/README.md`（解析为 `bench/8454h/roofline_v4/kernel_schedule_src/README.md`）
- 存在：`bench/8454h/roofline_v4/kernel_schedule_runs/kernel_schedule_20261014T142400Z/matched_raw.csv`（解析为 `bench/8454h/roofline_v4/kernel_schedule_runs/kernel_schedule_20261014T142400Z/matched_raw.csv`）
- 存在：`bench/8454h/roofline_v4/kernel_schedule_runs/kernel_schedule_20261014T142400Z/matched_summary.json`（解析为 `bench/8454h/roofline_v4/kernel_schedule_runs/kernel_schedule_20261014T142400Z/matched_summary.json`）
- 存在：`bench/8454h/roofline_v4/kernel_schedule_runs/kernel_schedule_20261014T142400Z/validation_state.json`（解析为 `bench/8454h/roofline_v4/kernel_schedule_runs/kernel_schedule_20261014T142400Z/validation_state.json`）
**`docs/8454H_V4_LAYOUT_RESULTS.md`**
- 存在：`bench/8454h/roofline_v4/search_runs/layout_b2_m256_n256_20261014_retry2/layout_analysis.json`（解析为 `bench/8454h/roofline_v4/search_runs/layout_b2_m256_n256_20261014_retry2/layout_analysis.json`）
**`docs/8454H_V4_PAGE_LAYOUT_RESULTS.md`**
- 存在：`bench/8454h/roofline_v4/page_layout_src/PAGE_LAYOUT_SOURCE_SNAPSHOT.json`（解析为 `bench/8454h/roofline_v4/page_layout_src/PAGE_LAYOUT_SOURCE_SNAPSHOT.json`）
- 存在：`bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/gates/a4k_hint0_full.json`（解析为 `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/gates/a4k_hint0_full.json`）
- 存在：`bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/gates/a4k_hint1_full.json`（解析为 `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/gates/a4k_hint1_full.json`）
- 存在：`bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/gates/a2m_hint0_full.json`（解析为 `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/gates/a2m_hint0_full.json`）
- 存在：`bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/gates/a2m_hint1_full.json`（解析为 `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/gates/a2m_hint1_full.json`）
- 存在：`bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/logs/a4k_hint0_ctest.log`（解析为 `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/logs/a4k_hint0_ctest.log`）
- 存在：`bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/logs/a4k_hint1_ctest.log`（解析为 `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/logs/a4k_hint1_ctest.log`）
- 存在：`bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/logs/a2m_hint0_ctest.log`（解析为 `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/logs/a2m_hint0_ctest.log`）
- 存在：`bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/logs/a2m_hint1_ctest.log`（解析为 `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/logs/a2m_hint1_ctest.log`）
- 存在：`bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a4k_hint0/build_identity.json`（解析为 `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a4k_hint0/build_identity.json`）
- 存在：`bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a4k_hint1/build_identity.json`（解析为 `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a4k_hint1/build_identity.json`）
- 存在：`bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a2m_hint0/build_identity.json`（解析为 `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a2m_hint0/build_identity.json`）
- 存在：`bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a2m_hint1/build_identity.json`（解析为 `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a2m_hint1/build_identity.json`）
**`docs/8454H_V4_PAGE_MATCHED_RESULTS.md`**
- 存在：`bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/gates/a2m_hint1_full.json`（解析为 `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/gates/a2m_hint1_full.json`）
- 存在：`bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/gates/a4k_hint1_full.json`（解析为 `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/gates/a4k_hint1_full.json`）
**`docs/8454H_V4_RC_CONFIRMATION.md`**
- 存在：`bench/8454h/roofline_v4/matched_calls/results/rc1_independent_confirmation_20261014/startup_resources.txt`（解析为 `bench/8454h/roofline_v4/matched_calls/results/rc1_independent_confirmation_20261014/startup_resources.txt`）
**`docs/8454H_V4_RECON_ILP_RESULTS.md`**
- 存在：`bench/8454h/roofline_v4/recon_ilp_runs/ilp4_recon_bracket_20261014T112800Z/dataset.json`（解析为 `bench/8454h/roofline_v4/recon_ilp_runs/ilp4_recon_bracket_20261014T112800Z/dataset.json`）
- 存在：`bench/8454h/roofline_v4/recon_ilp_runs/ilp4_recon_bracket_20261014T112800Z/analysis.json`（解析为 `bench/8454h/roofline_v4/recon_ilp_runs/ilp4_recon_bracket_20261014T112800Z/analysis.json`）
**`docs/8454H_V4_ROOFLINE_CALIBRATION.md`**
- 存在：`bench/8454h/roofline_v4/calibration_20261014/analysis.json`（解析为 `bench/8454h/roofline_v4/calibration_20261014/analysis.json`）
**`docs/8454H_V4_ROUND_RESULTS.md`**
- 存在：`bench/8454h/roofline_v4/archive_integrity_audit.json`（解析为 `bench/8454h/roofline_v4/archive_integrity_audit.json`）
- 存在：`bench/8454h/roofline_v4/round_analysis/figures/v3_vs_v4_fp32_p6.png`（解析为 `bench/8454h/roofline_v4/round_analysis/figures/v3_vs_v4_fp32_p6.png`）
- 存在：`bench/8454h/roofline_v4/round_analysis/figures/round_plot_data.json`（解析为 `bench/8454h/roofline_v4/round_analysis/figures/round_plot_data.json`）
**`docs/8454H_V4_SEARCH_PLAN.md`**
- 存在：`bench/8454h/roofline_v4/design_notes.md`（解析为 `bench/8454h/roofline_v4/design_notes.md`）
- 存在：`bench/8454h/roofline_v4/techrefs.json`（解析为 `bench/8454h/roofline_v4/techrefs.json`）
**`docs/ENVIRONMENT.md`**
- 存在：`third_party/docs/amx-instruction-notes.md`（解析为 `third_party/docs/amx-instruction-notes.md`）
**`docs/FP64_DIAGNOSTIC.md`**
- 存在：`docs/FP64_DIAGNOSTIC_RESULTS.json`（解析为 `docs/FP64_DIAGNOSTIC_RESULTS.json`）
**`docs/NATIVE_KERNEL_AUDIT.md`**
- 存在：`bench/8454h/validation_results.json`（解析为 `bench/8454h/validation_results.json`）
**`docs/PAPER_SECTION_6_3_IMPLEMENTATION.md`**
- 存在：`third_party/papers/2609.04663v1.pdf`（解析为 `third_party/papers/2609.04663v1.pdf`）
**`docs/PAPER_STUDY.md`**
- 存在：`third_party/papers/2609.04663v1.pdf`（解析为 `third_party/papers/2609.04663v1.pdf`）
- 存在：`third_party/papers/2609.04663v1.preflight_manifest.json`（解析为 `third_party/papers/2609.04663v1.preflight_manifest.json`）
**`docs/PROJECT_SUMMARY.md`**
- 存在：`third_party/papers/2609.04663v1.pdf`（解析为 `third_party/papers/2609.04663v1.pdf`）
- 存在：`third_party/intel/README.md`（解析为 `third_party/intel/README.md`）
- 存在：`bench/8454h/versions/v2_release/README.md`（解析为 `bench/8454h/versions/v2_release/README.md`）
- 存在：`bench/benchmark.cpp`（解析为 `bench/benchmark.cpp`）
- 存在：`bench/8454h/versions/v3_release/README.md`（解析为 `bench/8454h/versions/v3_release/README.md`）
- 存在：`bench/8454h/versions/v3_paper_release/README.md`（解析为 `bench/8454h/versions/v3_paper_release/README.md`）
- 存在：`bench/8454h/versions/v4_roofline_search_round1/freeze_info.json`（解析为 `bench/8454h/versions/v4_roofline_search_round1/freeze_info.json`）
- 存在：`bench/8454h/roofline_v4/V4_FREEZE_RECEIPT.json`（解析为 `bench/8454h/roofline_v4/V4_FREEZE_RECEIPT.json`）
**`docs/PUBLICATION_PACKAGE.md`**
- 存在：`third_party/papers/2609.04663v1.pdf`（解析为 `third_party/papers/2609.04663v1.pdf`）
- 存在：`third_party/intel/SOURCES.md`（解析为 `third_party/intel/SOURCES.md`）
- 存在：`third_party/SOURCES.md`（解析为 `third_party/SOURCES.md`）
**`docs/REPRODUCTION_RESULTS.md`**
- 存在：`bench/final_main_40.csv`（解析为 `bench/final_main_40.csv`）
- 存在：`bench/final_timing_statistics.csv`（解析为 `bench/final_timing_statistics.csv`）
- 存在：`bench/raw_bf16.csv`（解析为 `bench/raw_bf16.csv`）
- 存在：`bench/diagnostics/alt_256/native_results.csv`（解析为 `bench/diagnostics/alt_256/native_results.csv`）
**`docs/REPRODUCTION_SPEC.md`**
- 存在：`third_party/papers/2609.04663v1.pdf`（解析为 `third_party/papers/2609.04663v1.pdf`）
**`third_party/SOURCES.md`**
- 存在：`docs/amx-instruction-notes.md`（解析为 `third_party/docs/amx-instruction-notes.md`）
- 存在：`bench/raw_bf16_manifest.md`（解析为 `bench/raw_bf16_manifest.md`）
**`third_party/intel/README.md`**
- 存在：`docs/ENVIRONMENT.md`（解析为 `docs/ENVIRONMENT.md`）
- 存在：`docs/FULL_SWEEP_MANIFEST.json`（解析为 `docs/FULL_SWEEP_MANIFEST.json`）
**`third_party/intel/simd/STUDY.md`**
- 存在：`docs/8454H_PERFORMANCE_BASELINE.md`（解析为 `docs/8454H_PERFORMANCE_BASELINE.md`）
**`third_party/roofline/SOURCES.md`**
- 存在：`docs/8454H_ROOFLINE_CALIBRATION.md`（解析为 `docs/8454H_ROOFLINE_CALIBRATION.md`）
- 存在：`docs/8454H_ROOFLINE_SEARCH_LOG.md`（解析为 `docs/8454H_ROOFLINE_SEARCH_LOG.md`）
- 存在：`docs/figures/8454H_ROOFLINE_AMX_LOGICAL_AI.svg`（解析为 `docs/figures/8454H_ROOFLINE_AMX_LOGICAL_AI.svg`）
- 存在：`docs/figures/8454H_ROOFLINE_STAGE_DIAGNOSTIC.svg`（解析为 `docs/figures/8454H_ROOFLINE_STAGE_DIAGNOSTIC.svg`）
**`third_party/roofline/study.md`**
- 存在：`docs/8454H_ROOFLINE_CALIBRATION.md`（解析为 `docs/8454H_ROOFLINE_CALIBRATION.md`）
- 存在：`docs/8454H_ROOFLINE_SEARCH_LOG.md`（解析为 `docs/8454H_ROOFLINE_SEARCH_LOG.md`）
- 存在：`docs/figures/8454H_ROOFLINE_AMX_LOGICAL_AI.svg`（解析为 `docs/figures/8454H_ROOFLINE_AMX_LOGICAL_AI.svg`）
- 存在：`docs/figures/8454H_ROOFLINE_STAGE_DIAGNOSTIC.svg`（解析为 `docs/figures/8454H_ROOFLINE_STAGE_DIAGNOSTIC.svg`）

## 缺失的 Markdown 本地相对链接

- `docs/8454H_V4_LAYOUT_RESULTS.md` → `../bench/8454h/roofline_v4/search_runs/layout_b2_m256_n256_20261014_retry2/builds/layout_b2_m256_n256_p64_h1_l1__mode3_b2_m256_n256_p64_h1_l1/libozamx.a`（解析为 `bench/8454h/roofline_v4/search_runs/layout_b2_m256_n256_20261014_retry2/builds/layout_b2_m256_n256_p64_h1_l1__mode3_b2_m256_n256_p64_h1_l1/libozamx.a`）
- `docs/8454H_V4_LAYOUT_RESULTS.md` → `../bench/8454h/roofline_v4/search_runs/layout_b2_m256_n256_20261014_retry2/builds/layout_b2_m256_n256_p0_h1_l1__mode3_b2_m256_n256_p0_h1_l1/libozamx.a`（解析为 `bench/8454h/roofline_v4/search_runs/layout_b2_m256_n256_20261014_retry2/builds/layout_b2_m256_n256_p0_h1_l1__mode3_b2_m256_n256_p0_h1_l1/libozamx.a`）
- `docs/8454H_V4_PAGE_LAYOUT_RESULTS.md` → `../bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a4k_hint0/libozamx.a`（解析为 `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a4k_hint0/libozamx.a`）
- `docs/8454H_V4_PAGE_LAYOUT_RESULTS.md` → `../bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a4k_hint1/libozamx.a`（解析为 `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a4k_hint1/libozamx.a`）
- `docs/8454H_V4_PAGE_LAYOUT_RESULTS.md` → `../bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a2m_hint0/libozamx.a`（解析为 `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a2m_hint0/libozamx.a`）
- `docs/8454H_V4_PAGE_LAYOUT_RESULTS.md` → `../bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a2m_hint1/libozamx.a`（解析为 `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a2m_hint1/libozamx.a`）
- `docs/8454H_V4_PAGE_MATCHED_RESULTS.md` → `summary.json`（解析为 `docs/summary.json`）
- `docs/8454H_V4_PAGE_MATCHED_RESULTS.md` → `../bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a2m_hint1/libozamx.a`（解析为 `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a2m_hint1/libozamx.a`）
- `docs/8454H_V4_PAGE_MATCHED_RESULTS.md` → `../bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a4k_hint1/libozamx.a`（解析为 `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a4k_hint1/libozamx.a`）

## 缺失的结果路径

未发现。

## 校验和核验

校验 `bench/diagnostics/**/checksums.sha256` 和 `bench/8454h/versions/` 下的 `MANIFEST.sha256`、`.sha256` 及名称含 checksum 的文件。冻结归档清单按所在版本包解析；包内含 `CMakeLists.txt` 的嵌套仓库清单以该仓库根为相对根。哈希文件中的绝对路径按其记录直接检查。

通过 **1018** 条；失败 **704** 条；无法识别 **0** 条。

| 校验文件 | 通过 | 失败 | 跳过 |
|---|---:|---:|---:|
| `bench/8454h/versions/v1/MANIFEST.sha256` | 33 | 0 | 0 |
| `bench/8454h/versions/v2/MANIFEST.sha256` | 33 | 0 | 0 |
| `bench/8454h/versions/v2_release/MANIFEST.sha256` | 69 | 0 | 0 |
| `bench/8454h/versions/v2_release/repo/bench/8454h/mkl_production/source_hashes_pre_run.sha256` | 11 | 0 | 0 |
| `bench/8454h/versions/v2_release/repo/bench/8454h/versions/v2/MANIFEST.sha256` | 25 | 8 | 0 |
| `bench/8454h/versions/v3_paper_release/MANIFEST.sha256` | 447 | 0 | 0 |
| `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` | 10 | 299 | 0 |
| `bench/8454h/versions/v3_paper_release/v3_release/v3_core_source_hashes.sha256` | 8 | 0 | 0 |
| `bench/8454h/versions/v3_release/MANIFEST.sha256` | 309 | 0 | 0 |
| `bench/8454h/versions/v3_release/repo/bench/8454h/mkl_roofline_v3/source_hashes.sha256` | 11 | 2 | 0 |
| `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2/MANIFEST.sha256` | 21 | 12 | 0 |
| `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` | 0 | 69 | 0 |
| `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/roofline_v4/diagnostic_src/results/20261014T091717Z-3/frozen_v3_final.sha256` | 3 | 0 | 0 |
| `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/roofline_v4/diagnostic_src/results/20261014T091717Z-3/frozen_v3_initial.sha256` | 3 | 0 | 0 |
| `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/roofline_v4/diagnostic_src/results/20261014T091717Z-3/initial_source_and_freeze.sha256` | 5 | 1 | 0 |
| `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/roofline_v4/diagnostic_src/results/20261014T091717Z-3/mode0_control.sha256` | 2 | 1 | 0 |
| `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/roofline_v4/diagnostic_src/results/20261014T091717Z-3/mode1_diagnostic_plain_nf.sha256` | 2 | 1 | 0 |
| `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/roofline_v4/diagnostic_src/results/20261014T091717Z-3/mode2_diagnostic_no_reconstruction.sha256` | 2 | 1 | 0 |
| `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/roofline_v4/diagnostic_src/results/20261014T091717Z-3/mode3_candidate_late32_unvalidated.sha256` | 2 | 1 | 0 |
| `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/roofline_v4/diagnostic_src/results/20261014T091717Z-3/source_and_freeze.sha256` | 7 | 1 | 0 |
| `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` | 1 | 308 | 0 |
| `bench/diagnostics/alt_256/checksums.sha256` | 9 | 0 | 0 |
| `bench/diagnostics/signed_shift_256/checksums.sha256` | 5 | 0 | 0 |

### 失配和缺失条目

- `bench/8454h/versions/v2_release/repo/bench/8454h/versions/v2/MANIFEST.sha256` 第 1 行 `./CMakeLists.txt`：哈希不匹配，期望 `3a2acbf7b6d340f96543fc1d267a968ace33e2d89d1476657eedf4b67c1039e0`，实际 `38fe0d708528f348aa7449c5933bbbdf1fe2c363e03bda16a0c7caa0aa0ee366`。
- `bench/8454h/versions/v2_release/repo/bench/8454h/versions/v2/MANIFEST.sha256` 第 2 行 `./README.md`：目标文件不存在，期望哈希 `36b06f6a32bd34457233a31737dc0bdf887a0363585a6fbe285c066a10218527`。
- `bench/8454h/versions/v2_release/repo/bench/8454h/versions/v2/MANIFEST.sha256` 第 4 行 `./bench/8454h/before/include/ozamx/gemm.hpp`：目标文件不存在，期望哈希 `0a7143bb72a3450e955bcdbb7302068cb10ca45ec5c9b519917a12315d2f499a`。
- `bench/8454h/versions/v2_release/repo/bench/8454h/versions/v2/MANIFEST.sha256` 第 5 行 `./bench/8454h/before/src/gemm.cpp`：目标文件不存在，期望哈希 `97257f881d9cccda88cc1918bf874b8c124fbd1c4e7e119ccb12b1849ca51ad0`。
- `bench/8454h/versions/v2_release/repo/bench/8454h/versions/v2/MANIFEST.sha256` 第 6 行 `./bench/8454h/before/src/runtime.cpp`：目标文件不存在，期望哈希 `be1d2bfc44f179febfbea54bcf5807bbee8aaea7c7539a51e7038a8cc3854474`。
- `bench/8454h/versions/v2_release/repo/bench/8454h/versions/v2/MANIFEST.sha256` 第 7 行 `./bench/8454h/bounded_commit_candidate_summary.json`：目标文件不存在，期望哈希 `8d87b060096df1e22932af519a101772e1606cc5a6fecdcea4affa65271a4f02`。
- `bench/8454h/versions/v2_release/repo/bench/8454h/versions/v2/MANIFEST.sha256` 第 13 行 `./bench/run_extended_validation.sh`：哈希不匹配，期望 `9a13a1c8508d788127f51c82479c0253f42b0a580eb33926c3605b3720687525`，实际 `871c2fb66f4e1d61522f91c1a3f60c1d718c825cb7e1032a978a4f9efc3387bb`。
- `bench/8454h/versions/v2_release/repo/bench/8454h/versions/v2/MANIFEST.sha256` 第 15 行 `./docs/8454H_PERFORMANCE_BASELINE.md`：哈希不匹配，期望 `a9798916338692a7ed81f23df6ece0eaad78fc505d8fe6a8630bd3324507b0ea`，实际 `f80105be8e5edd3e1fb2e8c595578ad4c9d5ed45777d6ff700114d56864170eb`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 4 行 `repo/README.md`：目标文件不存在，期望哈希 `dc59b71c44c58c9adce4aaef00ae7ada05134f765042e737534e1d92fd50a5ed`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 5 行 `repo/bench/8454h/create_v3_release_archive.py`：目标文件不存在，期望哈希 `b9a63235bc3555bb00774b5ecd10d820c85c033ec949b4dbc6301f051ea8a4b6`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 6 行 `repo/bench/8454h/equivalence_driver.cpp`：目标文件不存在，期望哈希 `5862298e4001805452e039e5d4b46d2985874f3d8318b841ed6d9d105dbd21af`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 7 行 `repo/bench/8454h/mkl_roofline_v3/README.md`：目标文件不存在，期望哈希 `fd8327a6889d1e9efbcd93e4aa2e462a6570a0ada1530e83a68449d32ad4457e`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 8 行 `repo/bench/8454h/mkl_roofline_v3/benchmark_roofline_v3.cpp`：目标文件不存在，期望哈希 `1ff045bd32a5f77686ce27e5d8bb1406b5887b43ed1158c25653dcf13c80a5c6`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 9 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp32.1024.6.json`：目标文件不存在，期望哈希 `d34f2b0398ae7ef67a3cb7add0fb9611b879ce46bd719cb77ae723cc56b5fed9`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 10 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp32.256.6.json`：目标文件不存在，期望哈希 `8202377fcac204d46134b4e4bc1ba6b511c768af6664b8c2b713d474a71d89e2`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 11 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp32.4096.6.json`：目标文件不存在，期望哈希 `4038ea8001a6504eff03097c3008fdaa0fa6e8ed703c154c1ff2012e276b541e`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 12 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp32.8192.6.json`：目标文件不存在，期望哈希 `951e8c26075a89ae2c24b871ba78e95a49ff6ab5402cf407122c100a04c2f3a9`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 13 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.1024.10.json`：目标文件不存在，期望哈希 `70555bd75296623a33cc7306080408fb2f04b6a680a3363f760c6af33e2bf38d`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 14 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.1024.15.json`：目标文件不存在，期望哈希 `9e46f122608f7316d9bfe0e4c478230a9060a5c76c4b86e3bd4bcb568aa2e149`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 15 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.1024.21.json`：目标文件不存在，期望哈希 `357c91fdffb4aee58059696213f430f1a07cf58624211411b883960204452bde`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 16 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.1024.6.json`：目标文件不存在，期望哈希 `4ad84a6699f9c0147591e47edc3b3d7f386b8dafda06cbd12bc16941ea5a944b`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 17 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.256.10.json`：目标文件不存在，期望哈希 `3221f06752925d4a801c49332bee6bbb8914f4d8bc9916096e1a803de130df68`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 18 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.256.15.json`：目标文件不存在，期望哈希 `32048b15bfc5044df8aed68f3c356c2bf456835ff1321fe4d2fa879b691cc317`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 19 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.256.21.json`：目标文件不存在，期望哈希 `1a6511ab8e62f0419186ed2d49aba938eb610cf4be63ad23ec8e131016a97248`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 20 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.256.6.json`：目标文件不存在，期望哈希 `3f204742123fed3398077c23596638cd1abc6c9701b22a9b894786df1d6f2e82`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 21 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.4096.10.json`：目标文件不存在，期望哈希 `217cbbd6c1bc57cb65e2b8260ed5d712a4d9bc3beff7f24a9147932bd95518da`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 22 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.4096.15.json`：目标文件不存在，期望哈希 `e3186ef94f358018c783cfa53dd9df86e9b256a3487839300c1e5edbd5eb204f`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 23 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.4096.21.json`：目标文件不存在，期望哈希 `cc9e551e3e52703390d6c8d42afb7a2f79c514496a65c796c22ce35cdc600fc5`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 24 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.4096.6.json`：目标文件不存在，期望哈希 `5f8ce5f41adefe83282bbafbc70eff2960cd7528183f6f1664801ea01daf8d30`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 25 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.8192.10.json`：目标文件不存在，期望哈希 `873da1c88cec613f705d477134abf9f28d832140ff0ca3835f3a381473a1c7a6`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 26 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.8192.15.json`：目标文件不存在，期望哈希 `e2ef1e80254219d9d3e974840bf7e4e6980388ad90da3cec83b1523980a7494e`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 27 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.8192.21.json`：目标文件不存在，期望哈希 `70df23c921f01cfab322f83459392fc0205b9b1c0e3969415bd37e8739788fd2`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 28 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.8192.6.json`：目标文件不存在，期望哈希 `e554badc3ca7eb2126fac317f17059e8b4bf548590816c96cb353960200bd7b7`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 29 行 `repo/bench/8454h/mkl_roofline_v3/full_roofline_v3.csv`：目标文件不存在，期望哈希 `879045eead247c7dc7a88c9dddf9b854df048556e333a35e4265b031368b189f`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 30 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/README.md`：目标文件不存在，期望哈希 `bd1144274ba071c804c1eef72a271b32b4e9d348dff35097732d21f67ea56de9`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 31 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/analyze.py`：目标文件不存在，期望哈希 `25ed5f63c4e4df6b1c4a3296bf6d868c0d89b8966d77ad9abb716cbaceea03c8`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 32 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/comparison.json`：目标文件不存在，期望哈希 `d98fcb6fdbe391bd910faeac88f76cdfb5c14832de03900447af81583e39fcc8`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 33 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/benchmark_matched_recheck.cpp`：目标文件不存在，期望哈希 `acba662311017ec85360f1c9aafad6a0d9928911db9706bdb7cb3cc2c1d087bc`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 34 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/checkpoint_p1_v2a.fp32.1024.6.json`：目标文件不存在，期望哈希 `1a10636646a6918e475966fb52656220b189e521d4f87fdf46e71894afda2bc3`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 35 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/checkpoint_p1_v2a.fp32.2048.6.json`：目标文件不存在，期望哈希 `381f765531613c164dcd82316c6b9f5138f18dde71ccf4474262c6d899279d5d`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 36 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/checkpoint_p1_v2a.fp32.8192.6.json`：目标文件不存在，期望哈希 `d9947e975bab75ab9737f211f71b1fb9691c3f3af10b4d1ffbf36f701e588ab5`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 37 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/checkpoint_p1_v2a.fp64.1024.10.json`：目标文件不存在，期望哈希 `beae2d49968722db03a9a0cd07ae7d838863faa71ed816cc6d611742ae31adb6`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 38 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/checkpoint_p1_v2a.fp64.1024.15.json`：目标文件不存在，期望哈希 `894242e60db68c29aed5e94b15cb75a58fbd8a899049628a0e21610ed2fbb66a`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 39 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/checkpoint_p1_v2a.fp64.1024.21.json`：目标文件不存在，期望哈希 `ee9c2e0ab4ffe304fb3c4cfee306e01c16e9cc9fd6f52ff57f485372d85f4278`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 40 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/checkpoint_p1_v2a.fp64.1024.6.json`：目标文件不存在，期望哈希 `bc860973bedea53dc55f35bb11ac0903cb1cde7e98a4f8862551adfa43f8a812`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 41 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/checkpoint_p1_v2a.fp64.2048.10.json`：目标文件不存在，期望哈希 `b7a78be145f9a135e1c652f940a0f01271e3ffd5d1c242ec4469b01bd4dadc10`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 42 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/checkpoint_p1_v2a.fp64.2048.15.json`：目标文件不存在，期望哈希 `dd7b0c1e60070d9e83f3deffccbdcdd553b2255ebaf766967c2e72bebb5a1312`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 43 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/checkpoint_p1_v2a.fp64.2048.21.json`：目标文件不存在，期望哈希 `77a2f74a0a0bde80c8905553717dd51baa2e05ec84ee48eec4fd4b18f9a1e765`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 44 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/checkpoint_p1_v2a.fp64.2048.6.json`：目标文件不存在，期望哈希 `cbad506272845b041d221d56dbcb845ed575af8a415023d30a60e073fb62aea3`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 45 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/checkpoint_p1_v2a.fp64.8192.10.json`：目标文件不存在，期望哈希 `721b951cec3bc77381a8a1a28a58cfc4efdd116e32cc6bee83732570362db587`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 46 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/checkpoint_p1_v2a.fp64.8192.15.json`：目标文件不存在，期望哈希 `bf94917dcabe0a67d1f001a7ef3a6b6735995a32afb1ce80f80b7561d608f52f`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 47 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/checkpoint_p1_v2a.fp64.8192.21.json`：目标文件不存在，期望哈希 `54ae5b83c9f3d63e6bfaab310c5336f684f2dd7b0c6635be79a20097f57fe1dd`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 48 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/checkpoint_p1_v2a.fp64.8192.6.json`：目标文件不存在，期望哈希 `975983570317172ddb00fb6423c48aa0b49e3e4c64658ff289dc3ed780c4f131`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 49 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/full.csv`：目标文件不存在，期望哈希 `e43d083d3766c060e3e5231283177252d08d5df2860811aa444007ff412aee78`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 50 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/provenance.json`：目标文件不存在，期望哈希 `2ac1ffa7b8231e07902135269b718d03acfa7d40eb2656f7821f9f1d0ebf4d3f`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 51 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/benchmark_matched_recheck.cpp`：目标文件不存在，期望哈希 `1e36782212405cf1b439609147acae4207a9763436628f0cf01162bedc43acc4`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 52 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/checkpoint_p2_v3a.fp32.1024.6.json`：目标文件不存在，期望哈希 `30328fd628dfe2d51823ebddbf9b5e05f9c3d128abb758c2b75289cb749410bb`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 53 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/checkpoint_p2_v3a.fp32.2048.6.json`：目标文件不存在，期望哈希 `f3374ac83028c61328ac4ed8f55a4d26aac64ad781494bf80fa638fb1c04bf18`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 54 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/checkpoint_p2_v3a.fp32.8192.6.json`：目标文件不存在，期望哈希 `2109774b4f5747c140460820eafd9e559fd2ba6aa3594823fd52d1839d1d9cd9`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 55 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/checkpoint_p2_v3a.fp64.1024.10.json`：目标文件不存在，期望哈希 `25e0f5cf46152d031003009b88b96a1743e45e3e435674faa1a8a5cf0d992e80`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 56 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/checkpoint_p2_v3a.fp64.1024.15.json`：目标文件不存在，期望哈希 `7271ccb6f1c859f1ad71ffa0de6021e9238bf26b0b6fd8d9880cc6f108094f7f`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 57 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/checkpoint_p2_v3a.fp64.1024.21.json`：目标文件不存在，期望哈希 `990b268c1bb0058d0c34f2fa67354a62042fee0e306b0618ad8f3a3632568e97`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 58 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/checkpoint_p2_v3a.fp64.1024.6.json`：目标文件不存在，期望哈希 `2b1765a647458f5a4f79a9ca2e936abcd1a2d7fc1669524f5959629785662740`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 59 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/checkpoint_p2_v3a.fp64.2048.10.json`：目标文件不存在，期望哈希 `c0c06cf6f935a37b51542cc1d4fa5bfb0bd069e2fe0eefbf9cb1f7e04a83bc8f`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 60 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/checkpoint_p2_v3a.fp64.2048.15.json`：目标文件不存在，期望哈希 `13a2a5f3adac1dafe2687ff3509543e5465758e2a88ea0d3db2956945bfd6190`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 61 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/checkpoint_p2_v3a.fp64.2048.21.json`：目标文件不存在，期望哈希 `25f31d70ba8b7f77110f50f916e0adfba11c7e961c28f3c5fdaacc05ad783ab2`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 62 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/checkpoint_p2_v3a.fp64.2048.6.json`：目标文件不存在，期望哈希 `7f0665f21f5a0ff69a4182b682aecc97957c448dba6d9e3192753c6e8504c51f`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 63 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/checkpoint_p2_v3a.fp64.8192.10.json`：目标文件不存在，期望哈希 `259a8703010974431d4f4a153841b6d3c2f6d7a3622224a8d3cb2913c397884d`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 64 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/checkpoint_p2_v3a.fp64.8192.15.json`：目标文件不存在，期望哈希 `68c02d39f7624941ead61317bebc0feb7299fb5fd80f82b82d5585d539bb8345`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 65 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/checkpoint_p2_v3a.fp64.8192.21.json`：目标文件不存在，期望哈希 `034c9261b27e3bcd6575b1870e937b6e49e2a49e999340a72beb0384759db093`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 66 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/checkpoint_p2_v3a.fp64.8192.6.json`：目标文件不存在，期望哈希 `d2807829f75f4ce0694c4e83038c5f0927034e16498630e8424c344f7728bde3`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 67 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/full.csv`：目标文件不存在，期望哈希 `48884d97a60523b10a3f430880f5e4f26ee9a9fd762c067bbbb606d0482ebac1`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 68 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/provenance.json`：目标文件不存在，期望哈希 `4a5e89da3944da670f001b23394c6591bd83b0f68818b0103a612542e0f10a12`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 69 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/benchmark_matched_recheck.cpp`：目标文件不存在，期望哈希 `6f4130fe02e3e34a5aa388b3dcfa91d42d90c0662b975106c38c8e466600fd2f`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 70 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/checkpoint_p3_v2b.fp32.1024.6.json`：目标文件不存在，期望哈希 `265836b7d1844e8a01583ea6cfe3997f8ae2d4d93545c89e1bd2a201834094a1`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 71 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/checkpoint_p3_v2b.fp32.2048.6.json`：目标文件不存在，期望哈希 `78fe25c73e2947fae89d654ed0983f8825a7a5b5ea0e7f82221d3229445a70a4`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 72 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/checkpoint_p3_v2b.fp32.8192.6.json`：目标文件不存在，期望哈希 `8def5eefdbbcd313604ebc76194b454660836128e746d5313282ca26f2bab855`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 73 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/checkpoint_p3_v2b.fp64.1024.10.json`：目标文件不存在，期望哈希 `02e713e92746512606ae92d0dfb7e24de50a8d765c4699867a51ede973e7b523`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 74 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/checkpoint_p3_v2b.fp64.1024.15.json`：目标文件不存在，期望哈希 `1c7b4a8a0b235aed9c27b2e12d312c40e9f6a87991df54682265a9240d990633`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 75 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/checkpoint_p3_v2b.fp64.1024.21.json`：目标文件不存在，期望哈希 `7ea05d2349f83654adbcebc90525c2b208d5e4b6d7d351c379ca2d46a814db96`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 76 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/checkpoint_p3_v2b.fp64.1024.6.json`：目标文件不存在，期望哈希 `13741833af200af82e487002e3a1af3a4d6afac8421b49ab8baf20dfd01c9488`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 77 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/checkpoint_p3_v2b.fp64.2048.10.json`：目标文件不存在，期望哈希 `6ee7140908776151c46a9cea69484ee9f55a44b1c04fbab8ee4538770a7f3b4b`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 78 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/checkpoint_p3_v2b.fp64.2048.15.json`：目标文件不存在，期望哈希 `bea3bb5cf66f62d5cbe3197766fbf478a95c5ebb2c5af335ee123e938f9ae62c`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 79 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/checkpoint_p3_v2b.fp64.2048.21.json`：目标文件不存在，期望哈希 `99d4a5857b8d9bc44e100f5c0d2c95616206e7d4f0c2c5f42101a31bdb18c15d`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 80 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/checkpoint_p3_v2b.fp64.2048.6.json`：目标文件不存在，期望哈希 `decf6a2e3824181b0b6f6c0455828762f2aface20d56968aef2ac6a09962a7f6`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 81 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/checkpoint_p3_v2b.fp64.8192.10.json`：目标文件不存在，期望哈希 `2d881a16c7c8df5a4f85d5f26706e0f9e82d4f287bcb7814f4b8fe28e2bcf23a`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 82 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/checkpoint_p3_v2b.fp64.8192.15.json`：目标文件不存在，期望哈希 `8c190405714492a604de3e8d5a33e45e7264e6df79146f59a453ed9a4958fdc2`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 83 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/checkpoint_p3_v2b.fp64.8192.21.json`：目标文件不存在，期望哈希 `7ee211069a3f6a89fa84878584f30ee38fcb367dda8937494221037b732749c0`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 84 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/checkpoint_p3_v2b.fp64.8192.6.json`：目标文件不存在，期望哈希 `0b72e12663150d29d47bc4bac0eb40a63e0408b7c4296d8a87ce6337fe23c36f`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 85 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/full.csv`：目标文件不存在，期望哈希 `b079cc998e6715b1bc350efe845e405f74aab9d21f3a52478012332c5111dd18`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 86 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/provenance.json`：目标文件不存在，期望哈希 `660046e29ebb55cdf162ce5c6c125a852341cd9eda2f19c38b4bacc431857c51`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 87 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/benchmark_matched_recheck.cpp`：目标文件不存在，期望哈希 `97fef9ecfeb3219049a0fff858c837c00d2e72fbda4f039bb796ab531a86ad20`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 88 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/checkpoint_p4_v3b.fp32.1024.6.json`：目标文件不存在，期望哈希 `d7b244365d472c6c87a4b38175ea01dcd8061f8d26fe82565a3dc23d53fd5b17`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 89 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/checkpoint_p4_v3b.fp32.2048.6.json`：目标文件不存在，期望哈希 `e131a803b9b7ac7cf9623838017764ae0b5a11bf611955e1826865a458208571`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 90 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/checkpoint_p4_v3b.fp32.8192.6.json`：目标文件不存在，期望哈希 `7aa7f536151ca9a974679c1d0d9dd9fcfe1c575398e984af8f578130b6c39edd`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 91 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/checkpoint_p4_v3b.fp64.1024.10.json`：目标文件不存在，期望哈希 `5e346431497b06b6a111691c6f910b63d3aebf20112d17499ab42ce96479bd6e`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 92 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/checkpoint_p4_v3b.fp64.1024.15.json`：目标文件不存在，期望哈希 `087839c5ae3dcefed60b52d6c21473f2b6988a3a17d3dc053c7c99d5588ecba9`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 93 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/checkpoint_p4_v3b.fp64.1024.21.json`：目标文件不存在，期望哈希 `04b021a45f7d23dad081e2f702c2443c5d46e85615f88d79b6c673f4299de936`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 94 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/checkpoint_p4_v3b.fp64.1024.6.json`：目标文件不存在，期望哈希 `9b825ef87368111816fbf0a114084709c4040d0603661a4c767227ebbec4e6cb`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 95 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/checkpoint_p4_v3b.fp64.2048.10.json`：目标文件不存在，期望哈希 `269ea1146aa9fdefa536bf3d2473610f4fa1478ace8ea67885b05c8919aabc67`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 96 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/checkpoint_p4_v3b.fp64.2048.15.json`：目标文件不存在，期望哈希 `ae93909d2a2defa1c746505655c53011237e71b0b31241a8b5dc7ebcbd445423`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 97 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/checkpoint_p4_v3b.fp64.2048.21.json`：目标文件不存在，期望哈希 `2fd4d2dbde159e24608aaf77a1b70f765a10131e8189b5d85daa661621d9cc5e`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 98 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/checkpoint_p4_v3b.fp64.2048.6.json`：目标文件不存在，期望哈希 `638894711871799e612e9c19a61dd0bb275f6e90c5b6ad1567dc602af1ddca44`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 99 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/checkpoint_p4_v3b.fp64.8192.10.json`：目标文件不存在，期望哈希 `a6ed93ab7bb4b7ec850cf9f3d9aa26ebedcb3cbc689f1d05e3b6d6f9f467e269`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 100 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/checkpoint_p4_v3b.fp64.8192.15.json`：目标文件不存在，期望哈希 `213d738d3ee43739da34eaf6335235c5b56ec6b80c3ae92361cadaa26016eb07`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 101 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/checkpoint_p4_v3b.fp64.8192.21.json`：目标文件不存在，期望哈希 `de41adcd75347dd25b2d0c6360a39c30136e9159a8b4623ec120775663b68c0c`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 102 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/checkpoint_p4_v3b.fp64.8192.6.json`：目标文件不存在，期望哈希 `c48f069a216ca44649fea8410d9e9d118a47ee75aeae24d40d0557856fc8fd82`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 103 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/full.csv`：目标文件不存在，期望哈希 `6556fce1b8e0ccc0d4213d63e057f6bf97986d9464278b0d4f3c0086f5ca6933`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 104 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/provenance.json`：目标文件不存在，期望哈希 `9eae6dfc114b419a914f7356373bfef7dda8e74a743a8bfad3a40905bb62f63e`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 105 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/benchmark_matched_recheck.cpp`：目标文件不存在，期望哈希 `ba10fe53f80b484f7ca3188c41a38c112fb78e99af50fd589036ef359bf030e8`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 106 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/checkpoint_p5_v2c.fp32.1024.6.json`：目标文件不存在，期望哈希 `7ad5e82149caf5506f5d8f418aa83e697fbc836570c5c7c26118fe52e9dd2f50`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 107 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/checkpoint_p5_v2c.fp32.2048.6.json`：目标文件不存在，期望哈希 `9b53be40cc79d3bef322ff2362bfb926a52a82e363ba3a1285a792415f1d7f02`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 108 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/checkpoint_p5_v2c.fp32.8192.6.json`：目标文件不存在，期望哈希 `c3e34b41cceda350d2034740debc817dfac552cf30af71b8ac0dd1b98de66af1`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 109 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/checkpoint_p5_v2c.fp64.1024.10.json`：目标文件不存在，期望哈希 `5b0aacbf2c4d73ccf67c079518f4c09cee720f980902406b18cdfaa6e19b64f5`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 110 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/checkpoint_p5_v2c.fp64.1024.15.json`：目标文件不存在，期望哈希 `b3af47b9abb26c47a67531c44c1a144aa0ee29530693b0c3073ec988b1d5cdb0`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 111 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/checkpoint_p5_v2c.fp64.1024.21.json`：目标文件不存在，期望哈希 `1da8ca6786b1e67f73de2630607690dd165303cdd179df432fc0bd9bd7cdf9f2`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 112 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/checkpoint_p5_v2c.fp64.1024.6.json`：目标文件不存在，期望哈希 `4e91ce722c5259c76e45013b0909b53c1c1bf68198d23be617afb92ce0f6039e`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 113 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/checkpoint_p5_v2c.fp64.2048.10.json`：目标文件不存在，期望哈希 `6515e9666c4c09a2a6b7e56e2620c4a81a765a34a80832b96c700dfaa56676fa`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 114 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/checkpoint_p5_v2c.fp64.2048.15.json`：目标文件不存在，期望哈希 `78fa6bf1588343eafecb4089428f138c5e5a070744016ef7808b5312d91546a3`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 115 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/checkpoint_p5_v2c.fp64.2048.21.json`：目标文件不存在，期望哈希 `4b914f4e4e6d988b775b044cec94829e9df5ca1eb2c0f59bc518c455fc8e4e84`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 116 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/checkpoint_p5_v2c.fp64.2048.6.json`：目标文件不存在，期望哈希 `5f3fca51b44ea0281ff8ffacd69a37ab8b87f8118af74aa29b230ca54b7181c3`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 117 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/checkpoint_p5_v2c.fp64.8192.10.json`：目标文件不存在，期望哈希 `77a0810b6c1d83a0dec24deefd40f2c214af62e00ceb66e5a6a1b642a3939404`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 118 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/checkpoint_p5_v2c.fp64.8192.15.json`：目标文件不存在，期望哈希 `e72e94e4e8ecd7c13c0b0930a10c88030a2179b89d6773bc1371c69202995285`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 119 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/checkpoint_p5_v2c.fp64.8192.21.json`：目标文件不存在，期望哈希 `650f3627340fb1448bf4584862dd3b62d36a853711997e1f11507b95a15d2305`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 120 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/checkpoint_p5_v2c.fp64.8192.6.json`：目标文件不存在，期望哈希 `6e5c7608cc9f7882aac8e0d5ee1c35c5471407372dc1af2c11d9c30de0f15fb1`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 121 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/full.csv`：目标文件不存在，期望哈希 `9ea9448a8e4e0ba3a1537fc692192c57b61694769df3baa96cb3c52c717f1b0e`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 122 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/provenance.json`：目标文件不存在，期望哈希 `d1b259bd9257040f5174943ccb818daa7ce19782ccaf89790c54d9d38d8d3f81`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 123 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/run_matched_recheck.sh`：目标文件不存在，期望哈希 `e0b5bb6ada2ca334b79dd54d434e993328ca1841cb71d228337bc2cf149eaee7`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 124 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/write_provenance.py`：目标文件不存在，期望哈希 `5368a0777d3a21bf42bdff6095a2e1d8ec51e711b003c9983b4d04ae9038254e`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 125 行 `repo/bench/8454h/mkl_roofline_v3/provenance.json`：目标文件不存在，期望哈希 `7124790f87fb8925946e7b3a5abfb31b06f6a4a58df1224c9518528871119f70`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 126 行 `repo/bench/8454h/mkl_roofline_v3/run.sh`：目标文件不存在，期望哈希 `d5c1810d0cb912e9c779877751e9ec6a22457a0268a0d4edeccf9288a269821d`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 127 行 `repo/bench/8454h/mkl_roofline_v3/run_command.txt`：目标文件不存在，期望哈希 `6b0f6b2b179fe6d1fda355df3c7eae20101aa55f267b9da83e338e18075b2b0e`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 128 行 `repo/bench/8454h/mkl_roofline_v3/source_hashes.sha256`：目标文件不存在，期望哈希 `3a6fa7435aae952905b9df5470ae8b4182d77266fcc5ec32271b847593a7894b`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 129 行 `repo/bench/8454h/roofline/binary_gate.json`：目标文件不存在，期望哈希 `78c9f28cf1b8e945f06198c220cc2fbe613ad983592bdca48c6aa8c4e64e8345`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 130 行 `repo/bench/8454h/roofline/binary_gate_attempt1.json`：目标文件不存在，期望哈希 `7ebb5f00553ebf051ace74d9e5b990048af0403b6f08c0635702d46dfc933dd9`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 131 行 `repo/bench/8454h/roofline/calibration/kernel_disassembly.txt`：目标文件不存在，期望哈希 `70150b8a81e855d2e4e4d85188c2405a1471a0e65654805bb31f48da7a22f1db`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 132 行 `repo/bench/8454h/roofline/calibration/kernel_metadata.json`：目标文件不存在，期望哈希 `31b78b215ca5c1403b3338117dd8b13d79feed6b7ca695c483d5368a752fc79b`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 133 行 `repo/bench/8454h/roofline/calibration/kernel_summary.json`：目标文件不存在，期望哈希 `abc759689293fcb676f2e7e518233f5c028126875acdade482890e8d637eb687`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 134 行 `repo/bench/8454h/roofline/calibration/kernels.csv`：目标文件不存在，期望哈希 `2ab37da6f56bdbbc2459f5788ce379c868b4fc0c1c9ff29db50ccacb7a105179`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 135 行 `repo/bench/8454h/roofline/calibration/summarize_kernels.py`：目标文件不存在，期望哈希 `7cfb1d7c3fb43b123b61a715375c154c965bb759992b6936900ce6d29fb0bdb0`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 136 行 `repo/bench/8454h/roofline/extended47_cache_gate.json`：目标文件不存在，期望哈希 `bb9445c58410c50dd5438eace8a3e9803b6ac25e05bd13cce83de79c7f998d5b`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 137 行 `repo/bench/8454h/roofline/ideas/adaptive_block.patch`：目标文件不存在，期望哈希 `83a3a0a2aa8e47cfd450bc0d439df3065d3980ec7816c5e17359eb7dc0214c7f`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 138 行 `repo/bench/8454h/roofline/ideas/batch64.md`：目标文件不存在，期望哈希 `3979767c784308d39bd15a73777565afc790bbacf8c12c1512c1daa3a0b9dc08`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 139 行 `repo/bench/8454h/roofline/ideas/batch64.patch`：目标文件不存在，期望哈希 `603e7ea15d12e63df2d42ef6419a6c60db4804c2cb1adb2fbc3849db488e7b66`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 140 行 `repo/bench/8454h/roofline/ideas/hugepages.patch`：目标文件不存在，期望哈希 `c15bce4bda003a892c3457d91d140275d62300415f8e729a6106958fe30ef0eb`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 141 行 `repo/bench/8454h/roofline/ideas/numa_b.md`：目标文件不存在，期望哈希 `56736fe967d698aaa3a966de7b5a35da02f675d120964498a4579d45b08d0ae0`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 142 行 `repo/bench/8454h/roofline/ideas/numa_b.patch`：目标文件不存在，期望哈希 `3e3b8154f1385fa41bb8e379d15ca5f7bd3ae76b3e14fc4af84e633d82e9df0b`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 143 行 `repo/bench/8454h/roofline/ideas/numa_b_gate.json`：目标文件不存在，期望哈希 `7726c9853e00ba16bbcf6ab9c6e0dcdf4198ff57bdbbeb1ea35ed24d90a4334d`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 144 行 `repo/bench/8454h/roofline/ideas/numa_b_gate.sh`：目标文件不存在，期望哈希 `0b32fda13e546740fba0e79cc3bf1479e9c35b86c35e9c2cc01f9aa758672948`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 145 行 `repo/bench/8454h/roofline/ideas/numa_b_metadata.json`：目标文件不存在，期望哈希 `8496ca66f17e2ecb058743f81ad4963876294d516ab91a6b3b84abf08b1a9ef9`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 146 行 `repo/bench/8454h/roofline/ideas/numa_b_trigger_probe.json`：目标文件不存在，期望哈希 `ae10e06206e8eb15266bae04b4b19628b523c232269df7f8b899f13d9066e44f`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 147 行 `repo/bench/8454h/roofline/ideas/numa_partial_b.patch`：目标文件不存在，期望哈希 `a5bf451dbbc7cf6f236fed8d97427e933e7972992d5524fb13a5611ac69858ea`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 148 行 `repo/bench/8454h/roofline/ideas/pad_batch.patch`：目标文件不存在，期望哈希 `67207dd94c7559ea7e41719141c58001798147f4628084f76eb7e117d9088ca2`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 149 行 `repo/bench/8454h/roofline/ideas/rectangular_block.patch`：目标文件不存在，期望哈希 `8322207d9c5306a2fb0a8a193328cfb2339d100d6add2efd8b2ca84935e3eba0`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 150 行 `repo/bench/8454h/roofline/memory_calibration_20261013.csv`：目标文件不存在，期望哈希 `e5182d431eb28467f3ab9d457a45fce71298b2e3562d5f378dbf5466bae4f402`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 151 行 `repo/bench/8454h/roofline/memory_calibration_20261013.disasm.txt`：目标文件不存在，期望哈希 `777f2ea70a2eeeca347d0ef7923fe79a43a567fdca15a3340699609ce3e5430f`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 152 行 `repo/bench/8454h/roofline/memory_calibration_20261013.json`：目标文件不存在，期望哈希 `cd855a2fbbd3053e11ae6b56b1673ea195cd421d6b53272df0222b40cf692f33`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 153 行 `repo/bench/8454h/roofline/noomp_build/build_manifest.json`：目标文件不存在，期望哈希 `c9524b1851933544c11e8057acf67cf09b66d621358a34f2b65f1afaa4f4f012`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 154 行 `repo/bench/8454h/roofline/noomp_build/ctest.log`：目标文件不存在，期望哈希 `9ce6248af3c06c71e70fa9e3b71b3b2b80a1d3daf6b51f02cb6fa0bdeee84755`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 155 行 `repo/bench/8454h/roofline/noomp_gate.json`：目标文件不存在，期望哈希 `3ff76f03d9407bd397c5f4c969a6eced302cc6e92cda560e0436c14130aa398c`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 156 行 `repo/bench/8454h/roofline/production_native_audit.json`：目标文件不存在，期望哈希 `0ae8608c76719e771049111ac49247efa34714cceed850d63543d40a39e3b2a6`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 157 行 `repo/bench/8454h/roofline/production_validation.json`：目标文件不存在，期望哈希 `b787f4ac421c31ec87d79fb9741aee40a89f518ffc435deef2317c28d67eaceb`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 158 行 `repo/bench/8454h/roofline/run_binary_gate.py`：目标文件不存在，期望哈希 `491c6b750e984c2f2fcee90d167f890ca0ab53209eecf23a9cb96ef479101dfc`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 159 行 `repo/bench/8454h/roofline/run_extended47_stream.py`：目标文件不存在，期望哈希 `1e6c2fca91210e18cf85ffa955c516cc1a72e26d8bd857feaab5772588bc14d8`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 160 行 `repo/bench/8454h/roofline/run_kernel_calibration.sh`：目标文件不存在，期望哈希 `b774dbb7fb4e663842e1a878eff9cf8a24d80f7b5323aab8cecb52da3b0ef779`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 161 行 `repo/bench/8454h/roofline/run_memory_calibration.sh`：目标文件不存在，期望哈希 `ab13ca6f56c9525e7406ba033d6c4d6c529ae01e8f8d19da360ab34c6159c418`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 162 行 `repo/bench/8454h/roofline/search_adaptive/metadata.json`：目标文件不存在，期望哈希 `733be0ff389843f5ff29aea00c282cbf6eb7e364fd627dcba0a68114740cb953`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 163 行 `repo/bench/8454h/roofline/search_adaptive/pass0_frozen.csv`：目标文件不存在，期望哈希 `3a2889b59beb95bbaa3d9b33012ca5a5583c1e3dd925535b5837fc31b51b915f`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 164 行 `repo/bench/8454h/roofline/search_adaptive/pass1_adaptive.csv`：目标文件不存在，期望哈希 `6db616d269b3336367502ec1b3b5b72c0f15eb4cb0585037ff4cb0ff94532428`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 165 行 `repo/bench/8454h/roofline/search_adaptive/pass2_frozen.csv`：目标文件不存在，期望哈希 `b6757256377951b0bb515fd92122715f594f06925998152f7d0afdca30f0abc2`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 166 行 `repo/bench/8454h/roofline/search_adaptive/pass3_adaptive.csv`：目标文件不存在，期望哈希 `56997f47288b2995c19ab7f0ffc4accb83401331e254ee4732faf669f2622265`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 167 行 `repo/bench/8454h/roofline/search_adaptive/pass4_frozen.csv`：目标文件不存在，期望哈希 `8b4553315c71e52d2d2717df23977fb5a5a30a9508cd6047effdc2c1fa1ca253`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 168 行 `repo/bench/8454h/roofline/search_adaptive/summary.json`：目标文件不存在，期望哈希 `d5c695fe38455f5c6c2e23f4ea9227f18d5ec442c148b7cdc2d2f119680addbe`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 169 行 `repo/bench/8454h/roofline/search_batch64/comparison.json`：目标文件不存在，期望哈希 `e34f53517a5297305bd820c5290fc485f04e36e885d368fd75b299c277c19461`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 170 行 `repo/bench/8454h/roofline/search_batch64/metadata.json`：目标文件不存在，期望哈希 `8faca76f1ac799c0819ad712f04f01ddcfb618266d5a35fae3f652620673180b`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 171 行 `repo/bench/8454h/roofline/search_batch64/run01_frozen_before.csv`：目标文件不存在，期望哈希 `28bb7cf3f1a2865bb2ccf383555426259217bf63fe400c1e7be368a69b5b6939`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 172 行 `repo/bench/8454h/roofline/search_batch64/run02_batch1.csv`：目标文件不存在，期望哈希 `3b82ba68567aeae5b1c0064ec72c21ece7d36e86eaf454fa828636db1301727b`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 173 行 `repo/bench/8454h/roofline/search_batch64/run03_batch2.csv`：目标文件不存在，期望哈希 `3b70af9da6793ea75fa63fba4cc9516299d6e427cdc66dd83e00c0197a05542d`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 174 行 `repo/bench/8454h/roofline/search_batch64/run04_batch4.csv`：目标文件不存在，期望哈希 `ddd97179a0c147d129eaef72711decb6376300bcb220b272f816544dfb72adda`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 175 行 `repo/bench/8454h/roofline/search_batch64/run05_frozen_middle.csv`：目标文件不存在，期望哈希 `4d18bd77cb62ed544c7fdf889c9af912f3ca75d717d595ae6eb5eadab2f96236`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 176 行 `repo/bench/8454h/roofline/search_batch64/run06_batch4_repeat.csv`：目标文件不存在，期望哈希 `7b6fbae4ec46c3d64a3092e4616d00785a1e01d008b0918e5b09bd30741276d8`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 177 行 `repo/bench/8454h/roofline/search_batch64/run07_batch2_repeat.csv`：目标文件不存在，期望哈希 `e56dda422d5e65ba8491dc4ccfdc232903f58dcf1df03a60665919be6ffaaba1`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 178 行 `repo/bench/8454h/roofline/search_batch64/run08_frozen_after.csv`：目标文件不存在，期望哈希 `42cdf51e1bd5e6132fbc23461360c0cb858e12c53fc90a6699bd3eee95c9f990`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 179 行 `repo/bench/8454h/roofline/search_batch64/runner.sh`：目标文件不存在，期望哈希 `81605acd45253fa49ffdfb7bba1885a64119e433af368f53ee6e8b834a24fa05`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 180 行 `repo/bench/8454h/roofline/search_commands.md`：目标文件不存在，期望哈希 `70a35e7ac28d1e9c596d1c06d0550e98ae60ca9b4c107cdec36201b677c34752`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 181 行 `repo/bench/8454h/roofline/search_numa_b/RESULTS.md`：目标文件不存在，期望哈希 `5f4788c56c1bac5f11604dca8b4f7619487014185f6dbfc26fd0f424edc7c036`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 182 行 `repo/bench/8454h/roofline/search_numa_b/analyze.py`：目标文件不存在，期望哈希 `44eb5a62d7b8e2e50f55434e2e624330b4f25d05c4ac0821c97810b06471338b`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 183 行 `repo/bench/8454h/roofline/search_numa_b/comparison.json`：目标文件不存在，期望哈希 `413b420ad3a506ed16777d621e1776b06c21ce241bc5965579b1b0183b90122d`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 184 行 `repo/bench/8454h/roofline/search_numa_b/completed_utc.txt`：目标文件不存在，期望哈希 `97d62b9cb9832708a43a5058082787305446f0264423d2ced8a33b05b2e6ff78`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 185 行 `repo/bench/8454h/roofline/search_numa_b/completion_manifest.json`：目标文件不存在，期望哈希 `51c23da201a79d813a7ae2eca81c1292027af6074a9b1c0cd04895f2eeb9166f`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 186 行 `repo/bench/8454h/roofline/search_numa_b/logs/run_order.log`：目标文件不存在，期望哈希 `098ad505da4639432511cd4560744657a5224977acddc41ddd5edb8ccd0c8652`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 187 行 `repo/bench/8454h/roofline/search_numa_b/raw/control0_4g.csv`：目标文件不存在，期望哈希 `9d01006ec2f57bef77636f61b2519137c784b21de9b59b5386afcaba152cb4ba`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 188 行 `repo/bench/8454h/roofline/search_numa_b/raw/frozen_4g_a.csv`：目标文件不存在，期望哈希 `9fc117134a95ec8a3faced5392b0e625c1f6f51d60a42c7044013a4121811d31`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 189 行 `repo/bench/8454h/roofline/search_numa_b/raw/frozen_4g_b.csv`：目标文件不存在，期望哈希 `505af36b1e1dc4be14c5775108c87fa1dbe6e9b0f90168f6158ce3297d883386`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 190 行 `repo/bench/8454h/roofline/search_numa_b/raw/frozen_4g_c.csv`：目标文件不存在，期望哈希 `b675a15817cbd1f837ee572633aec9fbdb2a4f18bfdf995cdd73cd2e41eca207`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 191 行 `repo/bench/8454h/roofline/search_numa_b/raw/numa1_4g_a.csv`：目标文件不存在，期望哈希 `b58a6ef4b003175b68e50e330ab1a6b43b933be8d0a8dd4fa22f5e02bad12118`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 192 行 `repo/bench/8454h/roofline/search_numa_b/raw/numa1_4g_b.csv`：目标文件不存在，期望哈希 `5529b3fe77c7249cc1ca9a08d6a35d975845c323b7c3bb06a2b0bd3940b53201`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 193 行 `repo/bench/8454h/roofline/search_numa_b/run_manifest.json`：目标文件不存在，期望哈希 `fe7c1398f78cda0109fcfb8517f45f1119126ff8d672668e1e99399aef42280f`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 194 行 `repo/bench/8454h/roofline/search_numa_b/runner.sh`：目标文件不存在，期望哈希 `67a1f6ca0504035bdcf0fa292021e691c35bd5a2695e5dbbfbab63d8e8119a40`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 195 行 `repo/bench/8454h/roofline/search_numa_half/2g/RESULTS.md`：目标文件不存在，期望哈希 `bd23cf4831d06e64e55b26d7749c888eb8fbedadfa3322b01c4967e665f7fbcb`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 196 行 `repo/bench/8454h/roofline/search_numa_half/2g/analyze.py`：目标文件不存在，期望哈希 `23a861f0ed76d805e9a69fcbf29dc0bac930a16a586aeaa91d60463d41462903`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 197 行 `repo/bench/8454h/roofline/search_numa_half/2g/comparison.json`：目标文件不存在，期望哈希 `1db5da952fadf491f862a8a3555cdf03d8e262b186486f6ac0b63f7a5b3be2aa`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 198 行 `repo/bench/8454h/roofline/search_numa_half/2g/completed_utc.txt`：目标文件不存在，期望哈希 `67a9eb865037c0ffbb02c11e2c8fc476ff82e7ebc75c66a82223c78f31274470`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 199 行 `repo/bench/8454h/roofline/search_numa_half/2g/completion_manifest.json`：目标文件不存在，期望哈希 `46565faae7daf515befdb552a4fd386832ef8a968bf1155aa1d85633e4f6d3e8`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 200 行 `repo/bench/8454h/roofline/search_numa_half/2g/logs/run_order.log`：目标文件不存在，期望哈希 `410566801b167bc521c49c91c1366d477deab70d48d00543b65fd2e98b0f247f`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 201 行 `repo/bench/8454h/roofline/search_numa_half/2g/raw/control0_2g.csv`：目标文件不存在，期望哈希 `4ff5d8bec913f19f1c2456d52dabb9b0e2e48f6ff4aa526177ca44baa48f50fd`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 202 行 `repo/bench/8454h/roofline/search_numa_half/2g/raw/frozen_2g_a.csv`：目标文件不存在，期望哈希 `b2dbf4b15754f9aaaebdb3d6354fd10124b6da49cb20a0fdb3e1a5a06e50d5d5`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 203 行 `repo/bench/8454h/roofline/search_numa_half/2g/raw/frozen_2g_b.csv`：目标文件不存在，期望哈希 `e3d2c6872c2340dfa1c8f5cc7c0e4319f0bda12fd2e231323fcc8eee85601436`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 204 行 `repo/bench/8454h/roofline/search_numa_half/2g/raw/frozen_2g_c.csv`：目标文件不存在，期望哈希 `e0f426186b2f624ba20d29d836ea2dd53d6b1b23c00c0294f88613a88085253a`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 205 行 `repo/bench/8454h/roofline/search_numa_half/2g/raw/numa_half_2g_a.csv`：目标文件不存在，期望哈希 `52f35452bd5b5170df5afd84cdb54c41948ad7017474cdb180d93265c9fbe647`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 206 行 `repo/bench/8454h/roofline/search_numa_half/2g/raw/numa_half_2g_b.csv`：目标文件不存在，期望哈希 `69153aeb49546280be8c2fa56d2c4805138c92b0d25939425f1f8222a56ab20a`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 207 行 `repo/bench/8454h/roofline/search_numa_half/2g/run_manifest.json`：目标文件不存在，期望哈希 `766e762a2c5a94b465d244ae4ca318ec9c94395fab09216b996812be78c12086`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 208 行 `repo/bench/8454h/roofline/search_numa_half/2g/runner.sh`：目标文件不存在，期望哈希 `11f046397a0b3998769bf17688090f3f93031f5531ebcc871d4b7d7bbc0f502f`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 209 行 `repo/bench/8454h/roofline/search_numa_half/4g/RESULTS.md`：目标文件不存在，期望哈希 `889fa1bb74a1df9a2c54f55679d9aa5f4045e231f3b90fe70127cb69e12bfa3e`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 210 行 `repo/bench/8454h/roofline/search_numa_half/4g/analyze.py`：目标文件不存在，期望哈希 `23a861f0ed76d805e9a69fcbf29dc0bac930a16a586aeaa91d60463d41462903`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 211 行 `repo/bench/8454h/roofline/search_numa_half/4g/comparison.json`：目标文件不存在，期望哈希 `c6e1fb854545e19f219d902882dc85d5f2cfd8c7b233746faf8bbe038b2daf30`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 212 行 `repo/bench/8454h/roofline/search_numa_half/4g/completed_utc.txt`：目标文件不存在，期望哈希 `7094b7b54b72c1fb38eac7ca8de886add3652a4a365b37a48e4aab434613c925`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 213 行 `repo/bench/8454h/roofline/search_numa_half/4g/completion_manifest.json`：目标文件不存在，期望哈希 `b95597d33fe149f83c51ad451f4f3097b74192e1cc11ee29d6370fe9c983d036`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 214 行 `repo/bench/8454h/roofline/search_numa_half/4g/logs/run_order.log`：目标文件不存在，期望哈希 `c287dc6c4bddb3ad469b0f6754b803f5d54af6d810acdf8df0f9cb302a9c57d0`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 215 行 `repo/bench/8454h/roofline/search_numa_half/4g/raw/control0_4g.csv`：目标文件不存在，期望哈希 `54b4dd67466294ae9166ac59c3b0ed7db870ccd6ea967d89df9d052a704c91a7`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 216 行 `repo/bench/8454h/roofline/search_numa_half/4g/raw/frozen_4g_a.csv`：目标文件不存在，期望哈希 `8f6f3bc8a04f90ddcf3c62437dedf17ddc1bb0668fc63c343f93d28720ba6e3d`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 217 行 `repo/bench/8454h/roofline/search_numa_half/4g/raw/frozen_4g_b.csv`：目标文件不存在，期望哈希 `34aa1aa81c8b11db2b9f6b2ce81a51d63403b4f5941822863270c09a3d67574d`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 218 行 `repo/bench/8454h/roofline/search_numa_half/4g/raw/frozen_4g_c.csv`：目标文件不存在，期望哈希 `cd632ed899b6193c32c8c5a948d6e28be34849f878f5619ff47052be03a08f49`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 219 行 `repo/bench/8454h/roofline/search_numa_half/4g/raw/numa_half_4g_a.csv`：目标文件不存在，期望哈希 `3d94daf4d7799696fc569af0c68dcbe5e9cb79bf6c4eb2c38ee859abc1ecb3a8`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 220 行 `repo/bench/8454h/roofline/search_numa_half/4g/raw/numa_half_4g_b.csv`：目标文件不存在，期望哈希 `4ceaaafc73db29e9ff692f3c6654032404ce7b60cc08f3ab6b0fa582e7e3fb43`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 221 行 `repo/bench/8454h/roofline/search_numa_half/4g/run_manifest.json`：目标文件不存在，期望哈希 `7e1aea43fe85920ff80bf049706810b921b57f4050f6cd928825c037e2a0cb1d`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 222 行 `repo/bench/8454h/roofline/search_numa_half/4g/runner.sh`：目标文件不存在，期望哈希 `495184988c2e32645673b096913ba7602d786fb99fdea54648c7651389ce2957`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 223 行 `repo/bench/8454h/roofline/search_numa_half/README.md`：目标文件不存在，期望哈希 `f03948e5dbb324177847870bb56b59bb8d759577dc463c19bdd0ad0cae9948c3`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 224 行 `repo/bench/8454h/roofline/search_pad/metadata.json`：目标文件不存在，期望哈希 `573eaefe2a37c0dab3fd4b8013d2f799be1c59cdb73749884c9d897e4b4c53cc`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 225 行 `repo/bench/8454h/roofline/search_pad/pass0_frozen.csv`：目标文件不存在，期望哈希 `bca12f0da204f8167ede80a3eeebad682ed3c361969737b60c779ce73c43cb04`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 226 行 `repo/bench/8454h/roofline/search_pad/pass1_p1b1.csv`：目标文件不存在，期望哈希 `1380074b09f0b66d4d0b4a7ddb9215ccc386398758b2ba4ddfcbd14cb680bdce`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 227 行 `repo/bench/8454h/roofline/search_pad/pass2_p2b1.csv`：目标文件不存在，期望哈希 `9e1972ca5a41bfbc8e03bc8d238a1484d7cdc44aa5837b88ed90a889555b8af4`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 228 行 `repo/bench/8454h/roofline/search_pad/pass3_p3b1.csv`：目标文件不存在，期望哈希 `91e9f4d17be0e476a62098008fba14b2dd5b916b47ff274703674445aefd1b53`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 229 行 `repo/bench/8454h/roofline/search_pad/pass4_p1b2.csv`：目标文件不存在，期望哈希 `8ce798c43a2ce5e868ff2a12bb12fb1a0d3cf4c4fbf2391bdc2d94a6a6d286cf`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 230 行 `repo/bench/8454h/roofline/search_pad/pass5_frozen.csv`：目标文件不存在，期望哈希 `9194904a76331093492c9c2cb79e1821145ea52c3da1a1f67d923d4ff2f44c65`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 231 行 `repo/bench/8454h/roofline/search_pad/pass6_p1b2.csv`：目标文件不存在，期望哈希 `79122ce1ddf151f1452cbddc15c1e7bbffae3ff5049b14fc4ccb64e387de42cc`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 232 行 `repo/bench/8454h/roofline/search_pad/pass7_p1b1.csv`：目标文件不存在，期望哈希 `c7eba79463cbd3915cb1f2a7915dfda1deff8c9fe925209a3c2c56458ee83989`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 233 行 `repo/bench/8454h/roofline/search_pad/pass8_frozen.csv`：目标文件不存在，期望哈希 `da15a551198a351eab5b61588962d0465e6444a2ed8d72a6f40373de4200c7cc`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 234 行 `repo/bench/8454h/roofline/search_pad/summary.json`：目标文件不存在，期望哈希 `18ae3893c2fa8f0fc2a5b70655057548a5b8276271c160070dc85509f1b500f4`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 235 行 `repo/bench/8454h/roofline/search_rect/metadata.json`：目标文件不存在，期望哈希 `5acdfdf672d97b5694eab895e020a52d329a321e49ce3c1fbe1b24499ee16e4a`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 236 行 `repo/bench/8454h/roofline/search_rect/pass0_frozen.csv`：目标文件不存在，期望哈希 `0f0d265b6216d3e62d5489462443b8ec130b730a85cd4463dab55ca37320d19d`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 237 行 `repo/bench/8454h/roofline/search_rect/pass1_n256p1.csv`：目标文件不存在，期望哈希 `223f09d5f0438ee517b76d2147777d4d8fe96091c989b021f42503f5ee377698`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 238 行 `repo/bench/8454h/roofline/search_rect/pass2_n512p1.csv`：目标文件不存在，期望哈希 `1e312a63876bdbd50faad369717221e244b338539bfa196816fd22ff8d5e9976`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 239 行 `repo/bench/8454h/roofline/search_rect/pass3_n256p0.csv`：目标文件不存在，期望哈希 `f2f16cf9cb4b6e063198c4b2605935b130bc84d176efde1bb5ecc93a1996893e`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 240 行 `repo/bench/8454h/roofline/search_rect/pass4_n256p1b2.csv`：目标文件不存在，期望哈希 `8f16f033dff790d9a0de8ee2d0ff185cdb34e19a979a813a46601a631c3598a1`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 241 行 `repo/bench/8454h/roofline/search_rect/pass5_frozen.csv`：目标文件不存在，期望哈希 `ea83bf048337169a0e12940d2db00e76f9ee14ba17ed26b40a987e87cd77682e`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 242 行 `repo/bench/8454h/roofline/search_rect/pass6_n256p1.csv`：目标文件不存在，期望哈希 `8b53f3d75361a0f196baa7170de4ba422a950bba7d8a05017af596a5931f5549`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 243 行 `repo/bench/8454h/roofline/search_rect/pass7_n512p1.csv`：目标文件不存在，期望哈希 `0d57be2e3c622ee2e39b528227467f9fe64ba73f1e5cec8882e10b404689204f`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 244 行 `repo/bench/8454h/roofline/search_rect/pass8_frozen.csv`：目标文件不存在，期望哈希 `3a67cdd1924cd02c793311b1d10389fcef2687feedc4bb6171958ef40ce00ce8`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 245 行 `repo/bench/8454h/roofline/search_rect/summary.json`：目标文件不存在，期望哈希 `2da297ffb7ed08277a8cfc4086200fd1c9eee7fdb01a15d670d7e09515e8ae71`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 246 行 `repo/bench/8454h/roofline/search_thp/metadata.json`：目标文件不存在，期望哈希 `869c55af72c9af620233cde2d131d85147afb89b17ab11dd1d0135417128e5e4`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 247 行 `repo/bench/8454h/roofline/search_thp/pass0_frozen.csv`：目标文件不存在，期望哈希 `d0ac190b518664921d84932ce041f5b4c6d6c44f80b3835865b509b8bdafc16d`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 248 行 `repo/bench/8454h/roofline/search_thp/pass1_h1.csv`：目标文件不存在，期望哈希 `7a9c13c6572815f1bc0c781ab5aab544082013efe24e5bbc8138e270c94d59e9`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 249 行 `repo/bench/8454h/roofline/search_thp/pass2_frozen.csv`：目标文件不存在，期望哈希 `feda14031f8e23268e8f6d5bb87e5cfe8c939448b44aab78579d09cea8277b84`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 250 行 `repo/bench/8454h/roofline/search_thp/pass3_h1.csv`：目标文件不存在，期望哈希 `fb0808fdc5dafb7c58349cb6f27156b8d1f9d72e7eec0454bfe0f5419c0df2ae`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 251 行 `repo/bench/8454h/roofline/search_thp/pass4_frozen.csv`：目标文件不存在，期望哈希 `6507559740b67ddc7fd904d4b359e5455294f2ee8727bc866dd98bfea007802f`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 252 行 `repo/bench/8454h/roofline/search_thp/probe_hint0.json`：目标文件不存在，期望哈希 `52bb90d999ea7eae7a9e8af0feb53d74eb0b24c5205a041d7931b26f20410526`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 253 行 `repo/bench/8454h/roofline/search_thp/probe_hint1.json`：目标文件不存在，期望哈希 `25561620b15e3a1efde278a839ef51f9b4dd1e190b37d01854e03f1ee89670ed`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 254 行 `repo/bench/8454h/roofline/search_thp/summary.json`：目标文件不存在，期望哈希 `43f5a99b9f6781b4e7a35212b713f430d410a59c2e1111c6d44d2afdeb31fbbb`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 255 行 `repo/bench/8454h/roofline/summarize_searches.py`：目标文件不存在，期望哈希 `b7d43742c63a45fbb57c5583e28692805dfae4bd6dac63b2c6e8fbc94ff1828b`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 256 行 `repo/bench/8454h/roofline/traffic_model.json`：目标文件不存在，期望哈希 `73215d85e4757802049ff1eaa9c1075333fbebe725ad898ce9e310f30a981ca8`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 257 行 `repo/bench/8454h/run_equivalence.sh`：目标文件不存在，期望哈希 `cb85f10f02e97d76891bd2def5847d276511e100630015d4df9f17e3e6140df9`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 258 行 `repo/bench/8454h/versions/v2/MANIFEST.sha256`：目标文件不存在，期望哈希 `0811f7ba2169b4ca37de5a3ac670cd54435572cd7d30cf909ae7a6d992c6463e`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 259 行 `repo/bench/8454h/versions/v2/README.md`：目标文件不存在，期望哈希 `36b06f6a32bd34457233a31737dc0bdf887a0363585a6fbe285c066a10218527`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 260 行 `repo/bench/8454h/versions/v2_release/MANIFEST.sha256`：目标文件不存在，期望哈希 `8b68d0d095b38f117cb10083ae5272847c533821d037fbdba7c091b06e6d950b`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 261 行 `repo/bench/8454h/versions/v2_release/README.md`：目标文件不存在，期望哈希 `4d1d0c9a4693ccf18d8ce2090c9e2e28ed5935d9a9896b70d51481d3783db24d`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 262 行 `repo/bench/benchmark.cpp`：目标文件不存在，期望哈希 `1ff045bd32a5f77686ce27e5d8bb1406b5887b43ed1158c25653dcf13c80a5c6`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 263 行 `repo/bench/optimization_benchmark.cpp`：目标文件不存在，期望哈希 `54ca1dea3c988d41cf012191bbaea6e51d39a09020c6b5f14829d7e37b788d05`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 264 行 `repo/bench/run_8454h_baseline.sh`：目标文件不存在，期望哈希 `ab619ea24be77ced4ca77651b4a2f43124632e4857d236c0213373956e1be7ae`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 265 行 `repo/bench/run_extended_validation.sh`：目标文件不存在，期望哈希 `871c2fb66f4e1d61522f91c1a3f60c1d718c825cb7e1032a978a4f9efc3387bb`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 266 行 `repo/bench/run_packed_panel_audit.sh`：目标文件不存在，期望哈希 `9e07f723c4a35bf8f1ac4b413a3e08bf3bb94c786f096b63c4bf343ea4a5f055`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 267 行 `repo/docs/8454H_FINAL_PERFORMANCE_REPORT.md`：目标文件不存在，期望哈希 `23b841d5532e39fc8f29de8b8828e1b9ed338b43dad6b1670325ba3c70ebc639`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 268 行 `repo/docs/8454H_KERNEL_IDEAS.md`：目标文件不存在，期望哈希 `e8a0b3a5cb0a673d4e2633530976fff5c87a10dfe78b306d15908b26cb15c9a2`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 269 行 `repo/docs/8454H_PERFORMANCE_BASELINE.md`：目标文件不存在，期望哈希 `b4c6d7ae5144f59cef747a1d255ed3efdc7419a34f337608995233d2bff24a5d`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 270 行 `repo/docs/8454H_ROOFLINE_CALIBRATION.md`：目标文件不存在，期望哈希 `9d73b4705687383f16d729399e54c70406e041a02f3f0160535892252284e4d3`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 271 行 `repo/docs/8454H_ROOFLINE_MODEL.md`：目标文件不存在，期望哈希 `790cb3ac0faeb8f7e6d092f1fcc2b87d3b9e1d8d3120958076dfa15fb4d0e8e4`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 272 行 `repo/docs/8454H_ROOFLINE_RESULTS.md`：目标文件不存在，期望哈希 `4642c3a73a2f61c46536ab31c91d039803056415e76f1419914101e89dc403f7`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 273 行 `repo/docs/8454H_ROOFLINE_SEARCH_LOG.md`：目标文件不存在，期望哈希 `5f876492e80abe4c29ca973552333d297f54cf5272872bd0b9c498ecde436876`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 274 行 `repo/docs/8454H_ROOFLINE_TRAFFIC.md`：目标文件不存在，期望哈希 `f9c9c0f595e66edea33c76571caa7be400e1f5f2747a176aadf0a97d92b82726`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 275 行 `repo/docs/8454H_SEARCH_RESULTS.md`：目标文件不存在，期望哈希 `f4d83bc8c1ce044d4e247937b1c6520321456ef1b2559977ef316a29b849cbcc`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 276 行 `repo/docs/figures/8454H_ROOFLINE_AMX_LOGICAL_AI.png`：目标文件不存在，期望哈希 `546102a88dd355780e9677739a49c1d42b19f7fab1528207c1addc6016dcd813`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 277 行 `repo/docs/figures/8454H_ROOFLINE_AMX_LOGICAL_AI.svg`：目标文件不存在，期望哈希 `67ed200b2e952d3feebd6caf7ffc67cb36d23b3680d4df2714a2ec0a7474357e`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 278 行 `repo/docs/figures/8454H_ROOFLINE_PLOTS_METADATA.json`：目标文件不存在，期望哈希 `f17ffe85b0da1480e7360b8e2ff63392bba5c4812e8b4bd7a03f2ce1f15c9d60`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 279 行 `repo/docs/figures/8454H_ROOFLINE_STAGE_DIAGNOSTIC.png`：目标文件不存在，期望哈希 `d9ec211e00ed7704526af01754ae168fefc68c875535d952dff8f9646f225584`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 280 行 `repo/docs/figures/8454H_ROOFLINE_STAGE_DIAGNOSTIC.svg`：目标文件不存在，期望哈希 `0bbebf9ed12d877e038d1461b94dd437345d2128ef082e65a7f27e0507a4ef12`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 288 行 `repo/tests/bounded_commit_alias_probe.cpp`：目标文件不存在，期望哈希 `c29f55845e4a7b755635e86932f587a5106220afd1a681997d254bf4c63eaf09`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 289 行 `repo/tests/bounded_commit_overflow_probe.cpp`：目标文件不存在，期望哈希 `8c70309dd95e87908a064521cf56d935b34bebc81858cf2b1519bb0993410a84`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 290 行 `repo/tests/extended_validation.cpp`：目标文件不存在，期望哈希 `34e820efcf1d84a790047695b9b9e11fff371305ae23c83488ce3c53e8e2245c`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 291 行 `repo/tests/final_late_path_probe.cpp`：目标文件不存在，期望哈希 `ca73c8372bb39fc8c5ab0f6dfc51bf10034c0d61ee24fb05248d00533f8d9a53`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 292 行 `repo/tests/fp32_packed_panel_audit.cpp`：目标文件不存在，期望哈希 `855609e1aae13fc48edce62f1f2aa758dab7571c6cdebea769f74a43392f111c`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 293 行 `repo/tests/packed_panel_audit.cpp`：目标文件不存在，期望哈希 `29ddf9218c20c86f0be857361e209f2c91a3ea5e375f7fbc5ccc60ffac6419f2`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 294 行 `repo/tests/validation.cpp`：目标文件不存在，期望哈希 `059450a04960c12dc78b17d63ce270d41f24215f8d0aa53f426daef5bea5e264`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 295 行 `repo/third_party/SOURCES.md`：目标文件不存在，期望哈希 `d8df1a1f9bd46a43f772976612d04507c942f62aca686594c2fbf15a6fee0f68`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 296 行 `repo/third_party/roofline/ISC18-RooflineAdvisor-final.pdf`：目标文件不存在，期望哈希 `2fddb09d2b93440f84ca8090af0ebe33bd60bb7b4ffded46aa0c669c119d27b5`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 297 行 `repo/third_party/roofline/SOURCES.md`：目标文件不存在，期望哈希 `c0fa4eddc6f4430af92b8a7379cd47d63fbb9b97166c0601db4757f7c6faf42c`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 298 行 `repo/third_party/roofline/study.md`：目标文件不存在，期望哈希 `16794e07e352d331b03ddd748b0d450d857dafa75b6bbd8071f0166570a0b1e2`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 299 行 `repo/tools/amx_probe.c`：目标文件不存在，期望哈希 `9db413f970915067d83fe71183b583af08d3a75ecc13fff4c11b92206e648c5d`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 300 行 `repo/tools/native_alternative_accuracy.cpp`：目标文件不存在，期望哈希 `1522208e7556dc021b24b79c3bb1403254ae3251a47fb6a02358ba224b53c26a`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 301 行 `repo/tools/native_kernel_audit.cpp`：目标文件不存在，期望哈希 `8c3e66d56b6b81b65f067bee7380d5b41ca0eeca9529b94dfc6f92c262775178`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 302 行 `repo/tools/native_signed_shift_accuracy.cpp`：目标文件不存在，期望哈希 `31fed4d3f6ea6a9bea93e23a6e78c882e54be67bd7013efbca5ef404381882b8`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 303 行 `repo/tools/platform_baseline.cpp`：目标文件不存在，期望哈希 `25444b17c9df70fbc743fb621f60256ff2785395a2b41277fa9861303af67b4e`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 304 行 `repo/tools/plot_roofline_calibration.py`：目标文件不存在，期望哈希 `d8affbe14fce0f2479eb50020cf94de93da299c0122da3cc1d50a0775a98deeb`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 305 行 `repo/tools/roofline_binary_gate.cpp`：目标文件不存在，期望哈希 `6ee7c7b2ed423c52e2481756b51d1073229b55b49bdcbdabda965d0fc6f342df`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 306 行 `repo/tools/roofline_kernels.cpp`：目标文件不存在，期望哈希 `ae38a0192f20bec20a220f333d3d6d70856367109e5e02ed949dd64424b64db0`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 307 行 `repo/tools/roofline_memory.cpp`：目标文件不存在，期望哈希 `ec293893f272f6545ada0bbc6c0cfc1eb2f3c50af3911a0d61109faaa71a2c4e`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 308 行 `repo/tools/roofline_thp_probe.cpp`：目标文件不存在，期望哈希 `fc321e61f45dbbaa1bbeee61b60c4b97f4850172d019ed3b19c8519a9ec1ec23`。
- `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` 第 309 行 `repo/tools/roofline_tileloads.S`：目标文件不存在，期望哈希 `df26c82d11a73a7f16350d3dfb01ce26d11ce12b32a2c9960f642818191e41ef`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/mkl_roofline_v3/source_hashes.sha256` 第 11 行 `bench/8454h/mkl_roofline_v3/ozamx_benchmark`：目标文件不存在，期望哈希 `3de58ab85f04af0e0002f53c83c707bc9d8b246150a2a75b0b636ecc7ac159b6`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/mkl_roofline_v3/source_hashes.sha256` 第 12 行 `third_party/code/mkl-current/lib/libmkl_rt.so.3`：目标文件不存在，期望哈希 `b2ff0e31d7cd18c91813d8f6500f37665597d89de22649d90687aa6bf7bd2c0f`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2/MANIFEST.sha256` 第 1 行 `./CMakeLists.txt`：哈希不匹配，期望 `3a2acbf7b6d340f96543fc1d267a968ace33e2d89d1476657eedf4b67c1039e0`，实际 `83cc30f33c86fcfe6a3878a80eb8808d0e074518ac69801e209f13fc1146e5ad`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2/MANIFEST.sha256` 第 2 行 `./README.md`：哈希不匹配，期望 `36b06f6a32bd34457233a31737dc0bdf887a0363585a6fbe285c066a10218527`，实际 `dc59b71c44c58c9adce4aaef00ae7ada05134f765042e737534e1d92fd50a5ed`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2/MANIFEST.sha256` 第 3 行 `./bench/8454h/V2_VALIDATION.md`：目标文件不存在，期望哈希 `4ca29b2c75f3e1fe5232a48fcbc4dca0edaedb46c6b148428935b8f340b7f2dd`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2/MANIFEST.sha256` 第 4 行 `./bench/8454h/before/include/ozamx/gemm.hpp`：目标文件不存在，期望哈希 `0a7143bb72a3450e955bcdbb7302068cb10ca45ec5c9b519917a12315d2f499a`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2/MANIFEST.sha256` 第 5 行 `./bench/8454h/before/src/gemm.cpp`：目标文件不存在，期望哈希 `97257f881d9cccda88cc1918bf874b8c124fbd1c4e7e119ccb12b1849ca51ad0`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2/MANIFEST.sha256` 第 6 行 `./bench/8454h/before/src/runtime.cpp`：目标文件不存在，期望哈希 `be1d2bfc44f179febfbea54bcf5807bbee8aaea7c7539a51e7038a8cc3854474`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2/MANIFEST.sha256` 第 7 行 `./bench/8454h/bounded_commit_candidate_summary.json`：目标文件不存在，期望哈希 `8d87b060096df1e22932af519a101772e1606cc5a6fecdcea4affa65271a4f02`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2/MANIFEST.sha256` 第 9 行 `./bench/8454h/final_production_extended47.json`：目标文件不存在，期望哈希 `b0bf30da6c55d3b3a0350275772e23fa95debba7c01740c74364277a114f2d93`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2/MANIFEST.sha256` 第 10 行 `./bench/8454h/final_production_validation_summary.json`：目标文件不存在，期望哈希 `4c1dfce2cbd80ac40e41697b9aa0da237c4856314eaf512ffff223a4dd36cc01`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2/MANIFEST.sha256` 第 13 行 `./bench/run_extended_validation.sh`：哈希不匹配，期望 `9a13a1c8508d788127f51c82479c0253f42b0a580eb33926c3605b3720687525`，实际 `871c2fb66f4e1d61522f91c1a3f60c1d718c825cb7e1032a978a4f9efc3387bb`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2/MANIFEST.sha256` 第 15 行 `./docs/8454H_PERFORMANCE_BASELINE.md`：哈希不匹配，期望 `a9798916338692a7ed81f23df6ece0eaad78fc505d8fe6a8630bd3324507b0ea`，实际 `b4c6d7ae5144f59cef747a1d255ed3efdc7419a34f337608995233d2bff24a5d`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2/MANIFEST.sha256` 第 17 行 `./src/gemm.cpp`：哈希不匹配，期望 `8a5d27440c604df9304b75769e3c048a6748789aab6ee8fed3a5c3446335a85b`，实际 `7a4d0311dd12ee9a8a0ef6a3dca42bec6dca8a36ec34782da603b84c2419a164`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 1 行 `README.md`：哈希不匹配，期望 `4d1d0c9a4693ccf18d8ce2090c9e2e28ed5935d9a9896b70d51481d3783db24d`，实际 `dc59b71c44c58c9adce4aaef00ae7ada05134f765042e737534e1d92fd50a5ed`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 2 行 `repo/CMakeLists.txt`：目标文件不存在，期望哈希 `38fe0d708528f348aa7449c5933bbbdf1fe2c363e03bda16a0c7caa0aa0ee366`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 3 行 `repo/bench/8454h/V2_VALIDATION.md`：目标文件不存在，期望哈希 `4ca29b2c75f3e1fe5232a48fcbc4dca0edaedb46c6b148428935b8f340b7f2dd`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 4 行 `repo/bench/8454h/create_v2_release_archive.py`：目标文件不存在，期望哈希 `a2f126b586f4e5bf51c864c7ce83452096990b99d0f9cb2be40adf553147358c`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 5 行 `repo/bench/8454h/equivalence_driver.cpp`：目标文件不存在，期望哈希 `5862298e4001805452e039e5d4b46d2985874f3d8318b841ed6d9d105dbd21af`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 6 行 `repo/bench/8454h/final_production_extended47.json`：目标文件不存在，期望哈希 `b0bf30da6c55d3b3a0350275772e23fa95debba7c01740c74364277a114f2d93`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 7 行 `repo/bench/8454h/final_production_validation_summary.json`：目标文件不存在，期望哈希 `4c1dfce2cbd80ac40e41697b9aa0da237c4856314eaf512ffff223a4dd36cc01`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 8 行 `repo/bench/8454h/final_run_metadata.txt`：目标文件不存在，期望哈希 `7e77824c1a40d3256a25830d9bd0381b19abce1543249b4feddcae372c47914d`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 9 行 `repo/bench/8454h/machine_metadata.txt`：目标文件不存在，期望哈希 `0bcf2a82189fb74b2b353711b3240f30b6b3510261ba89c33846e0d2c4a92d65`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 10 行 `repo/bench/8454h/mkl_production/README.md`：目标文件不存在，期望哈希 `d1ba721f57f41686a9713a643b8575cee60622a5c9800c7ca3a521e6b9146be2`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 11 行 `repo/bench/8454h/mkl_production/benchmark_production.cpp`：目标文件不存在，期望哈希 `f07ddbb048f46738f97bc19607151b8d2112c2b9e30df93865db20249169b473`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 12 行 `repo/bench/8454h/mkl_production/checkpoint_final_prod.fp32.1024.6.json`：目标文件不存在，期望哈希 `f8176544549543cbb7a263637ed40d85bc0bb411861a019b092f58578dd7f4b7`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 13 行 `repo/bench/8454h/mkl_production/checkpoint_final_prod.fp32.256.6.json`：目标文件不存在，期望哈希 `01a57ebe2781e397f9f04d5ba6c0ad30cccbf45fcb64bef51e850053f6d9e58c`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 14 行 `repo/bench/8454h/mkl_production/checkpoint_final_prod.fp32.4096.6.json`：目标文件不存在，期望哈希 `4ae2f503af5cd28bd2035495ac4d016ae9e10cf568f92fe39ed35edc4905ffc9`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 15 行 `repo/bench/8454h/mkl_production/checkpoint_final_prod.fp32.8192.6.json`：目标文件不存在，期望哈希 `6531e41cf9d482f413fd0915a5ed0b1b527079bd8ca83c94be9e921ebfa18ddf`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 16 行 `repo/bench/8454h/mkl_production/checkpoint_final_prod.fp64.1024.10.json`：目标文件不存在，期望哈希 `7c870a15217ba400b2fdf4df8cc9467d17bd758cdae7a2701429b66de54bf480`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 17 行 `repo/bench/8454h/mkl_production/checkpoint_final_prod.fp64.1024.15.json`：目标文件不存在，期望哈希 `585cb6131d6cf420f5e6b91868b47c4ddb7d58155ac6c58c538472bf044ea405`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 18 行 `repo/bench/8454h/mkl_production/checkpoint_final_prod.fp64.1024.21.json`：目标文件不存在，期望哈希 `7ee314307d47dde30c23b15205519c4c394e617ea7b102f63873be5f489f3f11`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 19 行 `repo/bench/8454h/mkl_production/checkpoint_final_prod.fp64.1024.6.json`：目标文件不存在，期望哈希 `bee198b2bfcd8398d319c250cd8b0066c2a99371e4f16a10f10ec1138ebac163`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 20 行 `repo/bench/8454h/mkl_production/checkpoint_final_prod.fp64.256.10.json`：目标文件不存在，期望哈希 `f226f517380e984061cc6b69d9adb0503c1256ff6889663627b976228c6ae12d`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 21 行 `repo/bench/8454h/mkl_production/checkpoint_final_prod.fp64.256.15.json`：目标文件不存在，期望哈希 `128292dce02550d89c84527d5d621eff2e68ae32d0459bc1b4e4b580b4c58ca1`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 22 行 `repo/bench/8454h/mkl_production/checkpoint_final_prod.fp64.256.21.json`：目标文件不存在，期望哈希 `fed8ab2fae545321bbedb0338e1c1f5dc48f1aa388eb1bfa327a25e6fb8acad3`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 23 行 `repo/bench/8454h/mkl_production/checkpoint_final_prod.fp64.256.6.json`：目标文件不存在，期望哈希 `2404b51c3f5c8061ab619428ea147ce943f22503dc53d81cfc0a6b18c37d2118`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 24 行 `repo/bench/8454h/mkl_production/checkpoint_final_prod.fp64.4096.10.json`：目标文件不存在，期望哈希 `799acac42e7625b934a91d2f11c099d2e4bfcc78703419ec64ed514262bf8de7`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 25 行 `repo/bench/8454h/mkl_production/checkpoint_final_prod.fp64.4096.15.json`：目标文件不存在，期望哈希 `d2502adc5e92a4f3fd9527ff736ae9987fea70d41c9d393bdf20cde6a1e8b312`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 26 行 `repo/bench/8454h/mkl_production/checkpoint_final_prod.fp64.4096.21.json`：目标文件不存在，期望哈希 `80007d3a9d36290bfd629d194e55f2de750fd1cb2dc9c18cdc152336dd49a591`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 27 行 `repo/bench/8454h/mkl_production/checkpoint_final_prod.fp64.4096.6.json`：目标文件不存在，期望哈希 `c30f512453d12fc2731be405bfadfaf802b25db2d20760076c829476eb4a6fdb`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 28 行 `repo/bench/8454h/mkl_production/checkpoint_final_prod.fp64.8192.10.json`：目标文件不存在，期望哈希 `441a9222a16a084df48547b74b667cb4fd22de124cf7a9893c2fc9544b396b8b`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 29 行 `repo/bench/8454h/mkl_production/checkpoint_final_prod.fp64.8192.15.json`：目标文件不存在，期望哈希 `996ebca24eea852e35b7f0195424df64807791489559097b957d7026afd87b8b`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 30 行 `repo/bench/8454h/mkl_production/checkpoint_final_prod.fp64.8192.21.json`：目标文件不存在，期望哈希 `4761a57db2164732545c1fa2bf27b72d4fd893e121fd873462d0bc516723c944`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 31 行 `repo/bench/8454h/mkl_production/checkpoint_final_prod.fp64.8192.6.json`：目标文件不存在，期望哈希 `3f566582c2e1d1e94bb3092efbf7d3562432ffc706b140abfdcd6afaea89b200`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 32 行 `repo/bench/8454h/mkl_production/full_production.csv`：目标文件不存在，期望哈希 `50dfff366f26201aef2517583787470bb29da9c3c81a32c689275e3d20d5a37a`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 33 行 `repo/bench/8454h/mkl_production/production_comparison.md`：目标文件不存在，期望哈希 `7093f198ca5e59036238794d969287b529cd973910cec06df93f0b95174fa70e`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 34 行 `repo/bench/8454h/mkl_production/provenance.json`：目标文件不存在，期望哈希 `9f9cc46a1f82fe63177de708bfe73c0f205466f84385307938a4a85de935e5d6`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 35 行 `repo/bench/8454h/mkl_production/run_command.txt`：目标文件不存在，期望哈希 `5a15b86aa956dabf2626ec322e66ec5f06e00d6293659968d2b7de3b89a50ea0`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 36 行 `repo/bench/8454h/mkl_production/source_hashes_pre_run.sha256`：目标文件不存在，期望哈希 `14abcc16d129ddb9b2fee2af7b01209a3520fcedcc132bfe9778cd7ae33f3d3e`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 37 行 `repo/bench/8454h/run_equivalence.sh`：目标文件不存在，期望哈希 `cb85f10f02e97d76891bd2def5847d276511e100630015d4df9f17e3e6140df9`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 38 行 `repo/bench/8454h/versions/v2/MANIFEST.sha256`：目标文件不存在，期望哈希 `0811f7ba2169b4ca37de5a3ac670cd54435572cd7d30cf909ae7a6d992c6463e`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 39 行 `repo/bench/8454h/versions/v2/README.md`：目标文件不存在，期望哈希 `36b06f6a32bd34457233a31737dc0bdf887a0363585a6fbe285c066a10218527`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 40 行 `repo/bench/benchmark.cpp`：目标文件不存在，期望哈希 `5adddf4dc7ed4548f58ed76e4ce47cf93b0b5b6a803d0f238313cd31cab03da1`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 41 行 `repo/bench/optimization_benchmark.cpp`：目标文件不存在，期望哈希 `54ca1dea3c988d41cf012191bbaea6e51d39a09020c6b5f14829d7e37b788d05`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 42 行 `repo/bench/run_8454h_baseline.sh`：目标文件不存在，期望哈希 `ab619ea24be77ced4ca77651b4a2f43124632e4857d236c0213373956e1be7ae`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 43 行 `repo/bench/run_extended_validation.sh`：目标文件不存在，期望哈希 `871c2fb66f4e1d61522f91c1a3f60c1d718c825cb7e1032a978a4f9efc3387bb`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 44 行 `repo/bench/run_packed_panel_audit.sh`：目标文件不存在，期望哈希 `9e07f723c4a35bf8f1ac4b413a3e08bf3bb94c786f096b63c4bf343ea4a5f055`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 45 行 `repo/docs/8454H_FINAL_PERFORMANCE_REPORT.md`：目标文件不存在，期望哈希 `877f60631c8dc688be65e90e9e354a447f7ee7b7181805c8e4220a055bf5d71e`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 46 行 `repo/docs/8454H_KERNEL_IDEAS.md`：目标文件不存在，期望哈希 `e8a0b3a5cb0a673d4e2633530976fff5c87a10dfe78b306d15908b26cb15c9a2`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 47 行 `repo/docs/8454H_PERFORMANCE_BASELINE.md`：目标文件不存在，期望哈希 `f80105be8e5edd3e1fb2e8c595578ad4c9d5ed45777d6ff700114d56864170eb`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 48 行 `repo/docs/8454H_ROOFLINE_SEARCH_LOG.md`：目标文件不存在，期望哈希 `67bb3fe8530ec30d3b8b7c6848630e172b3ac769c6d57b284736bb3138b4aac9`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 49 行 `repo/docs/8454H_SEARCH_RESULTS.md`：目标文件不存在，期望哈希 `f4d83bc8c1ce044d4e247937b1c6520321456ef1b2559977ef316a29b849cbcc`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 50 行 `repo/include/ozamx/gemm.hpp`：目标文件不存在，期望哈希 `0430c3df107909436d7abf6afa037bfcc6ced94689660a8929fe9e00640241b5`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 51 行 `repo/src/gemm.cpp`：目标文件不存在，期望哈希 `8a5d27440c604df9304b75769e3c048a6748789aab6ee8fed3a5c3446335a85b`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 52 行 `repo/src/kernels.S`：目标文件不存在，期望哈希 `94af3cf4345b2383100e4d8d883be57b084ec68d12e056f80c4a8bb77bc9bd68`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 53 行 `repo/src/main.cpp`：目标文件不存在，期望哈希 `7ed7f5c2eb5bd9ef2b8572aadc7a3f3f116e8a8a62370197bd606f3b4035bcde`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 54 行 `repo/src/preprocess.hpp`：目标文件不存在，期望哈希 `df36a028fbbeec62bcacc5a0a50194f917285d20fd9cf231abd4c28d4013ee31`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 55 行 `repo/src/runtime.cpp`：目标文件不存在，期望哈希 `63a3df726c220dddd51dc1e962d1d2169c74722a4e9452b76a4d731a0c500774`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 56 行 `repo/src/tuning.hpp`：目标文件不存在，期望哈希 `2dc89e5f8a0986da508eca9931e94130be96a0b098c9f0ab8d35a6217ecb4798`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 57 行 `repo/tests/bounded_commit_alias_probe.cpp`：目标文件不存在，期望哈希 `c29f55845e4a7b755635e86932f587a5106220afd1a681997d254bf4c63eaf09`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 58 行 `repo/tests/bounded_commit_overflow_probe.cpp`：目标文件不存在，期望哈希 `8c70309dd95e87908a064521cf56d935b34bebc81858cf2b1519bb0993410a84`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 59 行 `repo/tests/extended_validation.cpp`：目标文件不存在，期望哈希 `34e820efcf1d84a790047695b9b9e11fff371305ae23c83488ce3c53e8e2245c`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 60 行 `repo/tests/final_late_path_probe.cpp`：目标文件不存在，期望哈希 `ca73c8372bb39fc8c5ab0f6dfc51bf10034c0d61ee24fb05248d00533f8d9a53`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 61 行 `repo/tests/fp32_packed_panel_audit.cpp`：目标文件不存在，期望哈希 `855609e1aae13fc48edce62f1f2aa758dab7571c6cdebea769f74a43392f111c`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 62 行 `repo/tests/packed_panel_audit.cpp`：目标文件不存在，期望哈希 `29ddf9218c20c86f0be857361e209f2c91a3ea5e375f7fbc5ccc60ffac6419f2`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 63 行 `repo/tests/v2_transaction_probes.cpp`：目标文件不存在，期望哈希 `458edef94b508c93264160e0c6835e0534f5b5082b83444e5f3cb2bd11c03c0a`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 64 行 `repo/tests/validation.cpp`：目标文件不存在，期望哈希 `059450a04960c12dc78b17d63ce270d41f24215f8d0aa53f426daef5bea5e264`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 65 行 `repo/tools/amx_probe.c`：目标文件不存在，期望哈希 `9db413f970915067d83fe71183b583af08d3a75ecc13fff4c11b92206e648c5d`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 66 行 `repo/tools/native_alternative_accuracy.cpp`：目标文件不存在，期望哈希 `1522208e7556dc021b24b79c3bb1403254ae3251a47fb6a02358ba224b53c26a`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 67 行 `repo/tools/native_kernel_audit.cpp`：目标文件不存在，期望哈希 `8c3e66d56b6b81b65f067bee7380d5b41ca0eeca9529b94dfc6f92c262775178`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 68 行 `repo/tools/native_signed_shift_accuracy.cpp`：目标文件不存在，期望哈希 `31fed4d3f6ea6a9bea93e23a6e78c882e54be67bd7013efbca5ef404381882b8`。
- `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` 第 69 行 `repo/tools/platform_baseline.cpp`：目标文件不存在，期望哈希 `25444b17c9df70fbc743fb621f60256ff2785395a2b41277fa9861303af67b4e`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/roofline_v4/diagnostic_src/results/20261014T091717Z-3/initial_source_and_freeze.sha256` 第 2 行 `/home/caiweili/ozAMX/bench/8454h/roofline_v4/diagnostic_src/bench/benchmark.cpp`：哈希不匹配，期望 `c50636e4eb5c57d0a6a60352e71697664a7ff93b7ca7f2b8ce91ed4de53913c7`，实际 `59a757b819bdc14385f4d9965dbeddb0675b5e7fa0290f2b879df6fdcbae47c0`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/roofline_v4/diagnostic_src/results/20261014T091717Z-3/mode0_control.sha256` 第 3 行 `/home/caiweili/ozAMX/bench/8454h/roofline_v4/diagnostic_src/build/mode0/libozamx.a`：目标文件不存在，期望哈希 `113b822dc22f02d61019f4b7dcf7693b335fa1e25f8e49be8e1bedc49bc8e462`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/roofline_v4/diagnostic_src/results/20261014T091717Z-3/mode1_diagnostic_plain_nf.sha256` 第 3 行 `/home/caiweili/ozAMX/bench/8454h/roofline_v4/diagnostic_src/build/mode1/libozamx.a`：目标文件不存在，期望哈希 `804ce5d0b6d0c79bce141624e9e6b97e92a6e72492a4d89555013b8407aae490`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/roofline_v4/diagnostic_src/results/20261014T091717Z-3/mode2_diagnostic_no_reconstruction.sha256` 第 3 行 `/home/caiweili/ozAMX/bench/8454h/roofline_v4/diagnostic_src/build/mode2/libozamx.a`：目标文件不存在，期望哈希 `09f28878c7506d480322c51952c8d74d621a6ef5cd32ec0dd6c5e2bc721fe8c4`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/roofline_v4/diagnostic_src/results/20261014T091717Z-3/mode3_candidate_late32_unvalidated.sha256` 第 3 行 `/home/caiweili/ozAMX/bench/8454h/roofline_v4/diagnostic_src/build/mode3/libozamx.a`：目标文件不存在，期望哈希 `512cf754a3ec7228fadd07c93521bcbe6b41573bff8e679c7551cbb84457c8f7`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/roofline_v4/diagnostic_src/results/20261014T091717Z-3/source_and_freeze.sha256` 第 2 行 `/home/caiweili/ozAMX/bench/8454h/roofline_v4/diagnostic_src/bench/benchmark.cpp`：哈希不匹配，期望 `c50636e4eb5c57d0a6a60352e71697664a7ff93b7ca7f2b8ce91ed4de53913c7`，实际 `59a757b819bdc14385f4d9965dbeddb0675b5e7fa0290f2b879df6fdcbae47c0`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 1 行 `README.md`：目标文件不存在，期望哈希 `79a07ad78115360480822f53a533e6818f211466107203a8454320d67f06e813`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 3 行 `repo/CMakeLists.txt`：目标文件不存在，期望哈希 `83cc30f33c86fcfe6a3878a80eb8808d0e074518ac69801e209f13fc1146e5ad`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 4 行 `repo/README.md`：目标文件不存在，期望哈希 `dc59b71c44c58c9adce4aaef00ae7ada05134f765042e737534e1d92fd50a5ed`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 5 行 `repo/bench/8454h/create_v3_release_archive.py`：目标文件不存在，期望哈希 `b9a63235bc3555bb00774b5ecd10d820c85c033ec949b4dbc6301f051ea8a4b6`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 6 行 `repo/bench/8454h/equivalence_driver.cpp`：目标文件不存在，期望哈希 `5862298e4001805452e039e5d4b46d2985874f3d8318b841ed6d9d105dbd21af`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 7 行 `repo/bench/8454h/mkl_roofline_v3/README.md`：目标文件不存在，期望哈希 `fd8327a6889d1e9efbcd93e4aa2e462a6570a0ada1530e83a68449d32ad4457e`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 8 行 `repo/bench/8454h/mkl_roofline_v3/benchmark_roofline_v3.cpp`：目标文件不存在，期望哈希 `1ff045bd32a5f77686ce27e5d8bb1406b5887b43ed1158c25653dcf13c80a5c6`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 9 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp32.1024.6.json`：目标文件不存在，期望哈希 `d34f2b0398ae7ef67a3cb7add0fb9611b879ce46bd719cb77ae723cc56b5fed9`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 10 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp32.256.6.json`：目标文件不存在，期望哈希 `8202377fcac204d46134b4e4bc1ba6b511c768af6664b8c2b713d474a71d89e2`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 11 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp32.4096.6.json`：目标文件不存在，期望哈希 `4038ea8001a6504eff03097c3008fdaa0fa6e8ed703c154c1ff2012e276b541e`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 12 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp32.8192.6.json`：目标文件不存在，期望哈希 `951e8c26075a89ae2c24b871ba78e95a49ff6ab5402cf407122c100a04c2f3a9`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 13 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.1024.10.json`：目标文件不存在，期望哈希 `70555bd75296623a33cc7306080408fb2f04b6a680a3363f760c6af33e2bf38d`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 14 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.1024.15.json`：目标文件不存在，期望哈希 `9e46f122608f7316d9bfe0e4c478230a9060a5c76c4b86e3bd4bcb568aa2e149`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 15 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.1024.21.json`：目标文件不存在，期望哈希 `357c91fdffb4aee58059696213f430f1a07cf58624211411b883960204452bde`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 16 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.1024.6.json`：目标文件不存在，期望哈希 `4ad84a6699f9c0147591e47edc3b3d7f386b8dafda06cbd12bc16941ea5a944b`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 17 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.256.10.json`：目标文件不存在，期望哈希 `3221f06752925d4a801c49332bee6bbb8914f4d8bc9916096e1a803de130df68`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 18 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.256.15.json`：目标文件不存在，期望哈希 `32048b15bfc5044df8aed68f3c356c2bf456835ff1321fe4d2fa879b691cc317`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 19 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.256.21.json`：目标文件不存在，期望哈希 `1a6511ab8e62f0419186ed2d49aba938eb610cf4be63ad23ec8e131016a97248`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 20 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.256.6.json`：目标文件不存在，期望哈希 `3f204742123fed3398077c23596638cd1abc6c9701b22a9b894786df1d6f2e82`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 21 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.4096.10.json`：目标文件不存在，期望哈希 `217cbbd6c1bc57cb65e2b8260ed5d712a4d9bc3beff7f24a9147932bd95518da`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 22 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.4096.15.json`：目标文件不存在，期望哈希 `e3186ef94f358018c783cfa53dd9df86e9b256a3487839300c1e5edbd5eb204f`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 23 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.4096.21.json`：目标文件不存在，期望哈希 `cc9e551e3e52703390d6c8d42afb7a2f79c514496a65c796c22ce35cdc600fc5`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 24 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.4096.6.json`：目标文件不存在，期望哈希 `5f8ce5f41adefe83282bbafbc70eff2960cd7528183f6f1664801ea01daf8d30`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 25 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.8192.10.json`：目标文件不存在，期望哈希 `873da1c88cec613f705d477134abf9f28d832140ff0ca3835f3a381473a1c7a6`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 26 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.8192.15.json`：目标文件不存在，期望哈希 `e2ef1e80254219d9d3e974840bf7e4e6980388ad90da3cec83b1523980a7494e`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 27 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.8192.21.json`：目标文件不存在，期望哈希 `70df23c921f01cfab322f83459392fc0205b9b1c0e3969415bd37e8739788fd2`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 28 行 `repo/bench/8454h/mkl_roofline_v3/checkpoint_roofline_v3.fp64.8192.6.json`：目标文件不存在，期望哈希 `e554badc3ca7eb2126fac317f17059e8b4bf548590816c96cb353960200bd7b7`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 29 行 `repo/bench/8454h/mkl_roofline_v3/full_roofline_v3.csv`：目标文件不存在，期望哈希 `879045eead247c7dc7a88c9dddf9b854df048556e333a35e4265b031368b189f`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 30 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/README.md`：目标文件不存在，期望哈希 `bd1144274ba071c804c1eef72a271b32b4e9d348dff35097732d21f67ea56de9`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 31 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/analyze.py`：目标文件不存在，期望哈希 `25ed5f63c4e4df6b1c4a3296bf6d868c0d89b8966d77ad9abb716cbaceea03c8`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 32 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/comparison.json`：目标文件不存在，期望哈希 `d98fcb6fdbe391bd910faeac88f76cdfb5c14832de03900447af81583e39fcc8`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 33 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/benchmark_matched_recheck.cpp`：目标文件不存在，期望哈希 `acba662311017ec85360f1c9aafad6a0d9928911db9706bdb7cb3cc2c1d087bc`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 34 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/checkpoint_p1_v2a.fp32.1024.6.json`：目标文件不存在，期望哈希 `1a10636646a6918e475966fb52656220b189e521d4f87fdf46e71894afda2bc3`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 35 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/checkpoint_p1_v2a.fp32.2048.6.json`：目标文件不存在，期望哈希 `381f765531613c164dcd82316c6b9f5138f18dde71ccf4474262c6d899279d5d`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 36 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/checkpoint_p1_v2a.fp32.8192.6.json`：目标文件不存在，期望哈希 `d9947e975bab75ab9737f211f71b1fb9691c3f3af10b4d1ffbf36f701e588ab5`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 37 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/checkpoint_p1_v2a.fp64.1024.10.json`：目标文件不存在，期望哈希 `beae2d49968722db03a9a0cd07ae7d838863faa71ed816cc6d611742ae31adb6`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 38 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/checkpoint_p1_v2a.fp64.1024.15.json`：目标文件不存在，期望哈希 `894242e60db68c29aed5e94b15cb75a58fbd8a899049628a0e21610ed2fbb66a`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 39 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/checkpoint_p1_v2a.fp64.1024.21.json`：目标文件不存在，期望哈希 `ee9c2e0ab4ffe304fb3c4cfee306e01c16e9cc9fd6f52ff57f485372d85f4278`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 40 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/checkpoint_p1_v2a.fp64.1024.6.json`：目标文件不存在，期望哈希 `bc860973bedea53dc55f35bb11ac0903cb1cde7e98a4f8862551adfa43f8a812`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 41 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/checkpoint_p1_v2a.fp64.2048.10.json`：目标文件不存在，期望哈希 `b7a78be145f9a135e1c652f940a0f01271e3ffd5d1c242ec4469b01bd4dadc10`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 42 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/checkpoint_p1_v2a.fp64.2048.15.json`：目标文件不存在，期望哈希 `dd7b0c1e60070d9e83f3deffccbdcdd553b2255ebaf766967c2e72bebb5a1312`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 43 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/checkpoint_p1_v2a.fp64.2048.21.json`：目标文件不存在，期望哈希 `77a2f74a0a0bde80c8905553717dd51baa2e05ec84ee48eec4fd4b18f9a1e765`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 44 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/checkpoint_p1_v2a.fp64.2048.6.json`：目标文件不存在，期望哈希 `cbad506272845b041d221d56dbcb845ed575af8a415023d30a60e073fb62aea3`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 45 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/checkpoint_p1_v2a.fp64.8192.10.json`：目标文件不存在，期望哈希 `721b951cec3bc77381a8a1a28a58cfc4efdd116e32cc6bee83732570362db587`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 46 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/checkpoint_p1_v2a.fp64.8192.15.json`：目标文件不存在，期望哈希 `bf94917dcabe0a67d1f001a7ef3a6b6735995a32afb1ce80f80b7561d608f52f`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 47 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/checkpoint_p1_v2a.fp64.8192.21.json`：目标文件不存在，期望哈希 `54ae5b83c9f3d63e6bfaab310c5336f684f2dd7b0c6635be79a20097f57fe1dd`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 48 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/checkpoint_p1_v2a.fp64.8192.6.json`：目标文件不存在，期望哈希 `975983570317172ddb00fb6423c48aa0b49e3e4c64658ff289dc3ed780c4f131`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 49 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/full.csv`：目标文件不存在，期望哈希 `e43d083d3766c060e3e5231283177252d08d5df2860811aa444007ff412aee78`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 50 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/provenance.json`：目标文件不存在，期望哈希 `2ac1ffa7b8231e07902135269b718d03acfa7d40eb2656f7821f9f1d0ebf4d3f`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 51 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/benchmark_matched_recheck.cpp`：目标文件不存在，期望哈希 `1e36782212405cf1b439609147acae4207a9763436628f0cf01162bedc43acc4`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 52 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/checkpoint_p2_v3a.fp32.1024.6.json`：目标文件不存在，期望哈希 `30328fd628dfe2d51823ebddbf9b5e05f9c3d128abb758c2b75289cb749410bb`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 53 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/checkpoint_p2_v3a.fp32.2048.6.json`：目标文件不存在，期望哈希 `f3374ac83028c61328ac4ed8f55a4d26aac64ad781494bf80fa638fb1c04bf18`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 54 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/checkpoint_p2_v3a.fp32.8192.6.json`：目标文件不存在，期望哈希 `2109774b4f5747c140460820eafd9e559fd2ba6aa3594823fd52d1839d1d9cd9`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 55 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/checkpoint_p2_v3a.fp64.1024.10.json`：目标文件不存在，期望哈希 `25e0f5cf46152d031003009b88b96a1743e45e3e435674faa1a8a5cf0d992e80`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 56 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/checkpoint_p2_v3a.fp64.1024.15.json`：目标文件不存在，期望哈希 `7271ccb6f1c859f1ad71ffa0de6021e9238bf26b0b6fd8d9880cc6f108094f7f`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 57 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/checkpoint_p2_v3a.fp64.1024.21.json`：目标文件不存在，期望哈希 `990b268c1bb0058d0c34f2fa67354a62042fee0e306b0618ad8f3a3632568e97`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 58 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/checkpoint_p2_v3a.fp64.1024.6.json`：目标文件不存在，期望哈希 `2b1765a647458f5a4f79a9ca2e936abcd1a2d7fc1669524f5959629785662740`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 59 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/checkpoint_p2_v3a.fp64.2048.10.json`：目标文件不存在，期望哈希 `c0c06cf6f935a37b51542cc1d4fa5bfb0bd069e2fe0eefbf9cb1f7e04a83bc8f`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 60 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/checkpoint_p2_v3a.fp64.2048.15.json`：目标文件不存在，期望哈希 `13a2a5f3adac1dafe2687ff3509543e5465758e2a88ea0d3db2956945bfd6190`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 61 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/checkpoint_p2_v3a.fp64.2048.21.json`：目标文件不存在，期望哈希 `25f31d70ba8b7f77110f50f916e0adfba11c7e961c28f3c5fdaacc05ad783ab2`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 62 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/checkpoint_p2_v3a.fp64.2048.6.json`：目标文件不存在，期望哈希 `7f0665f21f5a0ff69a4182b682aecc97957c448dba6d9e3192753c6e8504c51f`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 63 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/checkpoint_p2_v3a.fp64.8192.10.json`：目标文件不存在，期望哈希 `259a8703010974431d4f4a153841b6d3c2f6d7a3622224a8d3cb2913c397884d`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 64 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/checkpoint_p2_v3a.fp64.8192.15.json`：目标文件不存在，期望哈希 `68c02d39f7624941ead61317bebc0feb7299fb5fd80f82b82d5585d539bb8345`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 65 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/checkpoint_p2_v3a.fp64.8192.21.json`：目标文件不存在，期望哈希 `034c9261b27e3bcd6575b1870e937b6e49e2a49e999340a72beb0384759db093`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 66 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/checkpoint_p2_v3a.fp64.8192.6.json`：目标文件不存在，期望哈希 `d2807829f75f4ce0694c4e83038c5f0927034e16498630e8424c344f7728bde3`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 67 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/full.csv`：目标文件不存在，期望哈希 `48884d97a60523b10a3f430880f5e4f26ee9a9fd762c067bbbb606d0482ebac1`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 68 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/provenance.json`：目标文件不存在，期望哈希 `4a5e89da3944da670f001b23394c6591bd83b0f68818b0103a612542e0f10a12`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 69 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/benchmark_matched_recheck.cpp`：目标文件不存在，期望哈希 `6f4130fe02e3e34a5aa388b3dcfa91d42d90c0662b975106c38c8e466600fd2f`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 70 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/checkpoint_p3_v2b.fp32.1024.6.json`：目标文件不存在，期望哈希 `265836b7d1844e8a01583ea6cfe3997f8ae2d4d93545c89e1bd2a201834094a1`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 71 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/checkpoint_p3_v2b.fp32.2048.6.json`：目标文件不存在，期望哈希 `78fe25c73e2947fae89d654ed0983f8825a7a5b5ea0e7f82221d3229445a70a4`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 72 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/checkpoint_p3_v2b.fp32.8192.6.json`：目标文件不存在，期望哈希 `8def5eefdbbcd313604ebc76194b454660836128e746d5313282ca26f2bab855`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 73 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/checkpoint_p3_v2b.fp64.1024.10.json`：目标文件不存在，期望哈希 `02e713e92746512606ae92d0dfb7e24de50a8d765c4699867a51ede973e7b523`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 74 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/checkpoint_p3_v2b.fp64.1024.15.json`：目标文件不存在，期望哈希 `1c7b4a8a0b235aed9c27b2e12d312c40e9f6a87991df54682265a9240d990633`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 75 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/checkpoint_p3_v2b.fp64.1024.21.json`：目标文件不存在，期望哈希 `7ea05d2349f83654adbcebc90525c2b208d5e4b6d7d351c379ca2d46a814db96`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 76 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/checkpoint_p3_v2b.fp64.1024.6.json`：目标文件不存在，期望哈希 `13741833af200af82e487002e3a1af3a4d6afac8421b49ab8baf20dfd01c9488`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 77 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/checkpoint_p3_v2b.fp64.2048.10.json`：目标文件不存在，期望哈希 `6ee7140908776151c46a9cea69484ee9f55a44b1c04fbab8ee4538770a7f3b4b`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 78 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/checkpoint_p3_v2b.fp64.2048.15.json`：目标文件不存在，期望哈希 `bea3bb5cf66f62d5cbe3197766fbf478a95c5ebb2c5af335ee123e938f9ae62c`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 79 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/checkpoint_p3_v2b.fp64.2048.21.json`：目标文件不存在，期望哈希 `99d4a5857b8d9bc44e100f5c0d2c95616206e7d4f0c2c5f42101a31bdb18c15d`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 80 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/checkpoint_p3_v2b.fp64.2048.6.json`：目标文件不存在，期望哈希 `decf6a2e3824181b0b6f6c0455828762f2aface20d56968aef2ac6a09962a7f6`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 81 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/checkpoint_p3_v2b.fp64.8192.10.json`：目标文件不存在，期望哈希 `2d881a16c7c8df5a4f85d5f26706e0f9e82d4f287bcb7814f4b8fe28e2bcf23a`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 82 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/checkpoint_p3_v2b.fp64.8192.15.json`：目标文件不存在，期望哈希 `8c190405714492a604de3e8d5a33e45e7264e6df79146f59a453ed9a4958fdc2`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 83 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/checkpoint_p3_v2b.fp64.8192.21.json`：目标文件不存在，期望哈希 `7ee211069a3f6a89fa84878584f30ee38fcb367dda8937494221037b732749c0`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 84 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/checkpoint_p3_v2b.fp64.8192.6.json`：目标文件不存在，期望哈希 `0b72e12663150d29d47bc4bac0eb40a63e0408b7c4296d8a87ce6337fe23c36f`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 85 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/full.csv`：目标文件不存在，期望哈希 `b079cc998e6715b1bc350efe845e405f74aab9d21f3a52478012332c5111dd18`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 86 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/provenance.json`：目标文件不存在，期望哈希 `660046e29ebb55cdf162ce5c6c125a852341cd9eda2f19c38b4bacc431857c51`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 87 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/benchmark_matched_recheck.cpp`：目标文件不存在，期望哈希 `97fef9ecfeb3219049a0fff858c837c00d2e72fbda4f039bb796ab531a86ad20`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 88 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/checkpoint_p4_v3b.fp32.1024.6.json`：目标文件不存在，期望哈希 `d7b244365d472c6c87a4b38175ea01dcd8061f8d26fe82565a3dc23d53fd5b17`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 89 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/checkpoint_p4_v3b.fp32.2048.6.json`：目标文件不存在，期望哈希 `e131a803b9b7ac7cf9623838017764ae0b5a11bf611955e1826865a458208571`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 90 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/checkpoint_p4_v3b.fp32.8192.6.json`：目标文件不存在，期望哈希 `7aa7f536151ca9a974679c1d0d9dd9fcfe1c575398e984af8f578130b6c39edd`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 91 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/checkpoint_p4_v3b.fp64.1024.10.json`：目标文件不存在，期望哈希 `5e346431497b06b6a111691c6f910b63d3aebf20112d17499ab42ce96479bd6e`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 92 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/checkpoint_p4_v3b.fp64.1024.15.json`：目标文件不存在，期望哈希 `087839c5ae3dcefed60b52d6c21473f2b6988a3a17d3dc053c7c99d5588ecba9`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 93 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/checkpoint_p4_v3b.fp64.1024.21.json`：目标文件不存在，期望哈希 `04b021a45f7d23dad081e2f702c2443c5d46e85615f88d79b6c673f4299de936`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 94 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/checkpoint_p4_v3b.fp64.1024.6.json`：目标文件不存在，期望哈希 `9b825ef87368111816fbf0a114084709c4040d0603661a4c767227ebbec4e6cb`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 95 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/checkpoint_p4_v3b.fp64.2048.10.json`：目标文件不存在，期望哈希 `269ea1146aa9fdefa536bf3d2473610f4fa1478ace8ea67885b05c8919aabc67`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 96 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/checkpoint_p4_v3b.fp64.2048.15.json`：目标文件不存在，期望哈希 `ae93909d2a2defa1c746505655c53011237e71b0b31241a8b5dc7ebcbd445423`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 97 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/checkpoint_p4_v3b.fp64.2048.21.json`：目标文件不存在，期望哈希 `2fd4d2dbde159e24608aaf77a1b70f765a10131e8189b5d85daa661621d9cc5e`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 98 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/checkpoint_p4_v3b.fp64.2048.6.json`：目标文件不存在，期望哈希 `638894711871799e612e9c19a61dd0bb275f6e90c5b6ad1567dc602af1ddca44`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 99 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/checkpoint_p4_v3b.fp64.8192.10.json`：目标文件不存在，期望哈希 `a6ed93ab7bb4b7ec850cf9f3d9aa26ebedcb3cbc689f1d05e3b6d6f9f467e269`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 100 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/checkpoint_p4_v3b.fp64.8192.15.json`：目标文件不存在，期望哈希 `213d738d3ee43739da34eaf6335235c5b56ec6b80c3ae92361cadaa26016eb07`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 101 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/checkpoint_p4_v3b.fp64.8192.21.json`：目标文件不存在，期望哈希 `de41adcd75347dd25b2d0c6360a39c30136e9159a8b4623ec120775663b68c0c`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 102 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/checkpoint_p4_v3b.fp64.8192.6.json`：目标文件不存在，期望哈希 `c48f069a216ca44649fea8410d9e9d118a47ee75aeae24d40d0557856fc8fd82`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 103 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/full.csv`：目标文件不存在，期望哈希 `6556fce1b8e0ccc0d4213d63e057f6bf97986d9464278b0d4f3c0086f5ca6933`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 104 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/provenance.json`：目标文件不存在，期望哈希 `9eae6dfc114b419a914f7356373bfef7dda8e74a743a8bfad3a40905bb62f63e`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 105 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/benchmark_matched_recheck.cpp`：目标文件不存在，期望哈希 `ba10fe53f80b484f7ca3188c41a38c112fb78e99af50fd589036ef359bf030e8`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 106 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/checkpoint_p5_v2c.fp32.1024.6.json`：目标文件不存在，期望哈希 `7ad5e82149caf5506f5d8f418aa83e697fbc836570c5c7c26118fe52e9dd2f50`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 107 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/checkpoint_p5_v2c.fp32.2048.6.json`：目标文件不存在，期望哈希 `9b53be40cc79d3bef322ff2362bfb926a52a82e363ba3a1285a792415f1d7f02`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 108 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/checkpoint_p5_v2c.fp32.8192.6.json`：目标文件不存在，期望哈希 `c3e34b41cceda350d2034740debc817dfac552cf30af71b8ac0dd1b98de66af1`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 109 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/checkpoint_p5_v2c.fp64.1024.10.json`：目标文件不存在，期望哈希 `5b0aacbf2c4d73ccf67c079518f4c09cee720f980902406b18cdfaa6e19b64f5`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 110 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/checkpoint_p5_v2c.fp64.1024.15.json`：目标文件不存在，期望哈希 `b3af47b9abb26c47a67531c44c1a144aa0ee29530693b0c3073ec988b1d5cdb0`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 111 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/checkpoint_p5_v2c.fp64.1024.21.json`：目标文件不存在，期望哈希 `1da8ca6786b1e67f73de2630607690dd165303cdd179df432fc0bd9bd7cdf9f2`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 112 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/checkpoint_p5_v2c.fp64.1024.6.json`：目标文件不存在，期望哈希 `4e91ce722c5259c76e45013b0909b53c1c1bf68198d23be617afb92ce0f6039e`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 113 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/checkpoint_p5_v2c.fp64.2048.10.json`：目标文件不存在，期望哈希 `6515e9666c4c09a2a6b7e56e2620c4a81a765a34a80832b96c700dfaa56676fa`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 114 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/checkpoint_p5_v2c.fp64.2048.15.json`：目标文件不存在，期望哈希 `78fa6bf1588343eafecb4089428f138c5e5a070744016ef7808b5312d91546a3`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 115 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/checkpoint_p5_v2c.fp64.2048.21.json`：目标文件不存在，期望哈希 `4b914f4e4e6d988b775b044cec94829e9df5ca1eb2c0f59bc518c455fc8e4e84`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 116 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/checkpoint_p5_v2c.fp64.2048.6.json`：目标文件不存在，期望哈希 `5f3fca51b44ea0281ff8ffacd69a37ab8b87f8118af74aa29b230ca54b7181c3`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 117 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/checkpoint_p5_v2c.fp64.8192.10.json`：目标文件不存在，期望哈希 `77a0810b6c1d83a0dec24deefd40f2c214af62e00ceb66e5a6a1b642a3939404`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 118 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/checkpoint_p5_v2c.fp64.8192.15.json`：目标文件不存在，期望哈希 `e72e94e4e8ecd7c13c0b0930a10c88030a2179b89d6773bc1371c69202995285`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 119 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/checkpoint_p5_v2c.fp64.8192.21.json`：目标文件不存在，期望哈希 `650f3627340fb1448bf4584862dd3b62d36a853711997e1f11507b95a15d2305`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 120 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/checkpoint_p5_v2c.fp64.8192.6.json`：目标文件不存在，期望哈希 `6e5c7608cc9f7882aac8e0d5ee1c35c5471407372dc1af2c11d9c30de0f15fb1`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 121 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/full.csv`：目标文件不存在，期望哈希 `9ea9448a8e4e0ba3a1537fc692192c57b61694769df3baa96cb3c52c717f1b0e`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 122 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/provenance.json`：目标文件不存在，期望哈希 `d1b259bd9257040f5174943ccb818daa7ce19782ccaf89790c54d9d38d8d3f81`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 123 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/run_matched_recheck.sh`：目标文件不存在，期望哈希 `e0b5bb6ada2ca334b79dd54d434e993328ca1841cb71d228337bc2cf149eaee7`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 124 行 `repo/bench/8454h/mkl_roofline_v3/matched_recheck/write_provenance.py`：目标文件不存在，期望哈希 `5368a0777d3a21bf42bdff6095a2e1d8ec51e711b003c9983b4d04ae9038254e`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 125 行 `repo/bench/8454h/mkl_roofline_v3/provenance.json`：目标文件不存在，期望哈希 `7124790f87fb8925946e7b3a5abfb31b06f6a4a58df1224c9518528871119f70`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 126 行 `repo/bench/8454h/mkl_roofline_v3/run.sh`：目标文件不存在，期望哈希 `d5c1810d0cb912e9c779877751e9ec6a22457a0268a0d4edeccf9288a269821d`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 127 行 `repo/bench/8454h/mkl_roofline_v3/run_command.txt`：目标文件不存在，期望哈希 `6b0f6b2b179fe6d1fda355df3c7eae20101aa55f267b9da83e338e18075b2b0e`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 128 行 `repo/bench/8454h/mkl_roofline_v3/source_hashes.sha256`：目标文件不存在，期望哈希 `3a6fa7435aae952905b9df5470ae8b4182d77266fcc5ec32271b847593a7894b`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 129 行 `repo/bench/8454h/roofline/binary_gate.json`：目标文件不存在，期望哈希 `78c9f28cf1b8e945f06198c220cc2fbe613ad983592bdca48c6aa8c4e64e8345`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 130 行 `repo/bench/8454h/roofline/binary_gate_attempt1.json`：目标文件不存在，期望哈希 `7ebb5f00553ebf051ace74d9e5b990048af0403b6f08c0635702d46dfc933dd9`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 131 行 `repo/bench/8454h/roofline/calibration/kernel_disassembly.txt`：目标文件不存在，期望哈希 `70150b8a81e855d2e4e4d85188c2405a1471a0e65654805bb31f48da7a22f1db`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 132 行 `repo/bench/8454h/roofline/calibration/kernel_metadata.json`：目标文件不存在，期望哈希 `31b78b215ca5c1403b3338117dd8b13d79feed6b7ca695c483d5368a752fc79b`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 133 行 `repo/bench/8454h/roofline/calibration/kernel_summary.json`：目标文件不存在，期望哈希 `abc759689293fcb676f2e7e518233f5c028126875acdade482890e8d637eb687`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 134 行 `repo/bench/8454h/roofline/calibration/kernels.csv`：目标文件不存在，期望哈希 `2ab37da6f56bdbbc2459f5788ce379c868b4fc0c1c9ff29db50ccacb7a105179`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 135 行 `repo/bench/8454h/roofline/calibration/summarize_kernels.py`：目标文件不存在，期望哈希 `7cfb1d7c3fb43b123b61a715375c154c965bb759992b6936900ce6d29fb0bdb0`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 136 行 `repo/bench/8454h/roofline/extended47_cache_gate.json`：目标文件不存在，期望哈希 `bb9445c58410c50dd5438eace8a3e9803b6ac25e05bd13cce83de79c7f998d5b`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 137 行 `repo/bench/8454h/roofline/ideas/adaptive_block.patch`：目标文件不存在，期望哈希 `83a3a0a2aa8e47cfd450bc0d439df3065d3980ec7816c5e17359eb7dc0214c7f`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 138 行 `repo/bench/8454h/roofline/ideas/batch64.md`：目标文件不存在，期望哈希 `3979767c784308d39bd15a73777565afc790bbacf8c12c1512c1daa3a0b9dc08`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 139 行 `repo/bench/8454h/roofline/ideas/batch64.patch`：目标文件不存在，期望哈希 `603e7ea15d12e63df2d42ef6419a6c60db4804c2cb1adb2fbc3849db488e7b66`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 140 行 `repo/bench/8454h/roofline/ideas/hugepages.patch`：目标文件不存在，期望哈希 `c15bce4bda003a892c3457d91d140275d62300415f8e729a6106958fe30ef0eb`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 141 行 `repo/bench/8454h/roofline/ideas/numa_b.md`：目标文件不存在，期望哈希 `56736fe967d698aaa3a966de7b5a35da02f675d120964498a4579d45b08d0ae0`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 142 行 `repo/bench/8454h/roofline/ideas/numa_b.patch`：目标文件不存在，期望哈希 `3e3b8154f1385fa41bb8e379d15ca5f7bd3ae76b3e14fc4af84e633d82e9df0b`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 143 行 `repo/bench/8454h/roofline/ideas/numa_b_gate.json`：目标文件不存在，期望哈希 `7726c9853e00ba16bbcf6ab9c6e0dcdf4198ff57bdbbeb1ea35ed24d90a4334d`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 144 行 `repo/bench/8454h/roofline/ideas/numa_b_gate.sh`：目标文件不存在，期望哈希 `0b32fda13e546740fba0e79cc3bf1479e9c35b86c35e9c2cc01f9aa758672948`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 145 行 `repo/bench/8454h/roofline/ideas/numa_b_metadata.json`：目标文件不存在，期望哈希 `8496ca66f17e2ecb058743f81ad4963876294d516ab91a6b3b84abf08b1a9ef9`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 146 行 `repo/bench/8454h/roofline/ideas/numa_b_trigger_probe.json`：目标文件不存在，期望哈希 `ae10e06206e8eb15266bae04b4b19628b523c232269df7f8b899f13d9066e44f`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 147 行 `repo/bench/8454h/roofline/ideas/numa_partial_b.patch`：目标文件不存在，期望哈希 `a5bf451dbbc7cf6f236fed8d97427e933e7972992d5524fb13a5611ac69858ea`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 148 行 `repo/bench/8454h/roofline/ideas/pad_batch.patch`：目标文件不存在，期望哈希 `67207dd94c7559ea7e41719141c58001798147f4628084f76eb7e117d9088ca2`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 149 行 `repo/bench/8454h/roofline/ideas/rectangular_block.patch`：目标文件不存在，期望哈希 `8322207d9c5306a2fb0a8a193328cfb2339d100d6add2efd8b2ca84935e3eba0`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 150 行 `repo/bench/8454h/roofline/memory_calibration_20261013.csv`：目标文件不存在，期望哈希 `e5182d431eb28467f3ab9d457a45fce71298b2e3562d5f378dbf5466bae4f402`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 151 行 `repo/bench/8454h/roofline/memory_calibration_20261013.disasm.txt`：目标文件不存在，期望哈希 `777f2ea70a2eeeca347d0ef7923fe79a43a567fdca15a3340699609ce3e5430f`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 152 行 `repo/bench/8454h/roofline/memory_calibration_20261013.json`：目标文件不存在，期望哈希 `cd855a2fbbd3053e11ae6b56b1673ea195cd421d6b53272df0222b40cf692f33`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 153 行 `repo/bench/8454h/roofline/noomp_build/build_manifest.json`：目标文件不存在，期望哈希 `c9524b1851933544c11e8057acf67cf09b66d621358a34f2b65f1afaa4f4f012`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 154 行 `repo/bench/8454h/roofline/noomp_build/ctest.log`：目标文件不存在，期望哈希 `9ce6248af3c06c71e70fa9e3b71b3b2b80a1d3daf6b51f02cb6fa0bdeee84755`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 155 行 `repo/bench/8454h/roofline/noomp_gate.json`：目标文件不存在，期望哈希 `3ff76f03d9407bd397c5f4c969a6eced302cc6e92cda560e0436c14130aa398c`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 156 行 `repo/bench/8454h/roofline/production_native_audit.json`：目标文件不存在，期望哈希 `0ae8608c76719e771049111ac49247efa34714cceed850d63543d40a39e3b2a6`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 157 行 `repo/bench/8454h/roofline/production_validation.json`：目标文件不存在，期望哈希 `b787f4ac421c31ec87d79fb9741aee40a89f518ffc435deef2317c28d67eaceb`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 158 行 `repo/bench/8454h/roofline/run_binary_gate.py`：目标文件不存在，期望哈希 `491c6b750e984c2f2fcee90d167f890ca0ab53209eecf23a9cb96ef479101dfc`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 159 行 `repo/bench/8454h/roofline/run_extended47_stream.py`：目标文件不存在，期望哈希 `1e6c2fca91210e18cf85ffa955c516cc1a72e26d8bd857feaab5772588bc14d8`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 160 行 `repo/bench/8454h/roofline/run_kernel_calibration.sh`：目标文件不存在，期望哈希 `b774dbb7fb4e663842e1a878eff9cf8a24d80f7b5323aab8cecb52da3b0ef779`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 161 行 `repo/bench/8454h/roofline/run_memory_calibration.sh`：目标文件不存在，期望哈希 `ab13ca6f56c9525e7406ba033d6c4d6c529ae01e8f8d19da360ab34c6159c418`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 162 行 `repo/bench/8454h/roofline/search_adaptive/metadata.json`：目标文件不存在，期望哈希 `733be0ff389843f5ff29aea00c282cbf6eb7e364fd627dcba0a68114740cb953`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 163 行 `repo/bench/8454h/roofline/search_adaptive/pass0_frozen.csv`：目标文件不存在，期望哈希 `3a2889b59beb95bbaa3d9b33012ca5a5583c1e3dd925535b5837fc31b51b915f`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 164 行 `repo/bench/8454h/roofline/search_adaptive/pass1_adaptive.csv`：目标文件不存在，期望哈希 `6db616d269b3336367502ec1b3b5b72c0f15eb4cb0585037ff4cb0ff94532428`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 165 行 `repo/bench/8454h/roofline/search_adaptive/pass2_frozen.csv`：目标文件不存在，期望哈希 `b6757256377951b0bb515fd92122715f594f06925998152f7d0afdca30f0abc2`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 166 行 `repo/bench/8454h/roofline/search_adaptive/pass3_adaptive.csv`：目标文件不存在，期望哈希 `56997f47288b2995c19ab7f0ffc4accb83401331e254ee4732faf669f2622265`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 167 行 `repo/bench/8454h/roofline/search_adaptive/pass4_frozen.csv`：目标文件不存在，期望哈希 `8b4553315c71e52d2d2717df23977fb5a5a30a9508cd6047effdc2c1fa1ca253`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 168 行 `repo/bench/8454h/roofline/search_adaptive/summary.json`：目标文件不存在，期望哈希 `d5c695fe38455f5c6c2e23f4ea9227f18d5ec442c148b7cdc2d2f119680addbe`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 169 行 `repo/bench/8454h/roofline/search_batch64/comparison.json`：目标文件不存在，期望哈希 `e34f53517a5297305bd820c5290fc485f04e36e885d368fd75b299c277c19461`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 170 行 `repo/bench/8454h/roofline/search_batch64/metadata.json`：目标文件不存在，期望哈希 `8faca76f1ac799c0819ad712f04f01ddcfb618266d5a35fae3f652620673180b`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 171 行 `repo/bench/8454h/roofline/search_batch64/run01_frozen_before.csv`：目标文件不存在，期望哈希 `28bb7cf3f1a2865bb2ccf383555426259217bf63fe400c1e7be368a69b5b6939`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 172 行 `repo/bench/8454h/roofline/search_batch64/run02_batch1.csv`：目标文件不存在，期望哈希 `3b82ba68567aeae5b1c0064ec72c21ece7d36e86eaf454fa828636db1301727b`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 173 行 `repo/bench/8454h/roofline/search_batch64/run03_batch2.csv`：目标文件不存在，期望哈希 `3b70af9da6793ea75fa63fba4cc9516299d6e427cdc66dd83e00c0197a05542d`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 174 行 `repo/bench/8454h/roofline/search_batch64/run04_batch4.csv`：目标文件不存在，期望哈希 `ddd97179a0c147d129eaef72711decb6376300bcb220b272f816544dfb72adda`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 175 行 `repo/bench/8454h/roofline/search_batch64/run05_frozen_middle.csv`：目标文件不存在，期望哈希 `4d18bd77cb62ed544c7fdf889c9af912f3ca75d717d595ae6eb5eadab2f96236`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 176 行 `repo/bench/8454h/roofline/search_batch64/run06_batch4_repeat.csv`：目标文件不存在，期望哈希 `7b6fbae4ec46c3d64a3092e4616d00785a1e01d008b0918e5b09bd30741276d8`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 177 行 `repo/bench/8454h/roofline/search_batch64/run07_batch2_repeat.csv`：目标文件不存在，期望哈希 `e56dda422d5e65ba8491dc4ccfdc232903f58dcf1df03a60665919be6ffaaba1`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 178 行 `repo/bench/8454h/roofline/search_batch64/run08_frozen_after.csv`：目标文件不存在，期望哈希 `42cdf51e1bd5e6132fbc23461360c0cb858e12c53fc90a6699bd3eee95c9f990`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 179 行 `repo/bench/8454h/roofline/search_batch64/runner.sh`：目标文件不存在，期望哈希 `81605acd45253fa49ffdfb7bba1885a64119e433af368f53ee6e8b834a24fa05`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 180 行 `repo/bench/8454h/roofline/search_commands.md`：目标文件不存在，期望哈希 `70a35e7ac28d1e9c596d1c06d0550e98ae60ca9b4c107cdec36201b677c34752`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 181 行 `repo/bench/8454h/roofline/search_numa_b/RESULTS.md`：目标文件不存在，期望哈希 `5f4788c56c1bac5f11604dca8b4f7619487014185f6dbfc26fd0f424edc7c036`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 182 行 `repo/bench/8454h/roofline/search_numa_b/analyze.py`：目标文件不存在，期望哈希 `44eb5a62d7b8e2e50f55434e2e624330b4f25d05c4ac0821c97810b06471338b`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 183 行 `repo/bench/8454h/roofline/search_numa_b/comparison.json`：目标文件不存在，期望哈希 `413b420ad3a506ed16777d621e1776b06c21ce241bc5965579b1b0183b90122d`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 184 行 `repo/bench/8454h/roofline/search_numa_b/completed_utc.txt`：目标文件不存在，期望哈希 `97d62b9cb9832708a43a5058082787305446f0264423d2ced8a33b05b2e6ff78`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 185 行 `repo/bench/8454h/roofline/search_numa_b/completion_manifest.json`：目标文件不存在，期望哈希 `51c23da201a79d813a7ae2eca81c1292027af6074a9b1c0cd04895f2eeb9166f`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 186 行 `repo/bench/8454h/roofline/search_numa_b/logs/run_order.log`：目标文件不存在，期望哈希 `098ad505da4639432511cd4560744657a5224977acddc41ddd5edb8ccd0c8652`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 187 行 `repo/bench/8454h/roofline/search_numa_b/raw/control0_4g.csv`：目标文件不存在，期望哈希 `9d01006ec2f57bef77636f61b2519137c784b21de9b59b5386afcaba152cb4ba`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 188 行 `repo/bench/8454h/roofline/search_numa_b/raw/frozen_4g_a.csv`：目标文件不存在，期望哈希 `9fc117134a95ec8a3faced5392b0e625c1f6f51d60a42c7044013a4121811d31`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 189 行 `repo/bench/8454h/roofline/search_numa_b/raw/frozen_4g_b.csv`：目标文件不存在，期望哈希 `505af36b1e1dc4be14c5775108c87fa1dbe6e9b0f90168f6158ce3297d883386`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 190 行 `repo/bench/8454h/roofline/search_numa_b/raw/frozen_4g_c.csv`：目标文件不存在，期望哈希 `b675a15817cbd1f837ee572633aec9fbdb2a4f18bfdf995cdd73cd2e41eca207`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 191 行 `repo/bench/8454h/roofline/search_numa_b/raw/numa1_4g_a.csv`：目标文件不存在，期望哈希 `b58a6ef4b003175b68e50e330ab1a6b43b933be8d0a8dd4fa22f5e02bad12118`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 192 行 `repo/bench/8454h/roofline/search_numa_b/raw/numa1_4g_b.csv`：目标文件不存在，期望哈希 `5529b3fe77c7249cc1ca9a08d6a35d975845c323b7c3bb06a2b0bd3940b53201`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 193 行 `repo/bench/8454h/roofline/search_numa_b/run_manifest.json`：目标文件不存在，期望哈希 `fe7c1398f78cda0109fcfb8517f45f1119126ff8d672668e1e99399aef42280f`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 194 行 `repo/bench/8454h/roofline/search_numa_b/runner.sh`：目标文件不存在，期望哈希 `67a1f6ca0504035bdcf0fa292021e691c35bd5a2695e5dbbfbab63d8e8119a40`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 195 行 `repo/bench/8454h/roofline/search_numa_half/2g/RESULTS.md`：目标文件不存在，期望哈希 `bd23cf4831d06e64e55b26d7749c888eb8fbedadfa3322b01c4967e665f7fbcb`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 196 行 `repo/bench/8454h/roofline/search_numa_half/2g/analyze.py`：目标文件不存在，期望哈希 `23a861f0ed76d805e9a69fcbf29dc0bac930a16a586aeaa91d60463d41462903`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 197 行 `repo/bench/8454h/roofline/search_numa_half/2g/comparison.json`：目标文件不存在，期望哈希 `1db5da952fadf491f862a8a3555cdf03d8e262b186486f6ac0b63f7a5b3be2aa`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 198 行 `repo/bench/8454h/roofline/search_numa_half/2g/completed_utc.txt`：目标文件不存在，期望哈希 `67a9eb865037c0ffbb02c11e2c8fc476ff82e7ebc75c66a82223c78f31274470`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 199 行 `repo/bench/8454h/roofline/search_numa_half/2g/completion_manifest.json`：目标文件不存在，期望哈希 `46565faae7daf515befdb552a4fd386832ef8a968bf1155aa1d85633e4f6d3e8`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 200 行 `repo/bench/8454h/roofline/search_numa_half/2g/logs/run_order.log`：目标文件不存在，期望哈希 `410566801b167bc521c49c91c1366d477deab70d48d00543b65fd2e98b0f247f`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 201 行 `repo/bench/8454h/roofline/search_numa_half/2g/raw/control0_2g.csv`：目标文件不存在，期望哈希 `4ff5d8bec913f19f1c2456d52dabb9b0e2e48f6ff4aa526177ca44baa48f50fd`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 202 行 `repo/bench/8454h/roofline/search_numa_half/2g/raw/frozen_2g_a.csv`：目标文件不存在，期望哈希 `b2dbf4b15754f9aaaebdb3d6354fd10124b6da49cb20a0fdb3e1a5a06e50d5d5`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 203 行 `repo/bench/8454h/roofline/search_numa_half/2g/raw/frozen_2g_b.csv`：目标文件不存在，期望哈希 `e3d2c6872c2340dfa1c8f5cc7c0e4319f0bda12fd2e231323fcc8eee85601436`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 204 行 `repo/bench/8454h/roofline/search_numa_half/2g/raw/frozen_2g_c.csv`：目标文件不存在，期望哈希 `e0f426186b2f624ba20d29d836ea2dd53d6b1b23c00c0294f88613a88085253a`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 205 行 `repo/bench/8454h/roofline/search_numa_half/2g/raw/numa_half_2g_a.csv`：目标文件不存在，期望哈希 `52f35452bd5b5170df5afd84cdb54c41948ad7017474cdb180d93265c9fbe647`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 206 行 `repo/bench/8454h/roofline/search_numa_half/2g/raw/numa_half_2g_b.csv`：目标文件不存在，期望哈希 `69153aeb49546280be8c2fa56d2c4805138c92b0d25939425f1f8222a56ab20a`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 207 行 `repo/bench/8454h/roofline/search_numa_half/2g/run_manifest.json`：目标文件不存在，期望哈希 `766e762a2c5a94b465d244ae4ca318ec9c94395fab09216b996812be78c12086`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 208 行 `repo/bench/8454h/roofline/search_numa_half/2g/runner.sh`：目标文件不存在，期望哈希 `11f046397a0b3998769bf17688090f3f93031f5531ebcc871d4b7d7bbc0f502f`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 209 行 `repo/bench/8454h/roofline/search_numa_half/4g/RESULTS.md`：目标文件不存在，期望哈希 `889fa1bb74a1df9a2c54f55679d9aa5f4045e231f3b90fe70127cb69e12bfa3e`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 210 行 `repo/bench/8454h/roofline/search_numa_half/4g/analyze.py`：目标文件不存在，期望哈希 `23a861f0ed76d805e9a69fcbf29dc0bac930a16a586aeaa91d60463d41462903`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 211 行 `repo/bench/8454h/roofline/search_numa_half/4g/comparison.json`：目标文件不存在，期望哈希 `c6e1fb854545e19f219d902882dc85d5f2cfd8c7b233746faf8bbe038b2daf30`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 212 行 `repo/bench/8454h/roofline/search_numa_half/4g/completed_utc.txt`：目标文件不存在，期望哈希 `7094b7b54b72c1fb38eac7ca8de886add3652a4a365b37a48e4aab434613c925`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 213 行 `repo/bench/8454h/roofline/search_numa_half/4g/completion_manifest.json`：目标文件不存在，期望哈希 `b95597d33fe149f83c51ad451f4f3097b74192e1cc11ee29d6370fe9c983d036`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 214 行 `repo/bench/8454h/roofline/search_numa_half/4g/logs/run_order.log`：目标文件不存在，期望哈希 `c287dc6c4bddb3ad469b0f6754b803f5d54af6d810acdf8df0f9cb302a9c57d0`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 215 行 `repo/bench/8454h/roofline/search_numa_half/4g/raw/control0_4g.csv`：目标文件不存在，期望哈希 `54b4dd67466294ae9166ac59c3b0ed7db870ccd6ea967d89df9d052a704c91a7`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 216 行 `repo/bench/8454h/roofline/search_numa_half/4g/raw/frozen_4g_a.csv`：目标文件不存在，期望哈希 `8f6f3bc8a04f90ddcf3c62437dedf17ddc1bb0668fc63c343f93d28720ba6e3d`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 217 行 `repo/bench/8454h/roofline/search_numa_half/4g/raw/frozen_4g_b.csv`：目标文件不存在，期望哈希 `34aa1aa81c8b11db2b9f6b2ce81a51d63403b4f5941822863270c09a3d67574d`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 218 行 `repo/bench/8454h/roofline/search_numa_half/4g/raw/frozen_4g_c.csv`：目标文件不存在，期望哈希 `cd632ed899b6193c32c8c5a948d6e28be34849f878f5619ff47052be03a08f49`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 219 行 `repo/bench/8454h/roofline/search_numa_half/4g/raw/numa_half_4g_a.csv`：目标文件不存在，期望哈希 `3d94daf4d7799696fc569af0c68dcbe5e9cb79bf6c4eb2c38ee859abc1ecb3a8`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 220 行 `repo/bench/8454h/roofline/search_numa_half/4g/raw/numa_half_4g_b.csv`：目标文件不存在，期望哈希 `4ceaaafc73db29e9ff692f3c6654032404ce7b60cc08f3ab6b0fa582e7e3fb43`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 221 行 `repo/bench/8454h/roofline/search_numa_half/4g/run_manifest.json`：目标文件不存在，期望哈希 `7e1aea43fe85920ff80bf049706810b921b57f4050f6cd928825c037e2a0cb1d`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 222 行 `repo/bench/8454h/roofline/search_numa_half/4g/runner.sh`：目标文件不存在，期望哈希 `495184988c2e32645673b096913ba7602d786fb99fdea54648c7651389ce2957`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 223 行 `repo/bench/8454h/roofline/search_numa_half/README.md`：目标文件不存在，期望哈希 `f03948e5dbb324177847870bb56b59bb8d759577dc463c19bdd0ad0cae9948c3`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 224 行 `repo/bench/8454h/roofline/search_pad/metadata.json`：目标文件不存在，期望哈希 `573eaefe2a37c0dab3fd4b8013d2f799be1c59cdb73749884c9d897e4b4c53cc`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 225 行 `repo/bench/8454h/roofline/search_pad/pass0_frozen.csv`：目标文件不存在，期望哈希 `bca12f0da204f8167ede80a3eeebad682ed3c361969737b60c779ce73c43cb04`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 226 行 `repo/bench/8454h/roofline/search_pad/pass1_p1b1.csv`：目标文件不存在，期望哈希 `1380074b09f0b66d4d0b4a7ddb9215ccc386398758b2ba4ddfcbd14cb680bdce`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 227 行 `repo/bench/8454h/roofline/search_pad/pass2_p2b1.csv`：目标文件不存在，期望哈希 `9e1972ca5a41bfbc8e03bc8d238a1484d7cdc44aa5837b88ed90a889555b8af4`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 228 行 `repo/bench/8454h/roofline/search_pad/pass3_p3b1.csv`：目标文件不存在，期望哈希 `91e9f4d17be0e476a62098008fba14b2dd5b916b47ff274703674445aefd1b53`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 229 行 `repo/bench/8454h/roofline/search_pad/pass4_p1b2.csv`：目标文件不存在，期望哈希 `8ce798c43a2ce5e868ff2a12bb12fb1a0d3cf4c4fbf2391bdc2d94a6a6d286cf`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 230 行 `repo/bench/8454h/roofline/search_pad/pass5_frozen.csv`：目标文件不存在，期望哈希 `9194904a76331093492c9c2cb79e1821145ea52c3da1a1f67d923d4ff2f44c65`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 231 行 `repo/bench/8454h/roofline/search_pad/pass6_p1b2.csv`：目标文件不存在，期望哈希 `79122ce1ddf151f1452cbddc15c1e7bbffae3ff5049b14fc4ccb64e387de42cc`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 232 行 `repo/bench/8454h/roofline/search_pad/pass7_p1b1.csv`：目标文件不存在，期望哈希 `c7eba79463cbd3915cb1f2a7915dfda1deff8c9fe925209a3c2c56458ee83989`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 233 行 `repo/bench/8454h/roofline/search_pad/pass8_frozen.csv`：目标文件不存在，期望哈希 `da15a551198a351eab5b61588962d0465e6444a2ed8d72a6f40373de4200c7cc`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 234 行 `repo/bench/8454h/roofline/search_pad/summary.json`：目标文件不存在，期望哈希 `18ae3893c2fa8f0fc2a5b70655057548a5b8276271c160070dc85509f1b500f4`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 235 行 `repo/bench/8454h/roofline/search_rect/metadata.json`：目标文件不存在，期望哈希 `5acdfdf672d97b5694eab895e020a52d329a321e49ce3c1fbe1b24499ee16e4a`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 236 行 `repo/bench/8454h/roofline/search_rect/pass0_frozen.csv`：目标文件不存在，期望哈希 `0f0d265b6216d3e62d5489462443b8ec130b730a85cd4463dab55ca37320d19d`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 237 行 `repo/bench/8454h/roofline/search_rect/pass1_n256p1.csv`：目标文件不存在，期望哈希 `223f09d5f0438ee517b76d2147777d4d8fe96091c989b021f42503f5ee377698`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 238 行 `repo/bench/8454h/roofline/search_rect/pass2_n512p1.csv`：目标文件不存在，期望哈希 `1e312a63876bdbd50faad369717221e244b338539bfa196816fd22ff8d5e9976`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 239 行 `repo/bench/8454h/roofline/search_rect/pass3_n256p0.csv`：目标文件不存在，期望哈希 `f2f16cf9cb4b6e063198c4b2605935b130bc84d176efde1bb5ecc93a1996893e`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 240 行 `repo/bench/8454h/roofline/search_rect/pass4_n256p1b2.csv`：目标文件不存在，期望哈希 `8f16f033dff790d9a0de8ee2d0ff185cdb34e19a979a813a46601a631c3598a1`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 241 行 `repo/bench/8454h/roofline/search_rect/pass5_frozen.csv`：目标文件不存在，期望哈希 `ea83bf048337169a0e12940d2db00e76f9ee14ba17ed26b40a987e87cd77682e`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 242 行 `repo/bench/8454h/roofline/search_rect/pass6_n256p1.csv`：目标文件不存在，期望哈希 `8b53f3d75361a0f196baa7170de4ba422a950bba7d8a05017af596a5931f5549`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 243 行 `repo/bench/8454h/roofline/search_rect/pass7_n512p1.csv`：目标文件不存在，期望哈希 `0d57be2e3c622ee2e39b528227467f9fe64ba73f1e5cec8882e10b404689204f`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 244 行 `repo/bench/8454h/roofline/search_rect/pass8_frozen.csv`：目标文件不存在，期望哈希 `3a67cdd1924cd02c793311b1d10389fcef2687feedc4bb6171958ef40ce00ce8`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 245 行 `repo/bench/8454h/roofline/search_rect/summary.json`：目标文件不存在，期望哈希 `2da297ffb7ed08277a8cfc4086200fd1c9eee7fdb01a15d670d7e09515e8ae71`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 246 行 `repo/bench/8454h/roofline/search_thp/metadata.json`：目标文件不存在，期望哈希 `869c55af72c9af620233cde2d131d85147afb89b17ab11dd1d0135417128e5e4`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 247 行 `repo/bench/8454h/roofline/search_thp/pass0_frozen.csv`：目标文件不存在，期望哈希 `d0ac190b518664921d84932ce041f5b4c6d6c44f80b3835865b509b8bdafc16d`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 248 行 `repo/bench/8454h/roofline/search_thp/pass1_h1.csv`：目标文件不存在，期望哈希 `7a9c13c6572815f1bc0c781ab5aab544082013efe24e5bbc8138e270c94d59e9`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 249 行 `repo/bench/8454h/roofline/search_thp/pass2_frozen.csv`：目标文件不存在，期望哈希 `feda14031f8e23268e8f6d5bb87e5cfe8c939448b44aab78579d09cea8277b84`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 250 行 `repo/bench/8454h/roofline/search_thp/pass3_h1.csv`：目标文件不存在，期望哈希 `fb0808fdc5dafb7c58349cb6f27156b8d1f9d72e7eec0454bfe0f5419c0df2ae`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 251 行 `repo/bench/8454h/roofline/search_thp/pass4_frozen.csv`：目标文件不存在，期望哈希 `6507559740b67ddc7fd904d4b359e5455294f2ee8727bc866dd98bfea007802f`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 252 行 `repo/bench/8454h/roofline/search_thp/probe_hint0.json`：目标文件不存在，期望哈希 `52bb90d999ea7eae7a9e8af0feb53d74eb0b24c5205a041d7931b26f20410526`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 253 行 `repo/bench/8454h/roofline/search_thp/probe_hint1.json`：目标文件不存在，期望哈希 `25561620b15e3a1efde278a839ef51f9b4dd1e190b37d01854e03f1ee89670ed`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 254 行 `repo/bench/8454h/roofline/search_thp/summary.json`：目标文件不存在，期望哈希 `43f5a99b9f6781b4e7a35212b713f430d410a59c2e1111c6d44d2afdeb31fbbb`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 255 行 `repo/bench/8454h/roofline/summarize_searches.py`：目标文件不存在，期望哈希 `b7d43742c63a45fbb57c5583e28692805dfae4bd6dac63b2c6e8fbc94ff1828b`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 256 行 `repo/bench/8454h/roofline/traffic_model.json`：目标文件不存在，期望哈希 `73215d85e4757802049ff1eaa9c1075333fbebe725ad898ce9e310f30a981ca8`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 257 行 `repo/bench/8454h/run_equivalence.sh`：目标文件不存在，期望哈希 `cb85f10f02e97d76891bd2def5847d276511e100630015d4df9f17e3e6140df9`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 258 行 `repo/bench/8454h/versions/v2/MANIFEST.sha256`：目标文件不存在，期望哈希 `0811f7ba2169b4ca37de5a3ac670cd54435572cd7d30cf909ae7a6d992c6463e`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 259 行 `repo/bench/8454h/versions/v2/README.md`：目标文件不存在，期望哈希 `36b06f6a32bd34457233a31737dc0bdf887a0363585a6fbe285c066a10218527`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 260 行 `repo/bench/8454h/versions/v2_release/MANIFEST.sha256`：目标文件不存在，期望哈希 `8b68d0d095b38f117cb10083ae5272847c533821d037fbdba7c091b06e6d950b`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 261 行 `repo/bench/8454h/versions/v2_release/README.md`：目标文件不存在，期望哈希 `4d1d0c9a4693ccf18d8ce2090c9e2e28ed5935d9a9896b70d51481d3783db24d`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 262 行 `repo/bench/benchmark.cpp`：目标文件不存在，期望哈希 `1ff045bd32a5f77686ce27e5d8bb1406b5887b43ed1158c25653dcf13c80a5c6`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 263 行 `repo/bench/optimization_benchmark.cpp`：目标文件不存在，期望哈希 `54ca1dea3c988d41cf012191bbaea6e51d39a09020c6b5f14829d7e37b788d05`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 264 行 `repo/bench/run_8454h_baseline.sh`：目标文件不存在，期望哈希 `ab619ea24be77ced4ca77651b4a2f43124632e4857d236c0213373956e1be7ae`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 265 行 `repo/bench/run_extended_validation.sh`：目标文件不存在，期望哈希 `871c2fb66f4e1d61522f91c1a3f60c1d718c825cb7e1032a978a4f9efc3387bb`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 266 行 `repo/bench/run_packed_panel_audit.sh`：目标文件不存在，期望哈希 `9e07f723c4a35bf8f1ac4b413a3e08bf3bb94c786f096b63c4bf343ea4a5f055`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 267 行 `repo/docs/8454H_FINAL_PERFORMANCE_REPORT.md`：目标文件不存在，期望哈希 `23b841d5532e39fc8f29de8b8828e1b9ed338b43dad6b1670325ba3c70ebc639`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 268 行 `repo/docs/8454H_KERNEL_IDEAS.md`：目标文件不存在，期望哈希 `e8a0b3a5cb0a673d4e2633530976fff5c87a10dfe78b306d15908b26cb15c9a2`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 269 行 `repo/docs/8454H_PERFORMANCE_BASELINE.md`：目标文件不存在，期望哈希 `b4c6d7ae5144f59cef747a1d255ed3efdc7419a34f337608995233d2bff24a5d`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 270 行 `repo/docs/8454H_ROOFLINE_CALIBRATION.md`：目标文件不存在，期望哈希 `9d73b4705687383f16d729399e54c70406e041a02f3f0160535892252284e4d3`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 271 行 `repo/docs/8454H_ROOFLINE_MODEL.md`：目标文件不存在，期望哈希 `790cb3ac0faeb8f7e6d092f1fcc2b87d3b9e1d8d3120958076dfa15fb4d0e8e4`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 272 行 `repo/docs/8454H_ROOFLINE_RESULTS.md`：目标文件不存在，期望哈希 `4642c3a73a2f61c46536ab31c91d039803056415e76f1419914101e89dc403f7`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 273 行 `repo/docs/8454H_ROOFLINE_SEARCH_LOG.md`：目标文件不存在，期望哈希 `5f876492e80abe4c29ca973552333d297f54cf5272872bd0b9c498ecde436876`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 274 行 `repo/docs/8454H_ROOFLINE_TRAFFIC.md`：目标文件不存在，期望哈希 `f9c9c0f595e66edea33c76571caa7be400e1f5f2747a176aadf0a97d92b82726`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 275 行 `repo/docs/8454H_SEARCH_RESULTS.md`：目标文件不存在，期望哈希 `f4d83bc8c1ce044d4e247937b1c6520321456ef1b2559977ef316a29b849cbcc`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 276 行 `repo/docs/figures/8454H_ROOFLINE_AMX_LOGICAL_AI.png`：目标文件不存在，期望哈希 `546102a88dd355780e9677739a49c1d42b19f7fab1528207c1addc6016dcd813`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 277 行 `repo/docs/figures/8454H_ROOFLINE_AMX_LOGICAL_AI.svg`：目标文件不存在，期望哈希 `67ed200b2e952d3feebd6caf7ffc67cb36d23b3680d4df2714a2ec0a7474357e`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 278 行 `repo/docs/figures/8454H_ROOFLINE_PLOTS_METADATA.json`：目标文件不存在，期望哈希 `f17ffe85b0da1480e7360b8e2ff63392bba5c4812e8b4bd7a03f2ce1f15c9d60`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 279 行 `repo/docs/figures/8454H_ROOFLINE_STAGE_DIAGNOSTIC.png`：目标文件不存在，期望哈希 `d9ec211e00ed7704526af01754ae168fefc68c875535d952dff8f9646f225584`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 280 行 `repo/docs/figures/8454H_ROOFLINE_STAGE_DIAGNOSTIC.svg`：目标文件不存在，期望哈希 `0bbebf9ed12d877e038d1461b94dd437345d2128ef082e65a7f27e0507a4ef12`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 281 行 `repo/include/ozamx/gemm.hpp`：目标文件不存在，期望哈希 `0430c3df107909436d7abf6afa037bfcc6ced94689660a8929fe9e00640241b5`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 282 行 `repo/src/gemm.cpp`：目标文件不存在，期望哈希 `7a4d0311dd12ee9a8a0ef6a3dca42bec6dca8a36ec34782da603b84c2419a164`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 283 行 `repo/src/kernels.S`：目标文件不存在，期望哈希 `94af3cf4345b2383100e4d8d883be57b084ec68d12e056f80c4a8bb77bc9bd68`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 284 行 `repo/src/main.cpp`：目标文件不存在，期望哈希 `7ed7f5c2eb5bd9ef2b8572aadc7a3f3f116e8a8a62370197bd606f3b4035bcde`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 285 行 `repo/src/preprocess.hpp`：目标文件不存在，期望哈希 `df36a028fbbeec62bcacc5a0a50194f917285d20fd9cf231abd4c28d4013ee31`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 286 行 `repo/src/runtime.cpp`：目标文件不存在，期望哈希 `63a3df726c220dddd51dc1e962d1d2169c74722a4e9452b76a4d731a0c500774`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 287 行 `repo/src/tuning.hpp`：目标文件不存在，期望哈希 `2dc89e5f8a0986da508eca9931e94130be96a0b098c9f0ab8d35a6217ecb4798`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 288 行 `repo/tests/bounded_commit_alias_probe.cpp`：目标文件不存在，期望哈希 `c29f55845e4a7b755635e86932f587a5106220afd1a681997d254bf4c63eaf09`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 289 行 `repo/tests/bounded_commit_overflow_probe.cpp`：目标文件不存在，期望哈希 `8c70309dd95e87908a064521cf56d935b34bebc81858cf2b1519bb0993410a84`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 290 行 `repo/tests/extended_validation.cpp`：目标文件不存在，期望哈希 `34e820efcf1d84a790047695b9b9e11fff371305ae23c83488ce3c53e8e2245c`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 291 行 `repo/tests/final_late_path_probe.cpp`：目标文件不存在，期望哈希 `ca73c8372bb39fc8c5ab0f6dfc51bf10034c0d61ee24fb05248d00533f8d9a53`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 292 行 `repo/tests/fp32_packed_panel_audit.cpp`：目标文件不存在，期望哈希 `855609e1aae13fc48edce62f1f2aa758dab7571c6cdebea769f74a43392f111c`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 293 行 `repo/tests/packed_panel_audit.cpp`：目标文件不存在，期望哈希 `29ddf9218c20c86f0be857361e209f2c91a3ea5e375f7fbc5ccc60ffac6419f2`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 294 行 `repo/tests/validation.cpp`：目标文件不存在，期望哈希 `059450a04960c12dc78b17d63ce270d41f24215f8d0aa53f426daef5bea5e264`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 295 行 `repo/third_party/SOURCES.md`：目标文件不存在，期望哈希 `d8df1a1f9bd46a43f772976612d04507c942f62aca686594c2fbf15a6fee0f68`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 296 行 `repo/third_party/roofline/ISC18-RooflineAdvisor-final.pdf`：目标文件不存在，期望哈希 `2fddb09d2b93440f84ca8090af0ebe33bd60bb7b4ffded46aa0c669c119d27b5`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 297 行 `repo/third_party/roofline/SOURCES.md`：目标文件不存在，期望哈希 `c0fa4eddc6f4430af92b8a7379cd47d63fbb9b97166c0601db4757f7c6faf42c`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 298 行 `repo/third_party/roofline/study.md`：目标文件不存在，期望哈希 `16794e07e352d331b03ddd748b0d450d857dafa75b6bbd8071f0166570a0b1e2`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 299 行 `repo/tools/amx_probe.c`：目标文件不存在，期望哈希 `9db413f970915067d83fe71183b583af08d3a75ecc13fff4c11b92206e648c5d`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 300 行 `repo/tools/native_alternative_accuracy.cpp`：目标文件不存在，期望哈希 `1522208e7556dc021b24b79c3bb1403254ae3251a47fb6a02358ba224b53c26a`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 301 行 `repo/tools/native_kernel_audit.cpp`：目标文件不存在，期望哈希 `8c3e66d56b6b81b65f067bee7380d5b41ca0eeca9529b94dfc6f92c262775178`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 302 行 `repo/tools/native_signed_shift_accuracy.cpp`：目标文件不存在，期望哈希 `31fed4d3f6ea6a9bea93e23a6e78c882e54be67bd7013efbca5ef404381882b8`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 303 行 `repo/tools/platform_baseline.cpp`：目标文件不存在，期望哈希 `25444b17c9df70fbc743fb621f60256ff2785395a2b41277fa9861303af67b4e`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 304 行 `repo/tools/plot_roofline_calibration.py`：目标文件不存在，期望哈希 `d8affbe14fce0f2479eb50020cf94de93da299c0122da3cc1d50a0775a98deeb`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 305 行 `repo/tools/roofline_binary_gate.cpp`：目标文件不存在，期望哈希 `6ee7c7b2ed423c52e2481756b51d1073229b55b49bdcbdabda965d0fc6f342df`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 306 行 `repo/tools/roofline_kernels.cpp`：目标文件不存在，期望哈希 `ae38a0192f20bec20a220f333d3d6d70856367109e5e02ed949dd64424b64db0`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 307 行 `repo/tools/roofline_memory.cpp`：目标文件不存在，期望哈希 `ec293893f272f6545ada0bbc6c0cfc1eb2f3c50af3911a0d61109faaa71a2c4e`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 308 行 `repo/tools/roofline_thp_probe.cpp`：目标文件不存在，期望哈希 `fc321e61f45dbbaa1bbeee61b60c4b97f4850172d019ed3b19c8519a9ec1ec23`。
- `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` 第 309 行 `repo/tools/roofline_tileloads.S`：目标文件不存在，期望哈希 `df26c82d11a73a7f16350d3dfb01ce26d11ce12b32a2c9960f642818191e41ef`。

本地链接解析相对于 Markdown 所在目录；跳过外链、纯锚点、mailto 和以 `/` 开头的绝对链接。文本中的结果路径优先相对文档目录解析，再按仓库根目录解析。上述检查只验证路径和字节哈希。
