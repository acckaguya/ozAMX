# 第三方来源登记

原始核验日期：2026-10-12（UTC）；当前8454H资料补充：2026-10-13（北京时间）。论文是复现目标；Intel 文档是 ISA/平台实现依据；oneMKL 是独立的 CPU BLAS 对照依赖。三者用途分开登记。下面原有oneMKL环境及probe记录属于Gold6430历史实验，不表示当前检出已安装那些本地依赖。

## 当前 Xeon Platinum 8454H 架构与 SIMD 资料

新资料集中在 [intel/README.md](intel/README.md)，综合研读见 [intel/8454H_STUDY.md](intel/8454H_STUDY.md)。覆盖AMX、AVX/AVX2、AVX-512、BF16/FP16、缓存/NUMA、线程划分与优化代码参考。

- Intel SDM **v093** 的Vol.1/2B/2C及Optimization Reference Manual **Vol.1 v050**：[原始文件与manifest](intel/manuals/manifest.json)。
- Intel Intrinsics Guide **v3.6.9**离线包、展开文件与Linux XSTATE规范：[研读索引](intel/simd/STUDY.md)。Linux许可为进程级，独立的task状态分配另作说明。
- 官方8454H/Gold6430规格、Sapphire Rapids技术概览、调优页面、ISA Extensions（2024-12）、FP16 Technology Guide rev004和Product Brief：[平台manifest](intel/xeon-8454h/manifest.json)。原先登记但未随公开包分发的ISA PDF，现以原始副本保存在该平台目录的`pdfs/`下。
- 固定commit的Intel AMX/优化手册/AVX示例、oneDNN内核片段及许可证：[代码manifest](intel/examples/manifest.json)、[逐文件研读](intel/examples/STUDY.md)。
- 当前Linux拓扑、缓存、CPUID/XCR0和进程/worker核验：[机器快照](intel/xeon-8454h/hardware-snapshot/snapshot.json)。

Roofline 模型的Intel集成Roofline说明、Williams–Waterman–Patterson 原始文献和Koskela等人的多层模型论文来源登记及本项目笔记见[roofline来源目录](roofline/SOURCES.md)与[研读笔记](roofline/study.md)。本地只保存一份不足1 MiB的官方论文PDF，不包含Intel Advisor软件或缓存模拟器。

来源URL、版本、获取日期、bytes、SHA和授权边界以新manifest为准；本轮没有修改论文、GEMM实现或历史科学结果。旧实验发布manifest保留其历史身份，新资料库使用独立清单及 [COLLECTION_CHECK.json](intel/COLLECTION_CHECK.json)。

## 复现目标论文

- **作者：** Bing Cui、Yu Liu。
- **标题：** “BF16 Component-Product Emulation of FP32 and FP64 GEMM on Intel AMX”。
- **版本与日期：** arXiv:2609.04663v1，2026-09-04。
- **权威记录：** <https://arxiv.org/abs/2609.04663>；**固定版本 PDF：** <https://arxiv.org/pdf/2609.04663v1>。
- **本地文件：** `papers/2609.04663v1.pdf`。
- **SHA-256：** `11981bb2fc8be3d492a82aeb23898ee2ac999c1d5660fdd3c7fc2438615ef70f`。
- arXiv 显示授权为 CC BY 4.0：<https://creativecommons.org/licenses/by/4.0/>。
- 已检索论文本身的 HTML 与 arXiv 记录，没有找到作者提供的代码仓库链接或代码可用性章节。未将其他实现冒充为作者代码。

## Intel 官方 AMX/ISA 文档

- **发布者：** Intel Corporation。
- **文档：** *Intel Architecture Instruction Set Extensions Programming Reference*，2024 年 12 月 URL 版本。
- **来源：** <https://cdrdv2-public.intel.com/843860/architecture-instruction-set-extensions-programming-reference-dec-24.pdf>。
- **当前本地文件：** `intel/xeon-8454h/pdfs/intel-architecture-instruction-set-extensions-programming-reference-dec24.pdf`（2026-10-13重新获取，SHA-256与原登记一致）。
- **SHA-256：** `bbffe2b3bc6129cd9131a7c4981ab0c4b34fbc89a3032be0c7f822736f4b1bad`。
- 文档涵盖 AMX tile 配置/操作及 `TDPBF16PS` 等 BF16 指令。本地 PDF 来源页未发现明确再分发授权；请以 Intel 上游页面及文档附带条款为准。实现语义笔记另见 `docs/amx-instruction-notes.md`。

## oneMKL CPU BLAS 对照依赖

