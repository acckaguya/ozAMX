# 三种 FP64 六层分解的原生 AMX 对照诊断

本文描述历史 Gold 实验的数值诊断协议。下列构建命令已适配当前 SIMD/汇编实现；历史输入和诊断结果保持原样，当前机器的核心验收见 [8454H 基线](8454H_PERFORMANCE_BASELINE.md)。Python 导出器另外需要 NumPy。

本诊断针对同一组 N=256 输入，分别导出论文字面 `rho=45`、直接 BF16 residual 舍入和诊断性 `rho=44` 的六层切片。后两者是数值假设对照，不归因于论文作者。它复用 `tools/native_kernel_audit.cpp` 所包含的私有 AMX panel kernel，逐个 component product 执行真实 AMX FP32 store，并按预算的对角线次序 widen、累加至 FP64。long-double 独立 dot 仅作参考，不代替 AMX 执行。

导出文件采用显式的小端格式：`A.f64le`、`B.f64le` 是 row-major `<f8`，每个 `{method}_{A,B}.bf16le` 是 slice-major `[6,256,256]` 原始 `<u2` BF16 位模式。`metadata.json` 记录 seed、随机流、维度、方法归属、数据布局及每个文件的 SHA-256；`checksums.sha256` 可独立核验。导出不增加或重排随机数调用：沿用原诊断的 PCG64 流，先推进 64、128 的 A/B draws，再按 A 后 B 生成 N=256 输入。

在正式计时和 raw oneMKL campaign 完成后，运行完整管线（不要与测量任务并行）：

```sh
ROOT=$PWD
python3 "$ROOT/tools/diagnose_fp64_alternative.py" \
  --sizes 256 --seed 20261012 --export-dir /tmp/ozamx-alt-256 \
  > /tmp/ozamx-alt-256-report.json
(cd /tmp/ozamx-alt-256 && sha256sum -c checksums.sha256)
cmake -S "$ROOT" -B "$ROOT/build" -DCMAKE_BUILD_TYPE=Release -DOZAMX_ENABLE_OPENMP=ON
cmake --build "$ROOT/build" --target ozamx_native_alternative_accuracy -j4
OMP_NUM_THREADS=64 "$ROOT/build/ozamx_native_alternative_accuracy" /tmp/ozamx-alt-256 \
  > /tmp/ozamx-native-alternative.csv
```

命令从仓库根目录执行。CSV 的 `summary` 行中 `eF_*` 是相对原始 A@B long-double 参考的 Frobenius 相对误差，`scaledmax_*` 是逐元素误差除以 `|A|@|B|` 的最大值；`selected_longdouble` 只度量选中 BF16 乘积集合，`selected_fp32_rounded` 对每个独立 dot 先转 FP32 再重建，`actual_amx` 则来自 AMX 实际 tile store。配套的 `product` 行逐 component pair 比较每个所选 AMX FP32 store 与 long-double dot 转 FP32 的结果，列出不一致元素数和最大 ULP。

本次只准备导出器、独立诊断源码及复跑说明；正式 campaign 结束前不导出 N=256 矩阵、不编译或运行诊断。运行前应记录实际编译器、线程设置及 `long double` 位数；本机既有原生审计记载其 significand 为 64 bit（x87 extended 存入 16-byte ABI 槽），不是 binary128。
