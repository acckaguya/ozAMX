# 全新独立实验结果复核

日期：2026-10-16。只读复核 `docs/audit/independent/run_20261016/` 的原始 CSV、挑战二进制、负控、stdout/stderr 和 provenance；没有运行任何 GEMM 或性能基准。另对新写的独立 FP64 数学附件作限定源码审查。本文的统计全部由独立 Python 重新分组计算，不从旧报告复制结果，也不把原有 CTest/benchmark 当作数值 truth。

## 1. 本批能够确认的结论

**新 harness 的计时数据不支持“TFLOPS 因单位算错而虚高”的怀疑。** 198 次实际例程调用记录完整，其中 18 次预热、180 次正式计时；两个墙钟数值一致到本批所列精度。全部输入不变性/finite/数值检查通过；dyadic 每轮三个独立例程的完整输出 hash 还完全相同。负控不只是日志称失败：本次用保存的挑战和重新生成的整数输入，独立重算了两种错误的确切检出数，与日志一致。

在本次条件下，N4096 uniform 的完整 ozAMX FP32 调用平均为 **20.559180714 ms，常规 useful 吞吐 6.685040391 TFLOP/s**；SGEMM 为 21.909474675 ms、6.273037374 TFLOP/s；raw BF16 为 7.309225202 ms、18.803491435 TFLOP/s。ozAMX 相对 SGEMM 的均值时间比为 1.065678 倍速度比。dyadic 同尺寸的速度比却为 0.945105，故不能把一个 family 的结论泛化成稳定普遍优势。

这证明的是新受控条件下完整 API 调用、输入/输出新鲜性和所采用验证的结果；**没有证明论文性能已复现，也没有证明一般 FP32 全矩阵逐元素正确**。另一个全新FP64数学附件已经在N64三个seed上与独立binary128参照核验，支持literal分片/产品截断自身存在相应误差量级，仍不能宣称论文精度差距已完全解释或解决。

## 2. 运行条件与身份

provenance 记录开始于 `2026-10-16T00:02:11.363054+00:00`。双路 Xeon 8454H，共享机器，CPU affinity 0–63；OMP/MKL 请求64、close/core binding、dynamic关闭、GNU MKL；明确设置 `OMP_WAIT_POLICY=PASSIVE`、`GOMP_SPINCOUNT=0`，workspace cache 2 GiB。使用 GCC 11.4、`-O3 -march=sapphirerapids -ffp-contract=off -fopenmp`。与旧 runtime-default matched campaign 的等待条件不同。

本批源码 SHA 为 `dcee461b4f64fa7092fe630c711b9d60d7af2fdb6ec2cec16ad6e982aa7cae6d`，独立程序 SHA 为 `825ffc90a2eee2761b3002a8ac75d6a897e39815af50c928b9246893b3f69bd6`，ozAMX 静态库为 `7adcc98996d5a88aa21f74038a42710a28496cf601f2127c016b8e8687801b68`，oneMKL runtime 为 `b2ff0e31d7cd18c91813d8f6500f37665597d89de22649d90687aa6bf7bd2c0f`。本次分别重算四个实际文件 hash，全部与 provenance 一致。

结果 CSV SHA：`7c08cb50834c33d40e3f13e804a2b02b8efbe82d2b341d059067a87019871ef7`；挑战文件 SHA：`44c896dedeb57ac4be7c8dfdb4ddde36b54a34c45574ea830e9ba5f3164cfbb0`。stdout 报告 ready_team=64、long_double_digits=64、六个 family/N 完成及 validation=pass；stderr 为空，外部进程 exit status=0。ready team 不等于库内部每阶段实际使用64线程。

## 3. 逐次覆盖与校验关系

独立核查了 CSV 的全部198行，而不是仅检查最终 pass 文本：

- 18组 `family/N/routine` 各有正式 round0–9，另各有一个 round=-1 的 warmup；没有重复/缺失正式 round。
- 每个 family/N/round 恰有三个不同 routine，position 恰为0、1、2；同一轮 ozAMX 与 SGEMM 的 float A/B 输入 hash 相同。
- 每一行 `input_unchanged=1`、`nonfinite=0`、`mismatches=0`；raw wall、steady wall、CPU seconds 全部有限且正。
- 每组包含预热的11个 A hash 都不同，B hash始终只有一个；完整 C hash也有11个不同值。没有出现重复使用上一轮同一输出 hash 的迹象。
- dyadic 的33个 N/round（三尺寸×11轮）中，ozAMX、SGEMM、raw BF16 的完整输出 hash 全部一致。这比单个 scalar checksum 更强；hash本身仍不是密码学抗碰撞证明。
- dyadic N128 每次验证16384个逐项整数 oracle输出，并有三个 field challenge；N1024/N4096 每次为三个 field challenge、oracle_entries=0。
- uniform N128 每次独立检查全部16384个输出；N1024/N4096 每次检查512个索引，field_challenges=0，符合设计，没有把512点误报为全矩阵。

