# Intel AMX-BF16 实现核对笔记

以下笔记最初依据 Intel 官方托管的 *Intel Architecture Instruction Set Extensions Programming Reference*，2026-10-13 已以当前 SDM v093 和 Linux XSTATE 规范复核。当前原始文档、8454H 平台资料和 SIMD 示例见 [资料库入口](../intel/README.md)；SDM Vol.2B 的 `TDPBF16PS` 条目为印刷页4-715/716。AMX 指令语义以对应版本 Intel 手册为准，论文规定本次复现的算法和调度；未来指令汇编中的条目不表示8454H全部支持。

## Tile 与内存布局

- AMX-TILE palette 1 提供八个 tile register，每个最多 16 行×64 字节（1 KiB）。`TILECFG` 为各 tile 设置行数和每行字节数 `colsb`；这些元数据决定加载、运算、存储形状。（AMX 引言，手册印刷页 3-1–3-5。）
- `TILELOADD`/`TILESTORED` 按字节 stride 逐行传输。A 可按 row-major BF16 装载：16×32 面板每行恰为 64 字节。B 必须采用 `TDPBF16PS` 所需的成对 BF16 布局；本项目按论文把 K 维相邻 BF16 配成 VNNI pair，并在硬件 probe 和地址映射核验后使用。
- 指令只读写配置的行数与字节数，写入时会清零配置范围之外的 tile 区域。此性质可用于补齐边缘 tile，但不会令越界地址变安全：每个 load 仍须指向有效分配的内存。（AMX §3.1.3。）
- `TDPBF16PS` 从每个源行的 dword 中读取两个 BF16 值；对每个输出元素，在 reduction 方向计算 BF16 pair 的乘积并累加到 FP32 tile。源 tile 与累加 tile 维度必须满足指令的矩阵形状限制。手册的指令编码还规定了源、目的 tile register 的不同约束。（AMX-BF16 指令条目，印刷页 3-43–3-45。）

## 浮点行为

- AMX 浮点指令使用 round-to-nearest-even，等同于屏蔽浮点异常，且不读取或更新 MXCSR 异常标志。`TDPBF16PS` 把 BF16 次正规输入视为零；FP32 次正规累加输入也视为零；FP32 次正规结果会 flush-to-zero。这些是 AMX 的体系结构行为，与调用方的 MXCSR 模式无关。（手册 §3.2 与 `TDPBF16PS` 运算伪码。）
- 因此，可能落入次正规范围的分解分片和累加必须被拒绝或清楚列入数值支持域限制；用标量运算替代不能复现 AMX 的数值行为。

## CPU/OS 权限与安全 dispatch

- CPU feature bits 并不足以保证可执行 AMX。XTILECFG/XTILEDATA 属于扩展处理器状态；Linux 应用需要以 `arch_prctl(ARCH_REQ_XCOMP_PERM, XFEATURE_XTILEDATA)` 请求动态特征许可（feature number 18）。[Linux官方XSTATE规范](https://www.kernel.org/doc/html/latest/arch/x86/xstate.html)明确许可按进程有效，fork继承、exec清除；各task首次使用时另行分配状态缓冲。此前“许可按线程授予、每个worker必须分别请求”的说法混淆了进程许可和线程状态，现已纠正。当前8454H同进程worker核验见 [机器快照](../intel/xeon-8454h/hardware-snapshot/snapshot.json)。各执行线程仍需正确配置和管理自己的tile状态；优化前的每worker查询是实现选择，当前实现由调用方确认并缓存进程权限。
- 运行时先检查 CPU 的 AMX-TILE 和 AMX-BF16 能力，再请求/确认 OS 权限。未支持或未获权限时，不应执行 `LDTILECFG` 等 AMX 指令；应在进入 AMX 路径前 dispatch，使非 AMX 主机收到明确错误而不是 `SIGILL`。
- kernel 结束后以 `TILERELEASE` 释放 tile state。按论文计时边界，tile 配置可在 timed compute 区域之前完成，并在 kernel 之后释放。

## 历史平台编译与指令证据

本机 GCC 11.4.0 使用 `-mamx-tile -mamx-bf16` 成功编译并运行 `tools/amx_probe.c`。输出为 `AMX_PERM=OK`、`AMX_EXEC=OK sample_c00=64.0 expected=64.0`。该 probe 在执行指令前请求 `XFEATURE_XTILEDATA`，并计算已知 BF16 矩阵积。此结果证明本机编译器头文件提供 `_tile_dpbf16ps`，且当前主机/OS 允许该基础指令路径；它不验证论文的分解、打包或组件积求和顺序。

上段为2026-10-12 Gold6430实验记录，不能当作当前8454H的新性能测量。当前平台的CPUID/XCR0、进程许可和指令执行核验单独保存在上述机器快照中；AVX2、AVX-512及BF16/FP16指令研读见 [综合笔记](../intel/8454H_STUDY.md)。
