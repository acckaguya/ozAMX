# oneMKL 原始 BF16-BF16-FP32 headroom 基准

此工具独立测量官方 oneMKL 的 `cblas_gemm_bf16bf16f32`，不调用 ozAMX 内核。其 C 接口为 row/column-major 布局、转置参数、M/N/K、float alpha/beta、`MKL_BF16` 输入及 float 输出；签名见 [Intel oneMKL CBLAS reference](https://www.intel.com/content/www/us/en/docs/onemkl/developer-reference-c/2023-0/cblas-gemm-bf16bf16f32.html)。本地配套头文件 `third_party/code/mkl-2026/venv/include/mkl_cblas.h` 第 1014 行提供同一原型，`libmkl_rt.so.3` 导出 `cblas_gemm_bf16bf16f32`；无需手写 ABI 声明。

本地工具 SHA-256：`bench/raw_bf16.cpp` 为 `feeec6294fa6e090c8e4c90871409b8b43b925e5fe44f4214b9d0be8abd13b92`；`bench/run_raw_bf16.sh` 为 `20edfd3608680397ee6718bed892e2208342936aafa395da3d409ded982534be`。本机 AMX-TILE、AMX-BF16 CPU feature 与当前调用线程 XTILEDATA permission 已由项目 probe 确认。

## 运行方式

从任意目录执行以下命令即可编译并运行 Figure 6 的方阵尺寸序列。正式运行应由实验负责人安排在主基准时间空档，避免 64 核线程池争用：

```sh
/data/home/caiwl/ozAMX/bench/run_raw_bf16.sh \
  --sizes 256,512,1024,2048,4096,8192,16384,32768 \
  --threads 64 --reps 10 --seed 260904 \
  --output /data/home/caiwl/ozAMX/results/raw_bf16.csv
```

脚本固定 `taskset -c 0-63`，设置 oneMKL GNU threading layer，使用工作区 oneMKL 2026.0 runtime，并在输出列记录实际版本、`dladdr` 运行库路径和 `/proc/self/maps` 中的 OpenMP runtime。该主机 `lscpu -e` 显示 CPU 0–63 对应 64 个不同物理 core ID（分布于两个 NUMA node）。小尺寸 smoke 使用 `--sizes 64 --threads 4 --reps 2`。

## 数据与计时边界

- A、B 是独立 `std::mt19937_64` 生成的 FP32 均匀 `[-1,1]` 数据，基种子按 `seed + N`；每个值以 bitwise round-to-nearest-even 转成 BF16 一次。
- 输入生成、BF16 转换、输出分配均在计时区外。每个 N 先调用一次 warm-up，再记录十次原始调用耗时及算术平均值。调用使用 row-major、`alpha=1`、`beta=0`。
- 吞吐按标准 GEMM 工作量 `2N³ / mean_seconds` 计算，同时输出 GFLOP/s 与 TFLOP/s；不会把低精度运算计数混为另一单位。
- 每行 CSV 包含完整十次 raw seconds、checksum、oneMKL 版本、运行库路径、实际 threading runtime maps。CPU affinity 为固定 CPU 0–63。
- 2×2 BF16 与 SGEMM smoke 均检查 C=`[19,22;43,50]`。这验证 API 可执行，不构成 Figure 6 性能数据。
- 以 `MKL_VERBOSE=1` 做过 64×64 smoke，oneMKL 输出 `GEMM_BF16BF16F32(N,N,64,64,64,...)`、GNU thread layer、`NThr:4`；Verbose 首次调用额外包含 JIT 时间，因此不得将该模式用于正式计时。

## 来源和当前状态

目标论文 Figure 6 的参考对象是 oneMKL `bf16bf16fp32`；原始输入和 seed 未由论文提供，因此本工具使用固定、公开的 seed 生成新一组数据。官方 oneMKL C 文档描述该 API 在不具备本机 BF16 硬件的系统上可上转换到 FP32 并调用 SGEMM；本次运行必须同时保留 AMX-capable 主机信息及 runtime 记录，避免把 fallback 结果误标为 raw AMX headroom。

截至工具准备完成，已通过 2×2 BF16 API smoke 和 2×2 SGEMM smoke，并确认 `mkl_get_version_string` 为 `Intel(R) oneAPI Math Kernel Library Version 2026.0-Product Build 20260401 for Intel(R) 64 architecture applications`、`dladdr` 指向工作区 `libmkl_rt.so.3`，maps 显示 `libmkl_gnu_thread.so.3` 与 `libgomp.so.1.0.0`。正式 Figure 6 尺寸测量待主实验线程空档运行，结果由实验负责人保存到 `results/raw_bf16.csv`。
