# Xeon 8454H：匹配基线与优化结果

> **当前生产版本：V3。** 本页的匹配 GEMM 表和微基线是较早研究快照，保留作历史记录。当前 V3 的 Roofline 模型、搜索与负结果、正式 oneMKL 对照及验证入口见 [V3 最终性能报告](8454H_ROOFLINE_RESULTS.md)、[Roofline 搜索日志](8454H_ROOFLINE_SEARCH_LOG.md) 和 [分层 Roofline 模型](8454H_ROOFLINE_MODEL.md)。当前生产库 SHA-256 为 `73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c`；不可变 V2 档案仍见 [v2_release](../bench/8454h/versions/v2_release/README.md)。

本报告记录同一台机器上、同一基准驱动分别链接冻结旧版和当前实现所得的匹配结果，并补充独立 CPU、AMX 与内存微基线。所有旧版/新版 GEMM 数字均来自同一轮受锁保护的采集。报告不声称胜过 oneMKL 或论文中的其他机器结果。

当前机器状态、2026-10-14 roofline 校准与完整 V3 paper campaign 基线见 [8454H_CURRENT_BASELINE.md](8454H_CURRENT_BASELINE.md)。本页及其原始数据继续作为历史测量快照保留。

旧源快照在 [`bench/8454h/before/`](../bench/8454h/before/)。完整原始 GEMM CSV 为 [`final_before.csv`](../bench/8454h/final_before.csv) 和 [`final_optimized.csv`](../bench/8454h/final_optimized.csv)；8192 扩展在 [`final_before_8192.csv`](../bench/8454h/final_before_8192.csv) 和 [`final_optimized_8192.csv`](../bench/8454h/final_optimized_8192.csv)。机器与源码哈希、精确命令在 [`final_run_metadata.txt`](../bench/8454h/final_run_metadata.txt)。微基线原始 CSV 与指令审计分别是 [`platform_baseline.csv`](../bench/8454h/platform_baseline.csv) 和 [`platform_instruction_audit.txt`](../bench/8454h/platform_instruction_audit.txt)。


> **Final production update:** The main matched before/optimized CSVs and the 1/4 GiB capacity supplement below are earlier study snapshots. Production is now frozen with FP64 late64 specialization at K≥4096, eager checks below that, aligned large-matrix fusion, prep grain 16384, and a 2 GiB workspace-cache default. The authoritative production-linked oneMKL results, current source/library hashes, and complete 20-configuration phase/wall/error/checksum table are in [8454H_FINAL_PERFORMANCE_REPORT.md](8454H_FINAL_PERFORMANCE_REPORT.md) and [mkl_production](../bench/8454h/mkl_production/README.md). The earlier 1 GiB oneMKL candidate run is historical and remains at [mkl_v2](../bench/8454h/mkl_v2/README.md).

## 机器与运行条件

主机为双路 Intel Xeon Platinum 8454H，每路 32 物理核、每核 2 SMT，共 128 个在线逻辑 CPU。运行固定 `taskset -c 0-63`，在此机器上选取 64 个物理核各自的一个 SMT 线程；CPU 0–31 属 NUMA node 0，CPU 32–63 属 node 1。环境为 `OMP_NUM_THREADS=64`、`OMP_PLACES=cores`、`OMP_PROC_BIND=close`、`OMP_DYNAMIC=FALSE`。旧版和新版分别在独立进程中运行，各进程内部按配置顺序执行 warmup 和重复；runner 通过 `/tmp/ozamx-perf.lock` 串行运行，并在 old/new 两次 GEMM 之间一直持锁。

CPU 报告 3 MiB L1d（64 实例）、2 MiB L1i（64）、128 MiB L2（64）、165 MiB L3（2 个实例合计）。支持 AVX-512、AVX512-BF16、AMX-TILE、AMX-BF16 和 AMX-INT8。操作系统为 Ubuntu，Linux 5.15.0-161-generic。编译器为 GCC 11.4.0，OpenMP runtime 为 4.5。CPU 范围显示 800–3400 MHz，governor 为 `powersave`。微基线记录的 `scaling_cur_freq` 是每轮开始/结束时 CPU 0–63 的平均观测值，不代表保证频率或固定工作频率。原机器快照中的 cgroup v2 路径为 `/user.slice/user-1017.slice/session-160729.scope`；`cpu.max` 在可见根目录不可用，采集的 `cpu.stat` throttle 计数为 0。详见机器快照文件。

