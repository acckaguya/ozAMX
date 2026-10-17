"""Static audit figures. Run with matplotlib; no GEMM load is executed."""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

base = Path(__file__).resolve().parents[1]
out = Path(__file__).resolve().parent
rows = list(csv.DictReader((base / "independent/run_20261016/results.csv").open()))
analysis = json.loads((base / "independent/run_20261016/analysis.json").read_text())
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
colors = ["#2166ac", "#b35806", "#1b7837"]
routines = ["ozamx_fp32", "mkl_sgemm", "mkl_bf16"]
labels = ["ozAMX FP32", "oneMKL SGEMM", "oneMKL BF16"]
fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), sharey=True)
for ax, family, title in zip(axes, ["dyadic_exact", "uniform_fp32"], ["Dyadic exact inputs", "Ordinary FP32 inputs"]):
    for x, routine, label, color in zip(range(3), routines, labels, colors):
        values = [1000 * float(r["raw_wall_s"]) for r in rows if r["N"] == "4096" and r["family"] == family and r["routine"] == routine and r["warmup"] == "0"]
        group = next(g for g in analysis["groups"] if g["N"] == 4096 and g["family"] == family and g["routine"] == routine)
        ax.scatter(x + np.linspace(-0.10, 0.10, len(values)), values, s=28, color=color, alpha=.8)
        ax.scatter([x], [np.mean(values)], marker="D", s=45, color="black", zorder=4)
        ax.text(x, 45.4, f'{group["effective_TFLOP_s"]:.2f} TF/s', ha="center", fontsize=10, color=color)
    ax.set_xticks(range(3), ["ozAMX\nFP32", "oneMKL\nSGEMM", "oneMKL\nBF16"])
    ax.set_title(title)
    ax.set_ylim(0, 49)
    ax.grid(axis="y", alpha=.2)
axes[0].set_ylabel("Full synchronous API wall time (ms)")
fig.suptitle("Independent N=4096 audit: all 10 timed calls per routine", fontsize=12)
fig.text(.5, .015, "Dots: retained individual calls. Black diamonds: arithmetic mean time.\nRates: 2N^3 / mean(time), 64 cores; validation between calls changes historical campaign conditions.", ha="center", fontsize=9)
fig.tight_layout(rect=(0, .09, 1, .94))
for suffix in ["png", "pdf"]:
    fig.savefig(out / f"independent_n4096.{suffix}", dpi=180)
plt.close(fig)

data = json.loads((base / "evidence/recomputed_summary.json").read_text())
groups = [r for r in data["fresh_runs"] if r["N"] == 256]
assert len(groups) == 5
names = ["FP32 p6", "FP64 p6", "FP64 p10", "FP64 p15", "FP64 p21"]
current = [r["eF_mkl"] for r in groups]
paper = [r["paper_eF"] for r in groups]
x = np.arange(5)
fig, ax = plt.subplots(figsize=(8, 4.8))
ax.bar(x-.18, paper, .36, label="Paper Table 4", color="#999999")
ax.bar(x+.18, current, .36, label="Current build vs oneMKL", color="#2166ac")
ax.set_yscale("log")
ax.set_ylim(1e-16, 2e-5)
ax.set_xticks(x, names)
for i, r in enumerate(groups):
    ax.text(i, max(current[i], paper[i])*2.3, f'{r["eF_over_paper"]:.2f}x', ha="center", fontsize=10)
ax.set_ylabel("Relative Frobenius error eF")
ax.set_title("N=256: accuracy gap persists in the current build")
ax.legend(loc="upper right")
ax.grid(axis="y", alpha=.2)
fig.text(.5, .015, "Different random matrices: empirical paper values are comparison points, not pass/fail tolerances.\nThe separate binary128 audit uses N=64; its results are not substituted into these N=256 bars.", ha="center", fontsize=9)
fig.tight_layout(rect=(0, .09, 1, 1))
for suffix in ["png", "pdf"]:
    fig.savefig(out / f"n256_accuracy_gap.{suffix}", dpi=180)
plt.close(fig)
print("Wrote 2 PNG and 2 PDF figures from retained audit evidence.")
