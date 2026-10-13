# FP64 六片算法数值诊断

## 结论

独立诊断在 `N=256` 得到 literal 六片、21 个 BF16 component products 的 `eF=6.40764e-15`，与实测约 `6.4e-15` 一致。分解并没有显示 BF16 slice 还原错误或 FP32 component-product 累加误差：12 个 slice 都可精确表示为 BF16，`sum(slices)+R6` 对输入的 longdouble 检查误差为 0；选中的 FP32-product 结果与高精度 selected-21 结果在这些测试矩阵上相同。误差主要来自两个被算法有意丢弃的项：六片后的 terminal residual 贡献和 `i+j>=6` 的 15 个遗漏 component products。

在 `N=256`，terminal 项单独 `eF=4.03234e-15`，遗漏 15 项单独 `eF=5.00152e-15`，selected-21 合并误差 `eF=6.40764e-15`。两项误差矩阵几乎正交，所以合并后接近平方和的平方根。论文表 4 在 N=256 对 FP64-21 报 `5.71e-16`（eF 缩放 `×10^-16`），低约 11.2 倍；本诊断确认 6.4e-15 是 literal algorithm 的截断误差量级，但没有足够证据解释论文表值为何更低。论文未给 RNG seed，且本实验的 random stream/reference 不同；不能将这项差异归因于实现缺陷或声称已复现论文数据。

## 方法与可复现命令

诊断独立于项目 GEMM kernel，不 import 或调用 `src/` 实现。`A`、`B` 分别用固定种子 `20261012` 的 NumPy `default_rng` 按顺序生成 `uniform[-1,1]` FP64 方阵，尺寸 64、128、256。每个 operand 按规格反复执行 `v=ceil(log2(max(abs(R))))`、`sigma=2**(v+45)`、`Z=fl64(fl64(R+sigma)-sigma)`、直接 binary64 到 BF16 round-to-nearest-ties-even，再算 `R=fl64(R-slice)`，共六轮。

longdouble 参考为直接 `A @ B`；36 项和 selected 21 项以 longdouble 分组利用分配律求和，遗漏 15 项也单独求和。FP32 对照逐项计算 BF16×BF16 matrix product，以 FP32 结果 widen 后按对角线顺序加入 longdouble accumulator，用于检查 AMX 的 FP32 component-product accumulation 是否足以解释观测差异。它不是 AMX 指令级仿真，也不模拟 oneMKL DGEMM 的归约顺序。

```sh
python3 tools/diagnose_fp64.py --sizes 64 128 256 --seed 20261012 > docs/FP64_DIAGNOSTIC_RESULTS.json
```

结果机器文件为 [`FP64_DIAGNOSTIC_RESULTS.json`](FP64_DIAGNOSTIC_RESULTS.json)。本机 NumPy 为 2.5.2；`numpy.longdouble` 占 16 byte storage、64-bit mantissa，即 x87 80-bit extended precision，放在 16-byte padded storage 中，**不是 IEEE binary128/quad precision**。它给出的直接 AB truth 比 FP64 精确，但不是精确实数运算。

## 分片检查

在三个尺寸上，A/B 两侧每轮 `v` 都是 `0,-8,-16,-24,-32,-40`，对应 `sigma` 为 `2^45, 2^37, 2^29, 2^21, 2^13, 2^5`。N=256 时每轮 residual-before 最大值与 zero count 如下；所有 12 个 slice 均通过直接 BF16 可表示性复核，非零 BF16 subnormal 数为 0。

| 轮次 | v | sigma | A max residual before | A zero count | B max residual before | B zero count |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0 | 2^45 | 9.999925e-1 | 218 | 9.999904e-1 | 198 |
| 1 | -8 | 2^37 | 3.906102e-3 | 294 | 3.906146e-3 | 299 |
| 2 | -16 | 2^29 | 1.525840e-5 | 287 | 1.525837e-5 | 274 |
| 3 | -24 | 2^21 | 5.960040e-8 | 285 | 5.960195e-8 | 264 |
| 4 | -32 | 2^13 | 2.328273e-10 | 289 | 2.328255e-10 | 306 |
| 5 | -40 | 2^5 | 9.094947e-13 | 327 | 9.094947e-13 | 302 |

六片后的 A/B terminal residual max absolute 均为 `3.552714e-15`；相对输入 Frobenius norm 分别约 `2.8240e-15` 与 `2.8209e-15`。只求六片和会留下该 terminal residual；加入 R6 后，对本例 FP64 输入的 longdouble reconstruction max error 为 0。六片 residual 并不是 BF16 round trip 丢失或 subnormal slice 造成的。

## Product 误差拆分

`eF` 使用直接 longdouble `A @ B` 作为参考，`scaledmax=max(|error|/(|A||B|))`，分母也由 longdouble 计算。`full36` 是六片求和矩阵相乘，等价于高精度的 36 项和；`selected21` 保留 `i+j<6`；`omitted15` 是被删去的 `i+j>=6` 项。Terminal output contribution 单独按 `R_A @ B + (sum A slices) @ R_B` 计算，包含 `R_A @ R_B`。

