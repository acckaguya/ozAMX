# 严格模拟实现与性能验收记录

分支：`codex/strict-emulation`（原 `codex/paper-alignment`）。起点：`b5523b1` 加用户原有注释/排版；原修改补丁保存在 `bench/8454h/paper_alignment/user_gemm_before.patch`，原未跟踪论文笔记保留。本阶段获得用户明确授权修改实现。此前只读审查的原始附件不覆盖。

命名边界：活跃实现、文档和构建开关使用 strict-emulation 命名；`bench/8454h/paper_alignment/**`、`bench/8454h/v3_paper_alignment/**`、历史 `source_id`、旧 JSON 字段、旧工具名和旧临时库路径保留创建时名称，属于不可改写的历史工件。后续新结果字段使用 `reference_protocol_and_identity_valid` 与 `figure7_fp32_speedups_all_met`。

2026-10-17 重新精读论文 §7–§8、Table 2–4、Figure 6–10 的协议核对与图表读数见本地（未推送）`trace/2026-10-17-paper-reread-experiments.md`。

当前状态：严格模拟路径实现与功能验证完成，正式 40 配置测量完成；完整性与身份检查全部通过。阶段 1（2GiB、两阶段 split+pack）FP32 全部尺寸低于 Figure 7、FP64 无预算超过 DGEMM。阶段 2（2026-10-16，见 §6）在**不偏离论文配置**的前提下完成宿主内存策略与 prep 实现优化：融合 split+pack writer 与 64GiB 工作区上限使 FP32 在 N=16384/32768 达到 1.094/1.159× SGEMM，FP64 p6 在 N=8192/16384/32768 达到 1.25/1.39/1.52× DGEMM；FP32 8/8 仍未达 Figure 7（大尺寸达成为点值的 88–94%），FP64 精度差距（约 5.70/11.1/21.9 倍）不受工程优化影响。**仍不宣称“论文性能已复现”**；结果按完整 API 墙钟报告。阶段 1 结论见 [RESULTS_20261016.md](strict_emulation/RESULTS_20261016.md)，阶段 2 明细表与原始样本在本地 trace（见 §6 工件边界）。

## 1. 已落实的严格模拟组织

默认 `OZAMX_STRICT_PATH=ON`：

- 固定 BM/BN/BK=256，TM/TN/TK=32；输出按宏块二维 static 分配，BK 顺序不变。
- FP32 保存三片，FP64 四种预算均保存并打包完整六片。正 σ、ρ=45、全矩阵 max 作用域及六轮残差公式保持不变，没有采用更接近 Table4 的非论文 signed-shift 变体。
- split 与 pack 以完整 256 宏块为静态任务。新增遍历策略复用数值主体；FP64 每轮仍须完成全局 max 规约、产生统一 σ、投影和同步，不改为 panel-local σ。
- 每 BK 将所需组件面板复制到 worker 的局部缓冲，再从其中供给原 AMX 微核。FP64 低预算只复制选中产品所需片，但全六片的预计算和全局打包确实执行。
- FP32 六项链保持 `11→10→20→00→01→02`。FP64 每个组件积独立 FP32 store，立即 widen/add 到 FP64，取消此路径的 batch2 延后物化。
- 工作缓冲在并行区外分配为三个池化 arena，worker 使用互不覆盖的片区并首次触页；没有每线程多 MiB 栈数组或上千个独立分配。

`OZAMX_STRICT_PATH=OFF` 保留原自适应路径。`OZAMX_STRICT_LOCAL_STAGING=OFF` 在严格模拟路径中仅关闭复制，其他数学/几何/预处理定义保持相同，用于区分 staging 的贡献。

`OZAMX_RESEARCH_STAGING_PIPELINE`、`OZAMX_RESEARCH_TASK_TEAMS`、`OZAMX_RESEARCH_PACK_USED_SLICES` 是 research-only 开关，默认均为 OFF；`OZAMX_STRICT_FP64_ROW_PAD_BYTES` 是仅改变私有累加器布局的 strict 优化，默认 **64**（证据见 §7）。改变 product/reconstruction 物理顺序的候选不得进入 strict。

其余实验开关（默认 OFF）：`OZAMX_PREP_FUSED_MAX`、`OZAMX_PACK_NT_STORE`，以及阶段 2 采用的 `OZAMX_STRICT_PREP_FUSED_DIRECT`（见 §6）。

## 2. 保留的 API 行为与优化边界

