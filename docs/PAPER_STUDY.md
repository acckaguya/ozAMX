# 论文研读记录：BF16 Component-Product Emulation of FP32 and FP64 GEMM on Intel AMX

## 文献与读取方法

- 本地原文：`third_party/papers/2609.04663v1.pdf`，标题页标注 arXiv:2609.04663v1、2026-09-04；作者 Bing Cui、Yu Liu；PDF 29 页，印刷页码 1–29。
- 阅读方式：`pdfinfo` 检查元数据与页数；`pdftotext -layout` 抽取 1621 行文本；`pdftoppm` 栅格查看图 6–10 和表格所在页。另在 workspace-local `third_party/code/pdf-tools` 安装 pypdf 6.20.0 后，结构预检为 `PASS, STRUCTURE_ONLY`：声明/枚举/reader 页数均为 29/29/29，无 warnings。清单见 `third_party/papers/2609.04663v1.preflight_manifest.json`。这仅验证结构；不等于语义完整性验证，也不代表人工逐页阅读。
- 下文页码使用 PDF 印刷页码；章节和公式号用于交叉定位。少量原文短句用于核验，未复制大段文本。
- 这是对文档内容的机器辅助研读记录，不表示人类已经阅读或核验。

## 逐章覆盖

| PDF 位置 | 内容与对复现的意义 |
|---|---|
| 摘要、§1 引言，pp.1–2 | 论文提出以 AMX-BF16 乘积组合模拟高精度 GEMM。FP32 使用 3 个 BF16 分量和 6 个选定乘积，目标是相对 oneMKL SGEMM 达到经验上的 FP32 级精度，不声称 bitwise/elementwise identity；FP64 使用受 BF16 指数范围限制的固定六片简化 Ozaki，FP32 乘积结果转成 FP64 重建，并试验 6/10/15/21 项。 |
| §2 相关工作，pp.2–4 | 回顾低精度硬件、浮点展开、误差恢复和 Ozaki 类 GEMM。FP32 六项方案承接 Henry 等人的 BF16 组件积；FP64 方案借用 Ozaki 残差片思想，但固定深度、取消显式尺度与误差界配置。它是经验近似研究，不是新的误差界证明。 |
| §3 背景与问题，pp.4–7 | 表 1 列 BF16/FP32/FP64 精度 8/24/53 位，单位舍入误差 2^-8/2^-24/2^-53；Eq.(2) 限定 BF16-range FP64。问题只定义实数矩阵 C=AB，输出分别 FP32/FP64，不含通用 BLAS 语义。Eq.(4) 将总时间拆成 split、pack、Np 次 AMX、reconstruction、parallel overhead。AMX 有 8 个 tile，單 tile 最大 16 行×64 字节。 |
| §4 算法，pp.7–11 | Eq.(8)–(10) 给出直接 FP32 residual split 与 6 个三角乘积；Eq.(13)–(16) 给出 rho=45 的六片简化 Ozaki、产品集合和逐项 FP64 累加。Algorithm 1 的伪代码次序与 §6.2 tile-reuse 物理次序不同，须按实现调度一节落地。 |
| §5 数值准确性，pp.11–12 | FP32 误差来源是被省略的对角线及终端 residual，并有 FP32 累加次序影响；只报告经验结果。FP64 误差还包括第 6 层后丢弃的 residual、残差更新舍入和三角截断。AMX 每项 BF16 乘积先在 FP32 累加；FP64 分项逐一 widen 后以 FP64 累加，不能把多个 component GEMM 先合并到同一个 FP32 tile。 |
| §6 AMX 实现，pp.13–17 | Eq.(18) 阻塞为 BM=BN=BK=256、微块 TM=TN=32。8 tile 分配：2 个 A 源 tile、2 个 VNNI B tile、4 个 16×16 FP32 累加象限。预计算并打包所有分片；A 为连续 row-major 子块，B 为 K 维相邻 BF16 成对的 VNNI 布局。FP32 调度用 7 次组件面板加载/14 次 TILELOADD，较朴素 12 面板/24 tile load 减少。输出块独立 OpenMP 静态调度，BK 顺序处理。 |
| §7 实验方法，pp.17–19 | 双路 Xeon Platinum 8462Y+、Rocky Linux 9.3、oneAPI 2026.1、oneMKL 2026.1，`-O3 -march=native -mkl -qopenmp`，Intel OpenMP、`KMP_AFFINITY=compact`。全核 64 个线程，每物理核一线程；先 warm-up（AMX warm-up 含 split），计时 10 次取算术平均。精度主数据用 [-1,1] 均匀随机，另有无完整表格的缩放/对数均匀与 cancellation-sensitive 补充验证。只测方阵。 |
| §8 结果，pp.19–25 | 图 6 给出原始 oneMKL BF16-GEMM headroom；表 4 给出 8 个阶数的两类误差；图 7–10 给出端到端性能、线程缩放和预处理/计算重建的时间占比。论文报告 FP32 加速 1.14×–2.56×；FP64-6 在 N≈4096 交叉、最大约 1.72×；FP64-10 只在最大两个 N 小幅胜出；FP64-15/21 未胜过 DGEMM。 |
| §9 讨论，pp.25–26 | 明示范围只有实数方阵 C=AB；矩形/瘦矩阵、完整 BLAS 接口、完整 FP64 指数域、异常值、下溢/溢出和 fallback 留待后续。8 tile 限制寄存器驻留与微块大小。提及可移植至其他带低精度矩阵单元的平台，但需要重做打包、阻塞和微内核。 |
| §10 结论，p.26 | 重申 FP32 目标是经验 FP32-level 而非逐元素相同；FP64 是精度/性能折衷，不宣称完整 FP64/DGEMM 精度。 |
| References，pp.26–29 | 共 37 条参考文献，覆盖浮点展开、Henry BF16、Ozaki、AMX 指令手册等。PDF 没有附录章节，也没有实现代码清单、仓库链接或代码可用性声明；因此结论是“此 PDF 未提供作者实现链接”，不推断作者在其他地方绝无代码。 |