- **发布者：** Intel Corporation，经 PyPI 的官方 IntelAutomationEngineering 发布者分发。
- **版本：** `mkl==2026.0.0`、`mkl-include==2026.0.0`、`onemkl-license==2026.0.0`、`intel-openmp==2026.1.2`、`intel-cmplr-lib-ur==2026.1.2`、`tbb==2023.1.0`、`tcmlib==1.5.0`、`umf==1.1.0`。上游：[mkl on PyPI](https://pypi.org/project/mkl/2026.0.0/)；[mkl-include](https://pypi.org/project/mkl-include/2026.0.0/)；[onemkl-license](https://pypi.org/project/onemkl-license/2026.0.0/)；[intel-openmp](https://pypi.org/project/intel-openmp/2026.1.2/)；[tbb](https://pypi.org/project/tbb/2023.1.0/)。
- **本地环境：** `code/mkl-2026/venv/`，由 Python venv 安装，未修改系统 Python、全局动态库或系统配置。PyPI 直接 `--target` 安装未把 wheel RECORD 指向安装树父目录的 `.so` 文件落盘；使用该隔离 venv 后，oneMKL runtime 完整可用。
- **实际运行库：** `code/mkl-2026/venv/lib/libmkl_rt.so.3`；SHA-256：`6de08b65f3949fbf785507b86d0c5c8decb83b978401dd6c404d3929996c1c28`。`mkl_get_version_string` 实测：`Intel(R) oneAPI Math Kernel Library Version 2026.0-Product Build 20260401 for Intel(R) 64 architecture applications`；`dladdr(cblas_sgemm)` 确认载入上述本地运行库路径。
- **许可证：** Intel Simplified Software License（专有授权），随包保存在 `code/mkl-2026/venv/lib/python3.14/site-packages/onemkl_license-2026.0.0.dist-info/LICENSE.txt`。限本地复现实验使用；未并入项目源码。
- **BLAS smoke：** 以同一 2026.0 runtime 调用 `cblas_sgemm`、`cblas_dgemm` 的 2×2 乘法均得到 `C[0,0]=19`。这只确认两种 CBLAS 入口可执行，不代表完整性能复现。
- **构建入口：** 根 `CMakeLists.txt` 在本地 runtime 存在时导出 `ozamx_onemkl` interface target，供参考程序使用本目录头文件与同版本 runtime。
- **Figure 6 raw BF16 API：** Intel 官方 [CBLAS `cblas_gemm_bf16bf16f32` 参考](https://www.intel.com/content/www/us/en/docs/onemkl/developer-reference-c/2023-0/cblas-gemm-bf16bf16f32.html)定义 BF16×BF16 输入、FP32 累加的 C 接口，并说明不支持原生 BF16 硬件的平台可能上转换到 SGEMM。当前 oneMKL 2026.0 配套头文件 `mkl_cblas.h` 第 1014 行也公开声明该 API，实际 `libmkl_rt.so.3` 导出对应符号；隔离 raw headroom runner 使用此官方入口，不调用项目 AMX kernel。

## 获取与重建依赖环境

oneMKL 是 Intel 专有软件，不随本仓库分发。要在有权使用 Intel oneMKL 且支持所需 AMX ISA 的机器上重建本地隔离环境，可在仓库根目录执行：

```sh
python3 -m venv third_party/code/mkl-2026/venv
third_party/code/mkl-2026/venv/bin/python -m pip install --upgrade pip
third_party/code/mkl-2026/venv/bin/python -m pip install \
  mkl==2026.0.0 mkl-include==2026.0.0 onemkl-license==2026.0.0 \
  intel-openmp==2026.1.2 intel-cmplr-lib-ur==2026.1.2 \
  tbb==2023.1.0 tcmlib==1.5.0 umf==1.1.0
```

CMake 配置时需将 `OZAMX_ONEMKL_ROOT` 指向该 venv 中提供 `include/` 和 `lib/libmkl_rt.so.3` 的目录；运行 benchmark 时按 [raw BF16 runner](../bench/raw_bf16_manifest.md) 设置本地 `LD_LIBRARY_PATH` 与 `MKL_THREADING_LAYER=GNU`。PDF 结构检查工具可单独装入本地环境：`python3 -m venv third_party/code/pdf-tools && third_party/code/pdf-tools/bin/python -m pip install pypdf==6.20.0`；检查记录为结构级通过，不代表人工阅读。Python 数据分析另需 NumPy、Matplotlib；GCC binary128 验证和 native 诊断命令见 `tools/` 与 `docs/`。诊断输入文件及 SHA-256 校验清单已包含于 `bench/diagnostics/`；可在相应目录执行 `sha256sum -c checksums.sha256` 验证。不要把本机 venv 或已编译二进制当作源码依赖。

## 获取及 PDF 检查记录

- 论文及 Intel 手册于 2026-10-12 UTC 下载；元信息经 arXiv 官方记录与 Intel 官方源核对。
- 论文 PDF 结构预检结果为 `PASS, STRUCTURE_ONLY`：声明、枚举和 reader 页数均为29，无结构警告。此项仅验证文档结构，不验证语义完整性或人工阅读；sidecar 和 SHA-256 记录在论文目录。
- oneMKL 官方 PyPI 包于 2026-10-12 UTC 安装到工作区 venv；`code/mkl-2026/venv/` 包含运行库及 Intel 发布的依赖文件。
