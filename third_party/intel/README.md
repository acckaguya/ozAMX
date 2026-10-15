# Xeon Platinum 8454H / Sapphire Rapids 资料库

更新：2026-10-13（北京时间）。本轮为当前双路 Intel Xeon Platinum 8454H 补充架构、指令、优化资料及代码参考，覆盖 AMX、AVX、AVX2、AVX-512、BF16、FP16、缓存、NUMA、线程和浮点语义。

先读 [综合研读与项目对应](8454H_STUDY.md)，再按主题使用以下索引。Intel 原始 PDF、网页和源码保留上游内容；`STUDY.md` 是本项目的阅读笔记。手册按相关章节研读，不声称通读数千页通用手册。

| 目录/资料 | 包含内容 | 入口 |
|---|---|---|
| `manuals/` | Intel SDM v093：Vol.1、Vol.2B、Vol.2C；Optimization Reference Manual Vol.1 v050 | [来源、版本、哈希、页数](manuals/manifest.json) |
| `simd/` | 官方 Intrinsics Guide v3.6.9 原网页、离线 ZIP 和完整展开包；SIMD/AMX 章节研读 | [SIMD/指令笔记](simd/STUDY.md) |
| `simd/linux-xstate/` | Linux 官方 XSTATE 网页、v6.12 固定版本 RST 和许可说明 | [固定版本规范](simd/linux-xstate/xstate-v6.12.rst) |
| `xeon-8454h/source-html/` | 8454H 与 Gold 6430 SKU 页面、Sapphire Rapids 技术概览、AI/媒体调优页面 | [平台资料笔记](xeon-8454h/STUDY.md) |
| `xeon-8454h/pdfs/` | ISA Extensions Reference（2024-12）、AVX-512 FP16 Technology Guide（rev004）、4th Gen Xeon Product Brief | [平台资料来源与哈希](xeon-8454h/manifest.json) |
| `xeon-8454h/hardware-snapshot/` | 当前 CPU/缓存/拓扑/NUMA/系统可见资源；CPUID、XCR0、AMX 许可与线程核验 | [机器快照](xeon-8454h/hardware-snapshot/snapshot.json) |
| `examples/amx_intrinsics/` | Intel 完整 AMX INT8 intrinsic 演示 | [源码](examples/amx_intrinsics/test-amxtile.c) |
| `examples/bf16_intrinsics/` | Intel AVX-512 BF16 转换及 dot-product 演示，原始 ZIP 和许可 | [源码](examples/bf16_intrinsics/testBF16.cpp) |
| `examples/intel_optimization_manual/` | 官方 AMX GEMM、BF16 转换、transpose/VNNI、FP64 稀疏 dot 和 SIMD transpose 片段及部分配套测试 | [示例研读](examples/STUDY.md) |
| `examples/simd_blog/` | Intel AVX2/AVX-512 矩阵向量及 mask 教学示例 | [适用范围说明](examples/STUDY.md) |
| `examples/onednn_x64/` | oneDNN AMX GEMM JIT、copy/packing、BF16 conversion/reorder 参考 | [来源与固定提交](examples/manifest.json) |

固定提交的代码参考来自 Intel AMX-TMUL、Intel optimization-manual、Intel Developer-Tools-Runtimes-Blogs，以及 oneDNN 官方仓库。片段有明确的依赖、固定形状和平台限制，不能把它们当作已构建的完整库；所有下载源码已由 Luna 静态研读，本轮未运行其性能示例。

机器快照中的 `local-probes/` 是本项目为核验平台编写的辅助代码，**不是 Intel 上游示例**；源码哈希、编译/运行命令及结果保存在快照中。

本轮来源登记见三个子 manifest，完整性验收见 [COLLECTION_CHECK.json](COLLECTION_CHECK.json)。原始来源保留 URL、获取日期、版本/提交、字节数、SHA-256 和许可边界。SDM 在目录间共享，不重复下载同一 PDF；保留的 ZIP 与展开内容用途不同。

发现的文档问题有单独记录：FP16 指南 rev004 第11/14页三处笔误、BF16 演示网页与 ZIP 的许可标注差异，以及部分手册示例包装器注释与配套测试的形状差异。未改动上游文件；指令语义以对应版本 SDM 为准。

`docs/ENVIRONMENT.md` 和原始 benchmark CSV 仍描述 Gold 6430 的历史实验，当前平台信息以这里的快照为准。`docs/FULL_SWEEP_MANIFEST.json` 是历史实验/发布记录；本轮新增资料和更正来源说明不重写该历史记录，其旧发布清单哈希也不作为新资料库的清单。
