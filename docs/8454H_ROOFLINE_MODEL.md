# 8454H：用于本轮搜索的分层 Roofline 模型

模型的用途是提出可检验的优化假说，再用完整 API 时间与数值门禁决定是否采用。当前没有 PMU 缓存/内存流量数据，因此图中的访存量是指令逻辑载荷，不能直接作为 DRAM 算术强度。Intel 对 [Integrated Roofline](https://www.intel.com/content/www/us/en/developer/articles/technical/integrated-roofline-model-with-intel-advisor.html) 的说明区分了指令访存与各级缓存之间的流量；本轮遵循这个区分。

## 工作量、边界与实测参考

令有效 GEMM 工作量为 `Weff=2MNK`；F32 的六个 BF16 产品及 F64 的 p6/p10/p15/p21 分别需要 `Wamx=p·Weff`，其中 p 为 6/6/10/15/21。尾部实际 tile 运算还包括补零，应使用 M、N、K 向 32 取整后的尺寸另算。逐产品 FP32→FP64 转换和加法不是 AMX FLOP，单独计数。

对阶段 s、存储层 l，模型为 `P_s <= min(P_compute,s, B_l·W_s/Q_s,l)`，或 `t_s >= max(W_s/P_compute,s, Q_s,l/B_l)`。只有同一访存边界的 Q 与 B 才能配对。时间上串行的 split、pack、compute、提交可以相加；compute 内的 AMX、SIMD 与缓存服务共享资源，不能把各自的独立上限直接相加得到生产上限。

实测的 64 核寄存器 AMX BF16 峰值约 **161.0 TFLOP/s**，只含驻留 tile 的运算。采用冻结产品内核、每个产品立即重构的热数据 p6/p21 诊断约 **85–86 TFLOP/s**（AMX 产品等效口径）；这说明加载、转换与累加必须进入分析。它们都是具体微基准的参考，并非所有生产形状的严格可达上限。

TILELOADDT1 逻辑读载荷在每核 1 MiB、2.25 MiB、24 MiB 输入下分别约 **9.34、2.64、0.525 TB/s**；不同脚印用于检验局部性假说，缓存驻留没有用计数器证实。单独 SIMD triad 的 DRAM 候选脚印约 **0.368 TB/s**，含写流，不能与只读 tile 探针混成一个带宽。原始数据、误差和边界见 [校准报告](8454H_ROOFLINE_CALIBRATION.md)。

## 假说一：减少重构的 double 缓冲读写

旧版 F64 每个产品、每个输出、每 BK256 的逻辑重构载荷为 `4+8+8=20 B`：读 float 微结果、读 double 累加值、写 double 累加值。两产品一批时，先将两个 AMX 结果分别写入 float scratch，再按原产品顺序逐次转换和加法；double 累加值保留在 ZMM 中，批末写回。禁止先把 float 产品相加，也不改变 BK256 边界。

因此完整一组 p 个产品的重构逻辑载荷由 `20p` 降至 `4p+16·ceil(p/2)` 字节/输出/BK：

| 预算 | 旧版字节 | batch2 字节 | 逻辑载荷减少 |
|---|---:|---:|---:|
| p6 | 120 | 72 | 40.0% |
| p10 | 200 | 120 | 40.0% |
| p15 | 300 | 188 | 37.3% |
| p21 | 420 | 260 | 38.1% |

AMX 输入 tile 载荷、TDP 数量与每个产品的 tile-store 数量均不变；scratch 增加 4 KiB/worker。这个公式只预测重构载荷，不预测同等幅度的 API 加速。独立 batch2 实验收益有限，需要与输出分块一起验证。

## 假说二：在 L2 预算内扩大输出列条带

固定 BK256 和 32×32 AMX 微块，扩大输出宏块的列数，可让同一个 A 行面板服务更多列。每次 BK 的工作集粗估为 `2d·BK·(CB_M+CB_N) + sizeof(T)·CB_M·CB_N`，另加行 padding、scratch 和运行时开销。这是假设面板复用有效的容量模型，不是实测 cache-miss 或 DRAM 流量。

| 模式 | CB_M×CB_N | 面板与活跃 C 主体 |
|---|---|---:|
| F32，d=3 | 128×512 | 1.188 MiB |
| F64，d=3 | 128×512 | 1.438 MiB |
| F64，d=4 | 128×512 | 1.750 MiB |
| F64，d=5，若用512列 | 128×512 | 2.063 MiB |
| F64，d=6，若用512列 | 128×512 | 2.375 MiB |
| F64，d=5/6，改256列 | 128×256 | 1.188/1.375 MiB |

据此选择：`min(M,N)>=4096` 时 F32、F64 p6/p10 用 512 列，F64 p15/p21 用 256 列；行宽 128，累加行加一条 64 B padding，并在 F64 使用 batch2。较小矩阵保留旧几何，避免减小任务数量带来的并行度损失。padding 单独没有稳定收益，不能把组合优化的收益都归因于 cache-set 冲突。

[候选重复测试](../bench/8454h/roofline/search_adaptive/summary.json) 的 8192 五种模式 API-wall 中位数下降约 6–16%。[正式 oneMKL 报告](8454H_ROOFLINE_RESULTS.md) 保留首次完整运行中的大波动，并附匹配复测。生产 AMX/SIMD/copy 合并阶段的产品等效吞吐仍远低于寄存器参考；不得把它与 161 TFLOP/s 的比值称为 AMX 发射利用率。

## 被证伪或未采用的支线

输出 padding 单独、全量/半量 NUMA B 复制、大页提示都完成了实现、数值验证和测量。NUMA 复制虽改善部分 compute 时间，却增加复制、缺页和内存开销，2 GiB 缓存协议下的完整 API 没有稳定收益；大页映射已由 smaps 证实，性能收益仍不足以成为默认策略。16×32 两产品共享 tile 的设计会增加 B 载荷，暂未实现；INT8 exact accumulation 改变数值路径，留作独立探索而非本版候选。

本轮采纳策略的验收证据为：与冻结 V2 的完整输出逐字节一致，错误时 C 不变，别名和尾部合法，正式 Release 库与通过门禁的候选库 SHA 相同。完整循环和所有负结果见 [搜索记录](8454H_ROOFLINE_SEARCH_LOG.md)。
