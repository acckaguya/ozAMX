# ozAMX 论文复现实验结果

## 结论与复现边界

本仓库完成了《BF16 Component-Product Emulation of FP32 and FP64 GEMM on Intel AMX》的独立实现、真实 Intel AMX 执行验证和已计划实验配置。正式主 campaign 覆盖 Table 4 所有 8 个矩阵阶数 × 5 种变体（40/40），每个配置执行 1 次 warm-up 和 10 次 timed repetitions；另外完成 FP32 线程伸缩 18/18 配置，以及 raw oneMKL BF16 headroom 8/8 阶。逐次时间、BLAS/reference 指标、产品次序、MKL元数据保存在原始 CSV 与 checkpoint 中。

这表示**实现及计划协议的本机实验已完成**，不表示论文结果已数值或性能复现成功。本机 literal FP64-21 精度与论文 Table 4 有明显、经独立分解分析仍未解释的差异；本机 AMX end-to-end 时间与 MKL GEMM-only 参照也未复现论文的加速结果。不能将平台不同或论文未公布随机 seed 当作该精度差异已解释。结论严格限于本机输入域、seed、编译器和计时边界。

## 平台与方法

本机 CPU/OS/AMX权限、GCC/CMake、oneMKL实际运行时版本与路径见 [ENVIRONMENT.md](ENVIRONMENT.md)。正式计时固定 uniform `[-1,1]`、`seed=260904+N`、64 物理核心 CPU affinity（0–63）、oneMKL GNU layer、1 warm-up + 10 reps；主 sweep 40/40 配置为 FP32 与 FP64 6/10/15/21 products。每个配置只生成一组由seed确定的A/B，warm-up和10次计时重复都复用同一输入；sample std描述时间离散度，不是精度误差的置信区间，误差列也不是十次独立随机实验的统计。正文还讨论 Gaussian、scaled/log-uniform、cancellation-sensitive 输入，但没有为这些补充分布逐阶发表 Table 4 精度/耗时表；本复现的完整表格协议仅对 uniform 主表，未测 supplementary distributions，不把它们误称为 Table 4 必须覆盖。

计时采用本实现 profile 边界：A/B/C调用者内存分配、输入生成、常规layout validation，以及主线程已授予 AMX permission 不计入 `total`；split与pack阶段的缓冲分配/写入和全矩阵slice projection均计入 `total`，误差参考不计入 AMX total。compute/reconstruction内含结果缓冲分配/清零、OpenMP调度和worker permission查询、每次调用的tile config load/release、AMX kernel、FP64 store/widen/add、最终扫描与复制。`total=split+pack+compute/reconstruction`。MKL列为 GEMM-only，二者工作范围不同；论文未给作者分配/验证/逐worker setup实现，不能把本地计时边界说成作者计时。

正式 benchmark 源码在 GCC 支持 `__SIZEOF_FLOAT128__` 的构建路径中使用 `__float128`（IEEE binary128）逐元素计算 direct `A@B`，并以binary128累加平方误差、reference平方和与scaled max；最终Frobenius比值/sqrt转到本机longdouble输出。`N≤256` 为全矩阵精度度量；较大阶每个配置只随机抽取 512 个输出索引，因此 CSV 标签 `full_float128` / `512_sample_float128` 的binary128含义准确，但较大阶 `eF_hp` 只是512次采样、不是full-matrix Frobenius error。历史CSV标签不重命名。独立 Python 数值诊断使用 `numpy.longdouble`，本机实际是 80-bit extended、64-bit significand、16-byte storage，不是binary128；独立 native audit另逐项核对真实AMX store。`eF_mkl`是完整N×N矩阵上的Frobenius误差；`e_scaled_mkl`也遍历完整输出矩阵，其逐元素分母由oneMKL DGEMM完整计算`abs(A) @ abs(B)`。只有 direct binary128 的`eF_hp/e_scaled_hp`在N>256时是512点采样；误差定义与算法证据见 [REPRODUCTION_SPEC.md](REPRODUCTION_SPEC.md) 和 [FP64_DIAGNOSTIC.md](FP64_DIAGNOSTIC.md)。

