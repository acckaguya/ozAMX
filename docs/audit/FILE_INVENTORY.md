# 文件清点与事实记录

扫描根目录：`/home/caiweili/ozAMX`。递归清点普通文件和目录，不跟随符号链接。排除 `.git/`、`.aws/`、`.codex/`、`.agents/` 内容；报告文件自身排除在统计之外。对每个可读普通文件计算完整内容 SHA-256。

## 总量

- 普通文件：**29,376** 个，共 **874,824,817 bytes**。
- 目录：**6,827** 个；符号链接：**0** 个；不可读文件：**0** 个。
- Git 状态：tracked **6,421**，untracked **1**，ignored **22,954**；索引中 tracked 文件 **6,421** 个。

## Git 工作区状态

```text
 M src/gemm.cpp
?? docs/PAPER_SECTION_6_3_IMPLEMENTATION.md
```

`src/gemm.cpp` 有用户未提交修改；`docs/PAPER_SECTION_6_3_IMPLEMENTATION.md` 是用户未跟踪文件。两者均须保留。审计报告在扫描时排除，报告所在的 `docs/audit/` 目录计入目录清单。

## 扩展名分类

| 扩展名 | 文件数 |
|---|---:|
| `.12` | 1 |
| `.2` | 5 |
| `.3` | 12 |
| `.a` | 124 |
| `.asm` | 2 |
| `.bf16le` | 8 |
| `.c` | 238 |
| `.check_cache` | 108 |
| `.cmake` | 4,806 |
| `.cpp` | 708 |
| `.css` | 2 |
| `.csv` | 685 |
| `.diff` | 4 |
| `.f` | 2 |
| `.f03` | 2 |
| `.f64le` | 4 |
| `.f90` | 42 |
| `.fi` | 16 |
| `.h` | 75 |
| `.hpp` | 111 |
| `.html` | 36 |
| `.i` | 1 |
| `.ico` | 1 |
| `.includecache` | 145 |
| `.internal` | 145 |
| `.js` | 4 |
| `.json` | 3,283 |
| `.jsonl` | 1 |
| `.lock` | 1 |
| `.log` | 6,525 |
| `.make` | 8,489 |
| `.marks` | 108 |
| `.md` | 196 |
| `.mod` | 8 |
| `.patch` | 24 |
| `.pdf` | 18 |
| `.pid` | 1 |
| `.png` | 25 |
| `.py` | 131 |
| `.rc` | 4 |
| `.rst` | 2 |
| `.s` | 51 |
| `.sh` | 57 |
| `.sha256` | 38 |
| `.sha256sums` | 2 |
| `.svg` | 10 |
| `.tcl` | 108 |
| `.toml` | 1 |
| `.txt` | 1,783 |
| `.whl` | 2 |
| `.zip` | 2 |
| `[no extension]` | 1,219 |

## 路径分布（按顶层目录粗分）

| 类别 | 文件数 |
|---|---:|
| `documentation_and_figures` | 63 |
| `experiment_and_benchmark_material` | 28,968 |
| `root_or_other` | 7 |
| `source_and_validation` | 37 |
| `third_party_material` | 301 |

该分类仅由顶层路径机械归类：`bench/` 视为实验与基准材料，`src/`、`include/`、`tools/`、`tests/` 视为源码/验证材料，`third_party/` 视为第三方材料，`docs/` 视为文档/图表。不能据此判断证据效力或文件用途。

## 最大文件（前 20）

| bytes | Git 状态 | 路径 |
|---:|---|---|
| 83,846,112 | ignored | `third_party/code/mkl-current/lib/libmkl_avx512.so.3` |
| 76,168,096 | ignored | `third_party/code/mkl-current/lib/libmkl_core.so.3` |
| 74,537,248 | ignored | `third_party/code/mkl-current/lib/libmkl_avx10.so.3` |
| 55,845,176 | ignored | `third_party/code/mkl-current/lib/libmkl_avx2.so.3` |
| 45,352,424 | ignored | `third_party/code/mkl-current/lib/libmkl_def.so.3` |
| 29,436,096 | ignored | `third_party/code/mkl-current/lib/libmkl_gnu_thread.so.3` |
| 19,450,800 | ignored | `third_party/code/mkl-current/lib/libmkl_intel_lp64.so.3` |
| 17,488,464 | ignored | `third_party/code/mkl-current/lib/libmkl_intel_ilp64.so.3` |
| 16,390,560 | ignored | `third_party/code/mkl-current/lib/libmkl_gf_lp64.so.3` |
| 15,708,856 | ignored | `third_party/code/mkl-current/lib/libmkl_rt.so.3` |
| 14,832,354 | ignored | `bench/8454h/versions/v4_roofline_search_round1/third_party/intel/manuals/optimization-reference-manual-v1-050.pdf` |
| 14,832,354 | tracked | `third_party/intel/manuals/optimization-reference-manual-v1-050.pdf` |
| 14,441,264 | ignored | `third_party/code/mkl-current/lib/libmkl_gf_ilp64.so.3` |
| 8,138,628 | tracked | `third_party/intel/xeon-8454h/pdfs/intel-architecture-instruction-set-extensions-programming-reference-dec24.pdf` |
| 7,688,192 | ignored | `third_party/code/mkl-current/lib/libmkl_intel_thread.so.3` |
| 7,438,486 | tracked | `third_party/intel/simd/intrinsics-guide-offline/Intel Intrinsics Guide/files/data.js` |
| 7,000,963 | ignored | `bench/8454h/local_cleanup/20261015/deletion_plan.json` |
| 6,915,682 | ignored | `bench/8454h/versions/v4_roofline_search_round1/third_party/intel/manuals/sdm-vol2b-v093.pdf` |
| 6,915,682 | tracked | `third_party/intel/manuals/sdm-vol2b-v093.pdf` |
| 3,656,572 | tracked | `third_party/intel/manuals/sdm-vol1-v093.pdf` |

