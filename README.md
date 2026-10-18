# Intel AMX 上的 FP32/FP64 GEMM 组件积实现

本项目是论文 **BF16 Component-Product Emulation of FP32 and FP64 GEMM on Intel AMX** 的独立实现与实验工程，不是作者源码的移植。

当前 clean 分支保留：

- AMX-BF16 组件积内核与 strict-emulation 路径；
- FP32 三片六项、FP64 六片 ρ=45、6/10/15/21 product 预算；
- 论文原文与官方资料：`third_party/`；
- 会话、实验和决策轨迹：`trace/`；
- 当前实现、误差诊断、构建与基准测试相关文档。

历史 V1–V4、roofline 搜索、旧 benchmark 归档已从 clean 分支移除；需要追溯时使用 `trace/` 中的会话记录。

## 实现要点

- 固定 `BM=BN=BK=256`、`TM=TN=32`；
- 8 个 AMX tile：2 个 A、2 个 B、4 个 FP32 C 象限；
- FP32 六项链：`11 → 10 → 20 → 00 → 01 → 02`；
- FP64 每个 component product 独立完成 `store → FP32→FP64 widen → FP64 add`；
- FP64 正 shift、全局 residual max、ρ=45；
- 输出块由单线程独占，全部完成后事务性提交；
- FP64 私有 block 默认使用 64 B 行 padding，只改变缓存布局，不改变数学和输出字节。

论文声明与工程边界见：

- [论文研读](docs/PAPER_STUDY.md)
- [论文 §6.3 重建](docs/REFERENCE_SECTION_6_3_IMPLEMENTATION.md)
- [复现规范](docs/REPRODUCTION_SPEC.md)
- [strict-emulation 实现与结果](docs/STRICT_EMULATION_IMPLEMENTATION.md)
- [2026-10-16 严格路径结果](docs/strict_emulation/RESULTS_20261016.md)

本项目不宣称作者源码逐行复现；FP64 的误差和性能仍需按论文 Table 4/Figure 9 的工作点解释。

## 环境

当前验证环境为双路 Intel Xeon Platinum 8454H（Sapphire Rapids），GCC 11.4、GNU OpenMP、Intel oneMKL 2026.1。

CPU 0–63 作为 64 个物理核使用；64–127 是 SMT 兄弟线程，性能计时期间必须保持空闲。

## 构建与验证

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
  -DOZAMX_ENABLE_OPENMP=ON \
  -DOZAMX_STRICT_FP64_ROW_PAD_BYTES=64
cmake --build build -j8
OMP_NUM_THREADS=64 ctest --test-dir build --output-on-failure
```

可选的小矩阵 C1 实验开关默认关闭：

```text
OZAMX_SINGLE_TASK_COMPUTE=ON
OZAMX_SINGLE_TASK_PREP_FP64=ON
```

C1 仅用于 N=256 量级的实验；当前大 N FP64 p6 的代码布局回归尚未完全解决，不要直接作为 strict 默认配置。

## 运行基准

当前 oneMKL 位于：

```text
third_party/code/mkl-current
```

构建带 oneMKL 的 benchmark 后，可按项目约定固定 CPU 0–63 和 64 线程运行：

```sh
LD_LIBRARY_PATH="$PWD/third_party/code/mkl-current/lib" \
OMP_NUM_THREADS=64 OMP_PLACES=cores OMP_PROC_BIND=close \
OMP_DYNAMIC=FALSE OMP_WAIT_POLICY=PASSIVE GOMP_SPINCOUNT=0 \
MKL_NUM_THREADS=64 MKL_DYNAMIC=FALSE MKL_THREADING_LAYER=GNU \
OZAMX_WORKSPACE_CACHE_BYTES=8589934592 \
taskset -c 0-63 build/ozamx_benchmark \
  --sizes 256,1024,4096,8192 --threads 64 --reps 5 --precision all \
  --budgets 6,10,15,21
```

N=32768 的完整测量需要更大工作区和更安静的宿主窗口；不能用普通均值替代 median/clean mean。

## 目录

```text
src/          生产实现与 AMX 微内核
include/      公共 API
tests/        正确性、事务和论文路径 probe
tools/        当前诊断、strict campaign 和平台工具
bench/        当前 benchmark driver 与 raw BF16 工具
third_party/  论文、Intel 官方资料和 oneMKL
trace/        跨会话/agent 的本地实验轨迹（不进入 Git）
```