## Table 4 精度覆盖

下表列出本机全矩阵 `eF_mkl`，即与 oneMKL SGEMM/DGEMM reference 的相对 Frobenius 误差。论文 Table 4 headline 也以 oneMKL SGEMM/DGEMM 为 reference，因此这是同定义的有限数值对照；但本机与论文平台、MKL版本、随机输入及seed不同，不是对相同矩阵的精确复算。`eF_hp` 及scope原值逐配置见 `bench/final_main_40.csv`；N>256 的 direct binary128 值仅为512点样本，不能替代这张full-matrix headline对照。论文 Table 4 准确度已核验于印刷页/PDF物理页21，FP64-21列缩放为`10^-16`。

| N | FP32 eF vs MKL | FP64-p6 | FP64-p10 | FP64-p15 | FP64-p21 |
|---:|---:|---:|---:|---:|---:|
| 256 | 3.12e-07 | 8.49e-08 | 3.62e-10 | 1.53e-12 | 6.39e-15 |
| 512 | 3.18e-07 | 8.48e-08 | 3.62e-10 | 1.52e-12 | 6.37e-15 |
| 1024 | 3.64e-07 | 8.49e-08 | 3.62e-10 | 1.53e-12 | 6.39e-15 |
| 2048 | 3.74e-07 | 8.49e-08 | 3.62e-10 | 1.53e-12 | 6.39e-15 |
| 4096 | 3.84e-07 | 8.5e-08 | 3.63e-10 | 1.53e-12 | 6.41e-15 |
| 8192 | 3.97e-07 | 8.5e-08 | 3.62e-10 | 1.53e-12 | 6.43e-15 |
| 16384 | 4.18e-07 | 8.5e-08 | 3.62e-10 | 1.53e-12 | 6.47e-15 |
| 32768 | 4.58e-07 | 8.5e-08 | 3.62e-10 | 1.53e-12 | 6.53e-15 |

| N | FP32 scaledmax vs MKL | FP64-p6 | FP64-p10 | FP64-p15 | FP64-p21 |
|---:|---:|---:|---:|---:|---:|
| 256 | 2.36e-07 | 2.98e-08 | 1.34e-10 | 5.32e-13 | 2.29e-15 |
| 512 | 1.53e-07 | 2.52e-08 | 9.86e-11 | 4.12e-13 | 1.83e-15 |
| 1024 | 1.5e-07 | 1.79e-08 | 7.14e-11 | 3e-13 | 1.3e-15 |
| 2048 | 8.37e-08 | 1.28e-08 | 5.77e-11 | 2.51e-13 | 9.44e-16 |
| 4096 | 5.58e-08 | 9.9e-09 | 4.35e-11 | 1.67e-13 | 7.41e-16 |
| 8192 | 4.16e-08 | 7e-09 | 3.04e-11 | 1.29e-13 | 5.67e-16 |
| 16384 | 4.14e-08 | 5.07e-09 | 2.32e-11 | 1e-13 | 4.05e-16 |
| 32768 | 3.73e-08 | 4.23e-09 | 1.72e-11 | 6.75e-14 | 2.93e-16 |

