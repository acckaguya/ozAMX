# 参数变体正确性搜索

`run_variant_gate.sh` 将 CMake cache 参数注入 100-case 严格等价性 gate；每个变体都会从冻结旧源重建 baseline、配置候选实现、依次运行 baseline 1 thread 与候选 1/4/64 threads，并逐 case 核对类型、M/N/K、ldc、budget、输出长度、每个 bit（含 signed zero）以及 padding sentinel。它不以平均误差替代输出一致性。示例：

```sh
bash bench/8454h/search/run_variant_gate.sh -D<root-exposed-tuning-option>=<value>
```

按当前 root 的 CMake tuning 接口替换参数名和值；参数必须是一个无空格的 `-DNAME=VALUE` token。`OZAMX_BUILD_DIR` 可指定保留候选构建目录；设置 `OZAMX_KEEP_VARIANT_BUILD=1` 时保留默认临时构建目录。所有编译和测试持有 `/tmp/ozamx-perf.lock`。

当前已有的逐位 corpus 来自同 seed 输入，覆盖小矩形、M/N=127/128/129/255/256/257、K=255/256/257/513、FP32、FP64 的 p6/p10/p15/p21、A/B/C 非紧密 leading dimension 和 C padding canary。该 gate 特别适用于有旧版逐位兼容约束的 tile/block/layout 调参。

后续探索时建议在这个 gate 之外安排独立 case 集：

- SIMD 边界：M/N/K 在 15/16/17、31/32/33、63/64/65、127/128/129、255/256/257 两侧；随机矩形和不同 `lda/ldb/ldc`，行 padding 与末尾 guard 区分别检查。
- IEEE 输入/拒绝边界：正负零、BF16 round-halfway 两侧、FP32/FP64 可表示边缘、残差项、NaN、正负 Inf、subnormal、累加溢出；错误输入必须验证 C 完全未写。
- 事务语义：K=0 的零结果、M/N=0 与无效 leading dimension、地址尺寸溢出；成功计算和验证失败都检查 C 的行间及尾部 guard。
- 工作区与并发：从新进程分别设 `OZAMX_WORKSPACE_CACHE_BYTES=0` 与默认上限；多个调用线程各自分配输入/输出并并发重复 GEMM，和串行同输入参考逐 bit 比较。不要在已经初始化 thread-local pool 的同一进程中临时改 cache 环境变量。

以上是扩展搜索设计，不表示所有项目已运行。已实际执行的固定测试以主仓库 `bench/8454h/validation_results.json` 和 v1 快照记录为准。

## Candidate analysis archive

The isolated-kernel experiments and current comparison are summarized in [docs/8454H_KERNEL_IDEAS.md](../../../docs/8454H_KERNEL_IDEAS.md). Concise candidate notes are in [`ideas/experiment_notes.md`](ideas/experiment_notes.md). Machine-readable phase/fault medians and provenance are in [`ideas/comparison.json`](ideas/comparison.json) and [`ideas/experiment_metadata.json`](ideas/experiment_metadata.json). These reports document candidates and do not mark them adopted.

The selected-v2 matched oneMKL follow-up is documented in [mkl_v2/README.md](../../mkl_v2/README.md), with the raw CSV and v1 comparison table linked there.

Final frozen production-linked oneMKL results (2 GiB cap) are archived in [`mkl_production`](../mkl_production/README.md); the full before/final/MKL table is linked there. The 1 GiB isolated v2 candidate run remains historical.