| N | full36 terminal eF / scaledmax | omitted 15 eF / scaledmax | selected 21 eF / scaledmax | FP32-product selected 21 eF |
|---:|---:|---:|---:|---:|
| 64 | 4.0051e-15 / 2.4579e-15 | 4.9386e-15 / 3.3853e-15 | 6.3423e-15 / 4.4494e-15 | 6.3423e-15 |
| 128 | 3.9422e-15 / 1.9684e-15 | 4.9333e-15 / 2.5928e-15 | 6.2789e-15 / 3.2255e-15 | 6.2789e-15 |
| 256 | 4.0323e-15 / 1.4748e-15 | 5.0015e-15 / 1.7245e-15 | **6.4076e-15 / 2.2291e-15** | **6.4076e-15** |

`full36 - selected21` 与单独计算的 omitted-15 矩阵符合到 `1e-19` 相对 Frobenius 量级；`(AB-full36)` 与 terminal residual 展开项的 identity check 也在约 `4e-19` 相对量级。选中产品的 FP32-product+widen 对照与 longdouble selected-21 在这些矩阵上的逐元素结果相同，所以当前差值证据指向算法本身的有限展开截断，而非 BF16 可表示性或 FP32 accumulation。

## 终端 residual 的标量量级核验（近似，不是误差界）

以下是对 binary64 spacing 的纸笔推导和小标量核算，不运行矩阵，也不模拟 AMX。按规格 `sigma=2^(v+45)`，且假设远离零、无 exponent/subnormal 异常并且加减保持在相邻 binade 的通常情形：当输入 residual `R>0` 时，`sigma+R` 落在 `sigma` 这一侧，binary64 间距为 `2^(v+45-52)=2^(v-7)`；当 `R<0` 时，和落在 `sigma` 下方的 binade，间距减半为 `2^(v-8)`。最近舍入时，减去 `sigma` 后 `Z` 的量化误差半宽分别为 `2^(v-8)` 和 `2^(v-9)`；在 slice `X_r=round_BF16(Z)` 精确等于该格点 `Z` 的常见正常数值情形，这也就是 `R_next=R-X_r` 的误差半宽。对观测到的典型层级 `v=0,-8,-16,-24,-32,-40`，第六次提取前 `v=-40`，于是 `R6=R5-X5` 的近似半宽是正侧 `2^-48`、负侧 `2^-49`。符号分组说的是最后一轮**输入** `R5` 的正负，不是声称最终 `R6` 残差符号正负各半。

若进一步近似认为舍入相位在两侧各自均匀、最后一轮输入 `R5` 正负各半，则

```text
Var(R6) ≈ 1/2 × (2^-48)^2/3 + 1/2 × (2^-49)^2/3
        = (5/24) × 2^-96.
```

对独立 `A,B ~ uniform[-1,1]`，取 `Var(A)=1/3`；只看终端项 `E = R_A B + (sum A_slices) R_B`，再近似假设 residual、输入和两侧误差足够独立，则相对 Frobenius 误差的均方量级为 `sqrt(2 Var(R6)/Var(A)) = sqrt(5/4) × 2^-48 = 3.9720546452e-15`。标量脚本式计算得到 `Var(R6)=2.6295363507e-30`，对应预测值 `3.9721e-15`；已有 N=256 JSON 的 `full36 terminal eF=4.0323352337e-15`，约为该预测的 `1.0152` 倍。这个吻合说明 literal 六片的终端 residual 单独就能处在数个 `1e-15` 的量级，无需引入 AMX product rounding 才出现该量级；这是一项有条件的 LLM 近似诊断，不是普适误差界或独立性证明。

上述估计依赖均匀舍入相位、`R5` 两侧符号近似均衡，以及 residual 与乘数、两矩阵之间相关性可忽略等假设。相关性不能未经数据检验就当作独立；该模型也没有包含 selected-21 所遗漏的 `i+j>=6` 产品，后者仍会叠加到最终误差。它只能解释本实验 terminal 部分为何已达 `~4e-15`，不能证明论文表 4 错误，也不能排除原文未披露的实现细节或输入差异。

### 对论文表值的解释边界

本测试中 `N=256` 的 6.41e-15 来自 terminal residual 与遗漏 15 项的合成；如果将二者中的任一项当作可保留结果，算法定义就已改变。表 4 的 5.71e-16 与 literal 六片/21 项结果差距仍未被解释。这里没有复现论文随机数发生器、确切的 MKL reference 或未知作者端实现细节；seed 未公开也使直接数值比对不可行。应继续把这视为论文表值与 literal 规格间的未解决差异，而不是擅自用 floor(v)、多一片或额外产品改写主算法。诊断没有对 `src/`、`tests/`、`bench/` 做修改。