| N | 本机 FP32 eF_hp scope | p6 | p10 | p15 | p21 |
|---:|---:|---:|---:|---:|---:|
| 256 | 1.28e-07 (full_float128) | 8.49e-08 (full_float128) | 3.62e-10 (full_float128) | 1.53e-12 (full_float128) | 6.36e-15 (full_float128) |
| 512 | 1.3e-07 (512_sample_float128) | 8.2e-08 (512_sample_float128) | 3.64e-10 (512_sample_float128) | 1.52e-12 (512_sample_float128) | 6.11e-15 (512_sample_float128) |
| 1024 | 1.37e-07 (512_sample_float128) | 8.47e-08 (512_sample_float128) | 3.79e-10 (512_sample_float128) | 1.46e-12 (512_sample_float128) | 6.08e-15 (512_sample_float128) |
| 2048 | 1.48e-07 (512_sample_float128) | 8.79e-08 (512_sample_float128) | 3.71e-10 (512_sample_float128) | 1.49e-12 (512_sample_float128) | 6.87e-15 (512_sample_float128) |
| 4096 | 1.51e-07 (512_sample_float128) | 8.13e-08 (512_sample_float128) | 3.5e-10 (512_sample_float128) | 1.42e-12 (512_sample_float128) | 5.98e-15 (512_sample_float128) |
| 8192 | 1.84e-07 (512_sample_float128) | 8.85e-08 (512_sample_float128) | 3.67e-10 (512_sample_float128) | 1.61e-12 (512_sample_float128) | 6.63e-15 (512_sample_float128) |
| 16384 | 1.88e-07 (512_sample_float128) | 8.05e-08 (512_sample_float128) | 3.49e-10 (512_sample_float128) | 1.47e-12 (512_sample_float128) | 5.99e-15 (512_sample_float128) |
| 32768 | 2.47e-07 (512_sample_float128) | 8.97e-08 (512_sample_float128) | 3.55e-10 (512_sample_float128) | 1.56e-12 (512_sample_float128) | 6.71e-15 (512_sample_float128) |

正式 benchmark N=256 FP64-p21 headline `eF_mkl` 为 `6.39e-15`，对照论文 `5.71×10^-16`，差约11.2倍；direct binary128 独立 full-matrix 结果为 `eF_hp=6.3638e-15`、`e_scaled_hp=2.3331e-15`，提供本机高精度对照。FP32 `eF_mkl` 八阶为 `3.12, 3.18, 3.64, 3.74, 3.84, 3.97, 4.18, 4.58 ×10^-7`，论文 headline 为 `3.02, 3.06, 3.59, 3.72, 3.83, 3.97, 4.18, 4.58 ×10^-7`：趋势和量级接近，大阶接近，但不同平台与输入下不称为逐位/同输入复现。FP64各budget见上表，与论文headline明显不匹配。独立 N=256 literal decomposition 诊断另得到 selected-21 `eF≈6.4076×10^-15`，terminal residual约`4.0323×10^-15`、遗漏15个高阶product约`5.0015×10^-15`；这些诊断使用x87 longdouble而不是binary128。另有147,456个component/BK AMX store逐位匹配独立FP32 dot+widen，pack/padding及输出产品序列也通过独立审计。因此该差异不由被审计kernel/product计算偏差解释，且不能据未知作者seed宣称已解决。详见 [FP64_DIAGNOSTIC.md](FP64_DIAGNOSTIC.md) 和 [NATIVE_KERNEL_AUDIT.md](NATIVE_KERNEL_AUDIT.md)。非零residual投影出BF16零片为合法；非零BF16 subnormal和明显域外输入按实现边界拒绝。AMX没有可读浮点异常flag；FTZ导致的内部下溢不可一般检测，也不宣称全面支持所有FP64值域。

## Table 4 性能原始统计

每格为`AMX total mean±sample std (s) / oneMKL GEMM-only mean (s) / oneMKL时间÷AMX时间`。比值大于1才代表本机AMX在此工作范围下更快；它仍不等于论文计时，具体原始10值与其他指标在 `bench/final_main_40.csv`、`bench/final_timing_statistics.csv`。