仍使用完整私有结果矩阵；全部线程完成有限性检查后才提交调用方 C。输入域检查、异常时 C 不变、C 与 A/B alias、leading dimension、尾块及 K=0 语义保留。没有为提高吞吐删掉 split/pack/reconstruct 或隐去分配/返回成本。

严格模拟路径将非有限分类延后到每个输出块完成后一次扫描：组件值一旦成为 Inf/NaN，后面只有拓宽与加法，不能恢复为有限值。这个优化保持每个标量的浮点加法顺序及最终异常/提交行为。旧自适应路径的原有检查策略保留。

还不能声称与作者逐行或逐阶段完全相同：作者没有完整 K32×product 伪码及 RNG；当前仍为全局 shift 的字面解释；worker tile 配置/release、公开 API 事务提交进入完整墙钟。新 profile 的 pack 阶段还包括结果和 arena 分配。当前 8454H/GNU/动态频率平台与论文 8462Y+/Intel/固定频率不同。不得从 headline 减掉这些真实成本来制造达标。

## 3. 数值与契约验证

新增 `tests/strict_emulation_probe.cpp` 不 include 生产 split/pack 内核。FP32 使用全输出整数点积；FP64 使用独立正 shift 六片、每 BK 的 binary128 组件点积→FP32→FP64 重建，与实际 API 逐位比较。

形状覆盖 `65×289×513`、`25×41×289`、`257×33×65`、`17×263×257`，包括两轴宏块边界、微块尾部、跨 BK 和非连续 leading dimension。四种 FP64 预算、C padding、输入保护全部检查；本例组件转换改变数为零，不泛化为所有输入的定理。

已通过：默认 OpenMP 的四项 CTest；staging-off 的新全输出 probe；关闭 OpenMP 的四项 CTest。日志均在 `bench/8454h/paper_alignment/`。现有 alias/overflow/late 路径检查与新参考互相补充，不把原宽松误差门当作 Table4 验收。

新 benchmark 的 N32 五模式实跑、同身份恢复两套 raw 向量逐字相同，以及改变等待环境后的拒绝恢复均通过。详见 `benchmark_contract/summary.json` 和 [benchmark 专项说明](STRICT_EMULATION_BENCHMARK_REVIEW.md)。

## 4. 性能协议与复现命令

正式数据使用每例程一次预热、十次配对计时。偶数轮 API 先，奇数轮 MKL 先；保留每轮两套秒数。headline=`2N³/mean(full API wall)`，profile 吞吐另列。比较的是完整 ozAMX API 与 oneMKL 原生 GEMM，符合论文的问题范围，同时披露附加事务成本。

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
  -DOZAMX_STRICT_PATH=ON -DOZAMX_STRICT_LOCAL_STAGING=ON
cmake --build build -j8
python3 tools/run_strict_emulation.py --build build \
  --out bench/8454h/strict_emulation/new_campaign --reps 10
python3 tools/analyze_strict_emulation.py \
  bench/8454h/strict_emulation/new_campaign/results.csv \
  --out bench/8454h/strict_emulation/new_campaign/analysis.json \
  --require-figure7-speedups
