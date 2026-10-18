# 严格模拟阶段：benchmark 证据修复与定点复核

日期：2026-10-16。本阶段只修改 `bench/benchmark.cpp` 与本文，不修改既有审计数据、计算公式或数学验收阈值。生产计算路径与 CMake 开关由主代理负责。

命名边界：`paper-alignment-paired-api-v2-20261016`、`paper_protocol_and_identity_valid`、`paper_fp32_speedup_targets_all_met` 以及 `历史本地 benchmark 工件（未纳入 clean 分支）` 是 2026-10-16 历史工件的原始标识，保留不改。后续新结果字段使用 `reference_protocol_and_identity_valid` 与 `figure7_fp32_speedups_all_met`。

## 完成的证据修复

本阶段 driver 使用 `timing_schema=api-wall-headline-v2`、`measurement_protocol=paired-alternating-api-first-even`；2026-10-16 历史 checkpoint 的 source_id 为 `paper-alignment-paired-api-v2-20261016`，2026-10-17 起的严格模拟 campaign 使用 `strict-emulation-paired-api-v3-20261017`。

- 每配置分别对 ozAMX、oneMKL 做一次未计时预热。随后每轮各计时一次：偶数轮先 ozAMX，奇数轮先 MKL。输入、分布、seed、alpha=1/beta=0、precision/budget 与旧 driver 保持相同定义。
- ozAMX 墙钟包住完整公开 profiled API，包括 dispatch、split/pack、compute/reconstruct、返回和清理；MKL 计时包住其原生 SGEMM/DGEMM 例程。两者用同一个 `steady_clock` 的秒数，互不混入另一个例程，也不包含参考指标计算或 checkpoint 文件 I/O。
- 每轮两个调用均完成后才保存 checkpoint。恢复时同时恢复两套样本；不会把保留的旧 ozAMX 向量与新一批 MKL 均值拼接。
- headline `effective_GFLOP_s` 改为 `2*N³/mean(raw_api_call_wall_s)/1e9`；保存 `raw_mkl_gemm_s` 并从其算术均值形成 `mkl_gemm_s`。不平均每次 throughput，不乘产品预算。
- 参考 C、完整 `abs(A)@abs(B)` 和辅助高精度误差只在所有计时之后计算一次。没有为交替计时重复计算 truth 或绝对乘积界。

交替调用减少固定先后批次的漂移混淆，不等于排除了共享机器竞争、缓存/NUMA状态、OpenMP等待策略或不同内部线程数量。checkpoint 写盘在 timer 外，仍可能影响下一轮状态；本阶段没有偷偷删除长样本或更换误差阈值。

## CSV 向后读取与明确的 profile 指标

原有列名及顺序保留，新字段追加在原 `status` 后；历史CSV文件不重写、不标成新schema。各字段应按其记录的schema解释：

| 字段 | 新schema含义 |
|---|---|
| `effective_GFLOP_s` | 常规 useful `2N³` / 完整 API 算术时间均值 |
| `api_call_wall_s_mean` / `raw_api_call_wall_s` | 完整API均值 / 逐次秒数 |
| `profile_total_s_mean` / `raw_profile_total_s` | 内部阶段profile，保留用于拆解 |
| `profile_effective_GFLOP_s`，新增 | 常规 useful `2N³` / profile时间均值 |
| `profile_speedup` | 保留旧列的明确含义：MKL GEMM mean / profile mean |
| `api_speedup`，新增 | MKL GEMM mean / 完整 API mean；新headline速度比 |
| `mkl_gemm_s` / `raw_mkl_gemm_s` | 交替轮次的MKL算术均值 / 逐次秒数 |
| `timing_schema` / `measurement_protocol`，新增 | 区分旧profile-headline、旧顺序测量与新API-headline交替协议 |

两个 raw 向量的相同索引表示同一轮；零基偶数索引是 ozAMX-first，奇数索引是 MKL-first。若reps为奇数，两个先后顺序次数会相差一，不声称严格等量ABBA。

新 `timing_scope` 列也直接描述 headline、profile 和交替顺序。旧CSV没有新schema时，应按历史定义读取其 `effective_GFLOP_s`，不能用新定义反向改写历史数值。原来的冻结V3专用分析器仍只适用于其冻结source_id；没有把新checkpoint冒充V3补测。

## checkpoint 身份与拒绝规则

在预热之后、所有 timed pair 之前生成运行身份。保存并核对：

