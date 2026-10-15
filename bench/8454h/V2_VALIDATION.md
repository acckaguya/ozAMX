# 8454H V2 最终生产版验证

本记录对应最终冻结的生产源码，不对应之前的 bounded-commit 实验候选。生产静态库来自 `/tmp/ozamx-production-final/libozamx.a`，SHA-256 为 `ddfe885c2ba58089accd4e747aecb53a18422554e06fc409965e2f47b7d92251`。核心源码 SHA-256：`src/gemm.cpp` `8a5d27440c604df9304b75769e3c048a6748789aab6ee8fed3a5c3446335a85b`，`src/preprocess.hpp` `df36a028fbbeec62bcacc5a0a50194f917285d20fd9cf231abd4c28d4013ee31`，`src/kernels.S` `94af3cf4345b2383100e4d8d883be57b084ec68d12e056f80c4a8bb77bc9bd68`，`src/runtime.cpp` `63a3df726c220dddd51dc1e962d1d2169c74722a4e9452b76a4d731a0c500774`，`src/tuning.hpp` `2dc89e5f8a0986da508eca9931e94130be96a0b098c9f0ab8d35a6217ecb4798`。完整清单见同目录的 `MANIFEST.sha256`。

最终构建配置为 CMake Release、OpenMP 开启、`CACHE_BLOCK=128`、`PREP_GRAIN=16384`、`MIN_COMPUTE_WORK=8`、`TILELOAD_HINT=1`、`LOAD_SCHEDULE=0`、`LOOP_ORDER=0`、`MN_ORDER=0`。工作区缓存默认值为 2 GiB；FP64 K≥4096 使用 late 检查模板，其余走 eager 检查。内核用 `-O3 -march=sapphirerapids -ffp-contract=off` 编译。

最终生产库的 47-case 扩展 gate 覆盖不规则矩形、256/512 对齐边界及 1024³，FP32 和 FP64 的 6/10/15/21 预算；包含 padded A/B/C、长双精度 oracle、小形状逐位输出比较及大形状完整槽摘要。默认 2 GiB cache 与 0 cache、生产库与旧优化库之间四组比较均为 0 bitwise mismatch，每组比较 8,333,440 个 C/guard 槽。机器结果在 [`final_production_extended47.json`](final_production_extended47.json)。

另有 100-case frozen-baseline 等价性检查：旧版单线程与生产版 1/4/64 线程均逐位相同，包含 signed zero 和 padding；生产版不同线程数之间也逐位相同。六组比较各覆盖 2,322,780 个 C/padding 槽，全部 0 mismatch；等价性重建库与最终生产库 SHA 完全一致。FP64 late 路径的 K=4096 和 K=4097 不规则矩形高幅溢出探针均按预期抛错且 C 完全不变；1024×1024×256 的 A=C、B=C alias 探针也都与非 alias 输出逐位相同。

OpenMP 开启的冻结构建通过 CTest 1/1 和 native kernel audit：147,456 个 FP32 store、730 个 FP64 reconstruction 均逐位相同，packing/padding/reconstruction mismatch 为 0。另以相同 tuning 配置完成 OpenMP 关闭的完整构建，CTest 1/1 通过。独立 v2 快照重建得到与生产库完全相同的静态库 SHA，快照 CTest 3/3 与 native audit 也通过。机器结果见 [`final_production_validation_summary.json`](final_production_validation_summary.json)。最终选中版本中不包含 bounded-commit 改动；该隔离实验的证据保留在 [`bounded_commit_candidate_summary.json`](bounded_commit_candidate_summary.json)。

快照独立重建及检查命令：

```bash
cmake -S bench/8454h/versions/v2 -B /tmp/ozamx-v2-snapshot-build \
  -DCMAKE_BUILD_TYPE=Release -DOZAMX_ENABLE_OPENMP=ON
cmake --build /tmp/ozamx-v2-snapshot-build -j2
flock -x /tmp/ozamx-perf.lock ctest --test-dir /tmp/ozamx-v2-snapshot-build --output-on-failure
flock -x /tmp/ozamx-perf.lock /tmp/ozamx-v2-snapshot-build/ozamx_native_kernel_audit
```