GEMM 驱动在 main 线程中分配并串行填充 A、B，调用者分配和输入生成都不计入 `GemmTimings`。运行绑定覆盖两个 NUMA 节点，没有设置显式 interleave 策略；调用者输入因此由首次触碰它们的线程决定 NUMA 位置，不能假设输入已均匀跨节点放置。当前预处理和打包的并行输出则会由相应 worker 访问/写入。独立内存微基线采用每个线程团队的静态并行 first-touch，和 GEMM 输入布置不同。

## 驱动与重复语义

两种库使用相同的 `bench/optimization_benchmark.cpp` 和固定 seed。每个尺寸、精度、预算配置只生成一组 A/B/C；驱动将输入生成、向量分配放在计时区间之外。CSV 写一条 `record=warmup` 行，再在同一 A/B 输入上执行五条 `record=rep`；summary 仅统计五条 rep，并给出算术均值、总体标准差、最小值和最大值。FP64 不同预算使用同一尺寸/精度 seed，输入也相同。每条 warmup 和 rep 都记录输出元素之和 `sum(C)` 作为 checksum，可用于配对复核，但本身不是逐元素正确性证明。

warmup 是“本配置的第一次 profile 调用”，不能称作严格冷启动：同一进程中此前可能已有运行时初始化、线程池/权限申请和其他尺寸/配置调用；A/B/C 的分配与生成又在计时外。该早期新版采集时工作区池默认上限为每个调用线程 1 GiB，由 `OZAMX_WORKSPACE_CACHE_BYTES` 控制；设为 `0` 可关闭缓存保留。经过 warmup 后的 rep 可作为本驱动的稳态对比；若临时缓冲需求超过缓存上限，后续重复仍可能发生分配和首次触页。旧版没有相同的工作区复用路径。当前一次 GEMM 的缓冲由调用线程持有，内部 OpenMP worker 不各自缓存一份；多个独立调用线程的保留容量可以叠加，因此缓存上限不是单进程总内存上限。8192 运行没有 OOM，采集时主机可用内存约 921 GiB；本轮没有采样单进程 RSS，也没有 NUMA 交错内存设置。

旧版冻结源直接按原 flags 构建：`-O3 -std=c++17 -mamx-tile -mamx-bf16 -fopenmp`。新版由 CMake Release 构建；当前 `src/gemm.cpp` 额外使用 `-march=sapphirerapids -ffp-contract=off`，库仍启用 `-mamx-tile -mamx-bf16`。平台微基线的最终构建及 flags 见 instruction audit。机器、源文件 SHA-256、准确命令在 run metadata 中。

复跑命令（默认生成新的 timestamp 目录，不覆盖这些最终 CSV）：

```sh
bench/run_8454h_baseline.sh --sizes 256,1024,4096 --precision all \
  --threads 64 --reps 5 --budgets 6,10,15,21
bench/run_8454h_baseline.sh --sizes 8192 --precision all \
  --threads 64 --reps 5 --budgets 6,10,15,21
```

## 匹配 GEMM 结果

总时长单位为毫秒，格式为 `mean ± 总体标准差`。speedup 为旧版 mean / 新版 mean。原始 CSV 保留 warmup、每条重复、checksum 以及 split、pack、compute/reconstruct 各阶段的统计。

