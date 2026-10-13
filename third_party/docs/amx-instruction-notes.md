# Intel AMX-BF16 实现核对笔记

以下摘录依据 Intel 官方托管的 *Intel Architecture Instruction Set Extensions Programming Reference*（本地文件 `intel-architecture-isa-extensions-programming-reference-dec-2024.pdf`，URL 与哈希见 `../SOURCES.md`）。AMX 指令语义以 Intel 手册为准，论文只规定本次复现的算法和调度。手册也提示部分 AMX 指令已移入最新 Intel SDM；若有歧义，应再查当前 SDM。

## Tile 与内存布局

- AMX-TILE palette 1 提供八个 tile register，每个最多 16 行×64 字节（1 KiB）。`TILECFG` 为各 tile 设置行数和每行字节数 `colsb`；这些元数据决定加载、运算、存储形状。（AMX 引言，手册印刷页 3-1–3-5。）
- `TILELOADD`/`TILESTORED` 按字节 stride 逐行传输。A 可按 row-major BF16 装载：16×32 面板每行恰为 64 字节。B 必须采用 `TDPBF16PS` 所需的成对 BF16 布局；本项目按论文把 K 维相邻 BF16 配成 VNNI pair，并在硬件 probe 和地址映射核验后使用。
- 指令只读写配置的行数与字节数，写入时会清零配置范围之外的 tile 区域。此性质可用于补齐边缘 tile，但不会令越界地址变安全：每个 load 仍须指向有效分配的内存。（AMX §3.1.3。）
- `TDPBF16PS` 从每个源行的 dword 中读取两个 BF16 值；对每个输出元素，在 reduction 方向计算 BF16 pair 的乘积并累加到 FP32 tile。源 tile 与累加 tile 维度必须满足指令的矩阵形状限制。手册的指令编码还规定了源、目的 tile register 的不同约束。（AMX-BF16 指令条目，印刷页 3-43–3-45。）

## 浮点行为

- AMX 浮点指令使用 round-to-nearest-even，等同于屏蔽浮点异常，且不读取或更新 MXCSR 异常标志。`TDPBF16PS` 把 BF16 次正规输入视为零；FP32 次正规累加输入也视为零；FP32 次正规结果会 flush-to-zero。这些是 AMX 的体系结构行为，与调用方的 MXCSR 模式无关。（手册 §3.2 与 `TDPBF16PS` 运算伪码。）
- 因此，可能落入次正规范围的分解分片和累加必须被拒绝或清楚列入数值支持域限制；用标量运算替代不能复现 AMX 的数值行为。

## CPU/OS 权限与安全 dispatch

- CPU feature bits 并不足以保证可执行 AMX。XTILECFG/XTILEDATA 属于扩展处理器状态；Linux 应用需要以 `arch_prctl(ARCH_REQ_XCOMP_PERM, XFEATURE_XTILEDATA)` 请求 XTILEDATA 权限（feature number 18）。权限按线程授予。主线程 probe 成功不能授权 OpenMP workers；每个可能执行 tile 指令的 worker 都必须先请求并获得权限。
- 运行时先检查 CPU 的 AMX-TILE 和 AMX-BF16 能力，再请求/确认 OS 权限。未支持或未获权限时，不应执行 `LDTILECFG` 等 AMX 指令；应在进入 AMX 路径前 dispatch，使非 AMX 主机收到明确错误而不是 `SIGILL`。
- kernel 结束后以 `TILERELEASE` 释放 tile state。按论文计时边界，tile 配置可在 timed compute 区域之前完成，并在 kernel 之后释放。

## 本机编译与指令证据

本机 GCC 11.4.0 使用 `-mamx-tile -mamx-bf16` 成功编译并运行 `tools/amx_probe.c`。输出为 `AMX_PERM=OK`、`AMX_EXEC=OK sample_c00=64.0 expected=64.0`。该 probe 在执行指令前请求 `XFEATURE_XTILEDATA`，并计算已知 BF16 矩阵积。此结果证明本机编译器头文件提供 `_tile_dpbf16ps`，且当前主机/OS 允许该基础指令路径；它不验证论文的分解、打包或组件积求和顺序。
