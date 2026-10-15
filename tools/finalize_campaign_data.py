#!/usr/bin/env python3
"""Validate the frozen campaign outputs and write derived tables/docs/plots."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "bench"
DOCS = ROOT / "docs"
SIZES = (256, 512, 1024, 2048, 4096, 8192, 16384, 32768)
BUDGETS = (6, 10, 15, 21)
MAIN_SOURCES = [
    BENCH / "full_sweep.csv",
    BENCH / "resume_8192_p21.csv",
    BENCH / "full_sweep_16384.csv",
    BENCH / "full_sweep_32768_fp32.csv",
    *(BENCH / f"full_sweep_32768_fp64_clean_p{b}.csv" for b in BUDGETS),
]


def rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise SystemExit(f"missing campaign source: {path.relative_to(ROOT)}")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def floats(text: str) -> list[float]:
    values = [float(x) for x in text.split(";") if x]
    if not all(math.isfinite(x) for x in values):
        raise SystemExit("nonfinite timing in raw repetition field")
    return values


def require_ten(row: dict[str, str], field: str, source: Path) -> list[float]:
    values = floats(row.get(field, ""))
    if len(values) != 10:
        raise SystemExit(f"{source.name}: expected 10 raw {field} values; got {len(values)}")
    if int(row.get("repetitions", "0")) != 10 or row.get("status") != "ok":
        raise SystemExit(f"{source.name}: row is not a successful 10-repetition result")
    return values


def require_complete_checkpoint(row: dict[str, str], prefix: str, source: Path) -> None:
    precision = row["precision"]
    budget = int(row["budget"])
    n = int(row["N"])
    path = BENCH / f"{prefix}.{precision}.{n}.{budget}.json"
    if not path.is_file():
        raise SystemExit(f"missing complete checkpoint for {source.name}: {path.name}")
    checkpoint = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "precision": precision,
        "N": n,
        "budget": budget,
        "threads": int(row["threads"]),
        "seed": int(row["seed"]),
        "requested_repetitions": 10,
        "completed_timed_repetitions": 10,
        "complete": True,
    }
    for key, value in expected.items():
        if checkpoint.get(key) != value:
            raise SystemExit(
                f"checkpoint {path.name}: {key}={checkpoint.get(key)!r}, expected {value!r}"
            )
    for field in (
        "split_seconds",
        "pack_seconds",
        "compute_reconstruction_seconds",
        "total_seconds",
    ):
        values = checkpoint.get(field)
        if (
            not isinstance(values, list)
            or len(values) != 10
            or not all(math.isfinite(float(v)) for v in values)
        ):
            raise SystemExit(f"checkpoint {path.name}: invalid {field} raw timings")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


PAPER_TABLE4_EF = {
    (256, "fp32", 6): 3.02e-7,
    (512, "fp32", 6): 3.06e-7,
    (1024, "fp32", 6): 3.59e-7,
    (2048, "fp32", 6): 3.72e-7,
    (4096, "fp32", 6): 3.83e-7,
    (8192, "fp32", 6): 3.97e-7,
    (16384, "fp32", 6): 4.18e-7,
    (32768, "fp32", 6): 4.58e-7,
    (256, "fp64", 6): 1.49e-8,
    (512, "fp64", 6): 1.49e-8,
    (1024, "fp64", 6): 1.49e-8,
    (2048, "fp64", 6): 1.49e-8,
    (4096, "fp64", 6): 1.49e-8,
    (8192, "fp64", 6): 1.49e-8,
    (16384, "fp64", 6): 1.49e-8,
    (32768, "fp64", 6): 1.49e-8,
    (256, "fp64", 10): 3.26e-11,
    (512, "fp64", 10): 3.25e-11,
    (1024, "fp64", 10): 3.26e-11,
    (2048, "fp64", 10): 3.25e-11,
    (4096, "fp64", 10): 3.25e-11,
    (8192, "fp64", 10): 3.25e-11,
    (16384, "fp64", 10): 3.25e-11,
    (32768, "fp64", 10): 3.25e-11,
    (256, "fp64", 15): 6.95e-14,
    (512, "fp64", 15): 6.94e-14,
    (1024, "fp64", 15): 6.97e-14,
    (2048, "fp64", 15): 6.95e-14,
    (4096, "fp64", 15): 6.96e-14,
    (8192, "fp64", 15): 6.96e-14,
    (16384, "fp64", 15): 6.96e-14,
    (32768, "fp64", 15): 6.96e-14,
    (256, "fp64", 21): 5.71e-16,
    (512, "fp64", 21): 5.88e-16,
    (1024, "fp64", 21): 6.96e-16,
    (2048, "fp64", 21): 7.45e-16,
    (4096, "fp64", 21): 8.19e-16,
    (8192, "fp64", 21): 9.41e-16,
    (16384, "fp64", 21): 1.14e-15,
    (32768, "fp64", 21): 1.46e-15,
}


def render_final_report(main_by_key, all_main, thread_rows, raw_rows, native_summary) -> str:
    local = []
    local_scaled = []
    for n in SIZES:
        vals = []
        for precision, budget, _label in (
            ("fp32", 6, "FP32"),
            ("fp64", 6, "p6"),
            ("fp64", 10, "p10"),
            ("fp64", 15, "p15"),
            ("fp64", 21, "p21"),
        ):
            r = main_by_key[(precision, n, budget)]
            vals.append(f"{float(r['eF_mkl']):.3g}")
        scaled_vals = [
            f"{float(main_by_key[(p, n, b)]['e_scaled_mkl']):.3g}"
            for p, b, _label in (
                ("fp32", 6, "FP32"),
                ("fp64", 6, "p6"),
                ("fp64", 10, "p10"),
                ("fp64", 15, "p15"),
                ("fp64", 21, "p21"),
            )
        ]
        local.append(f"| {n} | " + " | ".join(vals) + " |")
        local_scaled.append(f"| {n} | " + " | ".join(scaled_vals) + " |")

    perf = []
    for n in SIZES:
        cells = []
        for precision, budget, _label in (
            ("fp32", 6, "FP32"),
            ("fp64", 6, "p6"),
            ("fp64", 10, "p10"),
            ("fp64", 15, "p15"),
            ("fp64", 21, "p21"),
        ):
            r = main_by_key[(precision, n, budget)]
            times = require_ten(r, "raw_total_s", MAIN_SOURCES[0])
            cells.append(
                f"{statistics.mean(times):.4g}±{statistics.stdev(times):.2g} / {float(r['mkl_sgemm_dgemm_s']):.4g} / {float(r['speedup']):.3g}"
            )
        perf.append(f"| {n} | " + " | ".join(cells) + " |")

    hp = []
    for n in SIZES:
        vals = []
        for precision, budget, _label in (
            ("fp32", 6, "FP32"),
            ("fp64", 6, "p6"),
            ("fp64", 10, "p10"),
            ("fp64", 15, "p15"),
            ("fp64", 21, "p21"),
        ):
            r = main_by_key[(precision, n, budget)]
            scope = r["hp_scope"]
            vals.append(f"{float(r['eF_hp']):.3g} ({scope})")
        hp.append(f"| {n} | " + " | ".join(vals) + " |")

    threads = []
    for n in (1024, 4096, 16384):
        vals = []
        for t in (2, 4, 8, 16, 32, 64):
            r = next(x for x in thread_rows if int(x["N"]) == n and int(x["threads"]) == t)
            vals.append(
                f"{float(r['total_s_mean']):.4g}±{statistics.stdev(require_ten(r, 'raw_total_s', BENCH / f'thread_scaling_fp32_n{n}_t{t}.csv')):.2g}"
            )
        threads.append(f"| {n} | " + " | ".join(vals) + " |")

    raw_table = []
    for r in raw_rows:
        raw_table.append(
            f"| {r['N']} | {float(r['seconds_mean']):.4g} | {float(r['TFLOP_s']):.4g} | {r['mkl_version']} | `{r['mkl_runtime_path']}` |"
        )
    p21_n256 = main_by_key[("fp64", 256, 21)]
    p21_observed = float(p21_n256["eF_hp"])
    p21_paper = PAPER_TABLE4_EF[(256, "fp64", 21)]
    p21_ratio = p21_observed / p21_paper
    native_lines = []
    for key, summary in sorted(native_summary["summaries"].items()):
        method, budget = key.rsplit("/p", 1)
        native_lines.append(
            f"| {method} | {budget} | {summary['eF_selected_longdouble']:.5g} | "
            f"{summary['eF_actual_amx']:.5g} | {summary['product_store_mismatches']} | {summary['max_ulp']} |"
        )

    return f'''# ozAMX 论文复现实验结果

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
{chr(10).join(local)}

| N | FP32 scaledmax vs MKL | FP64-p6 | FP64-p10 | FP64-p15 | FP64-p21 |
|---:|---:|---:|---:|---:|---:|
{chr(10).join(local_scaled)}

| N | 本机 FP32 eF_hp scope | p6 | p10 | p15 | p21 |
|---:|---:|---:|---:|---:|---:|
{chr(10).join(hp)}

正式 benchmark N=256 FP64-p21 headline `eF_mkl` 为 `6.39e-15`，对照论文 `5.71×10^-16`，差约11.2倍；direct binary128 独立 full-matrix 结果为 `eF_hp={p21_observed:.5g}`、`e_scaled_hp={float(p21_n256['e_scaled_hp']):.5g}`，提供本机高精度对照。FP32 `eF_mkl` 八阶为 `3.12, 3.18, 3.64, 3.74, 3.84, 3.97, 4.18, 4.58 ×10^-7`，论文 headline 为 `3.02, 3.06, 3.59, 3.72, 3.83, 3.97, 4.18, 4.58 ×10^-7`：趋势和量级接近，大阶接近，但不同平台与输入下不称为逐位/同输入复现。FP64各budget见上表，与论文headline明显不匹配。独立 N=256 literal decomposition 诊断另得到 selected-21 `eF≈6.4076×10^-15`，terminal residual约`4.0323×10^-15`、遗漏15个高阶product约`5.0015×10^-15`；这些诊断使用x87 longdouble而不是binary128。另有147,456个component/BK AMX store逐位匹配独立FP32 dot+widen，pack/padding及输出产品序列也通过独立审计。因此该差异不由被审计kernel/product计算偏差解释，且不能据未知作者seed宣称已解决。详见 [FP64_DIAGNOSTIC.md](FP64_DIAGNOSTIC.md) 和 [NATIVE_KERNEL_AUDIT.md](NATIVE_KERNEL_AUDIT.md)。非零residual投影出BF16零片为合法；非零BF16 subnormal和明显域外输入按实现边界拒绝。AMX没有可读浮点异常flag；FTZ导致的内部下溢不可一般检测，也不宣称全面支持所有FP64值域。

## Table 4 性能原始统计

每格为`AMX total mean±sample std (s) / oneMKL GEMM-only mean (s) / oneMKL时间÷AMX时间`。比值大于1才代表本机AMX在此工作范围下更快；它仍不等于论文计时，具体原始10值与其他指标在 `bench/final_main_40.csv`、`bench/final_timing_statistics.csv`。

| N | FP32 | p6 | p10 | p15 | p21 |
|---:|---|---|---|---|---|
{chr(10).join(perf)}

**逐项判断：** Table 4 的40个配置均已测；精度指标字段全部生成。full-matrix oneMKL `eF_mkl` 与论文 Table 4 headline采用同类reference定义，可用于有限数值比较；本机FP32八阶值与论文量级/趋势接近，较大阶近似一致，但输入、平台和库版本不同。FP64各budget本机误差明显较大。direct binary128 full-matrix误差只在 N=256；其他阶只有512点采样`eF_hp`，不可与论文full-matrix Frobenius指标直接比较。算法严格保留论文字面分解/产品预算，未为贴近论文值更改`rho`或切片数。

## Figure 7：FP32端到端速度比

完整八阶本机测量列在上表，定义为`oneMKL SGEMM-only time / AMX end-to-end time`。全部点由CSV计算。若点小于1，本机AMX端到端较慢；这与论文Figure 7报告的1.14×至2.56×加速不匹配。平台及scope不同，但此处本机没有复现论文速度提升。

## Figure 8：FP32线程伸缩

18个配置按N=1024/4096/16384、线程2/4/8/16/32/64完成。表中给出AMX end-to-end时间mean±sample std(s)，逐次时间和oneMKL参照见线程CSV及统计CSV。

| N | 2 threads | 4 | 8 | 16 | 32 | 64 |
|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(threads)}

## Figure 6：raw oneMKL BF16 headroom

只调用 oneMKL `cblas_gemm_bf16bf16f32`，不调用ozAMX。以下本机数据以TFLOP/s报告，并不和论文图上标注的GFLOPS绝对值混画；原文单位存在文档所述疑点。每阶10次原始计时、实际MKL版本/路径和runtime映射见 `bench/raw_bf16.csv` / `bench/raw_bf16_n<N>.csv`。

| N | mean(s) | 本机TFLOP/s | oneMKL version | runtime path |
|---:|---:|---:|---|---|
{chr(10).join(raw_table)}

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
{chr(10).join(native_lines)}

详细表及其原始 product 行见 `bench/diagnostics/alt_256/native_results.csv`；导出输入的校验和、随机流与类别说明见同目录 `metadata.json` 和 `alternative_report.json`。这里的 Python reference 使用本机 80-bit longdouble，native product 是真实 AMX；正式benchmark direct-AB oracle使用GCC binary128，两者不混为同一参考。另有一次固定输入N=256的非作者 signed-shift 单点假设诊断，其公式和 MKL/full36 对照见 [SIGNED_SHIFT_DIAGNOSTIC.md](SIGNED_SHIFT_DIAGNOSTIC.md)，不计入正式覆盖，也不改变 literal 默认算法。

## 图表、数据与有效来源

全部统计脚本根据原始CSV逐条解析，不删除统计离群点。干净主数据白名单见 [`tools/finalize_campaign_data.py`](../tools/finalize_campaign_data.py)；旧重叠/污染p6数据保留为invalid diagnostic，不进入40行合并。原始CSV及逐rep checkpoint是最终可复核依据。绘图见 `docs/figures/*.png` 及同名PDF，均标注为本机独立复现实测，不是论文点值。
'''


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="validate raw coverage/checkpoints without writing derived outputs",
    )
    parser.add_argument(
        "--merge-only",
        action="store_true",
        help="write canonical merged CSV/statistics after validation",
    )
    args = parser.parse_args()
    if args.validate_only and args.merge_only:
        raise SystemExit("choose at most one finalization phase")

    main_by_key: dict[tuple[str, int, int], dict[str, str]] = {}
    all_main: list[dict[str, str]] = []
    source_for: dict[tuple[str, int, int], Path] = {}
    for path in MAIN_SOURCES:
        prefix = {
            "full_sweep.csv": "full_sweep_progress",
            "resume_8192_p21.csv": "resume_8192_p21_progress",
            "full_sweep_16384.csv": "full_sweep_16384_progress",
            "full_sweep_32768_fp32.csv": "full_sweep_32768_fp32_progress",
        }.get(path.name)
        if path.name.startswith("full_sweep_32768_fp64_clean_p"):
            prefix = path.stem + "_progress"
        if prefix is None:
            raise SystemExit(f"no checkpoint mapping for {path.name}")
        for row in rows(path):
            n, budget = int(row["N"]), int(row["budget"])
            precision = row["precision"]
            key = precision, n, budget
            if key in main_by_key:
                raise SystemExit(f"duplicate main config {key}: {source_for[key]} and {path}")
            if row.get("distribution") != "uniform" or int(row["threads"]) != 64:
                raise SystemExit(f"unexpected main protocol in {path.name}: {key}")
            if int(row["seed"]) != 260904 + n:
                raise SystemExit(f"unexpected seed in {path.name}: {key}")
            require_ten(row, "raw_total_s", path)
            for field in ("raw_split_s", "raw_pack_s", "raw_compute_recon_s"):
                require_ten(row, field, path)
            require_complete_checkpoint(row, prefix, path)
            main_by_key[key] = row
            source_for[key] = path
            all_main.append(row)

    expected = {("fp32", n, 6) for n in SIZES} | {("fp64", n, b) for n in SIZES for b in BUDGETS}
    missing, extra = expected - set(main_by_key), set(main_by_key) - expected
    if missing or extra:
        raise SystemExit(f"main coverage mismatch: missing={sorted(missing)} extra={sorted(extra)}")

    thread_rows: list[dict[str, str]] = []
    thread_keys = set()
    for n in (1024, 4096, 16384):
        for t in (2, 4, 8, 16, 32, 64):
            path = BENCH / f"thread_scaling_fp32_n{n}_t{t}.csv"
            part = rows(path)
            if len(part) != 1:
                raise SystemExit(f"{path.name}: expected exactly one row")
            row = part[0]
            require_ten(row, "raw_total_s", path)
            key = int(row["N"]), int(row["threads"]), row["precision"]
            if key != (n, t, "fp32") or row["status"] != "ok":
                raise SystemExit(f"unexpected thread config in {path.name}")
            if key in thread_keys:
                raise SystemExit(f"duplicate thread config: {key}")
            if int(row["seed"]) != 260904 + n:
                raise SystemExit(f"unexpected thread seed in {path.name}")
            require_complete_checkpoint(row, path.stem + "_progress", path)
            thread_keys.add(key)
            thread_rows.append(row)
    if len(thread_keys) != 18:
        raise SystemExit(f"expected 18 thread configs, got {len(thread_keys)}")

    raw_rows: list[dict[str, str]] = []
    for n in SIZES:
        path = BENCH / f"raw_bf16_n{n}.csv"
        part = rows(path)
        if len(part) != 1:
            raise SystemExit(f"{path.name}: expected exactly one row")
        row = part[0]
        samples = require_ten(row, "raw_seconds", path)
        if int(row["N"]) != n or row.get("routine") != "raw_mkl_bf16bf16fp32":
            raise SystemExit(f"unexpected raw BF16 config in {path.name}")
        if int(row["seed"]) != 260904 + n:
            raise SystemExit(f"unexpected raw BF16 seed in {path.name}")
        row["_samples"] = samples  # type: ignore[assignment]
        raw_rows.append(row)

    if args.validate_only:
        print(
            f"validated main={len(all_main)}/40 thread={len(thread_rows)}/18 raw_bf16={len(raw_rows)}/8; every benchmark checkpoint is complete with 10 finite timed samples"
        )
        return

    # Merge only the explicitly enumerated valid campaign inputs.
    merged_path = BENCH / "final_main_40.csv"
    fields = list(all_main[0]) + ["source_csv"]
    with merged_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in sorted(all_main, key=lambda r: (int(r["N"]), r["precision"], int(r["budget"]))):
            out = dict(row)
            out["source_csv"] = (
                source_for[(row["precision"], int(row["N"]), int(row["budget"]))]
                .relative_to(ROOT)
                .as_posix()
            )
            writer.writerow(out)

    summary_path = BENCH / "final_timing_statistics.csv"
    stat_fields = [
        "campaign",
        "precision",
        "budget",
        "N",
        "threads",
        "metric",
        "n",
        "mean",
        "sample_std",
        "min",
        "max",
        "source_csv",
    ]
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=stat_fields, lineterminator="\n")
        w.writeheader()
        for row in all_main + thread_rows:
            src = (
                source_for[(row["precision"], int(row["N"]), int(row["budget"]))]
                if row in all_main
                else BENCH / f"thread_scaling_fp32_n{row['N']}_t{row['threads']}.csv"
            )
            for field, metric in (
                ("raw_split_s", "split_s"),
                ("raw_pack_s", "pack_s"),
                ("raw_compute_recon_s", "compute_recon_s"),
                ("raw_total_s", "total_s"),
            ):
                values = require_ten(row, field, src)
                w.writerow(
                    {
                        "campaign": "main" if row in all_main else "thread",
                        "precision": row["precision"],
                        "budget": row["budget"],
                        "N": row["N"],
                        "threads": row["threads"],
                        "metric": metric,
                        "n": 10,
                        "mean": statistics.mean(values),
                        "sample_std": statistics.stdev(values),
                        "min": min(values),
                        "max": max(values),
                        "source_csv": src.relative_to(ROOT).as_posix(),
                    }
                )
        for row in raw_rows:
            values = row["_samples"]
            w.writerow(
                {
                    "campaign": "raw_bf16",
                    "precision": "bf16bf16f32",
                    "budget": "",
                    "N": row["N"],
                    "threads": row["threads"],
                    "metric": "seconds",
                    "n": 10,
                    "mean": statistics.mean(values),
                    "sample_std": statistics.stdev(values),
                    "min": min(values),
                    "max": max(values),
                    "source_csv": f"bench/raw_bf16_n{row['N']}.csv",
                }
            )

    # Keep raw original files as-is; this is the aggregate public interface.
    raw_fields = [k for k in raw_rows[0] if not k.startswith("_")]
    with (BENCH / "raw_bf16.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=raw_fields, lineterminator="\n")
        w.writeheader()
        w.writerows([{k: v for k, v in row.items() if not k.startswith("_")} for row in raw_rows])

    if args.merge_only:
        print(
            "canonical CSV merge and per-configuration statistics written after successful coverage validation"
        )
        return

    required_artifacts = [
        BENCH / "diagnostics/alt_256/alternative_report.json",
        BENCH / "diagnostics/alt_256/native_results.csv",
        BENCH / "diagnostics/alt_256/alternative_validation.json",
        BENCH / "diagnostics/alt_256/native_validation.json",
        DOCS / "trace/ctest.log",
        *(
            DOCS / "figures" / f"{name}.{suffix}"
            for name in (
                "accuracy_vs_size",
                "speedup_vs_mkl",
                "time_breakdown",
                "thread_scaling",
                "raw_bf16_throughput",
            )
            for suffix in ("png", "pdf")
        ),
    ]
    missing_artifacts = [
        p.relative_to(ROOT).as_posix() for p in required_artifacts if not p.is_file()
    ]
    if missing_artifacts:
        raise SystemExit(
            f"final report is deferred; required diagnostic/plot artifacts missing: {missing_artifacts}"
        )
    ctest_log = (DOCS / "trace/ctest.log").read_text(encoding="utf-8", errors="replace")
    if "100% tests passed" not in ctest_log:
        raise SystemExit("CTest result log does not contain a passing summary")
    native_summary = json.loads(
        (BENCH / "diagnostics/alt_256/native_validation.json").read_text(encoding="utf-8")
    )
    ctest_summary = {
        "log": "docs/trace/ctest.log",
        "sha256": sha256(DOCS / "trace/ctest.log"),
        "result": "100% tests passed",
    }

    manifest_path = DOCS / "FULL_SWEEP_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["status"] = "complete"
    manifest["completed_utc"] = (
        __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    )
    manifest["validated_coverage"] = {
        "main_configs": len(all_main),
        "expected_main_configs": 40,
        "thread_configs": len(thread_rows),
        "expected_thread_configs": 18,
        "raw_bf16_sizes": len(raw_rows),
        "expected_raw_bf16_sizes": 8,
        "timed_repetitions_each": 10,
        "unique_main_keys": len(main_by_key),
    }
    manifest["canonical_ctest"] = ctest_summary
    manifest["native_alternative_diagnostic"] = native_summary
    manifest["validated_sources_sha256"] = {
        p.relative_to(ROOT).as_posix(): sha256(p) for p in MAIN_SOURCES
    }
    thread_sources = [
        BENCH / f"thread_scaling_fp32_n{n}_t{t}.csv"
        for n in (1024, 4096, 16384)
        for t in (2, 4, 8, 16, 32, 64)
    ]
    raw_sources = [BENCH / f"raw_bf16_n{n}.csv" for n in SIZES]
    manifest["validated_input_sha256"] = {
        p.relative_to(ROOT).as_posix(): sha256(p)
        for p in [*MAIN_SOURCES, *thread_sources, *raw_sources]
    }
    manifest["derived_outputs"] = [
        "bench/final_main_40.csv",
        "bench/final_timing_statistics.csv",
        "bench/raw_bf16.csv",
        "docs/figures/*.png",
        "docs/figures/*.pdf",
    ]
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # Replace the old pilot-only status report once the full protocol validates.
    result_path = DOCS / "REPRODUCTION_RESULTS.md"
    result_path.write_text(
        render_final_report(main_by_key, all_main, thread_rows, raw_rows, native_summary),
        encoding="utf-8",
    )

    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    text = text.replace(
        "已完成 64 个线程的 AMX 功能验证和多阶数 pilot；Table 4 完整尺寸/预算的十次正式 campaign、线程伸缩与 raw BF16 测量正在按锁保护的串行队列中执行。",
        "已完成 64 个线程的 AMX 功能验证、Table 4 的 40 个配置、FP32 线程伸缩 18 个配置及 raw BF16 的 8 个阶数；每个正式配置均通过 1 次 warm-up 和 10 次计时校验。",
    )
    text = text.replace(
        "截至已完成的 pilot 和 N=16384/N=32768 部分配置，本机端到端 AMX 路径慢于 MKL GEMM-only 基线；最终结论以完整数据更新，不把局部结果称为完整复现。",
        "完整原始结果、每次 timing 和统计、论文逐项覆盖状态、误差差异与图表见 [docs/REPRODUCTION_RESULTS.md](docs/REPRODUCTION_RESULTS.md)；本机实测 AMX 端到端与 MKL GEMM-only 的比较采用不同计时范围，并按结果逐项报告，不宣称数值或性能完全匹配论文。",
    )
    readme.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