## 实现所需算法细节

### FP32 分解与乘积

对每个元素分别执行矩阵递推（论文写作矩阵形式）：从 `A^(0)=A` 开始，`r=0,1,2`：

```text
A_r       = round_BF16(A^(r))
A^(r+1)   = round_FP32(A^(r) - A_r)
```

B 同理。没有比例因子；BF16 片作为可精确嵌入 FP32 的值参与残差减法。论文的误差动机假设 normal 中间值、round-to-nearest 且残差减法精确；它没有把异常值/边界下溢行为纳入主张。

保留的数学乘积集合为 `S3={(i,j): i,j∈{0,1,2}, i+j<3}`，即 `(0,0),(0,1),(1,0),(0,2),(1,1),(2,0)`。其它 `(1,2),(2,1),(2,2)` 及涉及终端 residual 的项均舍弃。每个 AMX BF16 GEMM 对 K 维做 FP32 累加；所得 6 项在 FP32 输出中累加。

**物理累加顺序以论文优化调度为准：** `A1B1 → A1B0 → A2B0 → A0B0 → A0B1 → A0B2`（§6.2，Eq.(19)，印刷 p.15）。它使相邻操作共享一个输入分片，首项载入 A/B 两面板，后五项各只换一个面板。论文 Algorithm 1 的 `for i=0..2; for j=0..2-i` 会产生 `00,01,02,10,11,20`，Eq.(10) 的展示顺序又是 `00,01,10,02,11,20`；二者都不是式 (19) 的物理次序。实现要固定并记录式 (19)，因为 FP32 加法不满足结合律。

### BF16-range FP64 分解与乘积

输入的有限非零元素满足 `2^-126 ≤ |x| ≤ (2−2^-7)·2^127`，零允许。若整个 residual 矩阵为零，算法将本层与后续层置零；若某个元素的非零 residual 经投影后 round 成 BF16 零，该元素的零 slice 合法，残差更新仍保留该元素 residual，之后继续提取。只有产生非零 BF16 subnormal slice 的情况超出论文无缩放 fast path 的声称；端点和极端动态范围仍可能让更多残差落到被截断的尾部。NaN/Inf、区间外输入、AMX FP32 中间溢出/下溢无保护；当前没有 scale metadata 或 fallback。

对 `R^(0)=X`，`r=0..5`：若当前 residual 为零，则本层与以后全部分片为零；否则

```text
v_r       = ceil(log2(max_ij |R^(r)_ij|))
Σ_r       = 2^(v_r + ρ), ρ = 53 - 8 = 45
Z_r       = fl64(fl64(R^(r) + Σ_r) - Σ_r)
X_r       = round_BF16(Z_r)
R^(r+1)   = fl64(R^(r) - X_r)
```

这是简化的 Ozaki add–subtract projection：直接保存 BF16 片，不保存标准 Ozaki 的显式 `2^v` 缩放权重；第 6 次更新后的 residual 不再拆分。受支持输入上作者预期 `Z_r` 为正常 BF16 可表示值，于是 slice round 不是额外损失；FP64 residual 更新自身仍有舍入。

六片乘积集合 `Sd={(i,j):0≤i,j<6, i+j<d}`，按 `ℓ=i+j` 递增、同一对角线按 `i` 递增（`j=ℓ−i`）：

- `d=3, Np=6`: `(00),(01,10),(02,11,20)`
- `d=4, Np=10`: 上述再加 `(03,12,21,30)`
- `d=5, Np=15`: 上述再加 `(04,13,22,31,40)`
- `d=6, Np=21`: 上述再加 `(05,14,23,32,41,50)`

这里括号内依执行顺序排列。每一项独立完成 BF16×BF16→AMX FP32 结果，tile store 到 FP32 暂存，逐元素精确 widen 到 FP64，并立即加进 FP64 累加器；之后才算下一项。因此不同 component products 间绝无 FP32 累加。