```

runner 使用全新目录、性能锁、CPU0–63、64线程、显式等待/内存池设置，保存源码快照、实际二进制/库、CMakeCache、环境与硬件信息。分析器重算 raw 秒数与 CSV 所报公式；缺少完整覆盖或任一 FP32 速度比未达到 Figure7 点值时，要求达标的命令返回非零，不把运行成功当作性能通过。

Table4 是未披露输入的经验点，误差倍率单独报告，不用改容差或换 σ 假装逐项一致。Figure9 没有精确数表，只保留文中趋势，不制造逐点验收值。

## 5. 当前已有的独立结果与限制

最终版本（staging ON，`libozamx.a` SHA-256 `dfb8d08e…`，与正式 campaign 同库）通过独立审计程序的198次调用校验（180次计时、0例正确性失败、两项负控均被捕获）：N4096 普通输入 4.9526 有效TFLOP/s、SGEMM 6.1692、速度比 **0.803×**；dyadic 精确输入 5.1706 / 6.5362、0.791×（`bench/8454h/paper_alignment/independent_final/analysis.json`）。

staging 单变量同批对照（`bench/8454h/paper_alignment/matched_staging_*/matched_calls.json`，control=OFF、candidate=ON，输出逐字节一致）：FP32 N4096 比值 1.102、N8192 1.056（ON 更慢，属纯额外拷贝）；FP64 p6 为 1.012/1.012 约持平；p21 为 0.920/1.009，无稳定收益。严格模拟路径因此默认保留 staging（保真），OFF 仅作工程上限对照。

正式40配置 campaign（`bench/8454h/paper_alignment/main_passive_2g_20261016/`）已完整：达标检查器 `--require-figure7-speedups` 判定 exit 1——完整性/身份通过，FP32 完整API速度比 0.215/0.154/0.267/0.661/0.882/1.064/0.769/0.811（N=256…32768），全部未达论文Figure 7点值 2.56/2.17/1.70/1.39/1.14/1.16/1.25/1.32；FP64 eF 约为论文 p6/p10/p15 的 5.70/11.1/21.9 倍（只做比率，不设阈值）。完整表格、大N分配器空档与结论边界见 [RESULTS_20261016.md](strict_emulation/RESULTS_20261016.md)。没有对 Intel 工具链、频率或 PMU 计数作未经执行的声明；未修改系统全局设置。

## 6. 阶段 2：严格模拟配置内的性能搜索（2026-10-16）

约束：几何、数学、六片全存全用、正 shift ρ=45、全局 max、每组件积独立 store→widen→add、块内 staging、64 线程与输出块独占全部保持；只允许改变宿主内存策略与 split/pack 的实现方式，且产物必须逐字节相同。L3a（按任务缩队）与 L4a（只打包预算用到的片）不计入本阶段配置。

候选与判定（同进程配对、PASSIVE、reps=10，全部样本保留）：

| 候选 | 机制效果 | 墙钟效果 | 判定 |
|---|---|---|---|
| FP64 split 下一轮 max 融合（`OZAMX_PREP_FUSED_MAX`） | split −6.5~7% | ≤1%（噪声内） | 不采用（默认 OFF） |
| pack NT-store（`OZAMX_PACK_NT_STORE`） | pack −29~38% | ≈0；32768 触止损 | 不采用（默认 OFF） |
| **融合 split+pack writer（`OZAMX_STRICT_PREP_FUSED_DIRECT`）** | 面板与全 C 逐字节相同（面板级 6724 万 uint16 零 mismatch；全 C 20/20 byte-exact）；六片 dense slices 不再 materialize，prep 流量约 −22% | 8192 fp64 p6 −19%、16384 p6 −33%、p10 −24%、32768 p6 中位 −23% | **阶段 2 采用**（构建时 ON；默认仍 OFF 保留严格两阶段路径） |
| 宿主工作区上限 8→64GiB | 32768 的 split/pack 重映射与首触基本消失（pack 相位 3.38s→0.29s 量级） | 32768 fp64 p6 中位 −30%、fp32 −17%；16384 仅 −6%；无内存压力证据（PSI/回收/swap 全 0） | 32768 采用大 cap；≤16384 用 8GiB 足够 |
| compute staging 流水线（C1） | 预期 0–5% | 未实施 | 剩余备选 |

落地建议：`OZAMX_STRICT_PREP_FUSED_DIRECT=ON` + N=32768 用 64GiB 工作区上限（≤16384 用 8GiB 即可）+ teams OFF、staging ON。

### 6.1 阶段 2 总表（严格六片 + 融合 writer + 64GiB；40 配置×10 轮、单批、完整性/身份/重算三重验收）

FP32 完整 API 速度比（均值 / 中位）对论文 Figure 7：

| N | 实测（mean / median） | 论文点值 | 达成 |
|---:|---:|---:|---:|
| 256 | 0.199 / 0.179 | 2.56 | 8% / 7% |
| 512 | 0.187 / 0.186 | 2.17 | 9% / 9% |
| 1024 | 0.313 / 0.312 | 1.70 | 18% / 18% |
| 2048 | 0.781 / 0.810 | 1.39 | 56% / 58% |
| 4096 | 0.925 / 1.049 | 1.14 | 81% / 92% |
| 8192 | 0.983 / 1.034 | 1.16 | 85% / 89% |
| 16384 | **1.094 / 1.177** | 1.25 | **88% / 94%** |
| 32768 | **1.159 / 1.234** | 1.32 | **88% / 94%** |

FP64 对 DGEMM：p6 在 N=8192/16384/32768 为 **1.25/1.39/1.52**（N=4096 为 0.96）；p10 在 N=16384/32768 为 0.98/**1.00**（中位 1.06，N=4096 的均值受一枚 MKL 离群影响，中位口径 0.77）；p15 最好 0.74、p21 最好 0.49。首次在量级上复现论文 Figure 9 的定性趋势（p6 中途交叉并升至 ~1.5；p10 只在最大档触及 1；p15/p21 不超）。FP64 精度倍率未退化（仍为论文 p6/p10/p15 的 5.70/11.1/21.9 倍）。

### 6.2 边界与风险

- 归因只引用同进程配对效应（fused-direct −19%/−33%/−24%/−23%；cap64 −30%）；与阶段 1（2GiB）表的差异更大但跨批不可归因。
- N=32768 偶发候选侧 compute 尖刺（13.98/32.06/64.94 s 样本），均值失真、中位稳健；64GiB cap 下峰值 RSS ≈102 GiB/进程，部署侧需确认。
- 严格目标门仍为 exit 1：FP32 8/8 未达 Figure 7，不宣称“论文性能已复现”。小 N（256–1024）是固定开销与任务数决定的结构性差距；论文 N=256 的 2.56× 用硬件预算（AMX-BF16/FP32=16×，六积上限 2.67×，再扣 Figure 10 自报的 1/3 预处理占比）可证伪为小尺寸开销产物，不作为优化目标。

### 6.3 工件边界

历史工件目录 `bench/8454h/paper_alignment/**`（campaign、arms、字节门、配对运行）与 `trace/**` 为本地工作产物，**不随分支推送**；阶段 2 的完整表格、尖刺清单与配对原始数据见本地 `trace/2026-10-16-phase2-headline-results.md`、`trace/2026-10-16-prep-fused-direct.md` 与对应 arms 目录。

## 7. strict 布局优化：私有 FP64 block 64 B 行 padding（A1，2026-10-17）

机制：strict 路径的 thread-private FP64 block 逻辑形状仍为 `BM×BN=256×256`，但物理行 striding 从 `256` doubles（2048 B）改为 `264` doubles（2112 B，即每行多 64 B）。这只改变私有累加器的地址映射，不改变分片、product 顺序、每组件 `store→widen→add`、输出 block 所有权或最终 C 字节。默认 `OZAMX_STRICT_FP64_ROW_PAD_BYTES=64`；FP32 block 不 padding。设为 0 可复现旧布局。

原因：2048 B 行距是 64 B cache line 的整数倍（32 lines），多行工作集会集中到少数 L1 set；64 B padding 后行距为 33 lines，32 行分散到全部 64 个 set，减少 FP64 reconstruction 的 set 冲突。

同进程双库配对（PASSIVE、64 threads、CPU 0–63、8 GiB、10 reps、complete、full-C byte-exact；candidate/control，API 为 paired median）：

| N | 模式 | API ratio | compute ratio | 备注 |
|---:|---|---:|---:|---|
| 256 | fp64 p6 | 0.969 | 0.932 | 小尺寸噪声大，未回归 |
| 256 | fp64 p21 | 0.966 | 0.918 | 小尺寸噪声大，未回归 |
| 1024 | fp64 p6 | 0.975 | 0.949 | |
| 1024 | fp64 p21 | 0.963 | 0.873 | 小尺寸样本波动 |
| 8192 | fp64 p6 | **0.905** | **0.925** | |
| 8192 | fp64 p10 | **0.965** | **0.957** | |
| 8192 | fp64 p15 | **0.973** | **0.973** | |
| 8192 | fp64 p21 | **0.926** | **0.930** | |
| 16384 | fp64 p6 | **0.935** | **0.923** | 均值比 0.902 |
| 16384 | fp64 p21 | **0.908** | **0.907** | 均值比 0.862 |
| 8192 | fp32 p6 | 1.007 | 1.004 | padding 只对 FP64，观察为噪声中性 |

结论：A1 是 strict-compatible（仅布局）且大 N 收益稳定，默认采用。原始配对在本地 `/tmp/a1_pad_pair_*`，不进入推送；本结论不替代论文 Figure 7/9 的跨平台 headline。

## 8. product/reconstruction overlap 的边界

P4（下一 product 的 AMX 与当前 product 的 FP64 widen/add 交错）不属于 strict：重读论文 §6.3/§8.4 可见“每个 AMX product 必须 store、widen、add，之后才 evaluate the next product”。P4 只能作为 `research product/reconstruction overlap`，默认关闭、单独报表，不得混入本严格实现或论文 headline。完整依据见 `trace/2026-10-17-paper-reread-strict-overlap-synthesis.md`。
