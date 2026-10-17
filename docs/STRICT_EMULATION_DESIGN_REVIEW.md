# 严格模拟实现方案审查

日期：2026-10-16。对象：`codex/strict-emulation` 后续实现工作。依据：本地论文§6（PDF/印刷pp.13–17）、§7（pp.17–19），[综合审查](audit/COMPREHENSIVE_REVIEW.md)、[论文概念审查](audit/PAPER_AND_CONCEPT_REVIEW.md)，以及公共头文件和 `gemm_impl` 调度/提交部分的定点阅读。本审查使用codebase-design的Module/Interface/Seam原则；未运行负载、未修改生产代码。

## 1. 首要决策

**建立显式可选择、可核对的strict-emulation执行配置，先保留现有公开Interface的错误、别名及事务保证。** 它的任务是控制论文实现中已明确的几何和数据流，回答“论文描述的数据流是否解释本机性能差距”。不要同时把它定义成“去掉检查、直接写caller C、改rho或更换精度算法”的快路径。

用户的目标是达到论文性能，这是实施目标，不是当前已有证据能保证的结果。成功应同时报告：同机对MKL的完整API加速比、完整数值验证、明确输入和尺寸范围、相同状态下的原始样本。论文图表绝对吞吐仍存在GFLOPS标签疑点，因此以正确单位的本机时间与同机speedup为主，不以把图6数字直接贴成TFLOPS作为成功条件。

rho=45、正shift、六轮提取、三角产品集合、BK=256、FP64每产品独立FP32 partial后FP64累加全部冻结。新的全矩阵binary128证据已支持字面算法本身存在当前误差量级；不通过signed-shift、rho44或增加产品来追求Table4。若提出新算法，必须另命名、另证据，不得替换此路径。

## 2. strict-emulation应固定什么

| 项目 | strict-emulation契约 | 原文及说明 |
|---|---|---|
| 外层输出几何 | BM=BN=256；BK=256 | §6.1 p.13 Eq.(18)，包括小N，不沿用当前32/128/自适应块 |
| 微核 | TM=TN=32；2A+2B+4C tile | §6.1 pp.13–14；可复用已验证微核，避免同时引入新AMX算术 |
| FP32 | 三片；K32内11→10→20→00→01→02；BK末store与FP32 block累加 | §6.2 pp.15–16与§6.3 p.16；K32层级是本复现明确选择，原文未给完整伪码 |
| FP64 | 六轮、六片全部预计算并保存；计算仍按预算选6/10/15/21项 | §4.3 p.10、§8.3 p.23；不把只存depth片说成完全同工程实现 |
| FP64重建 | 每个产品单独store、widen、add，然后下个产品；先用batch1 | §6.3 p.16；batch2可保持数值，但先从严格路径隔离 |
| 全局packed布局 | A连续子块、B VNNI子块；先全部生成后计算 | §6.2 p.14；保持已有被验证的B配对语义 |
| 块本地staging | 每个输出块、每个BK，将该块需要的A/B组件面板复制到worker私有缓冲，块内微核复用 | §6.2 p.14、§6.3 p.17；原文说required panels，不要求复制不参与当前预算的低片 |
| 输出任务次序 | M外、N中；每输出块内部BK递增；OpenMP static，输出块独占 | §6.2 p.15、§6.3 p.17；不以新的动态调度混入首个对照 |
| 预处理任务 | A按(BM,BK)，B按(BK,BN)划分可并行的生成/写入任务 | §6.3 p.17；全局shift尺度的数学归约仍不得改成panel尺度 |
| 计时 | 完整调用外墙钟是headline；阶段profile仅诊断 | §7.4 p.19、§8.3 p.21；含每次split/pack/compute/reconstruct |

必须把原文未知事项写入metadata：FP64 max/shift作用域采用当前全局矩阵解释；同对角线内i递增；K32/BK具体嵌套；tails padding；每worker tile配置位置。strict-emulation是“对齐已披露工程约束的独立实现”，不是“已恢复作者源码”。

特别注意：全局shift需要每轮先得到全局残差max，之后才能按宏块投影/打包。把OpenMP块任务直接变成每panel独立max会改变分片，属于数值算法改变。允许改线程任务分配，不允许在同一开关下改数学作用域。

## 3. Interface与内部Seam

当前公开Interface是 `gemm_fp32/fp64` 及profiled版本，调用者不应了解A/B staging、FP64 batch或每worker scratch。需要两种真实Adapter：现行调度与strict-emulation调度，适合在内部执行计划处形成一个Seam。

首轮建议使用**显式构建配置或审计runner的内部执行选项**，输出不可省略的plan_id。可以分别构建两个静态库/常驻driver供受控对照，避免立即扩展公开函数参数和ABI。若需要同一库运行时切换，使用一次解析的执行计划枚举，不使用分散的环境变量和十几个bool穿过微核。

