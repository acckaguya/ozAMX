# 8454H 架构、SIMD 与 AMX 综合研读

日期：2026-10-13（北京时间）。资料入口见 [README.md](README.md)。下载、归档、源码扫描和校验由 Luna 分工完成；主代理复核架构/指令规范、关键图表和应用关系。本文保留优化前的源码观察和工作集估计；随后完成的 SIMD/AMX 优化及同机性能实测见 [8454H_PERFORMANCE_BASELINE.md](../../docs/8454H_PERFORMANCE_BASELINE.md)。

## 平台迁移的准确含义

[8454H](https://www.intel.com/content/www/us/en/products/sku/231738/intel-xeon-platinum-8454h-processor-82-5m-cache-2-10-ghz/specifications.html) 和 [Gold 6430](https://www.intel.com/content/www/us/en/products/sku/231737/intel-xeon-gold-6430-processor-60m-cache-2-10-ghz/specifications.html) 都是 Sapphire Rapids。迁移涉及 SKU 和机器配置差异，并没有把代码迁移到一个新的核心 ISA 世代。

| 产品规格 | Gold 6430（历史平台） | Platinum 8454H（当前 SKU） |
|---|---:|---:|
| 每插槽核心/线程 | 32 / 64 | 32 / 64 |
| 标称 base / 最大 turbo | 2.10 / 3.40 GHz | 2.10 / 3.40 GHz |
| LLC 规格 | 60 MB | 82.5 MB |
| UPI 链路上限 | 3 | 4 |
| DDR5 速率上限 | 4400 MT/s | 4800（1DPC）/4400（2DPC）MT/s |
| 扩展能力 | 2S | S8S |

本机实测可见：**2 插槽、64 个物理核、128 个逻辑 CPU、2 个 NUMA 节点**；每核 L1D 48 KiB、L1I 32 KiB、L2 2 MiB，每插槽 L3 82.5 MiB。节点0为 CPU `0–31,64–95`，节点1为 `32–63,96–127`。产品最高内存速率、8路能力和优先核心属性不能视作本机已启用配置。DIMM 实际速率/插槽分布、BIOS SNC 和持续 AMX 频率仍未确认，详见 [快照](xeon-8454h/hardware-snapshot/snapshot.json)。

## 指令组合与各阶段的关系

| 工作 | 8454H 上可研究的机制 | 数值/布局约束 |
|---|---|---|
| FP32 三片分解 | AVX-512 BF16 的 `VCVTNEPS2BF16/VCVTNE2PS2BF16`；SIMD 位操作和 residual subtraction | 固定 RNE；保留拒绝 NaN/Inf/subnormal 的接口规则，不能把硬件清零当域检查 |
| FP64 六片投影 | AVX2/AVX-512 FP64 load、max、add/sub、mask 分类和转换 | 保持全局 `max(abs(R))`、rho45、两次 binary64 舍入和六片定义；禁止重关联投影表达式 |
| B 打包 | AVX-512BW 的 word unpack/permutation、连续或 masked load/store；字节重排可另考虑 VBMI | 沿 K 配对；保持 `bpanel_index` 的实际地址映射和零填充 |
| FP32 输出合并 | SIMD FP32 add、连续读写、尾部 mask | 同一输出元素的累加顺序保持原契约 |
| FP64 重建 | `VCVTPS2PD` 加 SIMD FP64 add；考虑与下一微块计算交错 | 每个 FP32 component result 先 widen，不能先在 FP32 合并多个 component |
| 小尺寸/能力分派研究 | AVX2、AVX-512/FMA、AVX-512 BF16 dot-product | 每条路线需独立精度和端到端测量，不能由向量宽度预测固定加速倍数 |

AVX-512 可同时容纳16个 FP32 或8个 FP64；AVX/AVX2的256位寄存器分别容纳8个/4个。但吞吐还取决于执行端口、load/store、shuffle、依赖和实际频率。[优化手册](manuals/optimization-reference-manual-v1-050.pdf) §2.4 给出 Golden Cove 的资源描述；其较早微架构的周期和频率表不能直接用于8454H。

`AVX512_FP16`、`AVX512_BF16`、`AMX_BF16`、`AMX_INT8` 是独立能力。本机暴露前述向量扩展及 AMX TILE/INT8/BF16；AVX-512 FP16 支持不能推出 AMX FP16 支持。FP16 的指数范围和舍入/次正规语义也不同于 BF16，直接更换数据格式会更改算法。

## 必须保持的规范语义

[SDM Vol.2C](manuals/sdm-vol2c-v093.pdf) 的 BF16 转换条目说明：`VCVTNE2PS2BF16` 的低半结果来自 `src2`，高半来自 `src1`。写入 mask 不应被当成安全的内存尾部处理；尤其该双源转换明确不支持 memory fault suppression。尾部可先用适当的 masked load 将有效值装入寄存器，再执行转换。

[SDM Vol.2B](manuals/sdm-vol2b-v093.pdf) 的 `TDPBF16PS` 不等同于任意顺序的 FP32 dot：伪码分别处理每对 BF16 的偶/奇贡献，然后合并到目的 tile；相关舍入、DAZ/FTZ独立于 MXCSR。已有原生审计中逐位匹配只适用于所测输入和形状，不能由此推导所有 component dots 精确。

普通 SIMD FP32/FP64 指令、BF16 专用转换/dot、FP16 指令应分别查规范。把 `-ffast-math`、FMA收缩或不同求和树引入当前投影/重建，会改变数值定义；优化首先须保持分片位模式、产品集合与每元素累加顺序。

### Linux 许可与线程状态

[Linux v6.12 XSTATE 规范](simd/linux-xstate/xstate-v6.12.rst) 规定 AMX动态特征的 permission **按进程有效**，fork继承、exec清除；每个task首次使用时另行分配其状态缓冲。现有仓库文案把这两层混淆为线程级许可，此次已更正第三方说明。

本机临时进程核验：初始 mask `0x202e7`，请求 component18 后为 `0x602e7`；请求前已存在的worker和之后新建的worker都观察到新mask。随后执行 `TILERELEASE` 成功。无需把每worker重复许可查询解释为 Linux 强制要求；各worker的tile配置、首次使用及状态管理仍需正确处理。完整探针源与命令见 [local-probes](xeon-8454h/hardware-snapshot/local-probes/)。

## 优化手册对当前实现的启示

已重点研读 Optimization Manual §§2.2/2.4、SIMD相关章节，以及 Chapter20 的tile复用、cache blocking、转换/重排、流水、线程划分和高精度GEMM部分；位置见 [SIMD研读索引](simd/STUDY.md)。

源码已具备256级外块和32级AMX微块、四个C tile、FP32六项operand reuse。进一步可研究：64字节对齐、SIMD分解与packing、可复用scratch、按cache工作集调块、负载/存储与TDP流水、FP64向量重建、按NUMA分派和首次触页。

其中已有确定的源码事实：packed A/B 用普通 `new uint16_t[]`，没有显式64字节base alignment保证；输出 block/micro也没有源代码级 `alignas(64)`；B packing为标量循环；没有显式TILELOADDT1、prefetch或双缓冲AMX/AVX-512交错。源码的全局packed面板读取不等于每次访问DRAM，也不能证明改成本地copy必然更快。相关定位由Luna记录于 [STUDY.md](simd/STUDY.md)。

以当前 `BM=BN=BK=256` 估算一个面板阶段的潜在工作集（不含额外scratch、cache映射及预取）：

| 路径 | A/B 活跃片数 | A+B面板+C block |
|---|---:|---:|
| FP32 | 各3片 | 1 MiB |
| FP64 p6 | 各3片 | 1.25 MiB |
| FP64 p10 | 各4片 | 1.5 MiB |
| FP64 p15 | 各5片 | 1.75 MiB |
| FP64 p21 | 各6片 | 2 MiB |

这里每个BF16面板128KiB，FP32 C block256KiB，FP64 C block512KiB。p21估计已达到单核L2容量，说明需要研究缓存余量；这不是已经发生cache miss的测量。高于p6的额外片仍由当前split/pack预先全部生成，不能混淆预处理总内存与compute活跃工作集。

AMX与AVX-512交错需要处理真实数据依赖和资源竞争。手册§20.11.3还讨论AMX计算期间第二AVX-512 FMA端口的开关开销。因此不能把两套峰值简单相加，也不能不加测量地照搬TILEZERO补丁或non-temporal load。NUMA放置、SMT兄弟竞争、频率和内存通道配置要作为独立测量变量。

## 代码实例的正确用法

[示例笔记](examples/STUDY.md) 已逐文件分析所收源码：Intel AMX intrinsic例是完整INT8演示；BF16例展示AVX-512转换和dot；manual例比较reference/preload/interleaved GEMM与转换/transpose；oneDNN片段展示成熟JIT微核、copy、tail mask与BF16 reorder。FP64稀疏dot和AVX2/AVX-512矩阵向量例提供SIMD对照思路。

它们不是作者论文源码。部分是固定形状、Windows教学程序或依赖完整库的片段；矩阵向量演示不能当矩阵矩阵GEMM benchmark。官方demo的控制流、形状注释和测试也须核对，不能仅凭Intel归属当作正确性证明。

## 资料问题与核验范围

FP16指南rev004目视确认：p11 Figure9把BF16 fraction标签写成5，应为7；p14 Table7正/负方向舍入的说明和selector配对错误；同页512位addition intrinsic误用128位类型。上游PDF原样保留，正确语义按SDM/Intrinsics Guide交叉核对。BF16示例网页称BSD，ZIP许可与SPDX称MIT，也按原样记录，未自行替上游裁定。

所有来源有版本/固定commit、URL、bytes和SHA。PDF已做页结构/提取检查，Optimization Manual有CID-font警告，表格和异常字符需目视核对；不能把成功提取当作每页语义无误。此次研读重点章节与所有下载源码，没有宣称读完数千页通用手册；未修改GEMM算法、编译选项或历史benchmark数据，也没有重跑性能实验。
