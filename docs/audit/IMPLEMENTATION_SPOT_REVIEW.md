# 论文与当前实现的定点监察

审查日期：2026-10-15。按主代理指定，只读检查 `src/gemm.cpp` 的核心调度/重建、`src/kernels.S` 的两个 AMX 内核、`src/preprocess.hpp` 的 FP64 分解公式段，以及必要的 tuning/runtime 接口。没有全库泛读，没有修改实现，没有额外运行负载。论文依据为本地 `third_party/papers/2609.04663v1.pdf`，重点 §4.3、§5.2、§6.1–6.3、§7、§8。

**没有发现本次定点范围内可以确定的新数值计算 bug。** 可以确定当前实现和论文原型的执行组织并不逐项相同；FP32 的 K32/产品嵌套层次有未披露歧义，不能把歧义判成已证实错误。FP64 literal rho=45 与公式一致，并不等于已解释论文 Table 4 的误差差距。主代理新测 N256 五模式仍重复出现历史 FP64 误差量级，这是单独需要解释的事实。

## 1. 实现身份

当前 `src/gemm.cpp` 有用户未提交注释修改。源文件与 adopted 快照的字节 SHA 不同，不足以推断语义变化。主代理已核对八个关键文件：去注释、空白、escaped newline 并处理相邻字符串字面量拼接后 token 一致；新构建 `/tmp/ozamx-audit-20261015-build/libozamx.a` 的 SHA-256 为 `7adcc98996d5a88aa21f74038a42710a28496cf601f2127c016b8e8687801b68`，与已验证 V4 库逐字节相同。因此以下结论针对该实现组织；不以 dirty 状态自行推断逻辑换了。

## 2. 输出块和 operand staging：确定不同

论文 §6.1 Eq.(18)（PDF p.13）给出 `(BM,BN,BK,TM,TN)=(256,256,256,32,32)`，并称 FP32/FP64 使用相同外部结构。§6.2/§6.3（pp.14–17）明确：预先 split/pack 后，计算循环将需要的 256×256 分量面板复制到 block-local A/B buffer，再由 32×32 微块复用。

当前 `src/gemm.cpp:26-27` 的 BM/BN/BK 常量确实为 256，但**packed 面板尺寸不等于实际输出任务尺寸**。实际输出任务由 `cb/cbn` 决定（`464-475`），默认 `CACHE_BLOCK=128`（`src/tuning.hpp:8-9`、`CMakeLists.txt:7`）：

| 域 | 当前每个输出任务有效几何 | 选路证据 |
|---|---|---|
| `min(M,N)<1024`，FP32/FP64 | 32×32 | `gemm.cpp:464-471` |
| `1024<=min(M,N)<4096`，FP32/FP64 | 128×128 | `559-581` 选 non-Wide；cb/cbn 为 CACHE_BLOCK |
| FP32，M/N 均在 4096–8192、K 在 4096–8192 且默认 cache block | 256×256，另有行 padding | `562-565`，CompactWide |
| 其他大 FP32，`min(M,N)>=4096` | 128×512，另有行 padding | `566`、`466-475` |
| 大 FP64 p6/p10 | 128×512，另有行 padding | `574-577`，depth<=4 |
| 大 FP64 p15/p21 | 128×256，另有行 padding | `574-577`，depth>=5 |

当前每微块直接以 `apanel_index/bpanel_index` 算全局 packed buffer 地址，再传给汇编（`125-146`）；production 路径没有论文所说的每个 BK 先复制 A/B 到 block-local operand buffer。`149-184` 的兼容复制路径用于独立诊断，不是当前 production 的 local staging。

因此不能用“代码 BM/BN 常量是 256”声称外层调度已完全复现论文，也不能用 packing layout 对齐代替 operand staging 对齐。当前组织可能改善或恶化某尺寸的缓存复用，方向需要匹配测量；**不因不同就宣布数值错误或必然变慢**。同一输出元素的 BK 顺序和产品顺序可在改块几何后保留。

## 3. 配置线程、内部 team、有效任务要分开

论文配置 64 个 OpenMP 线程，外层 collapsed 静态循环按 256×256 输出块并行。按其组织，N256/N512/N1024 分别只有 1/4/16 个输出任务；“64 线程”并不表示 64 个 worker 都有 compute 工作。

当前外层 `OMP_NUM_THREADS=64` 也不保证每阶段内部 team64：

- `requested_threads()` 使用 `omp_get_max_threads()`；若嵌套调用已在 OpenMP parallel 内则返回 1（`gemm.cpp:49-54`）。
- 准备阶段 `nt=min(requested,ceil(max(MK,KN)/PREP_GRAIN))`，PREP_GRAIN 默认 16384（`58-60`）。
- compute 在 small 域用 `granularity=MIN_COMPUTE_WORK=8`，`nt=min(requested,ceil(work/8))`（`480-482`）；其他域粒度 1。
- `team_size` 确为 max(1,min(requested,work))（`preprocess.hpp:192-195`）。

