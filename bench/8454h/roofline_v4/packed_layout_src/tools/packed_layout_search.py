#!/usr/bin/env python3
"""Plan and, after authorization, run the isolated FP64 packed-slab gap study."""
from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

SRC = Path(__file__).resolve().parents[1]
REPO = SRC.parents[3]
LOCK = Path("/tmp/ozamx-perf.lock")
MARKER = REPO / "bench/8454h/v3_paper_alignment/FROZEN_COMPLETE"
EXPECTED_ARCHIVE = (REPO / "bench/8454h/versions/v3_paper_release").resolve()
FROZEN_LIB = REPO / "bench/8454h/versions/v3_release/artifacts/libozamx_v3.a"
FROZEN_LIB_SHA = "73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c"
MKL_ROOT = REPO / "third_party/code/mkl-current"
MKL_LIB = MKL_ROOT / "lib/libmkl_rt.so.3"
MANIFEST = "MANIFEST.sha256"
GAPS = (0, 64, 4096, 8192, 16384, 32768, 65536)
# Original eleven gap pairs (zero rotation), followed by five zero-gap rotations.
GAP_PLAN = ((0, 0), (64, 64), (4096, 4096), (8192, 8192), (16384, 16384),
            (32768, 32768), (65536, 65536), (64, 4096), (4096, 64),
            (8192, 16384), (16384, 8192))
ROTATION_PLAN = ((1, 0), (0, 1), (1, 1), (1, 3), (3, 1))
PLAN = tuple((a, b, 0, 0) for a, b in GAP_PLAN) + tuple((0, 0, a, b) for a, b in ROTATION_PLAN)
SEED = 260904
THREADS = 64
CPUS = os.environ.get("OZV4_CPUSET", "0-63")
REPS_PREFLIGHT = 1
REPS_SCREEN = 3
SIZES_PREFLIGHT = (256,)
SIZES_SCREEN = (8192,)
BUDGETS = "6,10,15,21"
HEADER_COLUMNS = 37
EXPECTED_STATUS = {0: "ok", 1: "diagnostic_only_accuracy_unvalidated",
                   2: "diagnostic_no_reconstruction_non_numeric", 3: "ok"}
EXPECTED_SCOPE = {0: "production_semantics",
                  1: "diagnostic_only_accuracy_unvalidated_finite_inputs",
                  2: "diagnostic_no_reconstruction_non_numeric",
                  3: "numeric_gate_pending"}
CHECKPOINT_SOURCE = {0: "mkl-wall-roofline-v4-mode0-control",
                     1: "mkl-wall-roofline-v4-mode1-diagnostic-plain-nf",
                     2: "mkl-wall-roofline-v4-mode2-diagnostic-no-reconstruction",
                     3: "mkl-wall-roofline-v4-mode3-candidate-late32-unvalidated"}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def plan() -> dict:
    return {
        "schema": "ozamx-v4-packed-layout-plan-1",
        "source_tree": str(SRC),
        "fixed": {"bk": 256, "k32_tile_bytes": 2048, "product_order": "V3 unchanged",
                  "fp32": "unchanged", "threads": THREADS, "cpuset": CPUS,
                  "seed": SEED, "workspace_cache_bytes": 2147483648},
        "gap_unit": "bytes between adjacent FP64 M32/N32 payload slabs; every gap is 64-byte aligned",
        "gaps_bytes": list(GAPS),
        "candidates": [{"id": f"a{a}_b{b}_ra{ra}_rb{rb}", "a_gap_bytes": a,
                        "b_gap_bytes": b, "a_rotation": ra, "b_rotation": rb,
                        "panel_physical_slab": "(logical_slab + part * rotation) & 7"}
                       for a, b, ra, rb in PLAN],
        "rotation_semantics": "part is the FP64 component/slice index; logical slabs permute only their physical 16 KiB+gap slots within each eight-slab 256x256 panel. A/B rotate independently. Payload and K32 order are unchanged.",
        "preflight": {"modes": [0, 1, 2, 3], "N": list(SIZES_PREFLIGHT),
                      "repetitions": REPS_PREFLIGHT, "precision": "all",
                      "budgets": [6, 10, 15, 21], "rows_per_mode": 5,
                      "csv_columns": HEADER_COLUMNS,
                      "check": "mode labels, mode status/accuracy_scope, each raw API-wall vector equals its complete per-row checkpoint"},
        "screen": {"mode": 0, "N": list(SIZES_SCREEN), "repetitions": REPS_SCREEN,
                   "precision": "fp64", "budgets": [6, 10, 15, 21],
                   "full_binary_gate_case_ids": list(range(1, 21)),
                   "gate_before_timing": True, "outlier_removal": False,
                   "control_included": True},
        "controls": {"frozen_v3_initial_repetitions": 7, "frozen_v3_final_repetitions": 7,
                     "frozen_v3_drift_control_every_candidates": 4, "drift_control_repetitions": 3},
        "execution": "No build, test, gate, or benchmark is performed by --plan. --execute requires a frozen marker and queues on the shared CPU lock for the whole sequence.",
    }


