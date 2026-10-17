# Benchmark 与吞吐口径定点审查

审查日期：2026-10-15。只读审查生产实现、benchmark、runner 和已保存的 CSV/JSON；没有重新运行性能基准，没有改动实现或脚本。原始论文为 `third_party/papers/2609.04663v1.pdf`，对照全文提取 `/tmp/ozamx-paper-full.txt` 的 §7、§8。本文的数值来自独立 Python 轻量重算，不以旧报告里的结果表代替原始记录。

## 结论与证据等级

1. **未发现当前核查数据的秒/毫秒/微秒换算错误，也未发现把常规 GEMM 的工作量误写成 p 倍的错误。** V3 最新完整论文对齐 campaign 的 66 个原始 CSV，raw 样本均值、主表 profile 吞吐和 raw BF16 的 GFLOP/s、TFLOP/s 均吻合其记录。161 TFLOP/s 的热 AMX 校准可从迭代计数、指令工作量和时间重算，不能因数值大就判假。
2. **确定存在并行使用不同指标的情况。** `bench/benchmark.cpp` 的 `effective_GFLOP_s` 与 `profile_speedup` 用内部 profile_total，而完整 API wall 另列。在 N=32768 FP32，这使 profile 吞吐比完整 API 吞吐高 9.4135%。若把这两个字段解释为完整端到端表现，就是口径错误；字段本身的除法没有算错。
3. **论文的性能结果确实没有在最新 V3 campaign 中复现，不能归咎于显示单位。** FP32 N=8192 的完整 API 速度比只有 0.506142，而论文 Figure 7 是 1.16；N=32768 是 0.506756，而论文是 1.32。改用较乐观的 profile 口径也不能消除这个差距。
4. **共享主机/执行状态漂移是已观察到的测量现象，其具体硬件根因尚无证据。** 同一个冻结 V3、相同 N/线程/seed，主表与稍后 scaling 测得的时间可差近 2.43 倍；不在优化域的 V4 N=16384 配对还出现“均值比 0.60487、逐对比中位数 1.00014”的分裂。不能把跨批差异全部记到某次代码优化名下。
5. **`status=ok`、有限误差、checksum 和与 V3 逐字节一致是不同保证。** 最新 V4 matched 有输入哈希和最后完整输出 SHA gate；论文对齐分析器没有论文精度通过阈值，`valid` 不是论文结果复现成功。FP64 最新数据的误差差距真实存在。
6. **源文件哈希不同不等于算法改变。** 主代理已确认当前源码与 adopted 快照去注释、格式差异及相邻字符串拼接后 token 一致，新构建静态库 SHA 还与 V4 库逐字节相同。历史数据可作同实现的历史观测，但当前环境性能仍应引用本轮新测量；不能把跨时段差异冒称算法变化。

## 1. 应用哪个数据集

| 数据 | 定位 | 可支持的结论 |
|---|---|---|
| 最新完整 V3 论文协议补测 | `bench/8454h/v3_paper_alignment/results/*.csv`、`checkpoints/`、`config_status.csv` | 40 主表 + 18 FP32 scaling + 8 raw BF16，各十次、一次预热 |
| 最新保存的实际主代码/V3 配对 | `bench/8454h/roofline_v4/production_validation_runs/main_current_20261014/matched/*/matched_calls.json` | 八配置的完整 API 交替对照；不是 oneMKL 对照 |
| 对应主代码的独立 oneMKL 补测 | 同目录 `onemkl_separate.csv` | 十配置，各三次；ozAMX 与 MKL 顺序测量；不能拼接成上述配对 campaign 的 MKL 结果 |
| 最新热工作集校准 | `bench/8454h/roofline_v4/calibration_20261014/raw/kernels.csv` | 57 配置，含预热共 228 行、171 条计时行，各三次；热寄存器、产品、重建的局部参照 |
| `matched_calls/results/final_rc_20261014/`、`rc1_independent_confirmation_20261014/` | 实验 RC1/RC2 | 不能替代实际采用版本的结果，更不能将其 FP64/N=16384 实验域说成当前采用域 |
| `bench/final_main_40.csv`、`bench/raw_bf16_n*.csv` | 原 Gold 6430 历史 campaign | 不作为最新 8454H 测量 |

