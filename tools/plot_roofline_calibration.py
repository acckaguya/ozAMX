#!/usr/bin/env python3
"""Plot roofline diagnostics from saved artifacts; performs no benchmark run."""
from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CAL = ROOT / "bench/8454h/roofline/calibration"
SUMMARY = CAL / "kernel_summary.json"
PLATFORM = ROOT / "bench/8454h/platform_baseline.csv"
MEMORY = ROOT / "bench/8454h/roofline/memory_calibration_20261013.csv"
OUT = ROOT / "docs/figures"


def find_config(configs, kernel, threads, bytes_per_worker=4096, stride=0):
    return next(
        c
        for c in configs
        if c["kernel"] == kernel
        and c["threads"] == threads
        and c["worker_input_bytes"] == bytes_per_worker
        and c["stride_elements"] == stride
    )


def median_sample_sd(config, metric):
    stats = config["metrics"][metric]
    return stats["median"], stats["sample_sd"]


def mem_refs():
    old = {1: [], 32: [], 64: []}
    with PLATFORM.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["benchmark"] == "memory_triad":
                old[int(row["threads"])].append(float(row["rate_per_s"]))
    old = {t: statistics.median(v) for t, v in old.items()}
    new = {t: [] for t in (1, 32, 64)}
    with MEMORY.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["level"] == "DRAM_footprint" and row["record_type"] == "timed":
                new[int(row["threads"])].append(float(row["logical_B_per_s"]))
    new = {t: statistics.median(v) for t, v in new.items()}
    return old, new


def points_for_product(configs, threads):
    definitions = [
        ("P6 no-reconstruction (diagnostic)", "p6_no_reconstruct", "#2864a0", "o"),
        ("P6 with reconstruction", "p6_with_reconstruct", "#2864a0", "s"),
        ("P21 no-reconstruction (diagnostic)", "p21_no_reconstruct", "#d17b0f", "^"),
        ("P21 with reconstruction", "p21_with_reconstruct", "#d17b0f", "D"),
    ]
    for label, kernel, color, marker in definitions:
        cfg = find_config(configs, kernel, threads, 196608, 128)
        ai = cfg["metrics"]["logical_arithmetic_intensity_ops_per_byte"]["median"]
        perf, sd = median_sample_sd(cfg, "total_ops_per_s")
        yield label, ai, perf / 1e12, sd / 1e12, color, marker


