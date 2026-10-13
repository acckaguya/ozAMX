#!/usr/bin/env python3
"""Create exportable static figures from validated local campaign CSVs."""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "bench"
OUT = ROOT / "docs" / "figures"
SIZES = (256, 512, 1024, 2048, 4096, 8192, 16384, 32768)


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save(fig: plt.Figure, stem: str) -> None:
    fig.savefig(OUT / f"{stem}.png", dpi=220, bbox_inches="tight")
    fig.savefig(OUT / f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": 0.25,
                         "figure.facecolor": "white", "axes.facecolor": "white"})
    rows = read(BENCH / "final_main_40.csv")
    by = {(r["precision"], int(r["N"]), int(r["budget"])): r for r in rows}
    variants = [("fp32", 6, "FP32"), ("fp64", 6, "FP64 p6"), ("fp64", 10, "FP64 p10"),
                ("fp64", 15, "FP64 p15"), ("fp64", 21, "FP64 p21")]

    # Full-matrix error relative to MKL reference; this is local measured data.
    fig, ax = plt.subplots(figsize=(7.2, 4.3))
    for precision, budget, label in variants:
        rr = [by[(precision, n, budget)] for n in SIZES]
        ax.loglog(SIZES, [float(r["eF_mkl"]) for r in rr], marker="o", label=label)
    ax.set_xlabel("Matrix order N")
    ax.set_ylabel("Relative Frobenius error vs oneMKL")
    ax.set_title("Local reproduction: measured error (not paper data)")
    ax.legend(ncol=2)
    save(fig, "accuracy_vs_size")

    # End-to-end AMX / GEMM-only MKL ratio, so values below one mean slower AMX.
    fig, ax = plt.subplots(figsize=(7.2, 4.3))
    for precision, budget, label in variants:
        rr = [by[(precision, n, budget)] for n in SIZES]
        ax.semilogx(SIZES, [float(r["speedup"]) for r in rr], marker="o", label=label)
    ax.axhline(1.0, color="black", linestyle="--", linewidth=1)
    ax.set_xlabel("Matrix order N")
    ax.set_ylabel("oneMKL GEMM-only / AMX end-to-end time")
    ax.set_title("Local reproduction: timing-range ratio (not paper data)")
    ax.legend(ncol=2)
    save(fig, "speedup_vs_mkl")

    # Fraction of AMX total spent in the three profiled segments.
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    x = list(range(len(SIZES)))
    width = 0.15
    for q, (precision, budget, label) in enumerate(variants):
        rr = [by[(precision, n, budget)] for n in SIZES]
        totals = [float(r["total_s_mean"]) for r in rr]
        split = [float(r["split_s_mean"]) / t for r, t in zip(rr, totals)]
        pack = [float(r["pack_s_mean"]) / t for r, t in zip(rr, totals)]
        compute = [float(r["compute_recon_s_mean"]) / t for r, t in zip(rr, totals)]
        xx = [i + (q - 2) * width for i in x]
        ax.bar(xx, split, width, label="split" if q == 0 else None, color="#4C78A8", alpha=0.75)
        ax.bar(xx, pack, width, bottom=split, label="pack" if q == 0 else None, color="#F2CF5B", alpha=0.8)
        bottom = [a + b for a, b in zip(split, pack)]
        ax.bar(xx, compute, width, bottom=bottom,
               label="compute + reconstruction" if q == 0 else None, color="#59A14F", alpha=0.75)
    ax.set_xticks(x, [str(n) for n in SIZES])
    ax.set_xlabel("Matrix order N")
    ax.set_ylabel("Fraction of AMX end-to-end time")
    ax.set_ylim(0, 1.03)
    ax.set_title("Local reproduction: time breakdown (not paper data)")
    ax.legend(title="Fraction of total")
    fig.subplots_adjust(bottom=0.19)
    fig.text(0.5, 0.025,
             "Within each N group, bars left to right: FP32, FP64-p6, FP64-p10, FP64-p15, FP64-p21",
             ha="center", va="bottom", fontsize=8)
    save(fig, "time_breakdown")

    # FP32 threading series; report speedup relative to two threads and mean time.
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    for n in (1024, 4096, 16384):
        rr = [read(BENCH / f"thread_scaling_fp32_n{n}_t{t}.csv")[0] for t in (2, 4, 8, 16, 32, 64)]
        threads = [int(r["threads"]) for r in rr]
        times = [float(r["total_s_mean"]) for r in rr]
        axes[0].plot(threads, times, marker="o", label=f"N={n}")
        axes[1].plot(threads, [times[0] / t for t in times], marker="o", label=f"N={n}")
    axes[0].set_xlabel("OpenMP threads")
    axes[0].set_ylabel("AMX end-to-end time (s)")
    axes[0].set_title("Measured time")
    axes[1].set_xlabel("OpenMP threads")
    axes[1].set_ylabel("Speedup vs 2 threads")
    axes[1].set_title("Measured scaling")
    axes[1].axhline(1, color="black", linestyle="--", linewidth=1)
    for ax in axes:
        ax.legend()
    fig.suptitle("Local reproduction: FP32 thread scaling (not paper data)")
    save(fig, "thread_scaling")

    raw = read(BENCH / "raw_bf16.csv")
    fig, ax = plt.subplots(figsize=(7.2, 4.3))
    ax.loglog([int(r["N"]) for r in raw], [float(r["TFLOP_s"]) for r in raw], marker="o", color="#E15759")
    ax.set_xlabel("Matrix order N")
    ax.set_ylabel("oneMKL BF16 GEMM throughput (TFLOP/s)")
    ax.set_title("Local raw BF16 headroom (not paper data)")
    save(fig, "raw_bf16_throughput")


if __name__ == "__main__":
    main()