V3 冻结库 SHA-256 为 `73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c`。`v3_paper_alignment/FROZEN_COMPLETE` 记录 66 配置，冻结于 2026-10-14；`campaign_completion.json` 记录最终结束时间 09:14:09Z、失败配置 0。第一次 runner 的 rc=127 是 main 完成后、scaling 开始前的 shell 文件编辑/读取竞争；修正后验证 checkpoint 并跳过完成的主表，补齐 18+8。不能沿用旧的“V3 论文对齐还未完成”描述。

V4 实际采用库身份为 `7adcc98996d5a88aa21f74038a42710a28496cf601f2127c016b8e8687801b68`。本次读取到工作树 `src/gemm.cpp` SHA 为 `f1e9e9cab94b3a6eb010fd8f3eddf0af8f342a2403393e8edde139754e68928a`，而 `roofline_v4/adopted_current_main/source/src/gemm.cpp` 为 `498fe70a1c7d343c67b19b495409fe0bbfb4440746fca4d03e7a02ce282c3eba`。仅字节哈希不同不能推断逻辑变化：主代理的 `docs/audit/evidence/source_identity.json` 及后续规范化核对覆盖八文件，处理 escaped newline 和相邻字符串拼接后 tokens 一致；本轮 `/tmp/ozamx-audit-20261015-build/libozamx.a` 的 SHA 与上述 V4 库相同。历史原 build 路径因清理缺失时，使用冻结备份，不能称结果算坏。用户未提交修改和 `docs/PAPER_SECTION_6_3_IMPLEMENTATION.md` 均保留。

## 2. 论文协议与计时边界

论文 §7.1（PDF pp.17–18）要求 64 个物理核、一次预热、十次计时、报告**算术平均运行时间**；使用双路 Xeon Platinum 8462Y+、Intel oneAPI/oneMKL 2026.1、compact 线程绑定。§7.3 及 Table 4 的 headline 精度参照是完整输出对 oneMKL SGEMM/DGEMM，较高精度诊断不替代它。§8.3 明确包含 BF16 decomposition、packing、AMX component products、target-format reconstruction。

生产 driver 与论文的共同点和差异：

- `bench/benchmark.cpp:382-396`：一次未计时 AMX 预热，随后用 `steady_clock`、`duration<double>` 记录秒；外层 wall 包住完整 profiled API。数据生成和 caller A/B/C 分配在计时外。
- `bench/benchmark.cpp:167-186`：MKL 关闭 dynamic、请求同样线程数，一次预热、reps 次 GEMM，除以 reps。MKL reference 接收**同一组** A/B；alpha=1、beta=0、RowMajor/NoTrans。MKL GEMM 自身所需的内部工作仍在其 routine timer 内。
- `bench/benchmark.cpp:413`：先把 ozAMX 的全部重复测完，再测 MKL；并非 ABBA 交替、随机顺序或同步匹配。
- `bench/benchmark.cpp:420-426`：旧 `effective_GFLOP_s` / `profile_speedup` 分母是内部 profile，不是外层 wall。`430-434` 同时保存完整 raw wall，并明确解释其 scope。
- `tools/analyze_v3_paper_alignment.py:211-247`：主结果从十个 raw wall 重新取算术均值，并算 `2N³/wall`、`MKL/wall`。这一步正确避免了继续把 profile 当端到端。
- V3 `run.sh:15-18,79-83,95-113`：taskset 0–63、GNU OpenMP、close、2 GiB workspace cache；主表、scaling、raw 顺序执行。与论文 Intel 编译器/OpenMP、CPU 型号及固定频率环境不同。没有证据把某一环境差异单独量化成复现差距。

“MKL GEMM-only / ozAMX 完整 API”的 scope 不同，但论文 §8.3 本来就在比较完整仿真方法与 native SGEMM/DGEMM。这里应精确注明 scope；**不能把这种差异本身当作应该删掉 split/pack/reconstruct 的理由**。一旦刪掉这些阶段，反而不再是论文的完整方法比较。额外事务保护、分配、tile 配置等差异另由实现监察记录。

## 3. 单位与工作量：逐项核对

常规 GEMM 有用吞吐：`P_useful = 2*M*N*K / mean(seconds) / 10^12`，单位 TFLOP/s。方阵为 `2N³`。秒转毫秒乘 1000；若直接用毫秒作分母，TFLOP/s 需除 `10^9`，不能再除 `10^12`。