一个内部执行计划应统一决定输出几何、staging模式、存储深度、FP64物化批次、任务顺序；数值契约在公共验证层保持共享。不要只在入口设一个 `strict_emulation=true`，而多处仍偷偷命中Wide/CompactWide dispatch。runner记录实际计划，而不是只记录请求计划；对不支持的形状明确报错或显式标记fallback，不静默用默认路径再打strict-emulation标签。

建议实现结构：

```text
公开Interface
  检查尺寸/stride、CPU/权限、输入域、别名与资源
  选择并记录内部执行计划
  生成所有必要组件与packed数据（固定数值定义）
  计算到完整私有result（current或strict-emulation Adapter）
  汇总错误；成功后统一commit到caller C
```

保持一个共享的数值与提交Module，两个Adapter只承担真正变化的数据流/调度。无需抽象每条tile load，也无需为只有一个实现的微核创建新的继承层。测试从同一个Interface调用两个计划，比较结果和失败行为。

## 4. 事务语义不能靠“先验证输入”消除

当前Interface允许输入输出别名，并在计算失败时保持caller C不变。输入有限且BF16片正常，并不保证AMX中间结果不溢出；没有可靠的全域输入预检查可以简单替代现有运行后错误检查。若直接把完成的block写caller C，后续block再出错，就破坏事务语义。

因此首轮strict-emulation仍保留完整私有result和最后commit；局部输出block完成后写result。这比原文有额外成本，但可清楚计量，并能保持公开Interface兼容。不要宣称保留全事务语义同时“一边算一边直接提交caller C”。双遍计算或保存原C也会有成本，当前没有必要引入。

如果后续确需最小研究入口，应另设内部审计Interface，明确：不重叠、指定正常输入、发生计算错误时输出可部分修改、仅用于研究对照。仍需真实split/pack/reconstruction，计时标签写research kernel，不能把它的speedup冒充原公开API。首次实施不必提供这个入口；先用实际phase与提交字节量判断是否值得。

线程私有staging缓冲建议在并行工作前或worker生命周期开始时分配并复用，不能每microtile malloc。FP32每侧3片完整256² BF16面板合计约768KiB；FP64每侧6片合计约1.5MiB，另有输出block与scratch。不要无评估地放在线程栈上，已有扩大block栈失败历史。低预算只复制实际使用的depth片时更小，但全六片全局预计算/存储契约仍保持。

OpenMP异常需在并行区外统一处理，分配失败也不能泄漏半成品到caller C。保证staging覆盖范围完整且padding已定义，不能依赖历史缓冲内容。

## 5. 仅做三个有判别力的实验

以下是建议实施顺序，不是本报告已执行的实验。所有性能负载与其它基准串行，同批交替运行，保留全部样本与失败；每个配置先通过数值和事务验证。

### 实验一：固定几何与staging的2×2因子对照

先用FP32 N4096，固定当前数值路径、线程/等待、输入、工作区与事务提交，比较：

| 输出几何 | direct packed供数 | 块本地staging |
|---|---|---|
| 当前同尺寸几何 | A | B |
| 论文256×256 | C | D |

**N4096当前默认已是256×256**，因此A与C几何相同，不能假装得到两个独立几何因素。该尺寸先只做direct/staged二臂对照；要辨别几何因素，再用当前128×512的N16384，或先用更小的N2048当前128×128做低成本因子pilot。N8192当前也已256×256，主要检验staging是否跨尺寸稳定。

这组对照保持FP32 load链和BK顺序不变。报告API、preprocessing、compute/reconstruct、commit/cleanup，并记录真实staging逻辑字节量。若staging仅改善compute却不改善API，不能采用为已实现整体加速。若N16384状态方差太大，停止归因、保留数据，先恢复稳定实验条件，不删除慢样本。

目的：判别“缺少论文面板本地化”是否值得继续，而不是再盲搜所有宏块。不同staging量可能改变NUMA首次触页，因此需记录页放置策略，不能把该变化直接命名为某级cache命中率改善。

### 实验二：strict-emulation完整路径的成本与FP64预算敏感性

在实验一确认基础数据流正确后，加入六片全存、预处理块任务、batch1和固定256输出任务，形成完整strict-emulation Adapter。先对N4096测FP32、FP64-p6与p21；再将有价值候选扩到N8192。与现行路径使用同一公开Interface、同一输入、同一线程、同一数值契约比较。

这不是单因素因果实验，标签应为“完整路径对照”；它回答严格对齐工程描述后的实际端到端结果。p6与p21能区分六片预处理固定成本和逐组件物化成本。若p6因全六片预计算变慢，这是重要结果，不应偷偷恢复只存depth然后仍称完全严格。