1. 运行时可读 `bench/benchmark.cpp` 的 SHA-256。
2. `/proc/<本进程PID>/exe` 的 SHA-256。它绑定实际编译后的 driver 和静态链接的 ozAMX，包括编译选项导致的二进制变化；不能仅靠手写 source_id 续用旧库样本。
3. 实际 `dladdr(cblas_sgemm)` 对应 oneMKL runtime 的 SHA-256，以及预热后实际加载共享对象的路径与SHA。
4. OMP/GOMP/KMP/MKL/OZAMX/LD/locale 相关环境变量的完整排序记录；实际OMP/MKL线程/动态配置；启动时CPU affinity、预热后主线程affinity，以及主机名、kernel release、architecture。
5. schema、交替协议以及原来的precision、distribution、N、budget、threads、seed、requested repetitions。

完整身份记录采用长度前缀规范化后十六进制编码，保存于CSV/checkpoint的 `run_identity`；不是只给环境字符串一个短哈希。显式source/executable/MKL SHA也单列，便于复核。

源码SHA指的是**运行时磁盘上的源码快照**，不谎称从可执行文件中还原出编译时源码。真正的编译产物身份由 executable SHA绑定。该工具按进程缓存已读文件的SHA，运行期间应保持源码/库文件不变；跨进程恢复会重新读取和核对。源码不可读或hash工具失败时停止，不以“unknown”放行checkpoint。

实现使用 `/usr/bin/sha256sum`，通过 `fork/exec` 的独立 argv 传文件路径，**不启动shell**。因此不需要改CMake或新增crypto链接库；这是Linux本地benchmark的显式运行依赖。源码以相对 `__FILE__` 编译时，应从能读取该路径的工作目录运行；推荐现有CMake绝对源路径构建。

旧版checkpoint、缺少MKL raw、schema/身份/参数不符、不同长度的两套raw、非有限/负时间、非正API/MKL时间，都会拒绝恢复。报错提示使用新的checkpoint路径，不自动迁移或混样。仅在完成整轮时写 `.tmp` 并替换checkpoint；写入或关闭失败触发异常，不将不完整数据标成complete。

动态加载共享对象集合也采取严格比较；即使某次差异只来自无关的额外加载，也可能保守拒绝恢复。不要手工编辑identity来绕过；应选择新路径并单独分析新批次。该身份不等于完整系统状态证明：其他租户、瞬时频率、内存压力、未加载的将来依赖、NUMA页实际放置等仍需外层runner另存环境/依赖manifest与机器观测。

## 已完成的限定验证

- `g++ -std=c++17 -O2 -fopenmp -Wall -Wextra -Wpedantic ... -fsyntax-only bench/benchmark.cpp` 通过。
- 编译并运行只调用checkpoint/身份辅助函数的临时契约检查，**不执行GEMM**：完整paired raw写读往返一致；改变运行identity或executable SHA、改变distribution、MKL时间为0、两套向量长度不一致、旧source_id，均被拒绝。SHA子进程返回有效64位hex摘要。
- `git diff --check -- bench/benchmark.cpp` 通过。

N32实际GEMM、真实CSV公式重算、同身份续跑、改变环境/二进制的拒绝，以及正式paired campaign，由主代理持统一性能锁执行，避免与其CTest/性能负载并行。本阶段没有自行运行CPU重载；后续验证结果应附在本节，不能把静态/辅助契约检查说成实际性能通过。

## 仍未由本次 benchmark 改动修复的严格模拟验收事项

计时/证据修复不决定生产计算是否按论文的固定256输出块、block-local operand staging、每product立即FP64拓宽、BK边界和FP32 K32产品嵌套执行。这些属于主代理的生产路径与专项probe复核范围。论文作者的完整RNG/seed、实际硬件/Intel OpenMP/固定频率、未披露嵌套层次和FP64误差表差距，也没有被本次CSV/schema改动解决。

原有零分母误差单列缺口、`status=ok`不代表论文精度门槛，以及更一般输入下的完整数学验证仍保持既有定义；没有为了让新benchmark通过而调整数学阈值。新库与旧冻结结果应使用各自实际二进制身份、输入生成及测量协议，不能拼接为同批加速比。

## 对主代理新增生产路径的只读定点监察

应主代理要求，另只读检查 `gemm_strict_emulation_impl`、必要的panel索引定义、CMake开关与新增 `tests/strict_emulation_probe.cpp`，未修改这些文件，未重跑负载。当前限定审查没有发现需要修正的索引或事务性错误：

