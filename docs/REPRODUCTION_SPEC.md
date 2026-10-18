# 复现规范：AMX 上以 BF16 component products 模拟 FP32/FP64 GEMM

本文保留原论文复现的数值规范；下文实现和计时细节描述优化前版本。2026-10-13 的 8454H 优化保留产品顺序与 BK=256，更新了 SIMD 分片/打包、内存布局、调度、权限缓存和累加还原。当前实现与同机测量见 [strict-emulation 实现与结果](STRICT_EMULATION_IMPLEMENTATION.md)。

## 来源与实验对象

来源为 Cui、Liu，*BF16 Component-Product Emulation of FP32 and FP64 GEMM on Intel AMX*，arXiv:2609.04663v1，2026-09-04；本地论文 `third_party/papers/2609.04663v1.pdf`。完整研读与证据覆盖见 [PAPER_STUDY.md](PAPER_STUDY.md)。当前 PDF 无作者实现链接或 appendix。

论文研究实数矩阵 `C=AB`。原始实验全部是方阵 `M=N=K`，没有 alpha/beta、transpose、conjugate、一般 BLAS 接口和矩形形状评测。其算法定义可支持一般 M/N/K，但 tile 边缘、任意 stride、公共 API、NaN/Inf/fallback 都未定义，需在复现工程中单独声明实现边界。

## 数值接口与支持域

- AMX-FP32：输入/输出 FP32；论文数值讨论假设 component products、AMX tile 累加及目标结果有限。TDPBF16PS 没有可读异常 flag；store 后 isfinite 检查能发现非有限结果（包括溢出），但合法零、抵消和被 FTZ/underflow 清零的项不能普遍区分。本复现可拒绝明显不安全的指数输入，无法证明所有运行时下溢都能检测；影响结果的下溢/overflow 一律属于 unsupported，不做 fallback。
- AMX-FP64：有限非零输入满足 `2^-126 ≤ |x| ≤ (2−2^-7)·2^127`，也允许 0；输出是 FP64，可超出 BF16 域。若整个 residual 矩阵为 0，本层和所有后续片置 0。对某个元素而言，若非零 residual 的 projection round 为 BF16 零，该零分片合法且 residual 仍保留（`R_next=R−0`），后续 slice 继续处理；这与整矩阵 residual 为 0 的提前终止不同。非零 BF16 subnormal slice 仍在论文无缩放实现范围之外；六片后遗漏的 residual 本来就是算法截断误差。
- NaN/Inf、FP64 域外值、非零 BF16 subnormal slice、影响 AMX FP32 结果的中间溢出/下溢不受支持；没有动态缩放、异常恢复或 native BLAS fallback。
- 目标是与 oneMKL SGEMM/DGEMM 比较，不是 bitwise 相同，也不提供普适误差界。

## 算法

### FP32

```text
R_A = A
for r = 0,1,2:
    A_r = round_BF16(R_A)
    R_A = round_FP32(R_A - A_r)
# B 同样处理
```

无 scaling。数学上选 `S3={(i,j):i+j<3, 0≤i,j<3}`，即六项 `00,01,10,02,11,20`。三个未选对 `12,21,22` 以及终端 residual 项不算。每个项是 BF16×BF16 的 AMX 矩阵积，沿 K 以 FP32 累加；六个组件项也累加进 FP32 输出。

落地时使用 §6.2、Eq.(19) 的 tile load 复用次序：`11,10,20,00,01,02`。它与 Algorithm 1 的循环次序 `00,01,02,10,11,20` 不同；FP32 求和不满足结合律，所以既保持物理顺序，也在结果与实验记录中声明该顺序。

### FP64

对每个 operand 固定六片，不因矩阵阶数改变深度：

```text
R = X
for r = 0..5:
    if R is exactly zero:
        X_r = 0; R = 0; remaining slices = 0
    else:
        v = ceil(log2(max_ij(abs(R_ij))))
        sigma = 2^(v + 45)       # ρ = 53 - 8 = 45
        Z = fl64(fl64(R + sigma) - sigma)
        X_r = round_BF16(Z)
        R = fl64(R - X_r)
# 丢弃 R^(6)，不做缩放或 scale metadata
```

论文描述每个 component result 的 store/widen/add 顺序，并规定所选产品的序列；以下将其落实为本实现契约：每个产品独立完成 FP32 tile accumulation，store 后精确 widen，再按表序加到 FP64 accumulator。论文 Eq.(16) 给的是 full-K 数学表达，没有完整 BK panel loop 伪码，故该 panel schedule 和其舍入次序不宣称为作者唯一可行调度。

| 变体 | 条件 | 按对角线及每条线内 i 递增的产品顺序 | 数量 |
|---|---|---|---:|
| FP64-6 | `i+j<3` | `00; 01,10; 02,11,20` | 6 |
| FP64-10 | `i+j<4` | 上一行全部；再 `03,12,21,30` | 10 |
| FP64-15 | `i+j<5` | 上一行全部；再 `04,13,22,31,40` | 15 |
| FP64-21 | `i+j<6` | 上一行全部；再 `05,14,23,32,41,50` | 21 |

