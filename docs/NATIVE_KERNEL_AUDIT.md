# AMX 原生乘积与面板验收

本文最初记录 Gold 6430 上的诊断。2026-10-13 已用当前 8454H 的 tile-contiguous 打包及汇编内核复查，下列验收计数仍全部通过；历史验证工件已从 clean 分支移除；当前源码 hash 以构建产物为准。

本记录只检查 BF16 component dot 的原生 AMX 路径、VNNI packing、padding 和 FP64 重建顺序；它不替代端到端精度报告，也不证明所有 FP64 输入域均受支持。

## 方法

持久化诊断源代码为 `tools/native_kernel_audit.cpp`；历史版本 SHA-256 为 `c95f08989c53c87fdc66db5211d537ed4f68359b954f35be4e531d7695ef9c2d`，当前版本为 `8c3e66d56b6b81b65f067bee7380d5b41ca0eeca9529b94dfc6f92c262775178`。它通过相对源文件位置的 `../src/gemm.cpp` 包含内核实现，调用内部 `split64`、`pack64` 和 `run_fp64_product`，没有改动稳定 API，也没有把 scalar 实现用于正式 GEMM。它对每个所选 component pair 与每个 BK 面板，将 AMX 存储的 FP32 tile 元素同 long-double 直接 dot 后转成 FP32 的结果逐位比较；同时使用当前索引映射逐项校验 A packing、B 的 K 相邻 VNNI pair 和所有边界零填充。最后用六层 p21 GEMM 输出与独立重建值逐位比较：参考值按 BK 顺序、对角线递增和对角内 A slice 递增，对每个 BF16 dot 求 long-double 和、转成 FP32，再 widen 并累加至 FP64。

测试形状为 `5×7×7`、`16×19×256`、`17×23×512`，输入为固定种子的有符号均匀 `[-1,1]` FP64 随机数。六个 slice 的所有 36 个 component pair 都参与单项验收。编译和运行方式：

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DOZAMX_ENABLE_OPENMP=ON
cmake --build build --target ozamx_native_kernel_audit -j4
OMP_NUM_THREADS=64 build/ozamx_native_kernel_audit
```

以上命令从仓库根目录执行。该主机的 `std::numeric_limits<long double>::digits` 为 64 bit，`sizeof(long double)` 为 16 byte；即 x87 80-bit extended 精度存放于 16-byte ABI 对齐槽中，不是 quad precision 或任意精度 superaccumulator。

## 结果

已从 `/tmp` 工作目录用上述持久化源码复跑，结果与 scratch 版本一致。诊断共检查 147,456 个 component/BK FP32 store；每一个都与对应 long-double dot 转换到 FP32 的结果逐位相同，最大差异为 0 ULP。A packing、B VNNI pair packing 和边缘 padding 均为 0 个不匹配或非零填充值。p21 面板顺序重建检查了 730 个输出元素，和公开 GEMM 路径逐位相同。

这说明在这些覆盖形状和随机输入上，AMX component product、BK 面板边界、pack 布局和 FP64 product 累加顺序没有产生可测偏差。它没有解释完整 GEMM 的 p21 与论文 Table 4 的差距；split/truncation 误差由单独诊断处理。long double 参考按本机 64-bit significand 扩展精度计算，不应解释为任意指数域上的精确 superaccumulator。

## 指令反汇编

历史 Release `gemm.cpp.o` 的 OpenMP tile-kernel clone 中，K32 六项产品链是 14 条 `TILELOADD` 指令。当前 [kernels.S](../src/kernels.S) 显式实现同一产品次序：每个 K32 步进 14 次输入装载、24 次 TDP，四个 FP32 accumulator tiles (`tmm4`–`tmm7`) 保持驻留。FP64 单组件内核每步装载 2 个 A tile 和 2 个 B tile，执行四条 TDP，并在完整 BK 后存储 FP32 结果供拓宽还原。