| 方阵 N | 当前输出任务数 | 默认 requested64 时 compute team | 准备 team 的外层上限 | 论文 256×256 输出任务数 |
|---:|---:|---:|---:|---:|
| 256 | 64 | 8 | 4 | 1 |
| 512 | 256 | 32 | 16 | 4 |
| 1024 | 64 | 64 | 64 | 16 |

这说明小矩阵的调度、线程启动成本与工作分配存在机制差异，不能只引用 CSV 的 threads=64 就说逐阶段完全对齐。它也**不单独证明比较不公平或结果无效**；论文自己小矩阵有效任务数也远低于 64。matched driver 的 ready-team64/CPU 检查证明启动时那个团队，不是所有内部阶段的实测 team。

## 4. FP32 六项产品与 K32：代码清楚，作者嵌套层次未清楚

代码的确定行为：

1. 每个 BK 的一个 32×32 微块进入 `run_fp32_micro`（`gemm.cpp:505-518`），通常 steps=8；BK 固定 256，TK 固定 32。
2. 汇编 `kernels.S:60-63` 清零四个 FP32 accumulator tile。
3. `.Lsix_k` 的每个 K32 步进，按 `11,10,20,00,01,02` 顺序做六项（`65-91`）。每项四条 `tdpbf16ps`，总计每 K32 24 条 TDP、14 条输入 tile load。
4. A/B 指针各前进 2048 字节后再循环 K32（`92-99`）；整个 BK 后只 store 四个输出 tile（`100`）。随后以 FP32 加入 private block（`gemm.cpp:518`）。

论文 Eq.(19) 的六项物理顺序与此一致；§6.3 也要求每 BK 清零、六项共享 AMX FP32 accumulator、BK 后 store/reconstruct。但论文没有展示 K32 微循环与 product 循环的明确双层伪代码。其 Algorithm 1 是未展开 blocking 的数学概要；不能直接据此强行认定作者真实内核一定“product 外、K 内”。

这两种结构分别是 `K32_0:六项; K32_1:六项; ...` 和 `产品11:所有K32; 产品10:所有K32; ...`。它们在实数算术下相同，一般浮点逐位结果不相同；因此不能无证据声称逐位复现作者执行。当前局部 Table 4 FP32 eF 接近论文是经验一致证据，不能单凭它证明作者嵌套顺序。应记录为**待作者源码/伪代码澄清的歧义**，没有充分证据将当前顺序定性为 bug。

## 5. FP64 Batch2：与 immediate 时序不同，保留每元素加法顺序

论文 §6.3（PDF p.16）明确要求每个 product 的 AMX FP32 结果 store 后立即 widen 为 FP64 并累加；禁止多个 component product 先合并在同一个 FP32 accumulator。

当前 non-Wide 路径 Batch1 符合该 immediate 组织：对角线优先/ai 次序，每 product 调用 AMX、store、`accumulate64`（`gemm.cpp:281-289`）。Wide 路径编译为 Batch2（`520-521`）：

- 每个 `run_fp64_product` 独立进入 `ozamx_bf16_product`；该函数独立 tilezero、K32 循环、store（`kernels.S:130-157`）。没有两个 product 共享一个未清零 FP32 累加器。
- 两个独立 FP32 结果先存到 `scratch[2][1024]`，然后 flush（`gemm.cpp:296-310`）。因此第一个结果的 widen/add 延后到了第二个 product 完成之后，严格时序不同于论文 “immediately”。
- flush 对每一组元素依次做 q0 转 double、加 double，再 q1 转 double、加 double（`245-271`），保持 diagonal-major/ai-major 的逐元素加法次序；短尾也按同序处理（`313-322`）。

对支持的有限输入、相同 AMX product 和舍入环境，这种不同元素间的重排没有改变每个标量输出的 FP64 加法序列。它也没有在 FP32 中合并两个产品。故这是**确定的执行/性能组织差异，而非已发现精度错误**。不能为了迎合 immediate 文字而声称此 Batch2 必定造成 Table 4 的 5–22 倍误差差距；没有这种证据。

## 6. 事务保护与配置的计时：确定的额外工作

论文描述完成一个 private output block 后写回 C。当前还额外分配完整 M×N 的 private `result`，各块先写 result，所有线程检查通过后再统一 parallel copy 到 caller C（`gemm.cpp:459,540-551`）。这是为别名及异常时 C 不变提供的事务保证；论文没有描述这层全矩阵提交。

- 除 private block 外，额外 result 容量为 `sizeof(T)*M*N`。方阵 N32768：FP32 4 GiB、FP64 8 GiB。
- 对比直接 block→caller C，额外 result→C 提交的逻辑读写为 `2*sizeof(T)*M*N`，N32768 分别约 8 GiB、16 GiB。这里是指令逻辑流量，不能冒称已测 DRAM traffic。
- compute timer 从 t2 开始，随后 result 分配、OpenMP 团队、`load_config()`、AMX/reconstruct、非有限检查、block→result、result→C 全部在内（`457-554`）。
- t3/total 在局部变量离开作用域前取值；workspace/result 等对象析构、返回与外层 dispatch 不全在内部 profile 内，外层 API wall 才包住。不能将 profile/API 差值全归给同一种 free 或 fault。
- 每 worker `_tile_loadconfig` 在内部 compute 内（`494`），`_tile_release` 也在内（`544`）。论文 §6.3 明说 configuration 在 timed compute region 前加载；此项存在明确边界差异。
- 当前 runtime 先在 API wrapper 请求/检查进程 AMX permission（`runtime.cpp:73-76,125-148`），再进入 native；当前 compute worker 不逐 worker 调 permission syscall。不要沿用旧报告把当前 worker configuration 和权限查询说成同一件事。