- B局部微块偏移 `j*BK` 正确。`pack_slices` 对每个32列组的基址为 `(j/32)*8192`；计算循环j恒为32倍数、BK=256，因此两式相等。不是普通行主序的 `j` 元素偏移；A对应的 `i*BK` 也与32行组布局一致。
- macro-panel基址分别是 `(mb*kblocks+kb)*BM*BK` 与 `(kb*nblocks+nb)*BK*BN`。每worker局部staging占独立的depth片区，片/worker跨度都是64字节倍数，没有跨worker覆盖。
- pack阶段完整补零M/N/K尾部。最后BK调用使用 `ceil(min(BK,remainingK)/32)` 步进，padding补足最后K32；输出只提交有效rows/cols。四budget的depth为3/4/5/6，产品 `s,diagonal-s` 均在已保存六片范围内。
- FP64始终split/pack六片，低budget只减少所需staging与产品选择；每product独立AMX/store，再立即float→double加，没有Wide Batch2。FP32保留原六项物理顺序及BK边界。
- 完整私有result、blocks/staging分配都在用户C提交之前；bad在并行区归约后检查，再统一copy C。异常时不提交、A/B与C alias时先完成全部输入预处理，公共K=0仍由runtime wrapper处理。
- CMake两个开关分别控制严格模拟路径和local staging，关闭严格模拟路径可保留旧组织作单独对照。未将两种库混成同一运行身份。

新增probe的FP32 `65×289×513` 使用独立整数oracle及带padding的A/B/C；FP64 `25×41×289`、`257×33×65`、`17×263×257` 对四budget分别构造独立rho45分片、每BK的binary128组件dot→float→double参考，检查全部输出及C行padding。这些尺寸覆盖两轴panel边界、32微块尾部与K257/289/513的跨BK/尾K32。component-rounding=0是这些有界输入下能以该oracle逐位比较的前提，不能泛化成所有组件dot都无FP32舍入。

仍需在新结果中明确：FP32的K32×六项嵌套没有作者源码来消除歧义；worker `load_config/release` 仍处于compute profile内，而论文文字称config在timed compute之前；新 `pack_s` 包含result/blocks/staging的分配，不能把它与历史纯packing阶段不加scope说明地同比。完整API作为headline包含这些实际成本。工具链、硬件、随机输入及FP64论文误差差距也不因工程组织更接近论文而自动消失。

## 续跑、达标检查器加固与最终验收（2026-10-16 第二轮）

本节记录 2026-10-16 第二轮（续跑会话）新增的工具、检查器加固与最终验收结果；不重写前文结论。工件：`tools/resume_strict_emulation.py`、加固后的 `tools/analyze_strict_emulation.py`、`tools/test_analyzer_negative_fixtures.py`、campaign 目录终态 `provenance.json`/`analysis.json`，以及 `docs/strict_emulation/RESULTS_20261016.md`。

### 续跑工具与身份校验

- `tools/resume_strict_emulation.py`（SHA-256 `068c351cc689ad7555b2497d423bfb85d809b7caebdeb01aaf2b8a2235b99f17`）在启动前重算 provenance 冻结的 10 个源码文件与 3 个产物（candidate、libozamx.a、CMakeCache.txt）的 SHA-256，任何一项不一致即拒绝；`--check-only` 可做全量干跑。
- 通过后把本次续跑作为显式 `resume_events` 条目追加到 provenance（runner、runner_sha256、完整 command、环境、status_before），状态置 running，然后在 `/tmp/ozamx-perf.lock` 上 `flock` 等待，持锁后执行 `candidate ... --resume`。
- `--resume` 下由 benchmark 自己对每个既有 checkpoint 做完整 run_identity 校验（driver source、可执行文件、oneMKL runtime/加载对象、OMP/MKL 环境、affinity、host、schema/protocol、precision/distribution/N/budget/threads/seed/reps）后才复用原始向量；不会把旧样本与新测量混拼。
- 子进程退出后重新核对源码哈希并原子写回 `returncode`、`finished_utc`、`source_unchanged` 与 `status=complete/failed`。本次最终：resume_events 1 条，01:28:22 记录、02:53:57 完成；returncode=0、source_unchanged=true。

### 达标检查器加固要点

