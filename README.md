# Intel AMX 上的 FP32/FP64 GEMM 组件积复现

本项目是对论文《BF16 Component-Product Emulation of FP32 and FP64 GEMM on Intel AMX》的独立实现与实验复现，不是作者代码的移植。它使用 Intel AMX BF16 点积实现 FP32，以及可选 6/10/15/21 个 BF16 组件积的 FP64 近似 GEMM。

论文方法、8454H架构、版本演进、精度差距、oneMKL对照、roofline搜索及冻结归档的完整梳理见 [项目总结](docs/PROJECT_SUMMARY.md)（截至2026年10月14日）。

`codex/strict-emulation` 分支默认采用固定 256 宏块、宏块预处理、块内 staging 和 FP64 逐组件即时重建。实现范围、验证及性能达标状态见 [严格模拟实现](docs/STRICT_EMULATION_IMPLEMENTATION.md)；此前的独立审查见 [综合审查报告](docs/audit/COMPREHENSIVE_REVIEW.md)。方法组织更接近论文不等于性能或 FP64 误差表已复现。

自有源码采用统一缩进与换行，并在分片、打包、累加还原等关键处补充说明。排版约定、维护命令和本次核对结果见 [代码可读性说明](docs/CODE_READABILITY.md)。

工作区中构建产物、实验记录与冻结包的保留规则，以及Git管理说明见 [工作区整理记录](docs/WORKSPACE_CLEANUP.md)。

## 环境

当前优化面向双路 Intel Xeon Platinum 8454H（Sapphire Rapids），使用 AMX-BF16 和 AVX-512。架构、指令手册及官方代码实例见 [third_party/intel/README.md](third_party/intel/README.md)；机器实测算力、内存带宽和同机优化前后比较见 [docs/8454H_PERFORMANCE_BASELINE.md](docs/8454H_PERFORMANCE_BASELINE.md)。原 Gold 6430 的实验环境与结果保留在历史文档中。

算法及论文证据见 [docs/PAPER_STUDY.md](docs/PAPER_STUDY.md)，数值支持域与产品顺序见 [docs/REPRODUCTION_SPEC.md](docs/REPRODUCTION_SPEC.md)。此实现保留 FP32 三片六项和 FP64 rho45 六轮投影、6/10/15/21 产品预算；FP64 每个组件的 FP32 结果先独立拓宽到 FP64，再按原顺序累加。

## 构建与验证

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DOZAMX_ENABLE_OPENMP=ON \
  -DOZAMX_STRICT_FP64_ROW_PAD_BYTES=64
cmake --build build -j8
OMP_NUM_THREADS=64 ctest --test-dir build --output-on-failure
```

需要支持 Sapphire Rapids 的 GCC/binutils（本机验证 GCC 11.4）。公共运行时先检查 CPU、OS 扩展状态及 Linux 进程级 AMX 权限，然后进入目标架构内核；每个 worker 管理自己的 tile 状态。不支持的平台会报告错误。验证覆盖真实 AMX GEMM、所有产品预算、非整块尺寸、带 padding 的 stride、异常输入和输出保护。

生产计算由 [src/kernels.S](src/kernels.S) 的手写 AMX 内核和 [src/preprocess.hpp](src/preprocess.hpp) 的 AVX-512 分片、VNNI 打包配合完成；[src/gemm.cpp](src/gemm.cpp) 使用向量累加、FP64 拓宽还原、边缘复制和分块调度。packed panels 按 32 级微块连续排列，工作缓冲按 64 字节对齐；K 累加块为 256，以保留数值顺序。工作区池在调用线程内复用，默认最多保留 2 GiB，可在进程启动前设置 `OZAMX_WORKSPACE_CACHE_BYTES=0` 禁用，或设为其他字节上限。默认严格模拟路径先保存完整三片/六片，再打包；FP64 thread-private block 默认使用 64 B 行 padding（只改布局、不改数学），每个输出块完成后扫描非有限值，全部通过才提交 C。product/reconstruction overlap 是 research-only，不属于 strict 默认路径。历史 V3 配置、最终 oneMKL 对照、搜索与验证见 [V3 Roofline 结果](docs/8454H_ROOFLINE_RESULTS.md)。

当前 CMake 项目版本为 0.4.0。`OZAMX_STRICT_PATH=ON` 为本分支默认；设为 `OFF` 可构建原自适应调度作受控对照，原路径仍含此前有限域的 CompactWide FP32 优化。`OZAMX_STRICT_LOCAL_STAGING=OFF` 只在严格模拟路径关闭局部面板复制，用于单变量实验。历史 V4 的构建、数值/事务 gate、matched V3 对照见 [V4 验证报告](docs/8454H_V4_CURRENT_MAIN_VALIDATION.md)，不能当作本分支的新测量。V3 历史数据和冻结副本见 [V3 Roofline 结果](docs/8454H_ROOFLINE_RESULTS.md) 与 [V3 release archive](bench/8454h/versions/v3_release/README.md)。不可变的 [冻结 V2 release archive](bench/8454h/versions/v2_release/README.md) 和 [V2 source snapshot](bench/8454h/versions/v2/README.md) 保留作历史对照。物理缓存层级/DRAM 流量 PMU 计数仍未测量。

复现当前机器的前后比较，无需 oneMKL：

```sh
bash bench/run_8454h_baseline.sh --sizes 256,1024,4096 \
  --threads 64 --reps 5 --budgets 6,10,15,21