| N | 精度/预算 | 旧版总时长 ms | 新版总时长 ms | 加速比 |
|---:|---|---:|---:|---:|
| 256 | FP32 p6 | 1.731 ± 0.060 | 0.608 ± 0.111 | 2.85× |
| 256 | FP64 p6 | 3.727 ± 0.230 | 1.259 ± 0.051 | 2.96× |
| 256 | FP64 p10 | 4.209 ± 0.020 | 1.331 ± 0.012 | 3.16× |
| 256 | FP64 p15 | 4.893 ± 0.032 | 1.443 ± 0.023 | 3.39× |
| 256 | FP64 p21 | 5.721 ± 0.024 | 1.545 ± 0.027 | 3.70× |
| 1024 | FP32 p6 | 13.879 ± 0.293 | 2.126 ± 0.049 | 6.53× |
| 1024 | FP64 p6 | 28.584 ± 5.339 | 3.367 ± 0.050 | 8.49× |
| 1024 | FP64 p10 | 29.472 ± 0.624 | 3.761 ± 0.029 | 7.84× |
| 1024 | FP64 p15 | 33.883 ± 2.337 | 5.040 ± 1.023 | 6.72× |
| 1024 | FP64 p21 | 35.753 ± 0.446 | 5.631 ± 0.292 | 6.35× |
| 4096 | FP32 p6 | 209.123 ± 7.123 | 24.648 ± 3.727 | 8.48× |
| 4096 | FP64 p6 | 484.069 ± 8.819 | 40.236 ± 3.735 | 12.03× |
| 4096 | FP64 p10 | 558.724 ± 46.505 | 58.795 ± 4.969 | 9.50× |
| 4096 | FP64 p15 | 605.080 ± 48.913 | 86.376 ± 7.553 | 7.01× |
| 4096 | FP64 p21 | 647.909 ± 14.529 | 108.126 ± 11.881 | 5.99× |

### 阶段变化

下表列出各阶段旧版/新版均值的比值；大于 1 表示新版更快。阶段耗时仍在上面的 raw CSV 中，不能简单把单阶段加速比当作总加速比。

| N | 精度/预算 | Split | Pack | Compute/reconstruct |
|---:|---|---:|---:|---:|
| 256 | FP32 p6 | 1.58× | 5.34× | 3.46× |
| 256 | FP64 p6 | 1.49× | 9.00× | 6.32× |
| 256 | FP64 p10 | 1.49× | 6.73× | 7.85× |
| 256 | FP64 p15 | 1.41× | 5.16× | 9.41× |
| 256 | FP64 p21 | 1.37× | 4.15× | 10.55× |
| 1024 | FP32 p6 | 30.41× | 3.08× | 3.48× |
| 1024 | FP64 p6 | 10.61× | 4.41× | 7.87× |
| 1024 | FP64 p10 | 10.66× | 3.23× | 7.28× |
| 1024 | FP64 p15 | 10.52× | 2.61× | 5.90× |
| 1024 | FP64 p21 | 9.64× | 2.09× | 6.12× |
| 4096 | FP32 p6 | 45.32× | 7.37× | 4.10× |
| 4096 | FP64 p6 | 23.85× | 14.55× | 6.60× |
| 4096 | FP64 p10 | 22.50× | 9.65× | 5.63× |
| 4096 | FP64 p15 | 18.33× | 7.86× | 4.27× |
| 4096 | FP64 p21 | 19.98× | 6.29× | 3.84× |

大尺寸的主要改善同时来自 split、pack 和 compute/reconstruct。FP32 N=4096 的 split 均值从 111.95 ms 降至 2.47 ms，compute/reconstruct 从 83.26 ms 降至 20.29 ms；FP64 p6 N=4096 的 split 从 280.45 ms 降至 11.76 ms，pack 从 28.43 ms 降至 1.95 ms，compute/reconstruct 从 175.19 ms 降至 26.52 ms。FP64 高预算仍由多个 BF16 component product 累加，计算阶段加速比随预算增加而收窄；4096 p21 compute/reconstruct 为 345.03 ms → 89.89 ms，且总加速比为 5.99×。小尺寸固定成本占比更大，因此总加速比低于中/大尺寸。

### 8192 扩展

此扩展包含 FP32 p6 与 FP64 p6/p10/p15/p21；各自仍为一条 warmup、五条 rep。单位为秒。

| 精度/预算 | 旧版 mean ± SD | 新版 mean ± SD | 加速比 |
|---|---:|---:|---:|
| FP32 p6 | 0.932 ± 0.038 | 0.248 ± 0.011 | 3.75× |
| FP64 p6 | 2.155 ± 0.057 | 0.733 ± 0.498 | 2.94× |
| FP64 p10 | 2.492 ± 0.055 | 0.652 ± 0.010 | 3.82× |
| FP64 p15 | 2.931 ± 0.270 | 0.908 ± 0.013 | 3.23× |
| FP64 p21 | 3.250 ± 0.022 | 1.121 ± 0.025 | 2.90× |