## 符号链接

扫描范围内未发现符号链接。

## 完整内容重复

全文件内容 SHA-256 比对得到 **2,954 组**重复内容，涉及 **22,800 个文件路径**。仅凭字节相同不能断定语义冗余。下列是重复次数最多的前 12 组；全部路径和哈希详见 [压缩 JSON 清单](file_inventory.json.gz)。

| 副本数 | 单份 bytes | 示例路径 |
|---:|---:|---|
| 4,263 | 0 | `bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/run.log`
| 3,027 | 1 | `bench/8454h/roofline_v4/adaptive_release_runs/adaptive_geom_20261014T122531Z/build/CMakeFiles/Continuous.dir/progress.make`
| 214 | 172 | `bench/8454h/roofline_v4/adaptive_release_runs/adaptive_geom_20261014T122531Z/build/CMakeFiles/FindOpenMP/OpenMPTryFlag.c`
| 192 | 324 | `bench/8454h/roofline_v4/search_runs/layout_b2_m256_n256_20261014/builds/layout_b2_m256_n256_p0_h0_l1__mode3_b2_m256_n256_p0_h0_l1/CMakeFiles/ozamx_alias_output_probe.dir/flags.make`
| 172 | 119 | `bench/8454h/roofline_v4/adaptive_release_runs/adaptive_geom_20261014T122531Z/gates/adaptive_full20_logs/candidate_10.stderr.log`
| 172 | 116 | `bench/8454h/roofline_v4/adaptive_release_runs/adaptive_geom_20261014T122531Z/gates/adaptive_full20_logs/candidate_15.stderr.log`
| 172 | 116 | `bench/8454h/roofline_v4/adaptive_release_runs/adaptive_geom_20261014T122531Z/gates/adaptive_full20_logs/candidate_16.stderr.log`
| 172 | 115 | `bench/8454h/roofline_v4/adaptive_release_runs/adaptive_geom_20261014T122531Z/gates/adaptive_full20_logs/candidate_09.stderr.log`
| 172 | 111 | `bench/8454h/roofline_v4/adaptive_release_runs/adaptive_geom_20261014T122531Z/gates/adaptive_full20_logs/candidate_14.stderr.log`
| 172 | 107 | `bench/8454h/roofline_v4/adaptive_release_runs/adaptive_geom_20261014T122531Z/gates/adaptive_full20_logs/candidate_13.stderr.log`
| 118 | 219 | `bench/8454h/roofline_v4/kernel_schedule_runs/kernel_schedule_20261014T142400Z/matched/group1_fp64_n8192_b10/logs/build_candidate.log`
| 112 | 331 | `bench/8454h/roofline_v4/search_runs/packed_rotation_screen_20261014T101015Z/preflight/builds/mode0_a0_b0_ra0_rb0/CMakeFiles/ozamx_alias_output_probe.dir/flags.make`

从路径可见，大量相同内容同时出现在活动实验树与 `bench/8454h/versions/` 下的版本快照中；另有构建目录中通用构建文件重复。此为可疑冗余线索，不能由文件清点认定可以删除。

## 绝不自动删除或覆盖

- 用户未提交内容：`src/gemm.cpp` 当前修改；`docs/PAPER_SECTION_6_3_IMPLEMENTATION.md` 未跟踪文件。
- `bench/` 下原始实验数据、日志、检查点、校验结果、来源信息及版本快照。
- `docs/` 下已提交的冻结报告、论文材料和图表。
- `third_party/` 下的原始收集材料、上游样本、许可证、手册及快照。

这是复现审查期间的保留边界；没有删除或修改清点范围内其他文件。

## 规则与口径限制

仓库范围内未找到 `AGENTS.md`。按要求没有读取 `.aws/`、`.codex/`、`.agents/`、`.git/` 内容；Git 状态仅通过 `git status --short`、`git ls-files`、`git check-ignore` 读取。逐文件路径/字节数/哈希/Git 状态和全部目录清单见 [压缩清单 `file_inventory.json.gz`](file_inventory.json.gz)。原 JSON SHA-256 为 `2a93bcf7627d07db89839b08a90e3d5712cf4829d5436a062241d7d01d3f6319`；gzip 解压后 SHA-256 一致，未压缩 JSON 已移除。
