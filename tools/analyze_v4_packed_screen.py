#!/usr/bin/env python3
"""Offline integrity, memory and descriptive analysis for the V4 packed screen.

Reads the immutable candidate records and source snapshots. It does not build,
test, gate, or run benchmarks. Re-running after a screen gains data refreshes
analysis.json and docs/8454H_V4_PACKED_LAYOUT_RESULTS.md.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN = ROOT / "bench/8454h/roofline_v4/search_runs/packed_rotation_screen_20261014T101506Z"
REPORT = ROOT / "docs/8454H_V4_PACKED_LAYOUT_RESULTS.md"
BUDGETS = (6, 10, 15, 21)
CSV_COLUMNS = 37
REPS = 3
N_EXPECTED = 8192
THREADS_EXPECTED = 64
CPUSET_EXPECTED = "0-63"
FROZEN_SHA = "73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c"
MKL_SHA = "b2ff0e31d7cd18c91813d8f6500f37665597d89de22649d90687aa6bf7bd2c0f"
CACHE_BYTES = 2 << 30


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def parse_vec(value: str, label: str, expected: int = REPS) -> list[float]:
    vals = [float(x) for x in value.split(";") if x.strip()]
    if len(vals) != expected or not all(math.isfinite(x) for x in vals):
        raise ValueError(f"{label}: expected {expected} finite samples, got {len(vals)}")
    return vals


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f, strict=True)
        fields = list(r.fieldnames or [])
        if len(fields) != CSV_COLUMNS:
            raise ValueError(f"expected {CSV_COLUMNS} CSV columns; found {len(fields)}")
        return fields, list(r)


def close(a: float, b: float, rel: float = 1e-9, abs_: float = 2e-9) -> bool:
    return math.isclose(a, b, rel_tol=rel, abs_tol=abs_)


def mean_median_sd(samples: list[float]) -> dict[str, Any]:
    return {
        "mean_s": statistics.mean(samples),
        "median_s": statistics.median(samples),
        "sample_sd_s": statistics.stdev(samples) if len(samples) > 1 else None,
        "raw_s": samples,
    }


def parse_budget_depth(source: str) -> dict[int, int]:
    # Keep the mapping source-derived and fail loudly if its syntax/values change.
    import re

    m = re.search(r"int\s+budget_depth\s*\([^)]*\)\s*\{(.*?)\}", source, re.S)
    if not m:
        raise ValueError("could not locate source gemm.cpp budget_depth mapping")
    pairs = {
        int(b): int(d)
        for b, d in re.findall(r"ProductBudget::p(6|10|15|21)\s*:\s*return\s*(\d+)", m.group(1))
    }
    if set(pairs) != set(BUDGETS):
        raise ValueError(f"unexpected budget_depth mapping: {pairs}")
    return pairs


def expected_candidates(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for i, vals in enumerate(dataset.get("candidates", []), 1):
        if len(vals) != 4:
            raise ValueError(f"candidate {i} config must have four fields")
        ag, bg, ar, br = map(int, vals)
        cid = f"a{ag}_b{bg}_ra{ar}_rb{br}"
        out.append(
            {
                "index": i,
                "candidate_id": cid,
                "a_gap_bytes": ag,
                "b_gap_bytes": bg,
                "a_rotation": ar,
                "b_rotation": br,
                "tag": f"candidate_{i:02d}_{cid}_n8192_fp64",
            }
        )
    return out


def verify_source(meta: dict[str, Any], source_root: Path) -> dict[str, Any]:
    declared = meta.get("source_sha256", {})
    items = []
    for rel, expected in sorted(declared.items()):
        path = source_root / rel
        actual = sha256(path) if path.is_file() else None
        items.append(
            {
                "path": rel,
                "expected_sha256": expected,
                "actual_sha256": actual,
                "matches": actual == expected,
            }
        )
    return {
        "file_count": len(items),
        "matches": bool(items) and all(x["matches"] for x in items),
        "files": items,
    }


def allocation(
    meta: dict[str, Any], budget_depth: dict[int, int], n: int, gaps: tuple[int, int]
) -> dict[str, Any]:
    ag, bg = gaps
    depth_by_budget = budget_depth
    out = {}
    for budget in BUDGETS:
        slices = depth_by_budget[budget]
        # Actual stored uint16 component slabs: one N^2 plane for A and one for B,
        # for each BF16 slice. The source bounds are panel-aligned at N=8192.
        base_payload = 4 * slices * n * n
        slab_count_a = (n // 32) * (n // 256)
        slab_count_b = (n // 32) * (n // 256)
        output_gap = slices * (slab_count_a * ag + slab_count_b * bg)
        packed_alloc = base_payload + output_gap
        # split_packed_residual64 allocates one double residual plane per packed
        # element while packing A, then reuses the same-sized pool block for B.
        base_residual = 8 * n * n
        residual_gap = 4 * (slab_count_a * ag + slab_count_b * bg)
        residual_peak = base_residual + residual_gap
        peak_workspace = packed_alloc + residual_peak
        # The cache is per caller thread and caps retained workspaces, not live
        # allocation. A single allocation larger than the limit is freed at end.
        after_cache_retention = min(peak_workspace, CACHE_BYTES)
        declared_rows = meta.get("packed_allocation_estimates", [])
        declared = next((x for x in declared_rows if int(x.get("budget", -1)) == budget), None)
        out[str(budget)] = {
            "stored_bf16_slices_from_source": slices,
            "packed_a_b_payload_bytes": base_payload,
            "gap_padding_bytes_in_packed_arrays": output_gap,
            "packed_a_b_allocated_bytes": packed_alloc,
            "temporary_residual_base_bytes_one_operand": base_residual,
            "temporary_residual_gap_bytes": residual_gap,
            "peak_packed_plus_residual_workspace_bytes_estimate": peak_workspace,
            "two_gibibyte_per_thread_workspace_cache_bytes": CACHE_BYTES,
            "peak_workspace_over_cache_limit_bytes": max(0, peak_workspace - CACHE_BYTES),
            "upper_bound_bytes_retained_by_cache_after_call": after_cache_retention,
            "metadata_declared_packed_allocation_bytes": (
                int(declared["packed_output_allocation_bytes"]) if declared else None
            ),
            "metadata_declared_padding_extra_bytes": (
                int(declared["padding_extra_bytes"]) if declared else None
            ),
            "metadata_payload_estimate_matches_source": bool(
                declared and int(declared["packed_output_allocation_bytes"]) == packed_alloc
            ),
            "metadata_padding_estimate_matches_source": bool(
                declared and int(declared["padding_extra_bytes"]) == output_gap
            ),
        }
    return out


def read_result_record(
    run: Path,
    expected: dict[str, Any],
    source_root: Path,
    budget_depth: dict[int, int],
    dataset: dict[str, Any],
) -> dict[str, Any]:
    tag = expected["tag"]
    rec = run / "records" / tag
    entry: dict[str, Any] = {
        **expected,
        "record_dir": str(rec.relative_to(run)),
        "complete": False,
        "validation_errors": [],
        "budgets": {},
    }
    errors: list[str] = entry["validation_errors"]
    if not rec.is_dir():
        errors.append("record directory missing")
        return entry
    metadata_path = rec / "metadata.json"
    command_path = rec / "command.json"
    result_path = rec / "result.csv"
    if not metadata_path.is_file():
        errors.append("metadata.json missing")
        return entry
    meta = read_json(metadata_path)
    entry["metadata_path"] = str(metadata_path.relative_to(run))
    ident = meta.get("build_identity", {})
    entry["build_identity"] = ident
    src_check = verify_source(meta, source_root)
    entry["source_verification"] = src_check
    if not src_check["matches"]:
        errors.append("actual source tree does not match metadata SHA-256 list")
    if int(meta.get("N", -1)) != N_EXPECTED or int(meta.get("threads", -1)) != THREADS_EXPECTED:
        errors.append("metadata N/thread mismatch")
    if meta.get("cpuset") != CPUSET_EXPECTED:
        errors.append("metadata cpuset mismatch")
    if int(meta.get("repetitions", -1)) != REPS:
        errors.append("metadata repetitions is not 3")
    if ident.get("candidate_id") != expected["candidate_id"]:
        errors.append("candidate_id mismatch")
    for k in ("a_gap_bytes", "b_gap_bytes", "a_rotation", "b_rotation"):
        if int(ident.get(k, -1)) != expected[k]:
            errors.append(f"build identity {k} mismatch")
    for k, src in (
        ("gemm_source_sha256", "src/gemm.cpp"),
        ("preprocess_source_sha256", "src/preprocess.hpp"),
        ("kernels_source_sha256", "src/kernels.S"),
        ("public_header_sha256", "include/ozamx/gemm.hpp"),
        ("benchmark_driver_sha256", "bench/benchmark.cpp"),
    ):
        if ident.get(k) != meta.get("source_sha256", {}).get(src):
            errors.append(f"build/source hash mismatch for {src}")
    if (
        ident.get("mkl_runtime_sha256") != dataset.get("mkl_runtime_sha256")
        or ident.get("mkl_runtime_sha256") != MKL_SHA
    ):
        errors.append("oneMKL runtime hash mismatch")

    build_rel = f"builds/mode0_a{expected['a_gap_bytes']}_b{expected['b_gap_bytes']}_ra{expected['a_rotation']}_rb{expected['b_rotation']}"
    build_dir = run / build_rel
    build_identity_path = build_dir / "build_identity.json"
    lib_path = build_dir / "libozamx.a"
    bench_path = build_dir / "ozamx_benchmark"
    ident_on_disk = read_json(build_identity_path) if build_identity_path.is_file() else {}
    if ident_on_disk != ident:
        errors.append(
            "metadata build identity differs from on-disk build_identity.json or file missing"
        )
    lib_actual = sha256(lib_path) if lib_path.is_file() else None
    bench_actual = sha256(bench_path) if bench_path.is_file() else None
    if lib_actual != ident.get("library_sha256"):
        errors.append("built candidate library SHA mismatch")
    if bench_actual != ident.get("benchmark_sha256"):
        errors.append("built benchmark SHA mismatch")
    entry["binary_hash_verification"] = {
        "candidate_library_expected": ident.get("library_sha256"),
        "candidate_library_actual": lib_actual,
        "candidate_library_matches": lib_actual == ident.get("library_sha256"),
        "benchmark_expected": ident.get("benchmark_sha256"),
        "benchmark_actual": bench_actual,
        "benchmark_matches": bench_actual == ident.get("benchmark_sha256"),
        "frozen_library_expected": dataset.get("frozen_library_sha256"),
        "mkl_runtime_expected": dataset.get("mkl_runtime_sha256"),
    }
    if ident.get("library_sha256") == dataset.get("frozen_library_sha256"):
        errors.append("candidate library unexpectedly equals frozen V3 library")

    # Confirm source-level mapping rather than accepting budget-as-slice estimates.
    allocations = allocation(
        meta, budget_depth, N_EXPECTED, (expected["a_gap_bytes"], expected["b_gap_bytes"])
    )
    entry["allocation_by_budget"] = allocations
    entry["metadata_allocation_estimate_mismatch_budgets"] = [
        int(b)
        for b, a in allocations.items()
        if not a["metadata_payload_estimate_matches_source"]
        or not a["metadata_padding_estimate_matches_source"]
    ]

    gate_tag = tag.removesuffix("_n8192_fp64")
    gate_path = run / "gates" / f"{gate_tag}.json"
    ctest_path = run / "logs" / f"{gate_tag}_ctest.log"
    gate = read_json(gate_path) if gate_path.is_file() else {}
    gate_ok = (
        gate.get("status") == "pass"
        and len(gate.get("cases", [])) == 20
        and all(x.get("pass") for x in gate.get("cases", []))
    )
    ctest_ok = ctest_path.is_file() and "100% tests passed" in ctest_path.read_text(
        errors="replace"
    )
    gate_identity_ok = (
        bool(gate)
        and gate.get("candidate_library_sha256") == ident.get("library_sha256")
        and gate.get("frozen_library_sha256") == dataset.get("frozen_library_sha256")
    )
    entry["gate"] = {
        "path": str(gate_path.relative_to(run)) if gate_path.exists() else None,
        "status": gate.get("status"),
        "case_count": len(gate.get("cases", [])),
        "all_20_cases_pass": gate_ok,
        "binary_hashes_match_metadata": gate_identity_ok,
        "ctest_log": str(ctest_path.relative_to(run)) if ctest_path.exists() else None,
        "ctest_pass": bool(ctest_ok),
    }
    if not gate_ok:
        errors.append("full 20/20 gate missing or failed")
    if not gate_identity_ok:
        errors.append("gate binary/library hashes mismatch metadata")
    if not ctest_ok:
        errors.append("CTest pass record missing")

    if command_path.is_file():
        command = read_json(command_path)
        entry["command"] = command
        cmd_text = " ".join(str(x) for x in command)
        if "--reps 3" not in cmd_text or "--sizes 8192" not in cmd_text:
            errors.append("command does not specify expected N=8192 and reps=3")
    else:
        errors.append("command.json missing")

    if not result_path.is_file():
        errors.append("result.csv missing/incomplete")
        return entry
    entry["result_csv"] = str(result_path.relative_to(run))
    try:
        fields, rows = read_csv(result_path)
    except Exception as exc:
        errors.append(f"result.csv parse/column error: {exc}")
        return entry
    entry["csv_column_count"] = len(fields)
    if len(rows) != 4 or {int(r.get("budget", -1)) for r in rows} != set(BUDGETS):
        errors.append(f"expected four budget rows, got {len(rows)}")
    for row in rows:
        budget = int(row["budget"])
        try:
            if (
                row.get("precision") != "fp64"
                or int(row.get("N", -1)) != N_EXPECTED
                or int(row.get("threads", -1)) != THREADS_EXPECTED
            ):
                errors.append(f"budget {budget}: CSV config mismatch")
            if (
                int(row.get("repetitions", -1)) != REPS
                or row.get("status") != "ok"
                or row.get("accuracy_scope") != "production_semantics"
            ):
                errors.append(f"budget {budget}: CSV reps/status/accuracy-scope mismatch")
            raw_api = parse_vec(row["raw_api_call_wall_s"], f"{tag} P{budget} API wall")
            raw_split = parse_vec(row["raw_split_s"], f"{tag} P{budget} split")
            raw_pack = parse_vec(row["raw_pack_s"], f"{tag} P{budget} pack")
            raw_compute = parse_vec(row["raw_compute_recon_s"], f"{tag} P{budget} compute")
            raw_profile = parse_vec(row["raw_profile_total_s"], f"{tag} P{budget} profile")
            for field, vec in (
                ("api_call_wall_s_mean", raw_api),
                ("split_s_mean", raw_split),
                ("pack_s_mean", raw_pack),
                ("compute_recon_s_mean", raw_compute),
                ("profile_total_s_mean", raw_profile),
            ):
                if not close(float(row[field]), statistics.mean(vec)):
                    errors.append(f"budget {budget}: {field} does not match its raw samples")
            cp_path = rec / f"checkpoint.fp64.8192.{budget}.json"
            cp = read_json(cp_path) if cp_path.is_file() else {}
            checkpoint_ok = (
                cp.get("complete") is True
                and cp.get("completed_timed_repetitions") == REPS
                and cp.get("requested_repetitions") == REPS
                and cp.get("source_id") == "mkl-wall-roofline-v4-mode0-control"
                and cp.get("precision") == "fp64"
                and cp.get("distribution") == "uniform"
                and cp.get("budget") == budget
                and cp.get("N") == N_EXPECTED
                and cp.get("threads") == THREADS_EXPECTED
                and len(cp.get("call_wall_seconds", [])) == REPS
                and all(
                    close(a, float(b)) for a, b in zip(raw_api, cp.get("call_wall_seconds", []))
                )
            )
            if not checkpoint_ok:
                errors.append(f"budget {budget}: checkpoint missing/incomplete/mismatched")
            entry["budgets"][str(budget)] = {
                "api_wall": mean_median_sd(raw_api),
                "split": mean_median_sd(raw_split),
                "pack": mean_median_sd(raw_pack),
                "compute_reconstruct": mean_median_sd(raw_compute),
                "profile_total": mean_median_sd(raw_profile),
                "mkl_gemm_mean_s": float(row["mkl_gemm_s"]),
                "mkl_effective_gflop_s": float(row["mkl_effective_GFLOP_s"]),
                "api_effective_gflop_s": 2 * N_EXPECTED**3 / statistics.mean(raw_api) / 1e9,
                "eF_mkl": float(row["eF_mkl"]),
                "e_scaled_mkl": float(row["e_scaled_mkl"]),
                "checkpoint": str(cp_path.relative_to(run)) if cp_path.exists() else None,
                "checkpoint_valid": checkpoint_ok,
                "csv_field_counts": {
                    "raw_api_call_wall_s": len(raw_api),
                    "raw_split_s": len(raw_split),
                    "raw_pack_s": len(raw_pack),
                    "raw_compute_recon_s": len(raw_compute),
                    "raw_profile_total_s": len(raw_profile),
                },
            }
        except Exception as exc:
            errors.append(f"budget {budget}: {exc}")
    entry["complete"] = not errors and len(entry["budgets"]) == 4
    return entry


def read_control(run: Path, name: str, source_root: Path) -> dict[str, Any]:
    rec = run / "records" / name
    entry: dict[str, Any] = {"name": name, "complete": False, "budgets": {}, "errors": []}
    mp = rec / "metadata.json"
    rp = rec / "result.csv"
    if not mp.is_file() or not rp.is_file():
        entry["errors"].append("control metadata or result missing")
        return entry
    meta = read_json(mp)
    ident = meta.get("build_identity", {})
    source_check = verify_source(meta, source_root)
    entry["source_verification"] = source_check
    if not source_check["matches"]:
        entry["errors"].append("V3 control source SHA list differs from actual source tree")
    control_reps = int(meta.get("repetitions", 0))
    entry["repetitions"] = control_reps
    entry["library_sha256"] = ident.get("library_sha256")
    entry["library_is_frozen_v3"] = ident.get("library_sha256") == FROZEN_SHA
    if not entry["library_is_frozen_v3"]:
        entry["errors"].append("V3 control library SHA does not match frozen archive")
    build_dir = run / "builds/frozen_v3_driver"
    bip = build_dir / "build_identity.json"
    binary = build_dir / "ozamx_benchmark"
    disk_ident = read_json(bip) if bip.is_file() else {}
    binary_actual = sha256(binary) if binary.is_file() else None
    entry["driver_hash_verification"] = {
        "build_identity_matches": disk_ident == ident,
        "driver_expected_sha256": ident.get("driver_sha256"),
        "driver_actual_sha256": binary_actual,
        "driver_hash_matches": binary_actual == ident.get("driver_sha256"),
    }
    if disk_ident != ident or binary_actual != ident.get("driver_sha256"):
        entry["errors"].append("frozen V3 control driver build identity/binary hash mismatch")
    if ident.get("mkl_runtime_sha256") != MKL_SHA:
        entry["errors"].append("frozen V3 control MKL runtime SHA mismatch")
    fields, rows = read_csv(rp)
    if len(rows) != 4 or {int(x["budget"]) for x in rows} != set(BUDGETS):
        entry["errors"].append("control must have four budgets")
    for row in rows:
        b = int(row["budget"])
        try:
            raw = parse_vec(row["raw_api_call_wall_s"], f"{name} P{b} API wall", control_reps)
            if row.get("status") != "ok" or int(row.get("repetitions", -1)) != control_reps:
                entry["errors"].append(f"P{b}: control row status/repetitions invalid")
            cp_path = rec / f"checkpoint.fp64.8192.{b}.json"
            cp = read_json(cp_path) if cp_path.is_file() else {}
            cp_ok = (
                cp.get("complete") is True
                and cp.get("completed_timed_repetitions") == control_reps
                and cp.get("requested_repetitions") == control_reps
                and len(cp.get("call_wall_seconds", [])) == control_reps
                and all(close(a, float(c)) for a, c in zip(raw, cp.get("call_wall_seconds", [])))
            )
            if not cp_ok:
                entry["errors"].append(f"P{b}: V3 control checkpoint invalid")
            entry["budgets"][str(b)] = {
                "api_wall": mean_median_sd(raw),
                "compute_reconstruct_mean_s": float(row["compute_recon_s_mean"]),
                "split_mean_s": float(row["split_s_mean"]),
                "pack_mean_s": float(row["pack_s_mean"]),
                "checkpoint_valid": cp_ok,
            }
        except Exception as exc:
            entry["errors"].append(f"P{b}: {exc}")
    entry["complete"] = not entry["errors"] and len(entry["budgets"]) == 4
    return entry


def control_bracket(index: int) -> list[str]:
    group = (index - 1) // 4
    names = [
        "frozen_v3_initial",
        "frozen_v3_drift_after_04",
        "frozen_v3_drift_after_08",
        "frozen_v3_drift_after_12",
        "frozen_v3_drift_after_16",
    ]
    return [names[group], names[group + 1]]


def add_neighbor_control_comparisons(
    candidates: list[dict[str, Any]], controls: dict[str, Any]
) -> None:
    for c in candidates:
        bracket = control_bracket(c["index"])
        for b, row in c.get("budgets", {}).items():
            usable = [
                (n, controls[n])
                for n in bracket
                if n in controls and b in controls[n].get("budgets", {})
            ]
            if not usable:
                row["neighbor_v3_control"] = {"controls": bracket, "available": False}
                continue
            neighbors = []
            for name, control in usable:
                stats = control["budgets"][b]["api_wall"]
                neighbors.append(
                    {
                        "name": name,
                        "complete_control_record": control["complete"],
                        "sample_count": len(stats["raw_s"]),
                        "mean_s": stats["mean_s"],
                        "median_s": stats["median_s"],
                        "sample_sd_s": stats["sample_sd_s"],
                        "candidate_mean_over_control_mean": row["api_wall"]["mean_s"]
                        / stats["mean_s"],
                        "candidate_median_over_control_median": row["api_wall"]["median_s"]
                        / stats["median_s"],
                    }
                )
            row["neighbor_v3_control"] = {
                "controls": bracket,
                "available": True,
                "neighbor_records": neighbors,
                "mean_range_s": [
                    min(x["mean_s"] for x in neighbors),
                    max(x["mean_s"] for x in neighbors),
                ],
                "median_range_s": [
                    min(x["median_s"] for x in neighbors),
                    max(x["median_s"] for x in neighbors),
                ],
                "candidate_over_each_control_mean_ratio_range": [
                    min(x["candidate_mean_over_control_mean"] for x in neighbors),
                    max(x["candidate_mean_over_control_mean"] for x in neighbors),
                ],
            }


def build_analysis(run: Path) -> dict[str, Any]:
    dataset = read_json(run / "dataset.json")
    source_root = ROOT / "bench/8454h/roofline_v4/packed_layout_src"
    source_gemm = (source_root / "src/gemm.cpp").read_text(encoding="utf-8")
    source_pre = (source_root / "src/preprocess.hpp").read_text(encoding="utf-8")
    budget_depth = parse_budget_depth(source_gemm)
    if "AlignedBuffer<double> residual(packed_count)" not in source_pre:
        raise ValueError("residual allocation expression changed; update analyzer formula")
    candidates = [
        read_result_record(run, x, source_root, budget_depth, dataset)
        for x in expected_candidates(dataset)
    ]
    frozen_archive = (
        ROOT / "bench/8454h/versions/v3_paper_release/v3_release/artifacts/libozamx_v3.a"
    )
    frozen_actual = sha256(frozen_archive) if frozen_archive.is_file() else None
    mkl_runtime = ROOT / "third_party/code/mkl-current/lib/libmkl_rt.so.3"
    mkl_actual = sha256(mkl_runtime) if mkl_runtime.is_file() else None
    freeze_marker = ROOT / "bench/8454h/v3_paper_alignment/FROZEN_COMPLETE"
    freeze_actual = sha256(freeze_marker) if freeze_marker.is_file() else None
    control_names = [
        "frozen_v3_initial",
        "frozen_v3_drift_after_04",
        "frozen_v3_drift_after_08",
        "frozen_v3_drift_after_12",
        "frozen_v3_drift_after_16",
    ]
    controls = {name: read_control(run, name, source_root) for name in control_names}
    add_neighbor_control_comparisons(candidates, controls)
    missing = [c["candidate_id"] for c in candidates if not c["complete"]]
    rankings = {}
    for budget in BUDGETS:
        eligible = [c for c in candidates if c["complete"] and str(budget) in c["budgets"]]
        ranked = sorted(eligible, key=lambda c: c["budgets"][str(budget)]["api_wall"]["mean_s"])
        rankings[str(budget)] = {
            "ranked_candidates": [
                {
                    "index": c["index"],
                    "candidate_id": c["candidate_id"],
                    "a_gap_bytes": c["a_gap_bytes"],
                    "b_gap_bytes": c["b_gap_bytes"],
                    "a_rotation": c["a_rotation"],
                    "b_rotation": c["b_rotation"],
                    "api_wall_mean_s": c["budgets"][str(budget)]["api_wall"]["mean_s"],
                    "api_wall_median_s": c["budgets"][str(budget)]["api_wall"]["median_s"],
                    "api_wall_sample_sd_s": c["budgets"][str(budget)]["api_wall"]["sample_sd_s"],
                    "compute_reconstruct_mean_s": c["budgets"][str(budget)]["compute_reconstruct"][
                        "mean_s"
                    ],
                    "split_mean_s": c["budgets"][str(budget)]["split"]["mean_s"],
                    "pack_mean_s": c["budgets"][str(budget)]["pack"]["mean_s"],
                    "neighbor_v3_control": c["budgets"][str(budget)].get("neighbor_v3_control"),
                    "allocation": c["allocation_by_budget"][str(budget)],
                }
                for c in ranked
            ],
            "top_two": [c["candidate_id"] for c in ranked[:2]],
            "ranking_metric": "mean of all three raw full-API wall samples; no sample removed",
        }
    # Compare zero-gap rotations against the zero-rotation control built by the
    # same experimental source, all using every sample. This is descriptive only.
    baseline = next((x for x in candidates if x["candidate_id"] == "a0_b0_ra0_rb0"), None)
    rotation_trends = {}
    if baseline:
        for budget in BUDGETS:
            base = baseline.get("budgets", {}).get(str(budget))
            rotation_trends[str(budget)] = []
            if not base:
                continue
            for c in candidates:
                if (
                    c["a_gap_bytes"]
                    or c["b_gap_bytes"]
                    or (c["a_rotation"] == 0 and c["b_rotation"] == 0)
                ):
                    continue
                cur = c.get("budgets", {}).get(str(budget))
                if not cur:
                    continue
                rotation_trends[str(budget)].append(
                    {
                        "candidate_id": c["candidate_id"],
                        "api_mean_delta_vs_zero_rotation_percent": (
                            cur["api_wall"]["mean_s"] / base["api_wall"]["mean_s"] - 1
                        )
                        * 100,
                        "api_median_delta_vs_zero_rotation_percent": (
                            cur["api_wall"]["median_s"] / base["api_wall"]["median_s"] - 1
                        )
                        * 100,
                        "compute_mean_delta_vs_zero_rotation_percent": (
                            cur["compute_reconstruct"]["mean_s"]
                            / base["compute_reconstruct"]["mean_s"]
                            - 1
                        )
                        * 100,
                        "split_mean_delta_ms_vs_zero_rotation": (
                            cur["split"]["mean_s"] - base["split"]["mean_s"]
                        )
                        * 1e3,
                        "pack_mean_delta_us_vs_zero_rotation": (
                            cur["pack"]["mean_s"] - base["pack"]["mean_s"]
                        )
                        * 1e6,
                        "packed_payload_bytes": c["allocation_by_budget"][str(budget)][
                            "packed_a_b_allocated_bytes"
                        ],
                    }
                )
    p21_rotation_over = []
    for c in candidates:
        d = c.get("allocation_by_budget", {}).get("21")
        if d:
            p21_rotation_over.append(
                {
                    "candidate_id": c["candidate_id"],
                    "packed_bytes": d["packed_a_b_allocated_bytes"],
                    "peak_workspace_bytes_estimate": d[
                        "peak_packed_plus_residual_workspace_bytes_estimate"
                    ],
                    "cache_over_limit_bytes": d["peak_workspace_over_cache_limit_bytes"],
                }
            )
    phase_comparison = {}
    if baseline:
        for budget in BUDGETS:
            base_row = baseline.get("budgets", {}).get(str(budget))
            if not base_row:
                continue
            base_api = base_row["api_wall"]["mean_s"]
            base_comp = base_row["compute_reconstruct"]["mean_s"]
            base_noncomp = base_api - base_comp
            symmetric, asymmetric = [], []
            rotations = []
            for c in candidates:
                r = c.get("budgets", {}).get(str(budget))
                if not r or c["index"] == 1:
                    continue
                api, comp = r["api_wall"]["mean_s"], r["compute_reconstruct"]["mean_s"]
                item = {
                    "candidate_id": c["candidate_id"],
                    "api_delta_percent": (api / base_api - 1) * 100,
                    "compute_reconstruct_delta_percent": (comp / base_comp - 1) * 100,
                    "api_minus_compute_delta_ms": ((api - comp) - base_noncomp) * 1e3,
                }
                if c["a_gap_bytes"] == c["b_gap_bytes"] and c["a_gap_bytes"] > 0:
                    symmetric.append(item)
                elif c["a_gap_bytes"] or c["b_gap_bytes"]:
                    asymmetric.append(item)
                else:
                    rotations.append(item)

            def summary(items: list[dict[str, Any]]) -> dict[str, Any]:
                return {
                    "candidate_count": len(items),
                    "candidates": items,
                    "api_delta_percent_median": (
                        statistics.median(x["api_delta_percent"] for x in items) if items else None
                    ),
                    "api_delta_percent_range": (
                        [
                            min(x["api_delta_percent"] for x in items),
                            max(x["api_delta_percent"] for x in items),
                        ]
                        if items
                        else None
                    ),
                    "compute_delta_percent_median": (
                        statistics.median(x["compute_reconstruct_delta_percent"] for x in items)
                        if items
                        else None
                    ),
                    "compute_delta_percent_range": (
                        [
                            min(x["compute_reconstruct_delta_percent"] for x in items),
                            max(x["compute_reconstruct_delta_percent"] for x in items),
                        ]
                        if items
                        else None
                    ),
                    "api_minus_compute_delta_ms_median": (
                        statistics.median(x["api_minus_compute_delta_ms"] for x in items)
                        if items
                        else None
                    ),
                }

            phase_comparison[str(budget)] = {
                "reference_candidate": "a0_b0_ra0_rb0",
                "symmetric_nonzero_gap_candidates": summary(symmetric),
                "asymmetric_gap_candidates": summary(asymmetric),
                "zero_gap_rotation_candidates": summary(rotations),
            }
    artifact = {
        "schema": "ozamx-v4-packed-rotation-screen-analysis-v1",
        "analysis_generated_offline": True,
        "run_dir": str(run.relative_to(ROOT)),
        "dataset_schema": dataset.get("schema"),
        "dataset_started_utc": dataset.get("started_utc"),
        "expected_candidates": 16,
        "completed_candidates": sum(c["complete"] for c in candidates),
        "missing_or_invalid_candidate_ids": missing,
        "dataset_complete": not missing,
        "outlier_removal": False,
        "per_candidate_full_gate_and_ctest_required": True,
        "full20_gate_candidates_passed": sum(
            c.get("gate", {}).get("all_20_cases_pass", False)
            and c.get("gate", {}).get("binary_hashes_match_metadata", False)
            for c in candidates
        ),
        "ctest_candidates_passed": sum(
            c.get("gate", {}).get("ctest_pass", False) for c in candidates
        ),
        "source_budget_depth_from_actual_source": {str(k): v for k, v in budget_depth.items()},
        "frozen_v3_expected_sha256": FROZEN_SHA,
        "frozen_v3_archive_actual_sha256": frozen_actual,
        "frozen_v3_archive_matches_expected": frozen_actual == FROZEN_SHA,
        "mkl_runtime_expected_sha256": MKL_SHA,
        "mkl_runtime_actual_sha256": mkl_actual,
        "mkl_runtime_matches_expected": mkl_actual == MKL_SHA,
        "freeze_marker_expected_sha256": dataset.get("freeze_marker_sha256"),
        "freeze_marker_actual_sha256": freeze_actual,
        "freeze_marker_hash_matches_dataset": freeze_actual == dataset.get("freeze_marker_sha256"),
        "dataset_library_hash_matches_frozen": dataset.get("frozen_library_sha256") == FROZEN_SHA,
        "dataset_mkl_hash_matches_expected": dataset.get("mkl_runtime_sha256") == MKL_SHA,
        "v3_controls": controls,
        "neighbor_control_method": "Bracket each group of four candidates by the adjacent V3 controls (initial/after04, after04/after08, after08/after12, after12/after16); report the mean of both control means/medians. If only one control is complete for a budget, use and disclose that one.",
        "allocation_model": {
            "stored_payload_formula": "4 * stored_slice_count * N * N bytes (two uint16 operands)",
            "stored_slices_source_mapping": {str(k): v for k, v in budget_depth.items()},
            "gap_padding_formula": "stored_slices * ((N/32)*(N/256)) * (A_gap_bytes+B_gap_bytes), for N panel-aligned as in this screen",
            "residual_formula": "one temporary double per packed element, with A then B using the same size; includes gap-expanded slab pitches",
            "cache_limit_bytes_per_caller_thread": CACHE_BYTES,
            "cache_semantics": "per-caller-thread retained-workspace cap, not a live-allocation limit; actual peak estimate is packed arrays plus one operand's residual buffer; input/output and other runtime storage excluded",
            "metadata_estimate_issue": "search metadata currently multiplies by product budget instead of source stored-slice count; corrected source-derived values are used below and discrepancy is flagged per budget",
        },
        "packed_p21_allocations_by_candidate": p21_rotation_over,
        "screen_leaders_by_budget": rankings,
        "zero_gap_rotation_trends_vs_zero_rotation": rotation_trends,
        "phase_delta_vs_zero_gap_zero_rotation_candidate": phase_comparison,
        "candidates": candidates,
        "claim_limit": "Three samples form a descriptive screen only. No candidate is declared a winner; any finalist needs at least seven repetitions and paired validation. These experimental results do not change production V3.",
    }
    return artifact


def write_report(data: dict[str, Any], path: Path) -> None:
    lines = [
        "# V4 packed-layout screen results",
        "",
        "This is an offline analysis of the timestamped N=8192 FP64 gap/rotation screen. It does not change production V3. The report preserves every available sample and never removes an outlier. Three samples support descriptive ranking only; finalists require a paired follow-up with at least seven repetitions and the full gate.",
        "",
        f"Coverage: **{data['completed_candidates']}/16** candidates satisfy row, checkpoint, gate, CTest and hash checks. Missing or invalid: {', '.join(data['missing_or_invalid_candidate_ids']) if data['missing_or_invalid_candidate_ids'] else 'none'}. Full gate pass: {data['full20_gate_candidates_passed']}/16; CTest pass: {data['ctest_candidates_passed']}/16. Any currently missing point is retained as pending, not interpolated.",
        "",
        "## Allocation and cache accounting",
        "",
        "The source maps p6/p10/p15/p21 to 3/4/5/6 stored FP64 BF16 slices. `packed_allocation_estimates` in the run metadata currently uses the product budget as the slice count, so it overstates actual packed payload; this analysis recalculates from `gemm.cpp::budget_depth()` and `preprocess.hpp`. The payload formula is `4 × stored_slices × N²` bytes for persistent uint16 A and B components. Rotation permutes existing slab slots and adds no storage. Gap candidates add physical hole bytes. A temporary double residual plane is allocated while packing each operand, with A/B reusing the same-size workspace block. The 2 GiB `OZAMX_WORKSPACE_CACHE_BYTES` cap is per caller thread and limits retained workspace, not live allocation; the table estimates live packed payload plus one residual plane, excluding caller inputs/outputs and other process memory.",
        "",
        "| Budget | Stored slices | Packed A+B payload, zero-gap | Residual plane | Packed + residual peak estimate | Above 2 GiB cache cap |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    baseline = next((x for x in data["candidates"] if x["candidate_id"] == "a0_b0_ra0_rb0"), None)
    for budget in BUDGETS:
        if baseline:
            a = baseline["allocation_by_budget"][str(budget)]
            lines.append(
                f"| P{budget} | {a['stored_bf16_slices_from_source']} | {a['packed_a_b_allocated_bytes']:,} B ({a['packed_a_b_allocated_bytes']/2**30:.3f} GiB) | {a['temporary_residual_base_bytes_one_operand']:,} B ({a['temporary_residual_base_bytes_one_operand']/2**30:.3f} GiB) | {a['peak_packed_plus_residual_workspace_bytes_estimate']:,} B ({a['peak_packed_plus_residual_workspace_bytes_estimate']/2**30:.3f} GiB) | {a['peak_workspace_over_cache_limit_bytes']:,} B |"
            )
        else:
            lines.append(
                f"| P{budget} | {data['source_budget_depth_from_actual_source'][str(budget)]} | pending | pending | pending | pending |"
            )
    lines += [
        "",
        "At N=8192 and zero gap, packed payload is 768 MiB / 1.0 GiB / 1.25 GiB / 1.5 GiB for p6/p10/p15/p21; adding the 512 MiB temporary residual plane gives 1.25 / 1.5 / 1.75 / 2.0 GiB. The p21 estimate lands exactly on the configured per-thread retention cap. Per-candidate gap-expanded bytes and the original metadata estimates are in the machine-readable analysis.",
        "",
        "## Top two screen candidates by product budget",
        "",
        "Ranking uses the mean of all three raw full-API wall samples. The median and sample SD are also reported; no repetition is dropped. Neighbor references show each bracketing frozen-V3 control separately, including its own mean and median; the initial control is not used as a permanent baseline or averaged away. Candidate groups are bracketed by initial/after04, after04/after08, after08/after12, or after12/after16 controls.",
        "",
        "| Budget | Rank | Candidate | A/B gap bytes | A/B rotation | API mean (s) | API median (s) | API sample SD (s) | Compute+reconstruct mean (s) | Neighbor V3 API means (s) | Candidate / each V3 mean | Packed A+B bytes |",
        "|---:|---:|---|---:|---:|---:|---:|---:|---:|---|---|---:|",
    ]
    for b in BUDGETS:
        ranked = data["screen_leaders_by_budget"][str(b)]["ranked_candidates"][:2]
        if not ranked:
            lines.append(f"| P{b} | 1–2 | pending | | | | | | | | | |")
            continue
        for rank, item in enumerate(ranked, 1):
            control = item.get("neighbor_v3_control") or {}
            neighbors = control.get("neighbor_records", [])
            ref = "/".join(f"{x['mean_s']:.6f}" for x in neighbors) if neighbors else None
            ratio = (
                "/".join(f"{x['candidate_mean_over_control_mean']:.3f}×" for x in neighbors)
                if neighbors
                else None
            )
            alloc = item["allocation"]["packed_a_b_allocated_bytes"]
            lines.append(
                f"| P{b} | {rank} | `{item['candidate_id']}` | {item['a_gap_bytes']}/{item['b_gap_bytes']} | {item['a_rotation']}/{item['b_rotation']} | {item['api_wall_mean_s']:.6f} | {item['api_wall_median_s']:.6f} | {item['api_wall_sample_sd_s']:.6f} | {item['compute_reconstruct_mean_s']:.6f} | {ref} | {ratio} | {alloc:,} |"
                if ref is not None and ratio is not None
                else f"| P{b} | {rank} | `{item['candidate_id']}` | {item['a_gap_bytes']}/{item['b_gap_bytes']} | {item['a_rotation']}/{item['b_rotation']} | {item['api_wall_mean_s']:.6f} | {item['api_wall_median_s']:.6f} | {item['api_wall_sample_sd_s']:.6f} | {item['compute_reconstruct_mean_s']:.6f} | pending | pending | {alloc:,} |"
            )
    lines += [
        "",
        "## Bracketing frozen-V3 control drift",
        "",
        "Each cell is control API mean / median in seconds; each control retains its own full raw vectors and actual repetition count in `analysis.json`. This avoids selecting an early control as a fixed baseline. The initial control has seven samples; later drift controls have three. The initial p10 mean/median divergence is left visible rather than filtered.",
        "",
        "| V3 control | p6 mean / median | p10 mean / median | p15 mean / median | p21 mean / median |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, control in data["v3_controls"].items():
        vals = []
        for b in BUDGETS:
            stats = control.get("budgets", {}).get(str(b), {}).get("api_wall")
            vals.append(f"{stats['mean_s']:.6f} / {stats['median_s']:.6f}" if stats else "pending")
        lines.append(f"| {name} (n={control.get('repetitions','?')}) | " + " | ".join(vals) + " |")
    lines += [
        "",
        "## Phase behavior",
        "",
        "Changes below compare each gap/rotation candidate with zero-gap, zero-rotation candidate 1 using the full three-sample means. `API−compute` is API wall minus the compute/reconstruction phase; it is a descriptive proxy for noncompute time, not a separately instrumented timer. Symmetric-gap summaries are medians across the five nonzero symmetric gaps; rotation summaries are medians/ranges across the five zero-gap rotations. Asymmetric cases are summarized by their observed min/max. No sample is removed.",
        "",
        "| Budget | Symmetric gaps: median API Δ | median compute Δ | median API−compute added | Asymmetric gaps: API Δ range | compute Δ range | Zero-gap rotations: API Δ range | compute Δ range |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for b in BUDGETS:
        phase = data["phase_delta_vs_zero_gap_zero_rotation_candidate"][str(b)]
        sg = phase["symmetric_nonzero_gap_candidates"]
        ag = phase["asymmetric_gap_candidates"]
        rt = phase["zero_gap_rotation_candidates"]

        def pct_range(obj, key):
            vals = obj.get(key + "_range")
            return f"{vals[0]:+.1f}% … {vals[1]:+.1f}%" if vals else "—"

        sm = f"{sg['api_delta_percent_median']:+.1f}%" if sg["candidate_count"] else "—"
        scm = f"{sg['compute_delta_percent_median']:+.1f}%" if sg["candidate_count"] else "—"
        snc = f"{sg['api_minus_compute_delta_ms_median']:+.1f} ms" if sg["candidate_count"] else "—"
        lines.append(
            f"| P{b} | {sm} | {scm} | {snc} | {pct_range(ag,'api_delta_percent')} | {pct_range(ag,'compute_delta_percent')} | {pct_range(rt,'api_delta_percent')} | {pct_range(rt,'compute_delta_percent')} |"
        )
    lines += [
        "",
        "## Interpretation limits",
        "",
        "The full-API result includes input splitting, packing, component-product compute/reconstruction, dispatch and teardown. Source-sized symmetric gaps usually increase API time sharply while compute/reconstruct stays flat or falls versus zero-gap candidate 1; the exact deltas are summarized by budget in `analysis.json`. This places much of the symmetric-gap penalty outside compute, but without PMU counters it does not identify the cause. Some asymmetric-gap candidates also show large compute/reconstruct regressions, so not every gap penalty is noncompute-only. Do not infer cache/TLB causality from wall-time phase labels alone.",
        "",
        "For zero-gap rotation candidates (12–16), source-derived packed payload and allocation are identical to candidate 1; rotation changes only which existing slab slot each component uses. The observed rotation deltas change sign across p6/p10/p15/p21, and the largest API/compute changes remain comparable to run-to-run control movement. There is no stable all-budget compute/API trend in this three-repetition screen. Current V3 remains the production release; these candidates are exploratory and not a V4 performance claim.",
        "",
        "Raw data, gates, checkpoints, builds and metadata remain under [`bench/8454h/roofline_v4/search_runs/packed_rotation_screen_20261014T101506Z/`](../bench/8454h/roofline_v4/search_runs/packed_rotation_screen_20261014T101506Z/). Full raw vectors, validation flags, source/library/runtime hashes, source-derived allocation accounting and candidate detail are in that directory's `analysis.json`. The offline analyzer is [`tools/analyze_v4_packed_screen.py`](../tools/analyze_v4_packed_screen.py).",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", type=Path, default=DEFAULT_RUN)
    ap.add_argument("--analysis-out", type=Path, default=None)
    ap.add_argument("--report-out", type=Path, default=REPORT)
    args = ap.parse_args()
    run = args.run_dir.resolve()
    result = build_analysis(run)
    out = args.analysis_out or (run / "analysis.json")
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    write_report(result, args.report_out)
    print(
        json.dumps(
            {
                "completed": result["completed_candidates"],
                "expected": 16,
                "full20_gates": result["full20_gate_candidates_passed"],
                "ctest_pass": result["ctest_candidates_passed"],
                "dataset_complete": result["dataset_complete"],
                "missing_or_invalid": result["missing_or_invalid_candidate_ids"],
                "analysis": str(out),
                "report": str(args.report_out),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