分量工作等价值：`P_components = p*2*M*N*K / time / 10^12`。FP32 p=6，FP64 按 6/10/15/21。这是不同 numerator；不能与常规 `2MNK` 不加说明地混用。若分母是 compute+reconstruct，它还包含转换、累加等时间，不能称实际 AMX issue rate。若分母是完整 API，又包括准备、调度和释放。

| 文件/行 | 核查结果 |
|---|---|
| `bench/benchmark.cpp:389-390,420-426` | 秒，`2N³/profile/1e9` 是 GFLOP/s，MKL 同理；未偷偷乘 p |
| `bench/raw_bf16.cpp:135-153` | BF16 转换与 caller 分配在计时外；raw MKL GEMM 秒均值；GFLOP/s 除 1e9、TFLOP/s 除 1e12，正确 |
| `bench/optimization_benchmark.cpp:135-149,176-191` | 输出阶段秒与完整 wall 秒，checksum 在 timer 之后；并未自算 TFLOP/s |
| `tools/platform_baseline.cpp:338,360` | 每个 SIMD FMA 按两次 FLOP；AMX 每条 `TDPBF16PS` 为 `2*16*16*32=16384`；每循环四条，计数正确 |
| `tools/roofline_kernels.cpp:202-223` | `REGISTER` 每 unit 四条 TDP；产品按 `p*2*32*32*256`；重建用 add 次数，logical bytes 另列，未当作实测 DRAM 字节 |
| matched `driver.cpp:48-58` | API 和阶段全部为秒；runner/summary 显示 ms 时另乘 1000 |

对 66 个 V3 CSV 的独立检查：全部 raw 样本算术均值吻合相应 mean 字段；所有主/scaling `effective_GFLOP_s` 吻合 **profile** 公式；八个 raw CSV 的 GFLOP/s 和 TFLOP/s 吻合 mean(raw_seconds) 公式；相对容差 1e-9 下错误数为 0。这个结果不等于对 MKL 逐次观测做了独立分布核验，因为主 driver 未保存 MKL 原始向量。

### 3.1 raw BF16 的实算

来自最新 `v3_paper_alignment/results/raw_bf16_nN.csv`，每项十次：

| N | raw GEMM 平均秒 | 重新计算 GFLOP/s | 重新计算 TFLOP/s |
|---:|---:|---:|---:|
| 256 | 0.0000336582 | 996.9170 | 0.9969170 |
| 512 | 0.0001027502 | 2612.5054 | 2.6125054 |
| 1024 | 0.0002801459 | 7665.5901 | 7.6655901 |
| 2048 | 0.0006549749 | 26229.8131 | 26.2298131 |
| 4096 | 0.0048192198 | 28518.9220 | 28.5189220 |
| 8192 | 0.0298952581 | 36778.7970 | 36.7787970 |
| 16384 | 0.2266286439 | 38812.8035 | 38.8128035 |
| 32768 | 1.7897276629 | 39318.1296 | 39.3181296 |

例如 N=8192，`2N³=1,099,511,627,776` FLOP，除以 `0.0298952581 s` 得 `36,778,796,961,649 FLOP/s`，即 36.778797 TFLOP/s。没有 1000 倍的计算错误。

论文 Figure 6 把 35.47 等值标为 GFLOPS，而本地数值以 TFLOP/s 的量级与之接近。**已确认的是图印刷标签和本地正确单位有显著疑点；未获得作者原始时间，不能独立证明其原图一定误标了 1000 倍。** `paper_reference.json` 和 `tools/analyze_v3_paper_alignment.py:454,538` 保留该疑点，没有静默改论文标签。图中数量级不能作为本地 raw 数据造假的证据。

### 3.2 热 AMX 校准不是不可能的 TFLOPS

最新 calibration 的 64-thread `amx_register` 第三条 timed 行：`units=196,574,976`、`elapsed_s=0.080008062`。每 unit 四个 TDP，每 TDP 16384 FLOP，因此 `196574976*4*16384/0.080008062/1e12 = 161.017993751 TFLOP/s`。三个 rate 为 161.027091196、160.927212177、161.017993751，其中位数确为 161.017993751。原始 CSV 的所有 `ops_per_s=amx_or_add_ops/elapsed_s` 均一致。