非有限检查也有实际成本：FP32 每次累加检查（`gemm.cpp:212-220`）；FP64 短 K 路径检查输入微块和逐次 double sum（`224-240,259-267`）；长 K `Late64` 把最终 private block 扫描合并到一次（`535-539`）。这类检查维护额外支持域/异常语义，论文没有逐条列出；不能在未计数和未隔离测量时宣称它们就是主要性能根因。

## 7. FP64 公式段与低预算六轮：与 literal 方法的关系

论文 Eq.(13)–(14)（PDF p.10）的核心是：残量全局最大值确定 `v=ceil(log2(max(abs(R))))`，`sigma=2^(v+rho)`，rho=45；先按 double 的 add/sub 做投影，存成 BF16，再从 double residual 减去该 BF16 的精确嵌入，重复六轮。

当前普通分片：

- `preprocess.hpp:452-455` 用 frexp 正确实现正数 ceil_log2，包括恰为 2 的幂时返回 e−1。
- `509-544` 六轮，对整个输入残量收集 global_max，再用 `ldexp(1.0,ceil_log2(global_max)+45)`。不是随意用另一个 rho，也没有把 sigma 取成每元素独立尺度。
- SIMD `560-562` 保留先加后减两个 double 操作；scalar `606,622` 也是 `(r+sigma)-sigma`。BF16 RNE 使用 `0x7fff + top_bit_lsb`（`567-571`）；再由 stored BF16 的精确值拓宽并更新 double residual（`589-593`、`614-615`）。
- 直接 packed residual 路径使用相同六轮/45 公式（`730-735`）、相同 residual subtraction（`783-787`），并把 next_max 收集合并到更新 pass（`788-789,834-846`）；没有因此跳过后续轮。

`budget_depth()` 把 p6/p10/p15/p21 映射到 3/4/5/6（`gemm.cpp:379-388`）。这些数字决定保留的平面数和产品对角线深度，**不把分解循环从六轮改成三/四/五轮**：`split_fp64` 始终 `s<6`（`509`），只在 `s<stored_slices` 时写入（`585-587,612-613`）；直接 packed 同理（`730,779-781`）。所以“低预算只存 depth 片”属确定事实，“低预算只做 depth 轮”不成立。

计算只访问 `ai+bi<depth`，因此丢掉永远不会读取的更低片平面并不改变所选产品数值。但论文所述固定六片全 precompute/pack 与当前只长期保存所需片，在空间/packing 成本上并非完全同一实现。不能声称 p6 持有六片的实际 packed payload，不能用 product budget 6/10/15/21 直接作 slice count。

主代理新 `docs/audit/evidence/n256_current.csv` 的 eF_mkl：p6 `8.49180085458e-8`、p10 `3.61535002948e-10`、p15 `1.52636844589e-12`、p21 `6.38727680118e-15`；与旧 literal rho45 历史值一致，差距不来自本次注释修改。定点读没有发现 rho 被替换、漏 widen、错产品集合或 FP32 合并产品这一类确定错误。公式一致仍不足以证明作者原型按同样方式执行，也不足以解决论文错误表的差异。

## 8. 可成立的结论边界

| 项目 | 证据判定 |
|---|---|
| 当前实际输出块普遍不同于论文 256×256 | 确定实现组织差异 |
| 当前不做论文描述的 block-local operand staging copy | 确定实现组织差异 |
| 当前内部 team 随规模缩小 | 确定机制；不等于论文 worker 全部有用或比较无效 |
| FP32 每 K32 跑六项 | 当前代码确定；作者是否产品外/K内仍有歧义 |
| FP64 Wide Batch2 延迟第一项 widen | 确定时序差异；每元素产品/FP64加法顺序保留 |
| 全 M×N 事务结果、提交和 checks | 确定额外工作；性能份额未单独证明 |
| worker config 处于 compute timer 内 | 确定边界差异 |
| rho45、六轮、budget三角集合 | literal 公式符合定点源码；不保证论文精度已复现 |
| 新的确定数值 bug | 本次限定范围未发现 |

性能数据/TFLOPS 指标、计时及 checksum gate 的完整监察见 `BENCHMARK_REVIEW.md`。需要继续获得的证据是作者明确的 K32/product 嵌套伪代码与分解/重建参考输出，或者在严格记录组织差异的前提下做匹配配置实验；本审查没有擅自修改实现去“修成”某个未经证实的解释。