dyadic 的 raw BF16 输入与 float 输入是不同存储表示，输入hash不能直接跨表示比；因为这些小 dyadic 数精确可表示为 BF16，三routine在数学上使用同一矩阵。uniform raw BF16 则使用实际量化后的不同精度输入，正确性参照也使用实际BF16解码数据，不能把其小误差直接解释为对原始FP32矩阵更准确。

## 4. 十次原始墙钟重算的18组吞吐

主公式固定为 `2*N³ / arithmetic_mean(raw_wall_s) / 10^12`，**没有乘6或其他产品预算**。下表只使用 warmup=0 的十个原始秒数，不删除样本，不对每次倒数取均值。墙钟差为 `(mean(raw)/mean(steady)-1)*100%`。

| Family | N | Routine | raw均值 ms | useful TFLOP/s | raw/steady均值差 % |
|---|---:|---|---:|---:|---:|
| dyadic | 128 | ozAMX FP32 | 0.304267555 | 0.013784920 | 0.098285 |
| dyadic | 128 | SGEMM | 1.498181839 | 0.002799596 | 0.025654 |
| dyadic | 128 | raw BF16 | 1.444792375 | 0.002903050 | 0.027754 |
| dyadic | 1024 | ozAMX FP32 | 2.201175224 | 0.975607768 | 0.023312 |
| dyadic | 1024 | SGEMM | 1.862881240 | 1.152775390 | 0.021409 |
| dyadic | 1024 | raw BF16 | 1.005805563 | 2.135088258 | 0.037980 |
| dyadic | 4096 | ozAMX FP32 | 23.973073810 | 5.733055117 | 0.008225 |
| dyadic | 4096 | SGEMM | 22.657079156 | 6.066049049 | 0.010206 |
| dyadic | 4096 | raw BF16 | 6.979032326 | 19.693124640 | 0.017484 |
| uniform FP32 | 128 | ozAMX FP32 | 0.334835518 | 0.012526461 | 0.116137 |
| uniform FP32 | 128 | SGEMM | 0.532624871 | 0.007874781 | 0.054772 |
| uniform FP32 | 128 | raw BF16 | 1.292197406 | 0.003245869 | 0.021573 |
| uniform FP32 | 1024 | ozAMX FP32 | 1.733402535 | 1.238883412 | 0.023943 |
| uniform FP32 | 1024 | SGEMM | 1.194212586 | 1.798242351 | 0.026601 |
| uniform FP32 | 1024 | raw BF16 | 0.550452620 | 3.901305164 | 0.065283 |
| uniform FP32 | 4096 | ozAMX FP32 | 20.559180714 | 6.685040391 | 0.009031 |
| uniform FP32 | 4096 | SGEMM | 21.909474675 | 6.273037374 | 0.008801 |
| uniform FP32 | 4096 | raw BF16 | 7.309225202 | 18.803491435 | 0.019619 |

例如 N4096 的有用工作是 `137,438,953,472` FLOP；除以 uniform ozAMX 的 `0.0205591807142s` 得 `6.6850403906e12 FLOP/s`。这里不是 GFLOP/s错标成TFLOP/s，也不是用微秒作为秒的分母。

198条记录均满足 raw>=steady，符合两计时器嵌套。所有记录 raw−steady 的绝对差为约0.0509–5.7581微秒。正式样本中最大的相对差是 uniform N128 SGEMM round3，约0.399736%，该次调用约80微秒，绝对差仅0.3197微秒。最坏组均值差0.116137%；N4096组均值差0.008225%–0.019619%。这支持计时API和单位一致，不能据此声称使用了两个独立硬件时钟。

## 5. 速度比、离散度与可疑现象

以 `mean(SGEMM raw wall)/mean(ozAMX raw wall)` 为本批描述性速度比：

| Family | N128 | N1024 | N4096 |
|---|---:|---:|---:|
| dyadic | 4.923896 | 0.846312 | 0.945105 |
| uniform FP32 | 1.590706 | 0.688941 | 1.065678 |