## AMX 微核和数据流

- Outer block 与微块：`BM=BN=BK=256`、`TM=TN=32`（论文 Eq.(18)）。
- 8 个 tile 的分配：2 个 tile 装 A 的两组 16×32 行块；2 个 tile 装 VNNI-packed B 的两个 16 列组；4 个 tile 各装一个 16×16 FP32 输出象限。合计恰好占用 8 个 tile。
- A 面板使用连续 row-major BF16 子块；B 面板预先按 K 维相邻 BF16 配对的 VNNI 布局重排。每个 256×256 组件面板复制到块本地缓冲并在块内复用。
- 所有分片都预先分解、打包为 block-contiguous 缓冲。A split 平行处理 `(BM,BK)`；B split 和 VNNI packing 平行处理 `(BK,BN)`；计算对独立 `(BM,BN)` 输出块做 collapse/static 分派；一个输出块由一个线程独占，BK 面板顺序遍历。
- FP32 loop nesting：对每个 BK=256 面板清零四个 C tiles；遍历 BK 内 32 个 K 值的子面板，对每个 K 子面板按 `11,10,20,00,01,02` 更新同一组驻留 C tiles；六产品链对 BK 内每个子面板重复。完成 256 reduction 后才 store 一次临时 32×32 FP32 微块、加进 thread-private 256×256 FP32 block。论文没有逐字给出嵌套循环伪码；本复现选择此 nesting 以匹配 §6.2/图4 宣称的跨产品 tile reuse 与 12→7 panel-load 计数；论文未明确给出完整 loop 伪码。
- FP64 loop nesting（本复现的实现契约/工程选择）：对每个 BK=256 面板，按选中 product 顺序逐项处理；每项内部遍历该 BK 的所有 K 子面板，将这个单独 product 的 reduction 累加到 FP32 tiles；BK partial 完成后立即 store、FP32→FP64 转换并加入 private FP64 输出 block，然后再进入下一个 product。每个输出块的 BK panels 顺序执行。论文 Eq.(16) 是 full-K 组件积的数学抽象，文中未明确完整 BK panel loop；逐 BK partial widen/add 是本复现为限制 FP32 accumulation range而采用的 schedule，不应写成论文明确要求的唯一物理执行次序。
- 本复现的 `load_config()`/`_tile_release()` 在每次调用的 compute 段内执行；该实现计时边界见 `STRICT_EMULATION_IMPLEMENTATION.md`。论文只说明一次性 permission/config setup 不计 steady-state，没有给出逐调用/逐线程具体实现细节，不能把本复现的配置开销描述成作者原始行为。

## 论文实验协议

- 平台：双路 Intel Xeon Platinum 8462Y+，Rocky Linux 9.3；Intel oneAPI 2026.1，oneMKL 2026.1，Intel OpenMP；编译 `-O3 -march=native -mkl -qopenmp`，`KMP_AFFINITY=compact`。同一 measurement campaign 固定频率策略。
- Full-core：64 OpenMP threads（一物理核一线程）。AMX 与 MKL 路径各 warm-up 一次；AMX warm-up 包含 decomposition。每配置 10 次，报告 arithmetic mean。
- 阶数：`N=256,512,1024,2048,4096,8192,16384,32768`，全为方阵。线程伸缩只测 FP32，`N=1024,4096,16384`，线程数 `2,4,8,16,32,64`。
- 输入：表 4 使用 `[-1,1]` uniform random；正文称另测 uniform/Gaussian、scaled/log-uniform、cancellation-sensitive，但只有主表完整报告 uniform 数据，补充分布没有逐阶数明细。随机 seed/RNG 未说明。
- 参考：FP32 用 oneMKL SGEMM，FP64 用 oneMKL DGEMM。额外精度结果可作为诊断，但不替代 oneMKL headline baseline。
- 准确度：`eF = ||Chat-Cref||F / ||Cref||F`；`escaled=max_ij |(Chat-Cref)_ij|/(|A||B|)_ij`。零分母项单独报绝对误差；分母可在 reference/wider diagnostic format 中算。
- 性能：报墙钟时间、有效吞吐 `2N^3/T`、speedup。该 FLOP 归一化只计目标精度 GEMM 的数学工作量，不计组件积操作数。计时不含输入初始化和 reference 计算；AMX permission/config 一次性 setup 不计 steady-state。提议 kernel 的端到端计时含 decomposition、packing、AMX compute、重建。
- 图 6 的 raw `bf16bf16fp32` 是 oneMKL AMX-BF16 例程 headroom，不等于本文端到端组件积 kernel 性能。

## 论文准确度结果（表 4）