8192 FP64 p6 新版的五次 rep 中首条为 1.728 s，其余四条约 0.472–0.496 s，导致总体标准差达到 0.498 s。表中保留所有重复，没有剔除异常值；这行的均值/加速比应结合原始重复谨慎解读。其他所有配置的配对 seed 与 `sum(C)` checksum 在旧版/新版间一致，且同一配置五次重复的 checksum 一致；这不是完整的逐元素误差审计。

### 8192 工作区容量补测

为检查上述波动和大矩阵预处理成本，额外用同一个新版二进制、相同输入和线程设置，各启动一个进程，分别设置默认 1 GiB 和 4 GiB 保留上限。每配置仍是一次 warmup、五次重复。原始文件为 [supplemental_default_8192.csv](../bench/8454h/supplemental_default_8192.csv) 和 [supplemental_cache4g_8192.csv](../bench/8454h/supplemental_cache4g_8192.csv)，命令和二进制 hash 在 run metadata 中。这里比较的是新版自身的容量设置，不替换前面的 old/new 数据。

| 精度/预算 | 默认 1 GiB 总时长（s，mean ± SD） | 4 GiB 总时长（s，mean ± SD） | 4 GiB split / pack 均值（ms） |
|---|---:|---:|---:|
| FP32 p6 | 0.438 ± 0.327 | 0.232 ± 0.065 | 9.25 / 7.75 |
| FP64 p6 | 0.628 ± 0.294 | 0.301 ± 0.017 | 52.73 / 8.61 |
| FP64 p10 | 0.632 ± 0.016 | 0.435 ± 0.026 | 63.15 / 12.39 |
| FP64 p15 | 0.897 ± 0.004 | 0.721 ± 0.300 | 59.89 / 14.82 |
| FP64 p21 | 1.104 ± 0.026 | 0.765 ± 0.020 | 57.80 / 16.99 |

默认设置的 FP64 p6 split / pack 均值为 164.64 / 72.03 ms；4 GiB 设置降至 52.73 / 8.61 ms。8192 p21 的活跃切片和 packed panels 各约 1.5 GiB，另有 512 MiB residual 与结果缓冲，因此 1 GiB 上限无法保留全部可复用缓冲。更大容量减少重新分配/触页的解释与测量吻合，但本次未采集逐调用 page-fault 或硬件计数器，不能证明它是全部波动的唯一原因。

补测的默认 p6 仍有一次 1.212 s 的重复；4 GiB 的 p15 也有较大的 compute 离散样本，所有样本均保留。该锁只控制本项目的测量任务，不能保证宿主机独占。不能据此得出 p6 本质上慢于 p10，或给出大尺寸固定加速倍数。对这台机器上重复调用的 8192 工作负载，可使用 `OZAMX_WORKSPACE_CACHE_BYTES=4294967296`；这是每个调用线程的保留上限，需要计入应用的内存预算。项目默认值仍为 1 GiB。

### 有效吞吐与实际 BF16 component 工作量

`2N³ / total_seconds` 是按一次理想 FP32/FP64 GEMM 计的有效吞吐，不等同于 AMX 实际执行的指令操作数。FP32 p6 路径执行 6 个 BF16 component products；FP64 执行对应预算数目的 products，即 p6/p10/p15/p21 分别为 6/10/15/21 个。按每个 product 的 `2N³` FLOPs 计，实际 component 工作量为 `2N³ × component_count`；分解和重构的额外操作不包含在这个乘积数中。

| N | 有效 GEMM 操作数 `2N³` | FP32 p6 component 操作数 | FP64 p6 / p10 / p15 / p21 component 操作数 |
|---:|---:|---:|---:|
| 256 | 0.034 GFLOP | 0.201 GFLOP | 0.201 / 0.336 / 0.503 / 0.705 GFLOP |
| 1024 | 2.147 GFLOP | 12.885 GFLOP | 12.885 / 21.475 / 32.212 / 45.097 GFLOP |
| 4096 | 137.439 GFLOP | 824.634 GFLOP | 824.634 / 1,374.390 / 2,061.584 / 2,886.218 GFLOP |
| 8192 | 1,099.512 GFLOP | 6,597.070 GFLOP | 6,597.070 / 10,995.116 / 16,492.674 / 23,089.744 GFLOP |