需要保存实际复制片数、全局保存片数、组件数、store次数与重建批次。保持rho45及FP64输出逐位一致的门；若不一致，先查归约/重建顺序或尺度作用域，不能仅凭误差仍低于宽容差就继续排名。

### 实验三：同机MKL对照与完整API成本闭合

只对已通过前两项验证的至多一个候选，在N4096/8192做候选、冻结现行、oneMKL的随机交错测量，warmup一次、各十次计时，统一外墙钟，记录每次MKL秒数。phase计时在单独instrumented运行用于解释，不把instrumented结果与无instrumentation API混算。

本实验检验用户目标：本机完整API是否稳定改善、对MKL比值是否达到论文对应点的范围。论文FP32 N4096/8192 speedup分别1.14/1.16；本机频率/平台不同，这些是比较目标，不是可通过删成本获得的保证。

同时闭合split+pack+compute/reconstruct+commit+cleanup与API。可将commit/释放成本直接测为phase，不必立刻写削弱事务的快路径。phase相加若不等于API，先解释未覆盖区间或重叠，不将差额全部算成malloc。若候选提升小于状态漂移且配对分布不稳定，应保留为未确认，而不是采用最优三次。

## 6. 实施与合入门

1. 固定现行基线的源码/库SHA、编译器、运行时、环境、真实CPU映射和输入hash。独立审计的PASSIVE等待协议与旧campaign分开，不拼接旧best值。
2. 首先完成strict-emulation的数据流和plan metadata，再运行小N/跨BK/tail正确性与失败不提交验证；阶段目标是可比较，不预设更快。
3. 对保持算术顺序的路径，完整结果应与冻结基线逐位相同；同时通过独立dyadic全矩阵概率验证及普通输入参考，避免只继承基线可能已有的问题。FP64另保留binary128差距，不因字节相同而写Table4已通过。
4. 至少覆盖N256/512固定256块的低并行任务、跨BK、实际优化范围和一个范围外形状；公开Interface继续覆盖padding、别名及晚发生的溢出失败。尾块属于工程扩展，需标注论文未测试。
5. 性能采用完整API算术平均、配对差异、离散程度和所有样本。有限域获益可以有限域启用，不扩大成“所有尺寸已达到论文”。若严格路径慢，保留可重复的对齐模式也有研究价值，默认不必替换。

## 7. 现在应执行的最小下一步

建议主实现代理先落实内部执行计划及**N4096的direct/staging二臂路径**，复用原微核、global shift、事务result与提交；记录每worker缓冲体量和复制字节。这里当前几何已经是论文256×256，能够最大限度隔离staging。待该路径数值门通过再测，不同时调整OpenMP等待、FP64数学分解或内存页策略。

随后完整strict-emulation对照才有意义：它把论文规定和复现选择变成可观察的执行契约，也允许性能不达目标时准确说明是哪一阶段的成本仍存在，而不是继续依赖“用了AMX/用了256块”这样的粗标签。

## 8. 新严格模拟路径落地后的定点复核：预处理任务与计时

本节为2026-10-16追加审查，只定点阅读新 `gemm_strict_emulation_impl`、现有split的循环层级和pack派工入口，未运行负载。主代理报告新路径已通过4项CTest；本子审查不将该状态冒充自己执行的测试。

### 8.1 当前已对齐与仍未对齐的内容

新路径明确采用固定256块、全六片separate split/pack、所需面板worker私有staging、FP64逐组件即时重建，以及完整私有result/事务提交。staging缓冲采用池化堆分配，避免大线程栈，这是合理实现。`OZAMX_STRICT_PATH=OFF`可留现行路径对照，local staging OFF可对照新路径供数。

但目前split仍调用原全矩阵vector-chunk派工；pack也将A面板拆为行任务、B面板拆为行对任务。因此严格说当前是“固定几何、全片、staging、即时重建对齐”，不能描述为“§6.3预处理任务组织已全部对齐”。默认选项ON只是默认选择，不是性能已优于旧路径的证据；实际采用理由仍需同批完整API对照。

若目标是可审查的strict-emulation，建议补宏块static调度。若为了先保持实验单变量暂不补，应在plan metadata显式写 `preprocess_schedule=vector_chunks`，之后单独切成 `panel_static`，不要先宣称完全对齐再悄悄更改。

### 8.2 保持全局FP64数学不变的宏块遍历

建议把“遍历哪些元素”与“每个vector做什么数值操作”分开。保留一份SIMD数值body和一份scalar/tail body，增加内部遍历策略，避免复制两套完整split。