同样重算的三样本 rate 中位数：FP32 六项产品 155.549694940，FP32 产品加重建 151.737646219，FP64 p6 产品加重建 84.422912445，p21 产品加重建 86.305867834 TFLOP/s。该校准用中位数是其局部 microbenchmark 的描述惯例；论文主表仍须用十次运行时间算术均值。这些热小工作集结果不包含完整矩阵遍历和 API 全部成本，不能直接拿 161 除以完整 GEMM 的 useful TFLOP/s 算“硬件利用率”。

## 4. 最新 V3 主表：完整 API 与 profile 的差异

FP32 原始样本独立重算如下。速度比均为 `MKL mean / ozAMX mean`，大于 1 表示 ozAMX 较快。

| N | API 均值 s | profile 均值 s | useful TFLOP/s / API | useful TFLOP/s / profile | MKL/API | MKL/profile | 论文 Fig.7 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 0.0005602849 | 0.0005591571 | 0.059888 | 0.060009 | 2.219997 | 2.224475 | 2.56 |
| 512 | 0.0008695253 | 0.0008683310 | 0.308715 | 0.309140 | 1.086466 | 1.087961 | 2.17 |
| 1024 | 0.0008878518 | 0.0008857900 | 2.418741 | 2.424371 | 0.661653 | 0.663194 | 1.70 |
| 2048 | 0.0056814962 | 0.0056790055 | 3.023828 | 3.025155 | 0.591206 | 0.591465 | 1.39 |
| 4096 | 0.0411513942 | 0.0411461705 | 3.339837 | 3.340261 | 0.631458 | 0.631538 | 1.14 |
| 8192 | 0.3183118357 | 0.3183059835 | 3.454196 | 3.454260 | 0.506142 | 0.506152 | 1.16 |
| 16384 | 3.8199669101 | 3.591786662 | 2.302662 | 2.448946 | 0.377328 | 0.401299 | 1.25 |
| 32768 | 22.2868187918 | 20.36935094 | 3.157415 | 3.454639 | 0.506756 | 0.554459 | 1.32 |

N=32768 的 API 比 profile 多 1.91746785 秒（API 的约 8.60%），profile 吞吐相对 API 虚高 9.4135%。这里的“虚高”只针对把 profile 当全 API 的解释。现有阶段 raw 数据并不能将差额全部独立分解成 malloc/free、page fault 或 teardown 某一种原因；具体实现边界可以证明有未包含于 profile 的前后工作，但不能仅凭时间差给出其全部归因。

性能比未复现与精度未复现也要分开。N=32768 最新完整 oneMKL 精度：

| 模式 | full-matrix eF | eF / 论文 Table 4 | e_scaled | e_scaled / 论文 |
|---|---:|---:|---:|---:|
| FP32 p6 | 4.58399427885e-7 | 1.000872 | 3.72938120065e-8 | 0.994502 |
| FP64 p6 | 8.49511445063e-8 | 5.701419 | 4.22845951426e-9 | 6.218323 |
| FP64 p10 | 3.62332301533e-10 | 11.148686 | 1.71613124772e-11 | 11.595481 |
| FP64 p15 | 1.52527466975e-12 | 21.914866 | 6.74715994875e-14 | 22.194605 |
| FP64 p21 | 6.53306012067e-15 | 4.474699 | 2.93264023207e-16 | 1.519503 |

这说明 FP32 Table 4 精度可以接近而性能不接近；FP64 的误差差异也不能用时间单位解释。这里不以“同 seed”声称与作者使用了同一矩阵，因为作者没有公开 RNG/seed。

## 5. 均值、中位数、漂移与顺序

### 5.1 同冻结 V3 在不同时间段显著变化

主表与 scaling 的 64-thread 点均由同一个 `run.sh` 使用同库、同 driver、同分布和 seed，代码没有换成新优化：

| N | 主表 API 均值 s | scaling t64 API 均值 s | 主表/scaling 时间比 | 主表 useful TFLOP/s | scaling useful TFLOP/s |
|---:|---:|---:|---:|---:|---:|
| 1024 | 0.0008878518 | 0.0007268411 | 1.2215 | 2.4187 | 2.9545 |
| 4096 | 0.0411513942 | 0.0219134828 | 1.8779 | 3.3398 | 6.2719 |
| 16384 | 3.8199669101 | 1.5731077619 | 2.4283 | 2.3027 | 5.5915 |