| N | FP32 | p6 | p10 | p15 | p21 |
|---:|---|---|---|---|---|
| 256 | 0.002178±0.00062 / 7.533e-05 / 0.0346 | 0.003567±0.00019 / 8.373e-05 / 0.0235 | 0.004136±4.9e-05 / 8.558e-05 / 0.0207 | 0.00483±3.9e-05 / 8.479e-05 / 0.0176 | 0.005555±6e-05 / 7.89e-05 / 0.0142 |
| 512 | 0.004085±6.2e-05 / 0.0001238 / 0.0303 | 0.007856±0.00037 / 0.0002032 / 0.0259 | 0.009079±0.0003 / 0.0001857 / 0.0205 | 0.0103±5.4e-05 / 0.0001819 / 0.0177 | 0.012±0.00012 / 0.0001822 / 0.0152 |
| 1024 | 0.0131±0.0003 / 0.0005055 / 0.0386 | 0.02424±0.0018 / 0.0008241 / 0.034 | 0.02786±0.002 / 0.0008347 / 0.03 | 0.02988±0.0001 / 0.0008529 / 0.0285 | 0.03413±0.00099 / 0.0007805 / 0.0229 |
| 2048 | 0.04958±0.0011 / 0.002675 / 0.054 | 0.0995±0.0016 / 0.005373 / 0.054 | 0.106±0.0042 / 0.005888 / 0.0555 | 0.1116±0.0058 / 0.005542 / 0.0497 | 0.1188±0.0083 / 0.005371 / 0.0452 |
| 4096 | 0.2016±0.0078 / 0.02121 / 0.105 | 0.4671±0.017 / 0.0395 / 0.0846 | 0.5554±0.035 / 0.03951 / 0.0711 | 0.6651±0.044 / 0.03904 / 0.0587 | 0.6746±0.055 / 0.03953 / 0.0586 |
| 8192 | 0.967±0.079 / 0.151 / 0.156 | 2.259±0.029 / 0.3138 / 0.139 | 2.778±0.075 / 0.3178 / 0.114 | 3.378±0.022 / 0.3144 / 0.0931 | 3.477±0.069 / 0.3109 / 0.0894 |
| 16384 | 5.12±0.15 / 1.292 / 0.252 | 10.45±0.76 / 2.533 / 0.243 | 14.88±1.8 / 2.497 / 0.168 | 15.98±0.23 / 2.526 / 0.158 | 19.92±0.26 / 2.485 / 0.125 |
| 32768 | 23.56±0.79 / 9.899 / 0.42 | 67.42±16 / 20.48 / 0.304 | 88.31±21 / 20.08 / 0.227 | 135.3±43 / 19.87 / 0.147 | 157.6±25 / 20.49 / 0.13 |

**逐项判断：** Table 4 的40个配置均已测；精度指标字段全部生成。full-matrix oneMKL `eF_mkl` 与论文 Table 4 headline采用同类reference定义，可用于有限数值比较；本机FP32八阶值与论文量级/趋势接近，较大阶近似一致，但输入、平台和库版本不同。FP64各budget本机误差明显较大。direct binary128 full-matrix误差只在 N=256；其他阶只有512点采样`eF_hp`，不可与论文full-matrix Frobenius指标直接比较。算法严格保留论文字面分解/产品预算，未为贴近论文值更改`rho`或切片数。

## Figure 7：FP32端到端速度比

完整八阶本机测量列在上表，定义为`oneMKL SGEMM-only time / AMX end-to-end time`。全部点由CSV计算。若点小于1，本机AMX端到端较慢；这与论文Figure 7报告的1.14×至2.56×加速不匹配。平台及scope不同，但此处本机没有复现论文速度提升。

## Figure 8：FP32线程伸缩

18个配置按N=1024/4096/16384、线程2/4/8/16/32/64完成。表中给出AMX end-to-end时间mean±sample std(s)，逐次时间和oneMKL参照见线程CSV及统计CSV。