## AMX 数据布局与并行实现要求

- 论文块参数固定为 `(BM,BN,BK,TM,TN)=(256,256,256,32,32)`。每个 32×32 输出微块是四个 16×16 FP32 accumulator tiles。
- 两个 A tile 分别装 16×32 BF16 的两组行；两个 B tile 分别覆盖输出列 0–15 和 16–31，数据预先 VNNI pack。VNNI 沿 reduction 维将相邻 BF16 配对。图 2 的 8×8 示例转成 4×16 packed cells，再分成两个 4×8 输出列组。
- 全部分片提前分解并打包到 block-contiguous 缓冲区。A 为标准 row-major 子块；B 为 BF16 VNNI 子块。计算时复制当前 256×256 A/B 面板到块本地缓冲，在块内复用于 32×32 微核更新。
- 访问大致是 M 外、N 中、K 内；每个输出块内 BK 面板顺序推进。论文尝试 streamed residual slices 认为在此 loop order 下会对输出块重复 split/pack，因此最终预计算全部 slices。
- A 的 split 并行遍历 `(BM,BK)` 块静态调度；B split/VNNI pack 并行遍历 `(BK,BN)`；计算阶段将独立 `(BM,BN)` 输出块 collapse 后静态分配。无两个线程写同一个输出块。
- FP32 每个 BK 面板清零 4 个 accumulator tiles、按复用次序完成 6 项，store 一次 32×32 微块，再加进 thread-private FP32 256×256 输出块。所有 BK 完成后写出 C。
- FP64 本复现对每个被保留项单独清零/运行 tile、按 BK 面板 store/widen/add 到 thread-private FP64 输出块；这是工程性 panel schedule，不将其称为论文唯一的物理循环次序。论文 Eq.(16)给full-K数学表达，且描述component result store/widen/add，但未给完整 BK panel loop 伪码。AMX tile config 在本机计时 compute 段中逐次调用设置并在结束 release；论文中的 AMX permission one-time setup 不计进steady-state，不能据此声称作者逐次配置边界与本实现相同。

## 可核验的关键证据短句

| 论文原句（短摘录） | 定位 | 用途 |
|---|---|---|
| “three BF16 components per operand” | §4.2，印刷 p.8 | FP32 slice 数 |
| “A1 B1 → A1 B0 → A2 B0 → A0 B0 → A0 B1 → A0 B2” | §6.2，Eq.(19)，印刷 p.15 | FP32 tile-resident 累加顺序 |
| “ρ = 53 − 8 = 45” | §4.3，Eq.(14)，印刷 p.10 | FP64 projection 参数 |
| “If A(r) = 0, set Aᵣ = A(r+1) = 0” | §4.3，印刷 p.10 | 整个 residual 矩阵为零时才一次置零后续层；单个元素的零 slice 不清除其残差 |
| “each component result is stored, widened, and added” | §4.3，Eq.(16) 后，印刷 p.11 | FP64 产品重建次序 |
| “(BM, BN, BK, TM, TN) = (256, 256, 256, 32, 32)” | §6.1，Eq.(18)，印刷 p.13 | 阻塞参数 |
| “measured 10 times” | §7.1，印刷 p.17 | 重复次数 |
| “detailed results across the tested matrix orders are not reported here” | §7.3，印刷 p.18 | 补充分布结果限制 |

## 图表、代码与补充材料清点

- 表 1（p.4）：数值格式精度；表 2（p.17）：实验平台；表 3（p.18）：变体；表 4（印刷页 21，PDF 物理页 21）：准确度完整数据（见 [REPRODUCTION_SPEC.md](REPRODUCTION_SPEC.md)）。Table 4 原图以 600 dpi 栅格复核：FP64-21 两列标题逐字为 `e_F × 10^16` 与 `e_scaled × 10^16`；结合表注 FP32 示例 `e_F × 10^7 = 3.02` 表示真实值 `3.02 × 10^-7`，FP64-21 数据须乘 `10^-16`，不是缩放因子方向误读。结构 sidecar 只做页结构校验，不承担这项视觉读取证据。
- 图 1（p.6）：AMX primitive 数据流；图 2（p.14）：8 tile 映射；图 3（p.15）：组件预计算与打包；图 4（p.16）：FP32 复用调度；图 5（p.17）：FP32/FP64 重建对比。
- 图 6（p.20）：raw BF16 GEMM headroom，图中每个柱体标为 GFLOPS；这些量级与所述硬件/问题规模不相称，单位可能误标，原文没有原始计时可核实，故仅保留图面标签，不擅自换算为 TFLOP/s；图 7（p.22）：FP32 总体性能和标注 speedup；图 8（p.23）：线程伸缩，线程数 2/4/8/16/32/64；图 9（p.24）：FP64 性能及曲线 speedup；图 10（p.25）：预处理与计算重建归一化占比。
- 文中没有 Appendix/补充章节。PDF 没有作者代码链接、repo 声明或可复现性补充包。未据此断言外部不存在作者代码。