N=16384 主表十个 API 样本保留了 10.488156708s 和 7.647869994s，其他八个约 2.44–2.58s；population CV 约 70.68%。稍后的 scaling 样本为 1.497746025–1.667923546s，CV 约 3.07%。这不只是“删除两个离群值”可以解释，因为剩余主表典型值仍比 scaling 慢。不得选择性删样本制造漂亮均值；也不得将两批之间的 2.43 倍直接称作代码加速。

频率、其他租户、缓存、OpenMP 等待策略、first touch/NUMA 等都可能有关，但本审查没有硬件计数器数据给出因果份额。run 自有 flock 只序列化合作进程，不排除机器上的其他任务。

### 5.2 最新实际主代码的 paired 结果

matched `driver.cpp:48-58` 的计时只包住 API；父进程通讯、JSON、20ms 暂停不在这个秒数里。`run_matched_runtime.py:100-103` 移除 OMP_WAIT_POLICY/GOMP_SPINCOUNT；`175-177` 在每次调用回复后暂停 20ms。另一版本 `run_matched.py:95-98` 则固定 PASSIVE/GOMP_SPINCOUNT=0，二者不能混成同一运行条件。实际主代码验证 runner `run_validation.py:45-61` 清楚区分 runtime-default matched 与 passive oneMKL 补测。

最新原始 JSON 重算：

| FP32 N | 样本对数 | V3 API 均值 ms | candidate API 均值 ms | 均值时间比 cand/ctrl | 逐对时间比算术均值 | 逐对时间比中位数 |
|---:|---:|---:|---:|---:|---:|---:|
| 1024 | 7 | 1.212434714 | 1.108831143 | 0.914549 | 0.934123 | 0.909411 |
| 4096 | 11 | 34.262336636 | 32.858250455 | 0.959020 | 0.957853 | 0.948055 |
| 8192 | 11 | 273.243502273 | 252.521499545 | 0.924163 | 0.924355 | 0.925439 |
| 16384 | 5 | 4107.1647072 | 2484.3104534 | 0.604872 | 0.842802 | 1.000141 |

4096/8192 的均值减少 4.0980% / 7.5837%，吻合现有最终报告。16384 不在 adopted FP32 compact guard 内，逐对比的中位数接近 1，但运行时间均值比看似快 39.5%；这条数据适合展示共享主机不稳定，不能用于声称这个域被代码加速。

`mean(candidate/control)`、`median(candidate/control)`、`mean(candidate)/mean(control)` 三者本来就不同。论文主运行时间应坚持第三种的两个算术时间均值来形成比值；逐对统计用于描述配对分布，不能无说明地替换论文协议。每次调用的 TFLOP/s 再平均，也不等于 `work/mean(time)`。

### 5.3 最新 V4 TFLOPS 的独立展开

N=8192 最新 matched candidate：API mean `0.252521499545s`，compute+reconstruct mean `0.234934993909s`。

- `2N³/API/1e12 = 4.354130756 TFLOP/s`，是常规 useful GEMM 吞吐。
- `6*2N³/API/1e12 = 26.124784537 TOP/s`，是完整 API 的分量工作等价值。
- `6*2N³/compute_reconstruct/1e12 = 28.080404953 TOP/s`，是阶段的分量工作等价值。

其中 26.1248 与 `docs/8454H_V4_ROUND_RESULTS.md:54` 的约 **26.126** 存在小舍入/抄录差异（约 0.0047%），4.354 与 28.080 正确；这不是单位量级错误。151.738 热小工作集混合校准与 28.080 的比约 18.5%，只是一组不同条件数值的距离，不能当真实硬件利用率或已证明的 5.4 倍可兑现收益。

独立 oneMKL CSV 的 FP32 N4096：API mean `0.016787286s`、MKL mean `0.0187975343333s`，useful `8.187085957 TFLOP/s`，比值 `1.119748263`；N8192：API mean `0.223053811667s`、MKL mean `0.139605989333s`，useful `4.929355923 TFLOP/s`，比值 `0.625884796`。它们与上面的 matched 时间不是同一批条件，不能用 8.187 对比 4.183 宣称某库快近两倍。

