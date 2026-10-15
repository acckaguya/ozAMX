# 8454H 优化版 v1 冻结归档

当前实现的独立可构建快照位于 [`bench/8454h/versions/v1/`](../bench/8454h/versions/v1/)。快照包含公共头文件、核心源码与汇编、验证和诊断程序、优化基准驱动、优化前核心源码、匹配前后 CSV、机器/运行元数据、性能报告及等价性复现驱动。它不含构建产物、重复的逐轮 run 目录或第三方下载。`MANIFEST.sha256` 记录快照内全部文件（清单本身除外）的 SHA-256。

## 重建与验证

在仓库根目录执行：

```sh
cd bench/8454h/versions/v1
sha256sum -c MANIFEST.sha256
cmake -S . -B /tmp/ozamx-v1-build -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/ozamx-v1-build -j2
ctest --test-dir /tmp/ozamx-v1-build --output-on-failure
/tmp/ozamx-v1-build/ozamx_native_kernel_audit
```

等价性程序从归档中的 `bench/8454h/before/` 重建旧版，从快照根目录配置新版；默认临时产物会自动清理：

```sh
bash bench/8454h/run_equivalence.sh
```

这类构建和运行需串行占用机器性能锁 `/tmp/ozamx-perf.lock`。关闭 OpenMP 的独立配置为 `cmake -S . -B /tmp/ozamx-v1-noomp -DCMAKE_BUILD_TYPE=Release -DOZAMX_ENABLE_OPENMP=OFF`。

## 设计与实现

v1 保持公共 GEMM API、FP32 与六片截断 FP64 数值算法和既有逐位输出。主要改进面向 8454H 的 AMX 与带宽：使用手写 AMX 汇编；在 tile-contiguous 面板中布局打包数据；以 128×128 输出块和 BK=256 执行；SIMD 化 split、pack、FP32 store 与 FP64 重建；复用 64 字节对齐的调用线程工作区，thread-local LRU 默认最多保留 1 GiB；针对 SIMD 尾 lane 做合法性掩码；运行时检查 CPUID/XSTATE 并请求进程级 AMX 权限。实现细节冻结在快照源码中，具体阶段划分和边界见性能报告。

## 验证结果

归档 `bench/8454h/validation_results.json` 是验证记录。100 个固定 case 覆盖 FP32 和 FP64 p6/p10/p15/p21、矩形尺寸、M/N tile 边界、K=255/256/257/513 与 C 行 padding。优化前 1 线程分别与优化版 1/4/64 线程作严格逐位比较，共 2,322,780 个 C 槽位，所有比较 mismatch 与 padding guard failure 均为 0；优化版线程数之间也一致。原生审计中 147,456 个组件/BK FP32 stores 与 730 个 FP64 reconstruction 输出均逐位通过。OpenMP 开启/关闭的 Release 构建及 CTest 通过；64 个同时发起的首次 AMX 权限请求成功，fork 子进程观察到继承权限。完整的独立复跑命令见上文及快照 `run_equivalence.sh`。

## 性能记录与适用范围

配对性能报告见快照中的 `docs/8454H_PERFORMANCE_BASELINE.md`，原始数据与硬件/编译元数据均随附。Platinum 8454H 的 256、1024、4096 主尺寸下，FP32/FP64 总耗时相对冻结旧版约提升 2.85×–12.03×；8192 扩展约提升 2.90×–3.82×。这些结果只适用于报告所列硬件、编译器、绑定和输入协议，不能外推到其他 CPU，也不代表对 oneMKL 的胜出。阶段变化和 8192 变异的限制在性能报告中有说明。

冻结算法仍沿用旧版六片 FP64 截断，性能优化没有改变其历史精度边界。归档未包含 oneMKL 比较；对应的 MKL baselines 仍待基线采集完成后链接。归档后如需实验优化参数，应从 v1 复刻并生成新版本，不覆盖本快照。