有效吞吐公式可用于和普通 GEMM 语义比较，但不能把上面的 component 操作数误标为“实际 FP64 FLOPs”或直接与 AVX/AMX 微基线峰值比较。端到端计时还包含打包、调度和重构成本。

## 独立硬件微基线

AVX-512 FMA 微基线经过反汇编核验：每种精度均有 8 条不同目标寄存器的独立 FMA accumulator 链；AMX 每个 loop 执行四条 TDP。Compute 每项约 100 ms，1/32/64 workers；一条 warmup 后记录五条 rep。下表为 arithmetic mean ± population SD，单位 TFLOP/s。

| Kernel | 1 thread | 32 threads | 64 threads |
|---|---:|---:|---:|
| AVX-512 FP32 register FMA | 0.1292 ± 0.0010 | 4.4299 ± 0.0967 | 9.9678 ± 0.0769 |
| AVX-512 FP64 register FMA | 0.0625 ± 0.0029 | 2.5073 ± 0.0394 | 5.0778 ± 0.0146 |
| AMX BF16 register TDP | 2.0497 ± 0.0922 | 80.2230 ± 0.1498 | 160.9841 ± 0.3746 |

AMX 微基线将两个 16×32 BF16 输入 tile 载入 tile registers 后保持驻留，循环更新四个独立 16×16 FP32 accumulator。每条 `TDPBF16PS` 按 `2×16×16×32 = 16,384 FLOPs` 计；不含 packing、矩阵遍历和 GEMM 重构。AVX/AMX 值是这段 register-only 代码的观测 ceiling，不是厂商保证峰值。

内存基线对每个数组分配 256 MiB 对齐缓冲区，并由测量线程团队按静态分工 first-touch。copy 两数组共 512 MiB working set；triad 三数组共 768 MiB，均超过 165 MiB LLC。每条 rep 重复完整 pass 至少 50 ms。CSV 按逻辑流量计字节：copy 每 pass 读 256 MiB、写 256 MiB；triad 读两个 256 MiB 输入并写一个 256 MiB 输出。普通 write-allocate 可能增加实际内存流量。下表是 decimal GB/s，mean ± population SD。

| Kernel | 1 thread | 32 threads | 64 threads |
|---|---:|---:|---:|
| Copy（逻辑带宽） | 8.74 ± 1.99 | 167.43 ± 5.55 | 188.54 ± 1.58 |
| Triad（逻辑带宽） | 12.37 ± 0.47 | 191.85 ± 20.12 | 190.88 ± 2.41 |

这些只是大工作集内存流量带宽，不是保证的 DRAM 峰值，也不是 packed GEMM 的有效带宽。GEMM 还要支付 split、pack、输出/重构和调度成本。

最初的 FMA 微基准使用八个相同初值，编译器把它们合并成一条依赖链，而计数仍乘八；该批 FMA 数字已作废。本报告和正式 CSV 使用不同初值、经过反汇编确认的八条独立链，旧的无效 CSV 不作为公开基线保留。

## 优化内容、正确性与剩余差距

生产路径的变化如下，测量反映这些改动的组合效果，没有将某个单独改动的贡献当作已完成消融实验：

- [preprocess.hpp](../src/preprocess.hpp)：FP32 用 AVX-512 整数 RNE 舍入与 residual 运算；FP64 在持久 OpenMP 团队中执行六轮全局最大值归约、rho45 投影和 SIMD residual 更新。p6/p10/p15 仅保存实际需要的前 3/4/5 片，但仍执行全部六轮投影和错误检查。显式软件 RNE 避免硬件 BF16 转换的 FTZ 行为改变原支持域检查。
- 同一预处理文件将 A、B 按 AMX tile 顺序打包，B 用 AVX-512BW 双源 word permutation 生成相邻 K 的 BF16 pair；每个完整 tile 的行 stride 为 64 字节。masked load/store 处理尾部，所有 padding 明确置零。
- [kernels.S](../src/kernels.S)：SysV 汇编显式安排四个 C tiles 和输入复用。FP32 每个 K32 步进使用 14 次 tile load、24 次 TDP，按 `11,10,20,00,01,02` 顺序；FP64 单组件每步四次 load、四次 TDP，在完整 BK=256 后存储 FP32 结果。
- [gemm.cpp](../src/gemm.cpp)：大矩阵采用 128×128 输出块，小形状使用 32×32 块和较小线程团队；用 AVX-512 完成 FP32 累加、FP32→FP64 拓宽及有序 FP64 相加、非有限检查与尾部复制。最终结果先写独立缓冲，全部成功后提交到 C，保留错误时 C 不变的行为。
- 全部 scratch 按 64 字节对齐，避免串行零初始化并复用工作区。[runtime.cpp](../src/runtime.cpp) 在通用目标代码中检查 CPUID/XSTATE，缓存已确认的进程级 AMX 权限并处理 fork；worker 仍各自配置/释放 tile 状态。

