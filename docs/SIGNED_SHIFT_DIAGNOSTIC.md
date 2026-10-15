# N=256 signed-shift 单点诊断

这是一个边界明确的独立诊断：仅一组输入、N=256、固定 seed `20261012`、六层和四个产品预算，不是论文算法复现，也没有参数搜索。它不改变项目默认 `rho=45` 实现，不计入正式40配置、18线程配置或8个raw BF16配置。

## 方法与输入

输入A/B与 `bench/diagnostics/alt_256` 的 little-endian binary64 文件逐字节相同；随机流是 NumPy PCG64 uniform `[-1,1]`，沿用先推进64、128阶A/B后生成256阶的streamskip。每层用整个残差矩阵的 `v=ceil(log2(max(abs(R))))`，而每个元素使用

```text
sigma(R) = copysign(2^(v+44), R)
Z = fl64(fl64(R + sigma(R)) - sigma(R))
component = round_to_BF16_RNE(Z)
R_next = fl64(R - component)
```

零元素保持零。这个带符号shift使两个符号的投影步长为 `2^(v−8)`；它是待检验的替代假设，不是把论文文字 `rho=45` 重新解释为该公式。六层分片都可精确表示为BF16；本次A、B六层后的残差逐元素为零。

Python计算使用本机 `numpy.longdouble`（x87 80-bit extended，64-bit significand，16-byte storage），不是IEEE binary128。独立C++ driver把导出的六层BF16送入真实AMX component-product kernel；逐产品FP32 store与longdouble dot再舍入至FP32比较。另调用本机 oneMKL DGEMM 得到全矩阵headline reference，并用完整DGEMM `abs(A) @ abs(B)`作scaled误差分母。oneMKL运行时为2026.0，路径见 [ENVIRONMENT.md](ENVIRONMENT.md)。这些是准确性诊断，无性能计时。

## 结果

| 产品预算 | LD selected-products `eF` | native AMX `eF` vs longdouble AB | native AMX `eF` vs oneMKL DGEMM | `e_scaled` vs oneMKL | component store mismatch / max ULP |
|---:|---:|---:|---:|---:|---:|
| p6 | 1.4935684e-8 | 1.4935684e-8 | 1.4935684e-8 | 5.6108348e-9 | 0 / 0 |
| p10 | 3.2690552e-11 | 3.2690552e-11 | 3.2690551e-11 | 1.1655222e-11 | 0 / 0 |
| p15 | 6.9636006e-14 | 6.9636006e-14 | 6.9635898e-14 | 2.5419529e-14 | 0 / 0 |
| p21 | 1.2468591e-16 | 1.2468599e-16 | 5.4811676e-16 | 3.6203591e-16 | 0 / 0 |

完整36项相对longdouble `A@B` 的 `eF=2.7406069e-19`；21项截断相对同参考 `eF=1.2468591e-16`。native driver产生52条逐产品记录（各budget所选链的总数），所有记录均为零store mismatch、0 ULP。p21本机oneMKL headline误差与论文对应表值数量级接近；单个N、单个输入的替代假设不能证明论文算法、作者实现或论文表格来源，也不能作为更换默认算法的依据。

表中“LD selected-products”一列来自 Python 报告的 `selected_product_errors`；“native AMX vs longdouble AB”来自独立C++ driver的longdouble direct-AB reference。两个实现的乘加归约顺序不同，p21分别为 `1.2468590571e-16` 与 `1.2468599086e-16`（差约 `8.5e-23`）；native driver的 `eF_selected_longdouble` 与其 actual-AMX p21 值相同，且产品store逐位比较均为0 mismatch。

## 可复核文件

- 导出与公式实现：[diagnose_signed_shift.py](../tools/diagnose_signed_shift.py)
- 独立真实AMX/oneMKL driver：[native_signed_shift_accuracy.cpp](../tools/native_signed_shift_accuracy.cpp)
- 输入、BF16片层、校验和、Python精度报告、原生逐产品结果和二进制：[`bench/diagnostics/signed_shift_256/`](../bench/diagnostics/signed_shift_256/)
- 逐文件SHA-256收录于 [FULL_SWEEP_MANIFEST.json](FULL_SWEEP_MANIFEST.json) 的 `supplementary_diagnostics.signed_shift_n256`。

重算报告和切片：

```sh
python3 tools/diagnose_signed_shift.py
```

重编译原生诊断（当前工作目录为仓库根目录）：

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DOZAMX_ENABLE_OPENMP=ON \
  -DOZAMX_ONEMKL_ROOT="$PWD/third_party/code/mkl-2026/venv"
cmake --build build --target ozamx_native_signed_shift_accuracy -j4
MKL_THREADING_LAYER=GNU MKL_NUM_THREADS=1 OMP_NUM_THREADS=64 \
  build/ozamx_native_signed_shift_accuracy \
  bench/diagnostics/signed_shift_256 > /tmp/signed_shift_native.csv
```