## 6. 输入、线程与 correctness gate

**相同 seed 不保证跨 harness 相同 A/B。** `bench/benchmark.cpp:112-121,129-138` 交错生成 A0、B0、A1、B1；论文 campaign 的快照同样如此（`source/benchmark.cpp:61-67`）。但 matched `driver.cpp:33-36`、`optimization_benchmark.cpp:169-174` 和 raw BF16 `raw_bf16.cpp:124-129` 是先填完整 A 再填完整 B。raw 还将输入 RNE 到 BF16。因此，“seed/分布一样”只能支持配置标签一样，不能支持不同 harness 精确同输入；matched 同一对的输入 FNV 确认则有效。raw BF16 headroom 也是不同精度、不同输入表示的独立 routine，不能认为它替代了全部产品的原矩阵工作。

**线程配置与实际线程放置的证据强弱不同。** 普通 driver 只设置 OMP/MKL 数量和 dynamic；V3 配置请求 64 已记录，但不像 matched `driver.cpp:71-103` 显式报告实际 OpenMP team/CPU。matched `run_matched.py:40-46` 校验每个 worker 正好占一个 CPU 0–63。这证明其 ready 阶段线程团队，不直接证明 oneMKL 每次内部 microkernel 都恰好运行全部 64 线程。MKL_VERBOSE 的 advertised AMX 能力也不证明每个 routine 实际用了哪条指令。

定点源码补查还发现内部实际 team 会按工作量缩小：`src/gemm.cpp:464-482` 与默认 `MIN_COMPUTE_WORK=8` 下，N256 的 64 个 32×32 输出任务使用 nt=8，N512 的 256 个任务使用 nt=32；准备阶段约分别 4、16 线程。应分别记录“外层配置线程数、内部 team 大小、有效输出任务数”。论文也不能把 64 配置线程直接理解成 64 个 worker 都有计算工作：按其 256×256 输出块，N256/N512/N1024 本来仅有 1/4/16 个任务。这里证明实现机制不同，不单凭 team 大小宣布结果不公平或无效。详细源码/论文对齐另见 `IMPLEMENTATION_SPOT_REVIEW.md`。

**checksum 保证不能过度解读。**

- `bench/benchmark.cpp:413-435` 计算完整 oneMKL eF/e_scaled 并记录 checksum，最后写 ok；没有论文误差门槛。`compare_mkl:190-207` 遍历完整 C，分母是完整 `abs(A)@abs(B)`；高精度对 N>256 只有 512 点（`213-215`）。两个参考范围不可互换。
- `compare_mkl:205` 在 denominator=0 时把 absolute error 混入 scaled max，没有论文 §7.3 所要求的单独零分母 absolute-error 报告/计数。这是确定的边界指标协议缺口；uniform 大矩阵本次分母非零，未见其影响 headline 数据。
- `tools/analyze_v3_paper_alignment.py:145-155,522,534` 只要求误差非负有限；明确 `accuracy_threshold=None`。因此 66/66 valid 是记录完整/配置一致，不等于达到 Table 4 误差。
- `bench/optimization_benchmark.cpp:146-149` 只在计时后求 scalar checksum，未与 expected/reference 比较。它是运行时间诊断，不是独立数值通过证明。
- raw BF16 `smoke:101-116` 验证 2×2 BF16/SGEMM；大矩阵最后只写 checksum（`148-160`）。没有完整大矩阵的独立精度 gate；这不等于已发现大矩阵计算错误。
- matched `run_matched.py:148-150,171-186` 核对输入哈希、完整 C 字节数及 SHA，最新实际主代码八配置全部 byte_exact_match=true。只比较最终 C；每条 timing reply 没有独立输出 SHA。它证明最后结果与 V3 一致，不证明 V3 等同数学精确 GEMM或论文精度。
- `tools/roofline_kernels.cpp:164-205,230-233` 检查每 worker 一个代表元素的精确值/finite 并 gate；比单写 checksum 更强，但不是每个输出元素的完整验证。
- `tools/platform_baseline.cpp:232-233` 的 AMX `ok` 来自 OpenMP single 选中 worker 的局部 `allowed`，不是全 worker 的失败归约；报错文字却说“at least one worker”。这是**确定的诊断门逻辑缺口**。此外该校准保存 checksum 而不核对 expected。未看到原始数据中的权限失败或误计吞吐证据，不能借此否定已算对的 TDP 指令计数。