def check_freeze() -> None:
    if not MARKER.is_file():
        raise RuntimeError(f"frozen V3 completion marker missing: {MARKER}")
    data = json.loads(MARKER.read_text())
    if data.get("complete") is not True or data.get("configurations") != 66:
        raise RuntimeError("frozen V3 marker must declare complete=true and configurations=66")
    if data.get("library_sha256") != FROZEN_LIB_SHA:
        raise RuntimeError("frozen V3 marker library SHA does not match the expected V3 library")
    archive = (REPO / str(data.get("archive", ""))).resolve()
    if archive != EXPECTED_ARCHIVE or not archive.is_dir():
        raise RuntimeError("frozen marker archive must resolve to bench/8454h/versions/v3_paper_release")
    manifest = archive / MANIFEST
    if not manifest.is_file() or sha(manifest) != data.get("manifest_sha256"):
        raise RuntimeError("frozen marker MANIFEST.sha256 is missing or its SHA does not match")
    result = subprocess.run(["sha256sum", "-c", MANIFEST], cwd=archive, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError("frozen paper-release manifest check failed:\n" + result.stdout)
    if not FROZEN_LIB.is_file() or sha(FROZEN_LIB) != FROZEN_LIB_SHA:
        raise RuntimeError("immutable V3 library missing or SHA-256 mismatch")
    if not MKL_LIB.is_file():
        raise RuntimeError(f"oneMKL runtime missing: {MKL_LIB}")


def common_env() -> dict[str, str]:
    env = dict(os.environ)
    env.update({"OMP_NUM_THREADS": str(THREADS), "OMP_PLACES": "cores", "OMP_PROC_BIND": "close",
                "OMP_DYNAMIC": "FALSE", "MKL_NUM_THREADS": str(THREADS), "MKL_DYNAMIC": "FALSE",
                "MKL_THREADING_LAYER": "GNU", "MKL_INTERFACE_LAYER": "LP64",
                "OZAMX_WORKSPACE_CACHE_BYTES": "2147483648",
                "LD_LIBRARY_PATH": str(MKL_ROOT / "lib") + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")})
    return env


def run_logged(argv: list[str], log: Path, env: dict[str, str] | None = None) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("wb") as f:
        proc = subprocess.run(argv, stdout=f, stderr=subprocess.STDOUT, env=env)
    if proc.returncode:
        raise RuntimeError(f"command failed ({proc.returncode}); log retained at {log}: {argv}")


def build(mode: int, a_gap: int, b_gap: int, root: Path, tag: str,
          a_rotation: int = 0, b_rotation: int = 0) -> Path:
    ident = f"mode{mode}_a{a_gap}_b{b_gap}_ra{a_rotation}_rb{b_rotation}"
    bdir = root / "builds" / ident
    bdir.mkdir(parents=True, exist_ok=False)
    run_logged(["cmake", "-S", str(SRC), "-B", str(bdir), "-DCMAKE_BUILD_TYPE=Release",
                "-DOZAMX_ENABLE_OPENMP=ON", f"-DOZAMX_ONEMKL_ROOT={MKL_ROOT}",
                f"-DOZV4_MODE={mode}", "-DOZV4_FP64_BATCH=2", "-DOZV4_WIDE_CBM=128",
                "-DOZV4_WIDE_CBN=0", "-DOZV4_WIDE_PAD_BYTES=64", "-DOZV4_FP32_LATE32=1",
                f"-DOZV4_FP64_A_GAP_BYTES={a_gap}", f"-DOZV4_FP64_B_GAP_BYTES={b_gap}",
                f"-DOZV4_FP64_A_ROTATION={a_rotation}", f"-DOZV4_FP64_B_ROTATION={b_rotation}"],
               root / "logs" / f"{tag}_configure.log")
    run_logged(["cmake", "--build", str(bdir), "-j2"], root / "logs" / f"{tag}_build.log")
    ident_json = json.loads((bdir / "build_identity.json").read_text())
    ident_json.update({"candidate_id": f"a{a_gap}_b{b_gap}_ra{a_rotation}_rb{b_rotation}", "mode": mode,
                       "a_gap_bytes": a_gap, "b_gap_bytes": b_gap,
                       "a_rotation": a_rotation, "b_rotation": b_rotation,
                       "library_sha256": sha(bdir / "libozamx.a"),
                       "benchmark_sha256": sha(bdir / "ozamx_benchmark"),
                       "source_tree": str(SRC)})
    (bdir / "build_identity.json").write_text(json.dumps(ident_json, indent=2) + "\n")
    return bdir


def build_v3_driver(root: Path) -> Path:
    bdir = root / "builds" / "frozen_v3_driver"
    bdir.mkdir(parents=True, exist_ok=False)
    binary = bdir / "ozamx_benchmark"
    cmd = [os.environ.get("CXX", "g++"), "-O3", "-std=c++17", "-Wall", "-Wextra", "-Wpedantic",
           "-march=sapphirerapids", "-ffp-contract=off", "-fno-fast-math", "-mamx-tile", "-mamx-bf16", "-fopenmp",
           f"-I{SRC / 'include'}", f"-I{MKL_ROOT / 'include'}", str(SRC / "bench/benchmark.cpp"), str(FROZEN_LIB),
           f"-L{MKL_ROOT / 'lib'}", f"-Wl,-rpath,{MKL_ROOT / 'lib'}", "-Wl,--no-as-needed", "-l:libmkl_rt.so.3", "-ldl", "-o", str(binary)]
    run_logged(cmd, root / "logs/frozen_v3_driver_build.log")
    (bdir / "build_identity.json").write_text(json.dumps({"reference": "immutable V3 release",
        "library_sha256": sha(FROZEN_LIB), "driver_sha256": sha(binary),
        "driver_source_sha256": sha(SRC / "bench/benchmark.cpp"), "mkl_runtime_sha256": sha(MKL_LIB)}, indent=2)+"\n")
    return bdir


def validate(csv_path: Path, checkpoint_prefix: Path, mode: int, sizes: tuple[int, ...], reps: int,
             precision_arg: str = "all") -> None:
    with csv_path.open(newline="") as f:
        reader = csv.DictReader(f)
        if len(reader.fieldnames or []) != HEADER_COLUMNS:
            raise RuntimeError(f"{csv_path}: expected {HEADER_COLUMNS} CSV columns")
        rows = list(reader)
    rows_per_size = 5 if precision_arg == "all" else 4 if precision_arg == "fp64" else 1
    expected_rows = len(sizes) * rows_per_size
    if len(rows) != expected_rows or any(None in row for row in rows):
        raise RuntimeError(f"{csv_path}: malformed row count or CSV fields")
    for row in rows:
        scope = row.get("accuracy_scope", "")
        scope_ok = scope.startswith(EXPECTED_SCOPE[mode]) if mode == 1 else scope == EXPECTED_SCOPE[mode]
        if row.get("status") != EXPECTED_STATUS[mode] or not scope_ok:
            raise RuntimeError(f"{csv_path}: mode {mode} invalid status/scope {row.get('status')}/{row.get('accuracy_scope')}")
        expected_label = {0: "mode0_control", 1: "mode1_diagnostic_plain_nf",
                          2: "mode2_diagnostic_no_reconstruction",
                          3: "mode3_candidate_late32_unvalidated"}[mode]
        if expected_label not in row.get("diagnostic_mode", ""):
            raise RuntimeError(f"{csv_path}: mode label does not identify {expected_label}")
        n = int(row["N"])
        if n not in sizes or int(row["repetitions"]) != reps:
            raise RuntimeError(f"{csv_path}: unexpected N/repetition count")
        precision = row["precision"]
        budget = "6" if precision == "fp32" else row["budget"]
        cp = Path(f"{checkpoint_prefix}.{precision}.{n}.{budget}.json")
        checkpoint = json.loads(cp.read_text())
        samples = [float(v) for v in row["raw_api_call_wall_s"].split(";")]
        vector = checkpoint.get("call_wall_seconds")
        if (checkpoint.get("source_id") != CHECKPOINT_SOURCE[mode] or
                checkpoint.get("precision") != precision or checkpoint.get("distribution") != "uniform" or
                checkpoint.get("N") != n or checkpoint.get("threads") != THREADS or
                checkpoint.get("seed") != SEED + n or checkpoint.get("budget") != int(budget) or
                len(samples) != reps or checkpoint.get("complete") is not True or
                checkpoint.get("requested_repetitions") != reps or
                checkpoint.get("completed_timed_repetitions") != reps or
                not isinstance(vector, list) or len(vector) != reps or
                any(abs(x - float(y)) > 2e-9 for x, y in zip(samples, vector))):
            raise RuntimeError(f"{csv_path}: checkpoint does not match raw API-wall samples: {cp}")


def run_bench(bdir: Path, mode: int, out: Path, tag: str, n: int, reps: int, precision: str) -> Path:
    record = out / "records" / tag
    record.mkdir(parents=True, exist_ok=False)
    csv_path = record / "result.csv"
    cp = record / "checkpoint"
    argv = ["taskset", "-c", CPUS, str(bdir / "ozamx_benchmark"), "--sizes", str(n),
            "--threads", str(THREADS), "--reps", str(reps), "--seed", str(SEED),
            "--precision", precision, "--budgets", BUDGETS, "--distribution", "uniform",
            "--checkpoint", str(cp), "--output", str(csv_path)]
    (record / "command.json").write_text(json.dumps(argv, indent=2) + "\n")
    run_logged(argv, record / "stderr.log", common_env())
    validate(csv_path, cp, mode, (n,), reps, precision)
    build_identity = json.loads((bdir / "build_identity.json").read_text())
    allocation_rows = []
    with csv_path.open(newline="") as f:
        for row in csv.DictReader(f):
            if row["precision"] != "fp64":
                continue
            nn, depth = int(row["N"]), int(row["budget"])
            gap_sum = int(build_identity.get("fp64_a_gap_bytes", 0)) + int(build_identity.get("fp64_b_gap_bytes", 0))
            extra = depth * (nn // 32) * (nn // 256) * (
                gap_sum)
            allocation_rows.append({"precision": "fp64", "budget": depth, "N": nn,
                "packed_output_allocation_bytes": 4 * depth * nn * nn + extra,
                "padding_extra_bytes": extra,
                "scope": "persistent packed uint16 A/B component arrays only; excludes temporary residual buffer and public input/output"})
    (record / "metadata.json").write_text(json.dumps({"mode": mode, "N": n, "repetitions": reps,
        "threads": THREADS, "cpuset": CPUS, "seed": SEED, "source_sha256": {
            str(p.relative_to(SRC)): sha(p) for p in sorted(SRC.rglob("*")) if p.is_file()},
        "build_identity": build_identity, "packed_allocation_estimates": allocation_rows,
        "timing_scope": "ozamx API-call wall; oneMKL column is GEMM-only"}, indent=2) + "\n")
    return csv_path


def gate(bdir: Path, out: Path, tag: str) -> None:
    dest = out / "gates" / f"{tag}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    run_logged([sys.executable, str(SRC / "tools/run_binary_gate_v4.py"),
                "--candidate-library", str(bdir / "libozamx.a"), "--output", str(dest),
                "--case-ids", ",".join(str(i) for i in range(1, 21)), "--lock-held"],
               out / "logs" / f"{tag}_gate.log", common_env())
    data = json.loads(dest.read_text())
    if data.get("status") != "pass" or len(data.get("cases", [])) != 20:
        raise RuntimeError(f"full 20-case binary gate failed; retained at {dest}")


def run_preflight(out: Path) -> None:
    for mode in range(4):
        bdir = build(mode, 0, 0, out, f"preflight_mode{mode}")
        csv_path = run_bench(bdir, mode, out, f"preflight_mode{mode}_n256", 256, REPS_PREFLIGHT, "all")
        print(f"preflight mode={mode} validated: {csv_path}", flush=True)


def run_search(out: Path) -> None:
    v3 = build_v3_driver(out)
    run_bench(v3, 0, out, "frozen_v3_initial", 8192, 7, "fp64")
    for index, (a_gap, b_gap, a_rotation, b_rotation) in enumerate(PLAN, start=1):
        tag = f"candidate_{index:02d}_a{a_gap}_b{b_gap}_ra{a_rotation}_rb{b_rotation}"
        bdir = build(0, a_gap, b_gap, out, tag, a_rotation, b_rotation)
        run_logged(["ctest", "--test-dir", str(bdir), "--output-on-failure"],
                   out / "logs" / f"{tag}_ctest.log", common_env())
        gate(bdir, out, tag)
        run_bench(bdir, 0, out, tag + "_n8192_fp64", 8192, REPS_SCREEN, "fp64")
        print(f"completed and validated {tag}", flush=True)
        if index % 4 == 0:
            run_bench(v3, 0, out, f"frozen_v3_drift_after_{index:02d}", 8192, REPS_SCREEN, "fp64")
    run_bench(v3, 0, out, "frozen_v3_final", 8192, 7, "fp64")


def execute(phase: str, out: Path) -> None:
    check_freeze()
    out.mkdir(parents=True, exist_ok=False)
    queued_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with LOCK.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        acquired_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        dataset = {"schema": "ozamx-v4-packed-layout-dataset-1", "phase": phase,
                   "queued_utc": queued_utc, "lock_acquired_utc": acquired_utc,
                   "started_utc": acquired_utc,
                   "freeze_marker_sha256": sha(MARKER), "frozen_library_sha256": sha(FROZEN_LIB),
                   "mkl_runtime_sha256": sha(MKL_LIB), "source_sha256": {
                       str(p.relative_to(SRC)): sha(p) for p in sorted(SRC.rglob("*")) if p.is_file()},
                   "candidates": PLAN, "threads": THREADS, "cpuset": CPUS,
                   "seed": SEED, "outlier_removal": False}
        (out / "dataset.json").write_text(json.dumps(dataset, indent=2) + "\n")
        if phase == "preflight":
            run_preflight(out)
        else:
            # The small all-mode preflight is a mandatory first phase for every scan dataset.
            pf = out / "preflight"
            pf.mkdir(parents=True, exist_ok=False)
            run_preflight(pf)
            run_search(out)
        dataset["completed_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        (out / "dataset.json").write_text(json.dumps(dataset, indent=2) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan", action="store_true", help="print the plan only; no build/test/gate/benchmark")
    ap.add_argument("--phase", choices=("preflight", "scan"))
    ap.add_argument("--execute", action="store_true", help="explicitly perform the selected phase")
    ap.add_argument("--result-dir", type=Path)
    args = ap.parse_args()
    if args.plan:
        print(json.dumps(plan(), indent=2))
        return 0
    if not args.execute or not args.phase or not args.result_dir:
        ap.error("execution requires --execute --phase {preflight,scan} --result-dir PATH")
    execute(args.phase, args.result_dir.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