**小矩阵比值不能当作稳定性能优势。** dyadic N128 SGEMM十样本范围0.089803–8.058342ms，均值1.498182ms，中位数0.162061ms，population CV167.1%，均值/中位数9.245。对应ozAMX中位数0.312832ms；若看中位数，SGEMM反而更快。uniform N128 SGEMM的均值/中位数也为3.444、CV116.4%。应保留均值协议和全部raw，明确尾部慢样本使小矩阵速度比敏感，不能选择性换中位数消除它们。

N1024 dyadic raw BF16同样有0.462615–5.448908ms范围，CV147.3%。N4096 dyadic ozAMX范围17.771868–42.411770ms，CV31.89%；uniform ozAMX范围17.996448–24.677786ms，CV12.27%，而uniform SGEMM CV1.93%。不同family并非完全平稳的重复采样。每组只有十次，routine随机洗牌也没有强制平衡三个位置；例如uniform N128 ozAMX没有position2样本。不能从少数样本量化位置的因果效应，或把某次尾部停顿直接归给NUMA/TLB/调度器。

CPU总时间作为旁证而非吞吐分母：uniform N4096 ozAMX meanCPU=1.1635102s，对应CPU/wall约56.59；SGEMM约62.11；raw BF16约53.73。进程所有线程累计CPU大于墙钟是正常现象，不代表单位错了。外部`time`整个程序42.36s，198条routine墙钟总和约1.386054s，正式180条约1.173419s；剩余绝大部分墙钟是生成、hash、精确/采样验证、getrandom、文件I/O等。不能把42.36s除进每个routine吞吐，也不能把诊断器总耗时当作一次GEMM时间。

## 6. 挑战文件和负控的独立复核

正常dyadic共99条，每条三向量；另有两个N1024负控，各三向量。按每行N、field_challenges、challenge_offset计算全部101段，排序后**无空洞、无重叠**，最终端点恰为2,102,784字节，也等于实际二进制长度：

- 正常记录：2,078,208字节；负控：24,576字节。
- 总uint32数525,696；所有数值都在 `[0,2147483647)`，最小1273，最大2147473304。
- 303个完整挑战向量各自SHA不同；不能仅凭此证明随机性，但未见重复或越域。
- 日志单元素破坏offset87552，三挑战mismatches=3；全零offset99840，三挑战mismatches=3072；两者oracle_entries都为0，确实不是借助N128逐项oracle检出。

本次进一步用独立Python重新生成N1024的Ai/Bi及预热输入变更，读取实际保存的Fp向量，未调用被测库：

1. 对 `one_entry_corrupt`，误差矩阵只有C00增加一个整数单位。三个实际r0是366985944、1211924577、130733251，均非零，独立期望逐挑战检出数 `[1,1,1]`，合计3，与日志一致。
2. 对 `all_zero_output`，独立重算 `Ai*(Bi*r mod p)`；三个实际向量分别有1024个输出行非零，检出数 `[1024,1024,1024]`，合计3072，与日志一致。

因此两个负控的成功不是只相信验证器自己写的 pass/fail。对正常C，本批没有保存完整C文件，只有hash和验证计数，故不能事后从原始附件逐项重放所有正常输出；能够独立复核的是保存完整性、参数关系、误检界与上述可重构负控。dyadic正常检查的数学保证和概率界见 `INDEPENDENT_HARNESS_REVIEW.md`，不是一般输入的确定性逐元素证书。

## 7. 新FP64独立数学附件与12条实测

另只读核查 `docs/audit/independent/independent_fp64_numerics.cpp`：96行，SHA-256 **`81bdf86e1d3ea65c8946a65cef459d2677c825b7f83cc431bf6981f2326eff50`**。主代理随后运行并保存 `run_20261016/fp64_numerics.csv` 和 `.log`，CSV SHA为 **`e6cdcfa4287d93e5d6f1e5268b367720eb1d1a40739abcd6cc7cfd04340d8b66`**。本审查只读和重算数据关系，没有运行该程序。

- 输入三个seed、N64，共4096输出；53位整数网格除2^52（`64-65`）。每个AB dot的整数分子绝对和≤2^110，GCC binary128的113位significand可精确承载，因此 `product:46-50` 的 AB oracle 不依赖MKL或native输出。
- `split:29-44` 独立写出全残量max、frexp ceil-log2、rho45 add/sub投影、BF16 RNE、double残量更新；六片固定，不include旧分解/测试实现。这个有界输入的投影网格可用FP32准确表示，经过float到BF16的实现不引入额外double-rounding疑点。
- `76-82` 按对角线/ai顺序计算三角component的binary128 dot，转float存储、再转double加；与native四预算作4096元素逐位比较（`84-91`）。`component_fp32_round_changed_entries` 是各产品元素转换的累计次数，不是最终C的不同坐标数。
- full36采用quad片和及quad点积（`70-72`），没有先把六片相加到double而丢掉低片；`tail_as_value=ref+full36-selected` 再送入error(value,ref)，测得的是 omitted-tail norm/reference norm，含义正确。`terminal_only_eF=error(full36,ref)` 是六片截断的整体效果。
- Frobenius平方和及最终sqrt不宣称exact；`error:52-55` 的输出是诊断近似值，不能从exact dot证明整个norm计算也逐位精确。