**checkpoint 续跑存在身份隔离缺口，但没有证据证明本批被污染。** `bench/benchmark.cpp:303-329` 验证固定 `kCheckpointSourceId`、维度、分布、seed、budget、reps 和向量长度，却不按当前静态库、源码、编译选项或运行环境的 hash 匹配。生产 driver 仍沿用 V3 命名的固定 source_id（`143`）；如果对改过的库/环境复用同一 checkpoint 路径并加 `--resume`，可能把旧样本和新样本混起来，甚至完整旧向量被直接复用。干净新目录的测量不受此风险；最新 V3 campaign 另用了独立 source_id 和 hash/provenance/manifest 核对，因此不能反推现存 66 CSV 已混样。checkpoint 写盘位于计时结束之后（`389-396`），不直接计入那次 API，但文件 I/O 可影响下一次运行的缓存、调度及等待状态；该影响尚未单独测量。

## 7. 历史报告入口与确定的小错误

1. `docs/8454H_FINAL_PERFORMANCE_REPORT.md:3` 已有 Historical V2 标签，但仍写 “Current production is V3”。相对于最新 V4 adopted 报告，这是过期的当前状态表述；`docs/8454H_V4_PACKED_LAYOUT_RESULTS.md:62` 同样保留 “Current V3 remains the production release”。应作为历史当时状态，不能当今日入口。
2. `docs/REPRODUCTION_RESULTS.md:3` 明确是 Gold 6430 历史报告，不能以其完整表格/标题冒充 8454H 当前结果。`docs/8454H_CURRENT_BASELINE.md` 与 `V4_CURRENT_MAIN_VALIDATION.md` 是较新的整理入口，其 current 是 2026-10-14 测量时段。当前 dirty src 已有主代理的 token/新构建 archive 一致证据，因此不因 dirty 状态否定算法身份；仍应区分测量日期。
3. `docs/8454H_V4_ROUND_RESULTS.md:54` 的 `26.126` 用其 raw matched 原始数据重算为 `26.124784537`，仅为约 0.0047% 数值文字差异。不是 TFLOPS 大错。
4. `tools/analyze_v3_paper_alignment.py:438-457` 将 raw CSV 的 GFLOP_s/TFLOP_s 原样带入报告；`check_case` 验证 raw 时间均值但不重新核对两列 throughput。**当前八行独立重算全部正确**，因此这是分析器可检查项不足，而不是现存结果错误。

## 8. 尚不能从这些数据推出什么

- 不能因 raw BF16 约 39 TFLOP/s、热 AMX 约 161 TFLOP/s 就说任一 TFLOPS 算错；输入遍历、地址跨度、重建、工作集和时段不同。
- 不能用缺少 PMU 的结果确证 TLB/L2/DRAM miss 是主要瓶颈，也不能用 governor 名称证明每次运行固定在哪个频率。
- 不能用 N16384 均值的巨大差异证明优化成功，也不能删掉长样本后声称满足论文。
- 不能以 oneMKL runtime 显示支持 AMX，就断言 SGEMM、DGEMM 或所有 BF16 调用执行了相同 ISA kernel。
- 不能以 checksum、V3 byte equivalence、CTest、66/66 status ok 代替论文的精度和完整 API 性能结论。
- 当前确证的测量问题是 profile/API 标签使用风险、跨时段/等待策略混用风险、同 seed 跨 harness 输入不同、历史 current 标签过期，以及少量诊断/分析器检查不足；没有证据证明 2MNK/秒的主公式错误。

主代理在本轮已另外提供 `docs/audit/evidence/n256_current.csv` 与 `n4096_current.csv`（各十次）及新构建身份。其 N4096 FP32 完整 API mean `0.0350985518s` 对应约 `3.915801 TFLOP/s`，MKL mean `0.02507974s`；该新时段同样非独占，不能与旧的约 8 TFLOP/s 数据拼接为同批结果。性能重跑由主代理统一安排；本审查未额外抢占硬件。后续要进一步独立审查 MKL 分布，仍需在 driver 保留其逐次 raw wall。
