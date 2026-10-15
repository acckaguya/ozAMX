# 8454H kernel tuning search log

本搜索只调整不改变数学路径的编译期调度选项。每个候选仍运行现有 CTest 正确性门，再使用固定 seed、固定输入和同一计时驱动测量。实际搜索现已按下述协议完成，结果和定量结论见 [8454H_SEARCH_RESULTS.md](8454H_SEARCH_RESULTS.md)。

## 假设与验收

| 变量 | 搜索假设 | 接受信号 | 拒绝信号 |
|---|---|---|---|
| `OZAMX_CACHE_BLOCK` | 64/128/256 accumulator block 控制寄存器/栈工作集与输出复用；32 是小矩阵特例及边界值 | 总调用 wall 中 compute 与 C 写回稳定下降，split/pack不回退过多 | 候选只赢单一尺寸，或增大块导致栈流量/尾块开销抵消收益 |
| `OZAMX_PREP_GRAIN` | 16K/32K/64K 改变预处理每线程工作量，影响小矩阵启动成本和大矩阵并行度 | FP32/FP64 split+pack全样本的中位数及总wall改善 | 线程过多增加 fork/sync，或粗粒度导致核数不足 |
| `OZAMX_MIN_COMPUTE_WORK` | 1/4/8/16 的小工作量门槛控制compute team启动 | 256/1024 小形状缩短调用wall且大尺寸无回退 | 小尺寸变快但造成有效并行度损失，或只改变计时噪声 |
| `OZAMX_TILELOAD_HINT` | T1 与普通 tile load 的缓存提示可能改变 panel 的 L1/L2 留存 | 多尺寸与 precision 上稳定收益，且未增加 cache miss/fault proxy | 收益仅单个尺寸、噪声区间交叠或整体wall恶化 |
| `OZAMX_LOAD_SCHEDULE` | interleaved 与先加载后更新的指令排序在 tile-load latency 覆盖和 AMX 发射间存在权衡 | FP64 component loop compute wall改善且 FP32 无显著倒退 | load burst 降低 tile 算术利用率或额外工作集伤害尾块 |
| `OZAMX_LOOP_ORDER` | K-block 外层/微块外层在保留每元素 K 累加顺序时改变 panel 重用和并行任务粒度 | 包含 4K/8K 的总wall改善且误差门逐项通过 | cache 重用收益被重复加载或可并行工作减少抵消 |
| `OZAMX_MN_ORDER` | row/column task mapping 影响 A/B panel 重用、NUMA first touch 和 C 写回连续性 | 多线程且双 NUMA 节点样本稳定收益 | cache locality 改善但写回/NUMA远端流量或负载平衡变差 |
| workspace cache cap | 8192 shape 的 1 GiB 默认和 4 GiB 对照，验证更大 retained workspace 是否减少跨调用分配/触页成本 | 8K 的 split/pack/callwall多轮中位数下降，minor faults也相符 | 只减少分配次数但提高内存压力、page faults或总wall |

这些是待验证假设，不是实现结果。平台 `perf_event_paranoid=4`，当前 cycles 事件 `perf_event_open` 返回 `EACCES`（errno 13）；搜索不尝试改主机设置，也不依赖 perf events。driver 增加了 `wall_s`、minor/major faults、voluntary/involuntary switches、user/system CPU time 和 `max_rss_kib`。runner 优先按 `wall_s` 汇总和排序，并自动保留新增 numeric fields 的中位数。`max_rss_kib` 是进程累计 high-water mark，不是每次 GEMM 的独立峰值，只作为背景数据保留。

## 协议

`bench/8454h/search/run_search.py` 由阶段控制；宏与计时driver冻结后按下列顺序运行：

```sh
python3 bench/8454h/search/run_search.py scout --resume
python3 bench/8454h/search/run_search.py refine --resume
python3 bench/8454h/search/run_search.py final --resume
python3 bench/8454h/search/run_search.py holdout --resume
python3 bench/8454h/search/run_search.py pool --resume
```

首轮16个候选覆盖默认值、全部单变量代表点与3个交互组合。初筛使用 N=1024/4096、FP32 和 FP64 p6/p21、固定输入、1 warmup+3 reps。每个候选依次执行CTest和100-case逐位旧版对照 gate；冻结旧版 gate binary 在同一 study 内只构建一次。`refine` 从初筛中选择表现最好的中心点，根据观察到的单变量效应自动生成6个邻近单变量点和6个两轴交叉点，并保留 default 作为对照。候选结果按所有共同 configuration 的 true-call wall 中位数计算几何平均 speedup，不以单点最快作为胜者。

`final` 将 default 与 refine 前两名夹跑：每个 pass 顺序执行 default/candidate/candidate，3 passes、每配置1 warmup+7 reps，覆盖 N=256/1024/4096/8192、FP32 和 FP64 p6/p10/p15/p21。阶段报告同时保留所有配置的 mean/median/SD/min/max、split/pack/compute 与 true-call wall。`holdout` 对 default 和暂定赢家在 N=512/2048 做同样多轮确认。`pool` 在 N=8192 分别以 `OZAMX_WORKSPACE_CACHE_BYTES=1GiB` 和 `4GiB` 独立 rank，运行环境差异写入 job fingerprint。

每个工作单元从编译、CTest、固定输入 benchmark、CSV/JSON 分析到 ledger append 都持有 `/tmp/ozamx-perf.lock`；运行时固定 CPU 0–63、64 OpenMP threads、`OMP_PLACES=cores`、`OMP_PROC_BIND=close`、`OMP_DYNAMIC=FALSE`。构建目录按 runner/source/config/stage/pass 隔离在 `/tmp/ozamx-search/`。CSV 与 metrics JSON 位于 `bench/8454h/search/runs/`；`ledger.jsonl` 追加 started/completed/failed 记录并 fsync。恢复仅在 runner版本、完整源码指纹、参数指纹、完成状态和 raw CSV SHA 全匹配时跳过任务。更改宏、测试、driver、runner 或候选表都会生成新 study fingerprint，不会复用旧结果。

默认 first-touch workspace pool 当前在 GEMM 调用结束时归还到调用线程缓存。最终测量需确认 allocator/cache 的实际收益与 true-call wall 一致；不能只按 compute profile 宣称改进。所有候选保留原始逐次 CSV，报告同时展示完整维度，避免只公布获胜的尺寸或阶段。

## 初轮候选来源

当前参数表在 `bench/8454h/search/variants.json`。默认配置来自生产编译宏：cache block 128、prep grain 32768、minimum compute work 8，load hint/schedule/order 与 M/N mapping 均为 0。单变量候选覆盖 cache 32/64/256、prep 16K/64K、minimum work 1/4/16，以及 T1、grouped-load、microtile loop、column-major M/N order；交互候选覆盖 T1+grouped-load、cache64+prep16K、microtile+column mapping。