**未发现阻止运行的明显数学或索引错误。** 但N64只有一个BK内的两个K32步进：没有跨BK累加、wide Batch2、长K检查和大矩阵全局最大值分布等覆盖。独立组件的“精确dot→float”与真实AMX逐步FP32累加不应未经证明地泛化为所有输入等价；本批的round-changed计数和native-bit-mismatch正用于实测检验这个有界case。若出现bit mismatch，需要定位组件误差，不可自动宣布native算法错误。该附件也不采集吞吐，不能把其数值诊断当FP64性能结果。

独立核查CSV实际含三个seed×四budget=12条，组合无缺失；全部 `native_vs_independent_bit_mismatches=0`、`component_fp32_round_changed_entries=0`，每条native和独立重建的eF字段相同。日志报告 `independent_fp64_validation=pass N=64 full_output_entries=4096 binary128_significand_bits=113`。这意味着本批12×4096=49152个native输出均与独立标量产品/重建路径逐位相同，并且所检查component的精确dot到float转换均未改变值。

| Seed | p6 eF | p10 eF | p15 eF | p21 eF | 六片terminal eF | p21 omitted-tail eF |
|---:|---:|---:|---:|---:|---:|---:|
| 20261016 | 8.58788655862e-8 | 3.63243735527e-10 | 1.53753398607e-12 | 6.41496625264e-15 | 4.00558949091e-15 | 5.03888242737e-15 |
| 260904 | 8.70538031515e-8 | 3.63935690307e-10 | 1.53450801168e-12 | 6.45751335166e-15 | 3.94686667164e-15 | 5.09166444561e-15 |
| 8454 | 8.46274054304e-8 | 3.65264266565e-10 | 1.47960680321e-12 | 6.39198410137e-15 | 3.94899107843e-15 | 4.86010322924e-15 |

这里eF全部以**同一输入的完整binary128 AB**为参照，不以MKL或既有测试为truth。低预算p6/p10/p15的omitted-tail norm与最终误差接近；p21时，仅六片表示的terminal效应约3.95–4.01e-15，三角omitted tail约4.86–5.09e-15，均已达到最终约6.39–6.46e-15的量级。这加强了“literal rho45六片及三角选择本身在这些输入上产生相应误差”的解释，排除了必须依赖旧benchmark或MKL reference才能观察到该量级的疑虑。

但terminal/tail是不同误差矩阵的范数，**不能把两个标量直接相加或唯一分配成最终误差百分比**；它们可能相互取消/强化。double重建加法舍入也没有另作独立列完全隔离。不能据此宣称Table4差异的所有来源已唯一证明，更不能把本批N64/不同seed/输入生成对binary128的eF直接除以论文N256对DGEMM的一个值，制作伪同输入误差倍数。

## 8. 尚未能够确认的结论

- 新结果确认本条件下的可核查吞吐，不确认旧报告每一历史数值，更不能将跨时段/等待策略/输入family结果混成同批加速比。
- dyadic低分量为零；uniform大N仅512点。二者合起来仍不是一般FP32所有输入/所有输出的正确舍入证明。
- 原始挑战全部保存且范围/偏移正确，不代表从有限样本证明OS熵质量；理论界以独立均匀挑战为前提。
- 没有PMU数据，不确认实际DRAM/cache流量、每routine具体MKL ISA或硬件利用率；常规useful TFLOP/s不等于实际执行FLOP计数。
- FP32吞吐数据只到N4096；不外推8192/16384/32768。新FP64附件只覆盖N64的三个seed和一个BK内，不在这个FP32吞吐campaign中；没有覆盖wide或跨BK，也没有证明达到论文Table4的相同矩阵精度。

本批独立结果使“只看旧测试/报告所以误信TFLOPS”的证据链得到补强。需要保留的实质不确定性是输入覆盖、共享环境波动、缺少正常完整C的离线重放，以及FP64 literal方法与论文数值的具体差异来源，而不是已被本批双墙钟和完整调用重算排除的1000倍单位错。