- FP32：OpenMP外层任务为二维256×256 block，flatten或collapse后static；每任务内部按行、16元素vector遍历并完成原三片递推。A的形状自然对应(M,K)，B对应(K,N)。同样的通用rows/cols block遍历器足够，不需要两个数值实现。
- FP64：初始化与校验可按block派工；每一层先遍历全部block计算worker-local max，然后全局归约为**一个**max；单线程算一个sigma，barrier发布；之后各block用相同sigma投影、存片、更新残差；更新完成后barrier，再进下一层。six rounds及whole_zero逻辑保留。
- 全局max是对正常、已验证有限值的max，改变分配不会像浮点求和那样引入结合律误差；但invalid标志必须先归约完成，NaN不得污染或绕过域检查。
- whole_zero时所有线程必须走一致分支；不能有线程局部退出而其他线程进入barrier。并行区内不直接抛异常。
- 行尾mask以当前block/实际行界限计算；存储地址仍是 `row*cols+col`，src仍用ld。256可被16/8整除，但末块不能复用无mask的整块路径。

共享数值body应返回invalid标志或写worker-private标志，不要把捕获外层共享`bad`的lambda拿进不同OpenMP归约上下文而产生数据竞争。可让范围body处理一行连续向量区间，调度器只传row/start/end；它是实际存在的内部Seam，不必增加public Interface。

不应为追求宏块派工而把sigma做成每block一个。那将改变分片、终端残差和Table4误差，超出当前工程对齐授权中的数值保持要求。论文对实际shift作用域未完整披露，仍须记录本复现使用全局解释。

### 8.3 pack也要按panel组织任务

现有 `pack_slices` 的A工作数为 `mblocks*kblocks*256`，每任务一行；B工作数为 `kblocks*nblocks*128`，每任务一个行对。static不等于panel-static：同一个256面板仍可分给不同worker。

严格路径应让外omp-for任务分别为(mb,kb)与(kb,nb)的完整panel，原来的行/行对及slice循环置于任务内部，保留所有原地址映射、VNNI配对与padding逻辑。可以抽出“打包一个A面板/一个B面板”的内部函数，旧细粒度路径继续复用更小的行body；不必复制格式转换代码。

无需立刻把split与pack融合成一个复杂大内核。先按原文宏块调度完成两阶段，对比数据流；将融合另列优化，尤其FP64全局逐层max同步使完全独立panel六层融合不成立。

小N会显露原文的低任务数：N256只有一个A/B宏块任务，N512各四个。严格路径因此可能比细粒度路径慢，这是协议真实结果。记录requested threads、实际team、有效任务数，不能用“小尺寸64线程”暗示64核都有有用工作。

### 8.4 tile setup与论文compute计时如何同时诚实表达

现有新路径 `load_config()` 在并行区中，且外部完整API墙钟包含它，这是正确的应用成本。论文§6.3 p.17称tile配置在timed compute region之前，不意味着现实公开调用的全部耗时可凭空删除。

建议保留两种明确计时：

1. `api_wall_s`：调用前到同步返回，包含许可/配置、并行启动、split/pack、内存分配、计算、提交、release和清理中实际发生的全部工作。它始终是API性能headline。
2. 单独instrumented的 `strict_compute_region_s`：在**同一个OpenMP team**内，各worker完成load_config后barrier；single写共享起点（保留single默认barrier）；执行block循环并在末尾barrier；single写共享终点；之后release。该窗口包含其实际必要的循环调度/等待，声明不含setup/release/最终commit，不能命名为完整API。

不能在另一个预热parallel region配置tile，再假定下一parallel region必然复用相同OS线程与tile状态。若未来持久线程团队跨调用复用，必须成为独立执行模型并记录生命周期成本，不得悄悄用它改旧Interface语义。

不要用 `API_time − 单独测量的setup_time` 生成所谓“修正API吞吐”；不同阶段的屏障/线程唤醒和分配行为不能靠异步测值相减精确重建。阶段窗口用于解释论文口径，完整API结果仍完整保留。

现有 `t1→t2` 包含pack、释放slices和result/worker缓冲分配；`t2→t3`包含配置、计算、release和commit；`t0→t3`仍不含函数返回时的局部对象析构。这些阶段名应披露真实覆盖，不能仅因叫pack/compute/total就把它们当纯pack、纯AMX或完整API。

### 8.5 此轮最小修改建议

先提交一个明确独立的预处理调度改动：共享数值body，新增panel-static遍历及panel粒度pack，固定全局sigma数学；验证分片和完整结果逐位保持，再与当前新严格模拟路径对照。tile计时先保持真实API，必要的compute-region instrument单独配置用于诊断。这样可以分清新的性能变化来自预处理派工，还是计时口径变化。