def save(fig, stem):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{stem}.svg", bbox_inches="tight")
    fig.savefig(OUT / f"{stem}.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def main():
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    configs = summary["configurations"]
    old_bw, new_bw = mem_refs()
    plt.rcParams.update(
        {
            "font.size": 8.5,
            "axes.grid": True,
            "grid.alpha": 0.24,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )
    x = np.logspace(-1.4, 1.45, 240)
    colors = {1: "#888888", 32: "#4c78a8", 64: "#222222"}

    # Overall logical-payload AI roofline: compute roof is measured AMX TDP;
    # slope lines are explicitly labeled payload-rate references, not PMU roofs.
    fig, axes = plt.subplots(1, 3, figsize=(14.4, 4.8), sharey=True)
    handles = []
    for ax, threads in zip(axes, (1, 32, 64)):
        ceiling_cfg = find_config(configs, "amx_register", threads)
        ceiling, ceiling_sd = median_sample_sd(ceiling_cfg, "amx_or_add_ops_per_s")
        ceiling /= 1e12
        ax.axhline(
            ceiling,
            color=colors[threads],
            linewidth=1.4,
            label=f"AMX register ceiling {ceiling:.1f} TF/s",
        )
        candidates = []
        l2cfg = find_config(configs, "tileload", threads, 1048576)
        candidates.append(
            (median_sample_sd(l2cfg, "logical_B_per_s")[0], "1 MiB/worker TILELOAD payload", "--")
        )
        candidates.append((old_bw[threads], "legacy 768 MiB triad logical reference", ":"))
        candidates.append((new_bw[threads], "new 24 MiB/worker triad logical reference", "-."))
        for bw, label, style in candidates:
            roof = np.minimum(ceiling, (bw * x) / 1e12)
            ax.plot(
                x,
                roof,
                linestyle=style,
                linewidth=1.05,
                alpha=0.72,
                label=f"{label}: {bw/1e9:.0f} GB/s",
            )
        for label, ai, perf, sd, color, marker in points_for_product(configs, threads):
            line = ax.errorbar(
                ai,
                perf,
                yerr=sd,
                marker=marker,
                color=color,
                markerfacecolor=("white" if "no-reconstruction" in label else color),
                markeredgewidth=1.2,
                capsize=2,
                linestyle="none",
                markersize=5,
                label=label,
            )
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(0.035, 32)
        ax.set_ylim(0.4, 240)
        ax.set_title(f"{threads} worker{'s' if threads != 1 else ''}")
        ax.set_xlabel("Total logical arithmetic intensity (ops/byte)")
        ax.grid(True, which="both")
    axes[0].set_ylabel("Measured/derived compute rate (TFLOP/s)")
    handles, labels = axes[-1].get_legend_handles_labels()
    fig.suptitle("8454H AMX roofline: total logical-payload intensity", y=1.02)
    fig.legend(
        handles,
        labels,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.15),
        ncol=3,
        frameon=False,
        fontsize=7.2,
    )
    fig.text(
        0.5,
        -0.04,
        "Dashed slopes use hand-counted logical payload rates; no PMU traffic or cache residency was measured. "
        "Open markers omit required reconstruction and are diagnostic only.",
        ha="center",
        fontsize=7.2,
    )
    fig.tight_layout(rect=(0, 0.14, 1, 0.98))
    save(fig, "8454H_ROOFLINE_AMX_LOGICAL_AI")

    # Stage view adds standalone SIMD reconstruction, showing the very different
    # operational intensities and the AMX ceiling. It keeps cache lines labeled
    # as candidate logical-payload references.
    fig, axes = plt.subplots(1, 3, figsize=(14.4, 5.4), sharey=True)
    for ax, threads in zip(axes, (1, 32, 64)):
        ceiling_cfg = find_config(configs, "amx_register", threads)
        ceiling = median_sample_sd(ceiling_cfg, "amx_or_add_ops_per_s")[0] / 1e12
        ax.axhline(
            ceiling,
            color=colors[threads],
            linewidth=1.4,
            label=f"AMX register ceiling {ceiling:.1f} TF/s",
        )
        # These are logical-byte-rate references only. They are not measured
        # cache-level or DRAM roofs because the experiment collected no PMU data.
        tile_cfg = find_config(configs, "tileload", threads, 1048576)
        stage_refs = [
            (
                median_sample_sd(tile_cfg, "logical_B_per_s")[0],
                "1 MiB/worker TILELOAD payload",
                "--",
            ),
            (old_bw[threads], "legacy triad logical reference", ":"),
            (new_bw[threads], "new triad logical reference", "-."),
        ]
        for bw, label, style in stage_refs:
            ax.plot(
                x,
                np.minimum(ceiling, bw * x / 1e12),
                linestyle=style,
                linewidth=0.9,
                alpha=0.55,
                color="#777777",
                label=f"{label} ({bw/1e9:.0f} GB/s)",
            )
        for label, ai, perf, sd, color, marker in points_for_product(configs, threads):
            ax.errorbar(
                ai,
                perf,
                yerr=sd,
                marker=marker,
                color=color,
                markerfacecolor=("white" if "no-reconstruction" in label else color),
                markeredgewidth=1.2,
                capsize=2,
                linestyle="none",
                markersize=5,
                label=label,
            )
        recon_defs = [
            ("FP64 reconstruction stride 128", "reconstruct64", 128, "#59a14f", "v"),
            ("FP64 reconstruction stride 136", "reconstruct64", 136, "#59a14f", "P"),
            ("FP32 reconstruction stride 128", "reconstruct32", 128, "#b279a2", "<"),
            ("FP32 reconstruction stride 144", "reconstruct32", 144, "#b279a2", ">"),
        ]
        for label, kernel, stride, color, marker in recon_defs:
            cfg = find_config(configs, kernel, threads, 4096, stride)
            ai = cfg["metrics"]["logical_arithmetic_intensity_ops_per_byte"]["median"]
            perf, sd = median_sample_sd(cfg, "amx_or_add_ops_per_s")
            ax.errorbar(
                ai,
                perf / 1e12,
                yerr=sd / 1e12,
                marker=marker,
                color=color,
                capsize=2,
                linestyle="none",
                markersize=5,
                label=label,
            )
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(0.035, 32)
        ax.set_ylim(0.005, 240)
        ax.set_title(f"{threads} worker{'s' if threads != 1 else ''}")
        ax.set_xlabel("Stage logical arithmetic intensity (ops/byte)")
        ax.grid(True, which="both")
    axes[0].set_ylabel("Stage compute rate (TFLOP/s)")
    handles, labels = axes[-1].get_legend_handles_labels()
    fig.suptitle("8454H roofline diagnostics by compute/reconstruction stage", y=1.02)
    fig.legend(
        handles,
        labels,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.25),
        ncol=3,
        frameon=False,
        fontsize=7.2,
    )
    fig.text(
        0.5,
        -0.05,
        "Slopes are hand-counted logical-payload rate references, not physical cache/DRAM roofs; "
        "no cache-level PMU coordinates are available.",
        ha="center",
        fontsize=7.2,
    )
    fig.tight_layout(rect=(0, 0.22, 1, 0.98))
    save(fig, "8454H_ROOFLINE_STAGE_DIAGNOSTIC")


if __name__ == "__main__":
    main()
