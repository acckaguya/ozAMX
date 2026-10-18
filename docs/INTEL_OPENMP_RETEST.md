# Intel OpenMP runtime retest

状态：初步完成。分支：`codex/intel-openmp-retest`。日期：2026-10-18。

## 结论

在**同一份 GCC 编译的 benchmark 二进制**上，通过 `LD_PRELOAD=libiomp5.so` 切换 Intel OpenMP runtime，和 GNU `libgomp` 做对照。`LD_DEBUG=bindings` 确认 benchmark 的 `GOMP_parallel` 实际绑定到了 `libiomp5.so`，`KMP_VERSION=1` 输出 Intel OMP 5.0.20260828。

结果**不支持把 strict 默认运行时无条件切到 Intel OpenMP**：

- N8192 FP32 有约 2% 的小幅收益；
- N16384 FP32 基本中性到约 1% 回退；
- FP64 p6 在 N16384 的交替配对中没有稳定收益，甚至约 2% 回退；
- FP64 p21 在 N8192 有小幅收益，但 N16384 受宿主尖刺污染，未完成有效对照；
- 先前单进程 10-rep 中 p6 N8192 的“Intel 明显更快”与后来交替进程配对方向不一致，说明窗口漂移和线程池启动成本足以改变结论，不能作为稳定因果证据。

因此这次测试只证明 **GNU codegen + Intel OMP runtime** 的兼容性和性能量级，不证明 full oneAPI + Intel compiler 会得到同样结果。

## 测试配置

- binary：`/tmp/ozamx-strict-fused-final/ozamx_benchmark`
- compiler：GCC 11.4，代码生成仍是 GNU ABI；未使用 `icpx`
- Intel runtime：`intel_openmp-2026.2.0` wheel 中的 `libiomp5.so`
- GNU runtime：系统 `libgomp.so.1`
- 64 threads，`taskset -c 0-63`
- `OMP_DYNAMIC=FALSE`、`MKL_DYNAMIC=FALSE`
- MKL baseline 对所有臂均使用 `MKL_THREADING_LAYER=GNU`
- GNU PASSIVE：`OMP_WAIT_POLICY=PASSIVE`、`GOMP_SPINCOUNT=0`
- Intel：`KMP_AFFINITY=compact`、`KMP_BLOCKTIME=200`、`OMP_WAIT_POLICY=ACTIVE`

Intel arm 的命令核心：

```sh
LD_PRELOAD=/tmp/ozamx-intel-openmp/intel_openmp-2026.2.0.data/data/lib/libiomp5.so \
KMP_AFFINITY=compact KMP_BLOCKTIME=200 OMP_WAIT_POLICY=ACTIVE \
OMP_NUM_THREADS=64 OMP_DYNAMIC=FALSE \
MKL_NUM_THREADS=64 MKL_DYNAMIC=FALSE MKL_THREADING_LAYER=GNU \
OZAMX_WORKSPACE_CACHE_BYTES=8589934592 \
taskset -c 0-63 ozamx_benchmark ...
```

## 代表性结果

数值为 API wall；ratio=Intel/GNU。下表的 N8192 FP32、N16384 FP32、N8192 p21 使用 10-rep 单进程；N8192/N16384 p6 另列交替进程 5-rep 的保守结果。

| 场景 | GNU PASSIVE 中位 | Intel 中位 | ratio | 判定 |
|---|---:|---:|---:|---|
| FP32 N8192 | 0.1462 s | 0.1432 s | **0.980** | Intel 小幅快 |
| FP32 N16384 | 1.1014 s | 1.1169 s | 1.014 | 约 1% 回退 |
| FP64 p6 N8192，交替 5-rep | 0.3417 s | 0.3677 s | 1.076 | Intel 回退，不能采用 |
| FP64 p6 N16384，交替 5-rep | 2.1276 s | 2.1684 s | 1.019 | 约 2% 回退 |
| FP64 p21 N8192，交替 5-rep | 0.7388 s | 0.7122 s | **0.964** | Intel 约 4% 快 |
| FP64 p21 N16384 | 5.10 s（仅 2 个有效样本） | 5.33 s（受尖刺） | 无有效结论 | 需要干净窗口重测 |

GNU ACTIVE 作为等待策略对照：N8192 FP32 约 0.1460 s，与 Intel 0.1432 s 接近；说明一部分差异来自等待策略，而不是 runtime 本身。

## 边界

1. 这是 runtime swap，不是 Intel oneAPI 编译器重编译；GCC 生成的 `GOMP_*` 调用由 libiomp5 的兼容层接管。
2. MKL baseline 的 `libmkl_gnu_thread` 在 Intel arm 中也通过 GOMP 符号绑定到 libiomp5，因此 MKL 侧不是独立固定 runtime；headline 只应看 ozAMX API。
3. 当前宿主是动态频率、NUMA balancing=1，N16384/N32768 多次出现秒级尖刺；p21 N16384 未完成。
4. 这次结果不能替代论文的 8462Y+ + Intel oneAPI + Intel OpenMP + 固定频率协议。
5. 需要真正评估 Intel 编译器代码生成时，应在独立分支安装 `icpx` + oneAPI 2026.1，用 `icpx -qopenmp` 重新构建，并保持输入、线程、亲和、cap 和 strict 配置不变。

## 原始产物

本地 `/tmp/intel_omp_*`、`/tmp/gnu_*` CSV 和日志保留；未推送。分支只保存本报告和后续可复现 runner。