- affinity 期望值修正为本机实际记录的 `"0;"`（initial/calling 两个字段）：此前把它误报为问题，现在只降级为 note（提示人工核对 launch mask）。
- CSV↔checkpoint 交叉核对：逐配置核对 identity/precision/budget/N/seed/threads/distribution/complete/10 轮，以及 6 组原始向量（`raw_api_call_wall_s`、`raw_mkl_gemm_s`、`raw_split_s`、`raw_pack_s`、`raw_compute_recon_s`、`raw_profile_total_s` ↔ checkpoint 同名字段）逐元素一致。
- provenance 与产物核对：主命令与全部 resume_events 必须以 `taskset -c 0-63` 开头；status/returncode/source_unchanged；candidate/libozamx.a/CMakeCache.txt 哈希；source_snapshot 与工作区源文件对照冻结哈希。
- 逐模式八尺寸覆盖：`fp32_p6`、`fp64_p6/p10/p15/p21` 每个模式必须恰好覆盖 8 个尺寸；checkpoint 集合必须恰等于 40 配置；否则 exit 2。
- 退出码语义：0=完整且 8 个 FP32 尺寸全部达到 Figure 7 点值；1=完整性通过但未达标；2=身份/协议/覆盖失败。
- 报告原子写入（`.tmp` + rename），并记录 `reference_sha256`（本次 `58a480b8fb221b53022e7e6d278f746c723a8e61d088be4ecee07444046796d8`）与 `csv_sha256`。
- 本次最终判定：`full_40_configuration_coverage=true`、`paper_protocol_and_identity_valid=true`、`issues=[]`、`notes=[]`、`paper_fp32_speedup_targets_all_met=false` → **exit 1**（完整但未达标）。分析器输出留存 `本地历史分析日志（未纳入 clean 分支）`。

### 负向夹具（`tools/test_analyzer_negative_fixtures.py`）

只读复制 campaign 后逐项单点突变，要求 exit 2 且命中对应问题；`--require-complete-clean` 额外断言未突变副本 exit 0。2026-10-16 第二轮运行（日志 `本地历史负向日志（未纳入 clean 分支）`）：

| 夹具 | 突变 | 结果 |
|---|---|---|
| clean | 无（完整性基线） | rc=0，integrity valid |
| mixed_identity | 改一行 run_identity 末位 | rc=2，命中 `Missing or mixed run_identity` |
| incomplete_checkpoint | complete=false 且 9 轮 | rc=2，命中 `not complete with ten timed pairs` |
| truncated_raw | raw_api 向量删一项 | rc=2，命中 `raw vector lengths do not match repetitions` |
| missing_checkpoint | 删除一个 checkpoint | rc=2，命中 `checkpoint set does not equal` |

夹具只读原 campaign（复制到临时目录），不修改测量数据。

### 最终验收与剩余缺口

- 终态：provenance `status=complete`、`returncode=0`、`source_unchanged=true`；40/40 checkpoint `complete=true`；检查器完整性/身份检查全过（`issues=[]`）。
- 性能：FP32 完整 API 速度比 0.215/0.154/0.267/0.661/0.882/1.064/0.769/0.811（N=256…32768）vs Figure 7 点值 2.56/2.17/1.70/1.39/1.14/1.16/1.25/1.32，全部未达；如实保留为"完整但未达标"的负结果（表格见 `docs/strict_emulation/RESULTS_20261016.md`）。
- 剩余缺口（不得当作通过）：
  1. **零分母列未实现**：论文要求 `e_scaled` 分母为 0 时单独报告绝对误差；当前 CSV/checkpoint 只有 `e_scaled`/`eF`，没有零分母计数或绝对误差列，检查器也不校验该协议。
  2. **launch mask 未结构化写入 provenance**：只能从 command 数组解析 `taskset -c 0-63`；identity 的 affinity 字段为 `"0;"`（已用 `objdump -d` 确认 candidate 的 `affinity_string()` 枚举全部置位 CPU，故该值反映进程当时的实际 affine 集合），campaign 没有记录 OMP team 的最终 CPU 列表，二者不能相互印证；运行侧旁证（`outer_time*.txt` %CPU=2072%/4328%，matched 对照 `omp_thread_cpus`=0..63）与多核执行一致，但"绑定到哪些核"未被直接记录。
  3. **Figure 9 无精确点值**：FP64 速度不设阈值，只报告比率；不得据此声称 FP64 达标。
  4. matched staging、independent_final 与正式 campaign 为不同批次，不能混拼。
  5. 检查器只对完整性/身份与 FP32 Figure 7 速度比设门槛；FP64 精度倍率、分配器空档等为描述性指标，无阈值语义。