最终验证记录在 [validation_results.json](../bench/8454h/validation_results.json)。100 个矩阵/预算 case 覆盖 K=255/256/257/513、M/N 分块边界、矩形及 padded stride；冻结旧版 1 线程分别与新版 1/4/64 线程比较，每次 2,322,780 个 C 槽位均逐 bit 相同（包含 signed zero），padding guard 全部通过。新版不同线程数也完全一致。原生审计的 147,456 个 component/BK FP32 store 和 730 个 FP64 重建输出均无不匹配。OpenMP ON/OFF Release 构建与 CTest 通过；OFF 构建存在编译器对忽略 pragma 和相关变量的警告。独立复跑命令是 `bash bench/8454h/run_equivalence.sh`，会从仓库内冻结旧源和当前源重新构建。

原代码性能差距有明确的实现因素：串行分片、标量打包/还原、大量每调用分配和初始化、面板布局及过大的输出工作集。4096 的阶段时间已直接展示这些成本大幅下降。Gold 6430 与 8454H 都属于 Sapphire Rapids；更换 SKU 本身不能代替内核优化。

新版仍不能把寄存器微基线直接兑现为完整 GEMM。以 N=4096 为例，FP32 有效端到端吞吐约 5.58 TFLOP/s；按六组件实际工作量和 compute 阶段计约 40.64 TFLOP/s。FP64 p21 对应约 1.27 和 32.11 TFLOP/s，均包含与微基准不同的面板装载、存储、调度和还原工作。寄存器 AMX 测量为约 160.98 TFLOP/s，除以六项/21 项也只得到理想化有效上限，不能作为实测 BLAS 性能。大矩阵仍有工作区容量、NUMA 放置、跨 socket 数据共享和缓存流量成本；这些尚未用硬件计数器逐项归因。

本轮优化保持旧版数值结果，不改变六片截断算法，因此历史 p21 精度与论文的差异也没有被这次性能优化消除。本轮没有重跑论文的完整 Table 4 精度/性能比较；历史差异解释边界仍见 [REPRODUCTION_RESULTS.md](REPRODUCTION_RESULTS.md)。

## 实现与比较边界

该早期优化快照使用手写 AMX 汇编 kernel、SIMD preprocessing/reconstruction、tile-contiguous packed panels、128×128 output cache block，并保留 BK=256。工作区池为 thread-local，该早期快照每个 pool 最高缓存 1 GiB；通过 `OZAMX_WORKSPACE_CACHE_BYTES=0` 禁止保留。N=8192 的实际内存峰值没有单独测量；该 1 GiB 是每 pool 缓存上限，不是进程 RSS 上限。

归档的 [`baseline_original.csv`](../bench/8454h/baseline_original.csv) 来自旧驱动：它固定初始 seed，但每次 warmup/rep 都重新分配、重新生成 A/B/C 并推进 RNG，因此不同重复使用不同输入，且没有输出 warmup 行。该初始记录保留作历史追溯，**不得直接与本报告的固定输入匹配数据计算 speedup**。匹配结果一律使用 `final_before.csv`/`final_optimized.csv` 和 8192 对应文件。

主报告的 before/optimized 数据不使用 oneMKL，也不与历史 Gold 数据作同机性能比较。后续为冻结 v1 额外取得了 workspace-local oneMKL 2026.1 runtime，并用独立基准作补充对照；版本来源、精确 flags、误差和分阶段/API wall 结果见 [oneMKL v1 comparison](../bench/8454h/mkl_v1/README.md)。该补充测量对应归档 v1，不代表后续搜索优化版本。平台峰值和 GEMM 提速均限于这里记录的主机、编译器、亲和性、数据尺寸和工作流。
