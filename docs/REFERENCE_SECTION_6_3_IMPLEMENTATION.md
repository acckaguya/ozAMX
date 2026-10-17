# 参考算法第 6.3 节：目标精度重建与并行化

本文依据仓库中的论文版本 [`2609.04663v1.pdf`](../third_party/papers/2609.04663v1.pdf)。以下页码是 PDF 阅读器页码；论文正文页码分别为 15–17。

## 先区分 Figure 4 和第 6.3 节

Figure 4 的标题是“Operand-reuse scheduling for the AMX-FP32 six-product path”，画的是六个 BF16 分量乘积的 FP32 操数复用顺序。它位于第 6.2 节末尾，论文正文第 15 页（PDF 第 16 页），不是第 6.3 节的图。图中依次计算 A₁B₁、A₁B₀、A₂B₀、A₀B₀、A₀B₁、A₀B₂；第一步载入 A₁ 和 B₁，后续每步只载入变化的那个分量面板，同时让 FP32 累加 tile 保持驻留。论文称这将每个六乘积序列的分量面板载入从 12 次降至 7 次、tile-load 指令从 24 条降至 14 条。 [论文第 6.2 节及 Figure 4，PDF 第 16 页](../third_party/papers/2609.04663v1.pdf#page=16)

第 6.2 节还说明，AMX-FP32 的三分量 BF16 残差拆分与 AMX-FP64 的固定深度 Ozaki 式拆分都在计算循环之前预计算；两者随后共用打包流程。论文明确把“多个分量乘积共用 AMX FP32 累加 tile”的调度收益限定于 AMX-FP32：AMX-FP64 必须先物化每个分量乘积，再做 FP64 累加，其重建路径转到第 6.3 节讨论。 [论文第 6.2 节，PDF 第 15–16 页](../third_party/papers/2609.04663v1.pdf#page=15) [论文第 6.2 节，PDF 第 16 页](../third_party/papers/2609.04663v1.pdf#page=16)

## 第 6.3 节讲什么

第 6.3 节标题为 **“Target-Format Reconstruction and Parallelization”**，正文跨论文第 16–17 页（PDF 第 17–18 页）。核心主题有两部分：FP32 与 FP64 路径如何把 AMX 分量乘积重建到目标精度，以及两条路径共用的块级 OpenMP 并行方式。 [论文第 6.3 节，PDF 第 17 页](../third_party/papers/2609.04663v1.pdf#page=17) [论文第 6.3 节续文，PDF 第 18 页](../third_party/papers/2609.04663v1.pdf#page=18)

**AMX-FP32 重建。** 重建融合在分块计算循环中。每个 Bₘ×Bₙ 输出块有自己的线程私有 FP32 块累加器。对每个 Bₖ 面板，程序为一个 32×32 微块清零四个 FP32 AMX 累加 tile，按调度顺序执行六个分量乘积，再把四个 tile 存入临时 32×32 FP32 缓冲区，并累加到线程私有块累加器。所有 Bₖ 面板处理完后，再把完整块写入输出矩阵。 [论文第 6.3 节，PDF 第 17 页](../third_party/papers/2609.04663v1.pdf#page=17)

**AMX-FP64 重建。** 块遍历和输出块并行结构与 FP32 相同，但每个选中的 BF16 矩阵乘法都单独产出 FP32 微核结果：四个 FP32 AMX tile 立即写出，临时 32×32 tile 转为 FP64，再加到线程私有 FP64 块累加器。论文解释，如果先把多个分量乘积合并在 AMX FP32 tile 中再转 FP64，乘积之间的求和会发生在 FP32 中，不符合预期的 FP64 重建。因此 FP64 路径无法像 FP32 路径那样让多个分量乘积共同驻留于 AMX FP32 tile 并取得相同的调度收益；额外的 tile 存储、FP32 转 FP64 和 FP64 累加也压缩了 AMX-FP64-6、-10、-15、-21 的性能空间。Figure 5 展示了这一分歧。 [论文第 6.3 节及 Figure 5，PDF 第 17 页](../third_party/papers/2609.04663v1.pdf#page=17)

**并行化。** 论文称当前 OpenMP 实现并行化三个阶段：A 的分解按 (Bₘ,Bₖ) 块静态调度；B 的分解和 VNNI 打包按 (Bₖ,Bₙ) 块并行；计算阶段把互不重叠的 Bₘ×Bₙ 输出块分给线程，用覆盖外层 M、N 块维度的 collapsed static loop，因此不同线程不会更新同一个输出块。此结构由 FP32 和 FP64 路径共享。单个输出块内部，Bₖ 面板仍按顺序遍历；预计算后的 A 分量与 VNNI 打包 B 分量被复制到块局部缓冲区，再交给 AMX 微核。计时计算区间前加载 AMX tile 配置，AMX 内核结束后释放 tile 状态。 [论文第 6.3 节续文，PDF 第 18 页](../third_party/papers/2609.04663v1.pdf#page=18)

这版论文从第 6.3 节直接进入第 7 节“Experimental Methodology”，没有第 6.4 节；因此这里没有可供补充的 6.4 上下文。 [论文第 6.3 节末及第 7 节开头，PDF 第 18 页](../third_party/papers/2609.04663v1.pdf#page=18)

## 与当前实现的对照

此处先记录论文定义。代码是否实现这些步骤，尤其是 Figure 4 的六步 FP32 操数复用、以及 FP64 每个分量乘积单独存储并转 FP64 的路径，需要结合当前源码另行逐项核对。