表中列值须乘对应缩放因子：FP32 两列 `×10^-7`；FP64-6 两列 `×10^-8`；FP64-10 `×10^-11`；FP64-15 `×10^-14`；FP64-21 `×10^-16`。每一对为 `eF / escaled`。

| N | FP32 | FP64-6 | FP64-10 | FP64-15 | FP64-21 |
|---:|---:|---:|---:|---:|---:|
| 256 | 3.02 / 2.25 | 1.49 / 0.546 | 3.26 / 1.30 | 6.95 / 2.49 | 5.71 / 3.41 |
| 512 | 3.06 / 1.54 | 1.49 / 0.441 | 3.25 / 0.931 | 6.94 / 1.88 | 5.88 / 2.96 |
| 1024 | 3.59 / 1.22 | 1.49 / 0.338 | 3.26 / 0.693 | 6.97 / 1.40 | 6.96 / 2.79 |
| 2048 | 3.72 / 0.941 | 1.49 / 0.234 | 3.25 / 0.510 | 6.95 / 1.08 | 7.45 / 2.16 |
| 4096 | 3.83 / 0.556 | 1.49 / 0.173 | 3.25 / 0.387 | 6.96 / 0.765 | 8.19 / 1.67 |
| 8192 | 3.97 / 0.416 | 1.49 / 0.124 | 3.25 / 0.286 | 6.96 / 0.615 | 9.41 / 1.52 |
| 16384 | 4.18 / 0.406 | 1.49 / 0.0936 | 3.25 / 0.210 | 6.96 / 0.440 | 11.4 / 1.61 |
| 32768 | 4.58 / 0.375 | 1.49 / 0.0680 | 3.25 / 0.148 | 6.96 / 0.304 | 14.6 / 1.93 |

## 论文性能结果

**图 6 原始单位疑点：** 栅格图坐标轴和 caption 均明确标作 GFLOPS，柱值最大 38.08（N=16384）。相对于双路 Xeon Platinum 8462Y+ 与这些规模的 GEMM，这个数值量级明显不协调，可能是作者将 TFLOP/s 标成 GFLOPS。因 PDF 未给原始 timing/勘误，下面按文图标注原样记录，不擅自重解释单位；跨平台性能分析应把该图视为存在单位疑点。

### 图 6：raw `bf16bf16fp32` headroom（GFLOPS）

按 `N=256,512,1024,2048,4096,8192,16384,32768`：

| 曲线 | GFLOPS |
|---|---|
| oneMKL bf16bf16fp32 | 0.21, 0.60, 2.72, 18.47, 23.3, 35.47, 38.08, 32.28 |
| oneMKL SGEMM | 0.03, 0.14, 0.98, 4.52, 8.09, 9.40, 8.97, 8.16 |
| oneMKL DGEMM | 0.03, 0.14, 0.86, 2.64, 4.43, 5.21, 4.47, 4.73 |

### 图 7：FP32 端到端 speedup

同样阶数上的 AMX-FP32 / oneMKL SGEMM：`2.56×, 2.17×, 1.70×, 1.39×, 1.14×, 1.16×, 1.25×, 1.32×`。论文解读为中等阶数 overhead 最显著，大阶数预处理更易摊销。

### 图 8–10 与 FP64

- FP32 线程图阶数 `1024,4096,16384`，线程 `2,4,8,16,32,64`。正文报告 1024 阶在 32 线程达到最佳后 64 线程下降；4096/16384 的绝对吞吐随线程增加，FP32 相对 SGEMM 的 speedup 随线程数增加而收窄，但所有测试点仍 >1.1×。图中未标每个 point 的数字表。
- FP64-6 在 `N≈4096` 与 DGEMM 交叉，最大两阶约 `1.7×`（结论给最高 `1.72×`）。FP64-10 到 8192 都落后，只在 16384、32768 略胜；FP64-15、FP64-21 所有尺寸均未胜 DGEMM。图 9 曲线含 GFLOPS 与 speedup，但没有可抽取的数据表，故这里不把曲线估读伪装成精确值。
- 图 10：FP32 preprocessing 占比从 N=256 的约 1/3 降至 N=32768 不足 4%；FP64 各变体在 N=256 的 preprocessing 占 56%–75%。FP64 产品数越多时预处理占总时间比例更低，是分母中的 compute/reconstruction 增大，并非 preprocessing 本身变便宜。

## 未规定事项与复现差异记录要求

论文没有定义 RNG/seed、输出/输入 stride、边缘 tile padding/掩码策略、矩形问题、alpha/beta、异常值处理、FP32 中间溢出 fallback、OpenMP worker 的 AMX permission 初始化细节、线程亲和细节之外的 NUMA 策略、结果方差/置信区间。实现时需将这些明确标为本复现选择，并与论文直接报告内容区分。至少报告所用 CPU/OS/compiler/BLAS、AMX permission 与 probe、线程 affinity/实际可用核、产品累加顺序、输入域检查、时间是否含 preprocessing，以及所有矩阵尺寸上的误差和时间。