```

runner 用同一计时驱动构建存档原版与新版，固定输入、CPU affinity 和线程设置，串行执行并保存每轮原始记录。独立机器微基准使用 `--hardware`。逐位等价验证方法见 [bench/8454h/](bench/8454h/)。

本机当前可用 Intel oneMKL 2026.1，CMake 会从 `third_party/code/mkl-current` 自动查找头文件和运行库。新 driver 使用完整 API headline、逐次 MKL 样本和同轮交替计时；新 checkpoint 绑定实际二进制、库与环境，拒绝旧版续跑。以下使用新前缀，不覆盖历史 campaign：

```sh
mkdir -p bench/local-strict-emulation
LD_LIBRARY_PATH="$PWD/third_party/code/mkl-current/lib" \
OMP_NUM_THREADS=64 OMP_PLACES=cores OMP_PROC_BIND=close OMP_DYNAMIC=FALSE \
MKL_NUM_THREADS=64 MKL_DYNAMIC=FALSE MKL_THREADING_LAYER=GNU \
OZAMX_WORKSPACE_CACHE_BYTES=2147483648 taskset -c 0-63 build/ozamx_benchmark \
  --sizes 256,1024,4096,8192 --threads 64 --reps 5 --precision all \
  --budgets 6,10,15,21 --seed 260904 --distribution uniform \
  --checkpoint bench/local-strict-emulation/checkpoint \
  --output bench/local-strict-emulation/results.csv
```

命令对每个配置执行五次计时，另先执行一次 warm-up。它覆盖 FP32 p6 和 FP64 p6/p10/p15/p21，并记录 oneMKL GEMM、完整 ozAMX API 时间和精度指标。历史 Gold 6430 大规模 campaign 保存在 [历史复现结果](docs/REPRODUCTION_RESULTS.md) 与 [campaign runner](bench/run_remaining_campaign.sh) 中；其中的环境前缀和队列配置仅适用于当时的 campaign。

## 历史论文复现实验

已完成 64 个线程的 AMX 功能验证、Table 4 的 40 个配置、FP32 线程伸缩 18 个配置及 raw BF16 的 8 个阶数；每个正式配置均通过 1 次 warm-up 和 10 次计时校验。完整原始结果、统计、论文逐项覆盖状态、误差差异与图表见 [docs/REPRODUCTION_RESULTS.md](docs/REPRODUCTION_RESULTS.md)。本机实测 AMX 端到端与 MKL GEMM-only 的比较采用不同计时范围，并按结果逐项报告，不宣称数值或性能完全匹配论文。公开包的文件选择、许可与可重算项见 [docs/PUBLICATION_PACKAGE.md](docs/PUBLICATION_PACKAGE.md)。