| N | 2 threads | 4 | 8 | 16 | 32 | 64 |
|---:|---:|---:|---:|---:|---:|---:|
| 1024 | 0.04392±0.00027 | 0.0196±0.0027 | 0.01771±0.00014 | 0.01413±0.00036 | 0.01236±0.00018 | 0.0118±0.00021 |
| 4096 | 1.153±0.043 | 0.6808±0.016 | 0.416±0.016 | 0.2882±0.0054 | 0.2505±0.015 | 0.2162±0.0017 |
| 16384 | 47.78±0.24 | 24.81±0.45 | 14.42±0.27 | 8.195±0.27 | 7.528±0.49 | 5.294±0.18 |

## Figure 6：raw oneMKL BF16 headroom

只调用 oneMKL `cblas_gemm_bf16bf16f32`，不调用ozAMX。以下本机数据以TFLOP/s报告，并不和论文图上标注的GFLOPS绝对值混画；原文单位存在文档所述疑点。每阶10次原始计时、实际MKL版本/路径和runtime映射见 `bench/raw_bf16.csv` / `bench/raw_bf16_n<N>.csv`。

| N | mean(s) | 本机TFLOP/s | oneMKL version | runtime path |
|---:|---:|---:|---|---|
| 256 | 4.238e-05 | 0.7918 | Intel(R) oneAPI Math Kernel Library Version 2026.0-Product Build 20260401 for Intel(R) 64 architecture applications | `/data/home/caiwl/ozAMX/third_party/code/mkl-2026/venv/lib/libmkl_rt.so.3` |
| 512 | 0.0001199 | 2.238 | Intel(R) oneAPI Math Kernel Library Version 2026.0-Product Build 20260401 for Intel(R) 64 architecture applications | `/data/home/caiwl/ozAMX/third_party/code/mkl-2026/venv/lib/libmkl_rt.so.3` |
| 1024 | 0.0002228 | 9.637 | Intel(R) oneAPI Math Kernel Library Version 2026.0-Product Build 20260401 for Intel(R) 64 architecture applications | `/data/home/caiwl/ozAMX/third_party/code/mkl-2026/venv/lib/libmkl_rt.so.3` |
| 2048 | 0.001134 | 15.14 | Intel(R) oneAPI Math Kernel Library Version 2026.0-Product Build 20260401 for Intel(R) 64 architecture applications | `/data/home/caiwl/ozAMX/third_party/code/mkl-2026/venv/lib/libmkl_rt.so.3` |
| 4096 | 0.008602 | 15.98 | Intel(R) oneAPI Math Kernel Library Version 2026.0-Product Build 20260401 for Intel(R) 64 architecture applications | `/data/home/caiwl/ozAMX/third_party/code/mkl-2026/venv/lib/libmkl_rt.so.3` |
| 8192 | 0.03471 | 31.68 | Intel(R) oneAPI Math Kernel Library Version 2026.0-Product Build 20260401 for Intel(R) 64 architecture applications | `/data/home/caiwl/ozAMX/third_party/code/mkl-2026/venv/lib/libmkl_rt.so.3` |
| 16384 | 0.2972 | 29.6 | Intel(R) oneAPI Math Kernel Library Version 2026.0-Product Build 20260401 for Intel(R) 64 architecture applications | `/data/home/caiwl/ozAMX/third_party/code/mkl-2026/venv/lib/libmkl_rt.so.3` |
| 32768 | 2.054 | 34.26 | Intel(R) oneAPI Math Kernel Library Version 2026.0-Product Build 20260401 for Intel(R) 64 architecture applications | `/data/home/caiwl/ozAMX/third_party/code/mkl-2026/venv/lib/libmkl_rt.so.3` |

## Figure 9–10 与论文其余实验

- Figure 9性能相关主尺寸/预算由40配置覆盖；本机端到端数据与论文曲线不匹配，详细每配置统计见CSV。
- Figure 10对应的split、pack、compute/reconstruction段均在CSV中按10次平均及std保存；`docs/figures/time_breakdown`显示的是本地计时段比例，不是论文柱值。
- Gaussian/scaled/cancellation-sensitive数据不是Table 4 uniform主表的已报告完整数组，本次没有对这些补充分布运行完整矩阵套件；边界输入和AMX FTZ行为由功能验证/域检查覆盖。
- 无法逐项重造作者未提供的随机种子、随机数引擎、平台库版本和内部参考实现。论文性能原始数据以作者报告为准，不将本机绝对GFLOPS与论文Figure 6叠加。
- 所用论文版本没有作者代码链接或复现补充包；本项目是独立实现，不声称作者代码不存在于其他渠道。原始测量中有一组p6/p10运行重叠风险；相关输入已从干净主数据合并白名单中排除，clean p6通过独立配置重新计时。运维日志保留在本地，不进入公开包；公开文件选择见 [PUBLICATION_PACKAGE.md](PUBLICATION_PACKAGE.md)。

## FP64 alternative 假设的真实 AMX 诊断

该部分仅对比假设，不是作者算法更改建议，也不替代主40配置。N=256 下三种 decomposition × 四种 product budget 的12个汇总以及156个逐项AMX product记录均由validator校验；longdouble参考与 native AMX 数值及 mismatch 数量按原样保留。任何非零差异均为观测结果，不被解释为测试失败或自动归为一致。

| 方法 | budget | selected longdouble eF | actual AMX eF | 产品store mismatch数 | 最大ULP差 |
|---|---:|---:|---:|---:|---:|
| diagnostic_rho44 | 10 | 1.5181e-10 | 1.5181e-10 | 0 | 0 |
| diagnostic_rho44 | 15 | 6.0753e-13 | 6.0753e-13 | 0 | 0 |
| diagnostic_rho44 | 21 | 2.1519e-15 | 2.1519e-15 | 0 | 0 |
| diagnostic_rho44 | 6 | 3.7721e-08 | 3.7721e-08 | 0 | 0 |
| direct_bf16_residual | 10 | 1.0673e-11 | 6.0434e-08 | 415604 | 393216 |
| direct_bf16_residual | 15 | 1.7179e-14 | 6.0434e-08 | 632139 | 3637248 |
| direct_bf16_residual | 21 | 2.3133e-17 | 6.0434e-08 | 813579 | 3637248 |
| direct_bf16_residual | 6 | 6.4671e-09 | 6.0814e-08 | 243475 | 393216 |
| paper_literal_rho45 | 10 | 3.6319e-10 | 3.6319e-10 | 0 | 0 |
| paper_literal_rho45 | 15 | 1.5402e-12 | 1.5402e-12 | 0 | 0 |
| paper_literal_rho45 | 21 | 6.4076e-15 | 6.4076e-15 | 0 | 0 |
| paper_literal_rho45 | 6 | 8.5225e-08 | 8.5225e-08 | 0 | 0 |

详细表及其原始 product 行见 `bench/diagnostics/alt_256/native_results.csv`；导出输入的校验和、随机流与类别说明见同目录 `metadata.json` 和 `alternative_report.json`。这里的 Python reference 使用本机 80-bit longdouble，native product 是真实 AMX；正式benchmark direct-AB oracle使用GCC binary128，两者不混为同一参考。另有一次固定输入N=256的非作者 signed-shift 单点假设诊断，其公式和 MKL/full36 对照见 [SIGNED_SHIFT_DIAGNOSTIC.md](SIGNED_SHIFT_DIAGNOSTIC.md)，不计入正式覆盖，也不改变 literal 默认算法。

## 图表、数据与有效来源

全部统计脚本根据原始CSV逐条解析，不删除统计离群点。干净主数据白名单见 [`tools/finalize_campaign_data.py`](../tools/finalize_campaign_data.py)；旧重叠/污染p6数据保留为invalid diagnostic，不进入40行合并。原始CSV及逐rep checkpoint是最终可复核依据。绘图见 `docs/figures/*.png` 及同名PDF，均标注为本机独立复现实测，不是论文点值。
