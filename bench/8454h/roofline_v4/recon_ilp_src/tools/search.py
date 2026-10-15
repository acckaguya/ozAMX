#!/usr/bin/env python3
"""Deterministic staged Roofline V4 source search. Execution requires --execute."""
from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time

SEARCH = Path(__file__).resolve().parents[1]
REPO = SEARCH.parents[3]
FROZEN_LIB = REPO / "bench/8454h/versions/v3_paper_release/v3_release/artifacts/libozamx_v3.a"
FROZEN_SHA = "73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c"
FREEZE_MARKER = REPO / "bench/8454h/v3_paper_alignment/FROZEN_COMPLETE"
MKL_ROOT = REPO / "third_party/code/mkl-current"
MKL_LIB = MKL_ROOT / "lib/libmkl_rt.so.3"
LOCK = Path("/tmp/ozamx-perf.lock")
SEED = 260904
CPUS = os.environ.get("OZV4_CPUSET", "0-63")
THREADS = 64
REPS_SCREEN = 3
REPS_MATCHED = 7
QUICK_CASES = "11,12,17,18,19,20"
ALL_CASES = ",".join(map(str, range(1, 21)))
SIZES_SCREEN = (8192,)
SIZES_MATCHED = (1024, 4096, 8192)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def knobs(batch=2, cbm=128, cbn=0, pad=64, hint=1, late=1) -> dict:
    return {"fp64_batch": int(batch), "wide_cbm": int(cbm), "wide_cbn": int(cbn),
            "wide_pad_bytes": int(pad), "tileload_hint": int(hint), "fp32_late32": int(late), "bk": 256}


def candidate_id(k: dict) -> str:
    n = "auto" if k["wide_cbn"] == 0 else str(k["wide_cbn"])
    return f"b{k['fp64_batch']}_m{k['wide_cbm']}_n{n}_p{k['wide_pad_bytes']}_h{k['tileload_hint']}_l{k['fp32_late32']}"


def parse_candidate_id(value: str) -> dict:
    m = re.fullmatch(r"b(2|4|8|12|21)_m(64|128|256)_n(auto|128|256|512|1024)_p(0|64|128)_h([01])_l([01])", value)
    if not m:
        raise ValueError(f"invalid candidate id: {value}")
    return knobs(m[1], m[2], 0 if m[3] == "auto" else m[3], m[4], m[5], m[6])


def stage1_candidates() -> list[dict]:
    choices = [knobs(b, 128, 0, 64, 1, 1) for b in (2, 4, 8, 12, 21)]
    choices += [knobs(2, m, 0, 64, 1, 1) for m in (64, 128, 256)]
    choices += [knobs(2, 128, n, 64, 1, 1) for n in (128, 256, 512, 1024)]
    choices += [knobs(2, m, n, 64, 1, 1) for m in (64, 256) for n in (128, 256, 512, 1024)]
    choices += [knobs(b, 128, n, 64, 1, 1) for b in (4, 8) for n in (256, 512, 1024)]
    choices += [knobs(b, 128, n, 64, 1, 1) for b in (12, 21) for n in (256, 512)]
    choices += [knobs(2, 128, 0, 64, 1, 0)]
    unique = {candidate_id(k): k for k in choices}
    out = [unique[x] for x in sorted(unique)]
    if not 20 <= len(out) <= 40:
        raise RuntimeError(f"stage 1 must stay in the 20–40 candidate envelope; got {len(out)}")
    return out


def layout_candidates(base: dict) -> list[dict]:
    return [knobs(base["fp64_batch"], base["wide_cbm"], base["wide_cbn"], pad, hint, base["fp32_late32"])
            for pad, hint in itertools.product((0, 64, 128), (0, 1))]


def default_modes() -> list[dict]:
    return [{"mode": mode, "knobs": knobs()} for mode in range(4)]


def plan() -> dict:
    first = stage1_candidates()
    return {
        "schema": "ozamx-v4-search-plan-1",
        "default_knobs": knobs(),
        "fixed": {"bk": 256, "fp64_product_order": "unchanged V3 order", "threads": THREADS,
                  "cpuset": CPUS, "seed": SEED, "workspace_cache_bytes": 2147483648},
        "screen_modes_at_n8192": default_modes(),
        "stage1_candidate_count": len(first),
        "stage1_candidates": [{"id": candidate_id(x), **x} for x in first],
        "stage1_candidate_ids": [candidate_id(x) for x in first],
        "stage1_protocol": {"mode": 3, "candidate_gate_case_ids": QUICK_CASES, "precision": "FP32 plus FP64 budgets 6,10,15,21",
                            "N": 8192, "repetitions": REPS_SCREEN, "gate_before_timing": True},
        "layout_stage_protocol": {"base_candidate_required": True, "variants": 6,
                                  "pad_bytes": [0, 64, 128], "tileload_hint": [0, 1]},
        "final_protocol": {"matched_pairs": 18, "N": list(SIZES_MATCHED), "repetitions": REPS_MATCHED,
                           "cases_per_N": ["mode0 FP32", "mode3 FP32", "mode3 FP64 p6", "mode3 FP64 p10",
                                           "mode3 FP64 p15", "mode3 FP64 p21"],
                           "full_gate_case_ids": ALL_CASES, "outlier_removal": False},
    }


def check_freeze() -> None:
    if not FREEZE_MARKER.is_file():
        raise RuntimeError(f"V3 freeze marker missing: {FREEZE_MARKER}")
    if not FROZEN_LIB.is_file() or sha(FROZEN_LIB) != FROZEN_SHA:
        raise RuntimeError("immutable V3 library missing or SHA-256 mismatch")
    if not MKL_LIB.is_file():
        raise RuntimeError(f"oneMKL runtime missing: {MKL_LIB}")


def common_env() -> dict:
    env = dict(os.environ)
    env.update({"OMP_NUM_THREADS": str(THREADS), "OMP_PLACES": "cores", "OMP_PROC_BIND": "close",
                "OMP_DYNAMIC": "FALSE", "MKL_NUM_THREADS": str(THREADS), "MKL_DYNAMIC": "FALSE",
                "MKL_THREADING_LAYER": "GNU", "MKL_INTERFACE_LAYER": "LP64",
                "OZAMX_WORKSPACE_CACHE_BYTES": "2147483648",
                "LD_LIBRARY_PATH": str(MKL_ROOT / "lib") + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")})
    return env


def run_logged(argv: list[str], log: Path, env: dict | None = None) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("wb") as f:
        p = subprocess.run(argv, stdout=f, stderr=subprocess.STDOUT, env=env)
    if p.returncode:
        raise RuntimeError(f"command failed ({p.returncode}): {shlex.join(argv)}; see {log}")


def cache_args(mode: int, k: dict) -> list[str]:
    return [f"-DOZV4_MODE={mode}", f"-DOZV4_FP64_BATCH={k['fp64_batch']}",
            f"-DOZV4_WIDE_CBM={k['wide_cbm']}", f"-DOZV4_WIDE_CBN={k['wide_cbn']}",
            f"-DOZV4_WIDE_PAD_BYTES={k['wide_pad_bytes']}", f"-DOZAMX_TILELOAD_HINT={k['tileload_hint']}",
            f"-DOZV4_FP32_LATE32={k['fp32_late32']}"]


def build(mode: int, k: dict, root: Path, tag: str) -> tuple[Path, Path]:
    # Include the stage tag because the default knobs are intentionally both a
    # baseline and one of the screened candidates; each must retain its own
    # independently built artifact directory.
    ident = f"{tag}__mode{mode}_{candidate_id(k)}"
    bdir = root / "builds" / ident
    bdir.mkdir(parents=True, exist_ok=False)
    run_logged(["cmake", "-S", str(SEARCH), "-B", str(bdir), "-DCMAKE_BUILD_TYPE=Release",
                "-DOZAMX_ENABLE_OPENMP=ON", f"-DOZAMX_ONEMKL_ROOT={MKL_ROOT}", *cache_args(mode, k)], root / "logs" / f"{tag}_configure.log")
    run_logged(["cmake", "--build", str(bdir), "-j2"], root / "logs" / f"{tag}_build.log")
    lib = bdir / "libozamx.a"
    identity = json.loads((bdir / "build_identity.json").read_text())
    identity.update({"candidate_id": candidate_id(k), "mode": mode, "library_sha256": sha(lib),
                     "driver_sha256": sha(bdir / "ozamx_benchmark"), "source_tree": str(SEARCH)})
    (bdir / "build_identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    return bdir, lib


def gate(lib: Path, root: Path, label: str, case_ids: str) -> None:
    out = root / "gates" / f"{label}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    run_logged([sys.executable, str(SEARCH / "tools/run_binary_gate_v4.py"), "--candidate-library", str(lib),
                "--output", str(out), "--case-ids", case_ids, "--lock-held"],
               root / "logs" / f"{label}_gate.log", common_env())
    data = json.loads(out.read_text())
    if data.get("status") != "pass" or len(data.get("cases", [])) != len(case_ids.split(",")):
        raise RuntimeError(f"binary gate did not pass all requested cases: {out}")


def validate_csv(csv_path: Path, checkpoint_prefix: Path, mode: int, sizes: list[int], reps: int, expected_rows: int) -> None:
    with csv_path.open(newline="") as f:
        reader = csv.DictReader(f)
        if len(reader.fieldnames or []) != 37:
            raise RuntimeError(f"{csv_path}: expected 37 CSV columns, got {len(reader.fieldnames or [])}")
        rows = list(reader)
    if len(rows) != expected_rows or any(None in r for r in rows):
        raise RuntimeError(f"{csv_path}: row count or column count malformed")
    # `status` reports a valid execution row. The distinct accuracy_scope field
    # carries mode 3's pending full numeric-validation state after its quick gate.
    expected_status = {0: "ok", 1: "diagnostic_only_accuracy_unvalidated", 2: "diagnostic_no_reconstruction_non_numeric", 3: "ok"}[mode]
    for row in rows:
        n = int(row["N"])
        if n not in sizes:
            raise RuntimeError(f"{csv_path}: unexpected N={n}")
        if row.get("status") != expected_status:
            raise RuntimeError(f"{csv_path}: mode {mode} unexpected status {row.get('status')!r}")
        precision = row["precision"]
        budget = "6" if precision == "fp32" else row["budget"]
        cp = Path(f"{checkpoint_prefix}.{precision}.{n}.{budget}.json")
        chk = json.loads(cp.read_text())
        samples = [float(x) for x in row["raw_api_call_wall_s"].split(";")]
        vector = chk.get("call_wall_seconds")
        if len(samples) != reps or chk.get("complete") is not True or chk.get("requested_repetitions") != reps or chk.get("completed_timed_repetitions") != reps:
            raise RuntimeError(f"{csv_path}: invalid {precision}/{budget} sample/checkpoint count")
        if not isinstance(vector, list) or len(vector) != reps or any(abs(a-float(b)) > 2e-9 for a,b in zip(samples,vector)):
            raise RuntimeError(f"{csv_path}: API-wall samples do not match checkpoint {cp.name}")
        if mode == 2 and row.get("accuracy_scope") != "diagnostic_no_reconstruction_non_numeric":
            raise RuntimeError("mode 2 must remain explicitly non-numeric")
        if mode == 1 and not row.get("accuracy_scope", "").startswith("diagnostic_only_accuracy_unvalidated"):
            raise RuntimeError("mode 1 must remain explicitly unvalidated")
        if mode == 3 and row.get("accuracy_scope") != "numeric_gate_pending":
            raise RuntimeError("mode 3 rows must remain pending full numeric validation")


def run_benchmark(binary: Path, label: str, root: Path, mode: int, sizes: list[int], reps: int,
                  precision: str = "all", budgets: str = "6,10,15,21") -> Path:
    outdir = root / "records" / label
    outdir.mkdir(parents=True, exist_ok=False)
    csv_path = outdir / "result.csv"
    checkpoint = outdir / "checkpoint"
    argv = ["taskset", "-c", CPUS, str(binary), "--sizes", ",".join(map(str, sizes)), "--threads", str(THREADS),
            "--reps", str(reps), "--seed", str(SEED), "--precision", precision, "--budgets", budgets,
            "--distribution", "uniform", "--checkpoint", str(checkpoint), "--output", str(csv_path)]
    (outdir / "command.json").write_text(json.dumps(argv, indent=2) + "\n")
    run_logged(argv, outdir / "stderr.log", common_env())
    expected_rows = len(sizes) * ((1 if precision in ("all", "fp32") else 0) + (len(budgets.split(",")) if precision in ("all", "fp64") else 0))
    validate_csv(csv_path, checkpoint, mode, sizes, reps, expected_rows)
    library_path = binary.parent / "libozamx.a"
    if not library_path.is_file():
        library_path = FROZEN_LIB
    build_identity = json.loads((binary.parent / "build_identity.json").read_text())
    chosen_id = build_identity.get("candidate_id", "frozen_v3")
    metadata = {"label": label, "mode": mode, "candidate_id": chosen_id, "library_sha256": sha(library_path),
                "source_sha256": sha(SEARCH / "src/gemm.cpp"), "mkl_runtime_sha256": sha(MKL_LIB), "seed_base": SEED,
                "sizes": sizes, "repetitions": reps, "threads": THREADS, "cpuset": CPUS,
                "timing_scope": "V3 benchmark API wall; oneMKL comparison field is GEMM-only",
                "expected_rows": expected_rows, "validated_rows": expected_rows, "build_identity": build_identity}
    (outdir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return csv_path


def build_v3_driver(root: Path) -> Path:
    bdir = root / "builds" / "frozen_v3_driver"
    bdir.mkdir(parents=True, exist_ok=False)
    binary = bdir / "ozamx_benchmark"
    cmd = [os.environ.get("CXX", "g++"), "-O3", "-std=c++17", "-Wall", "-Wextra", "-Wpedantic", "-march=sapphirerapids", "-ffp-contract=off", "-fno-fast-math", "-mamx-tile", "-mamx-bf16", "-fopenmp",
           f"-I{SEARCH / 'include'}", f"-I{MKL_ROOT / 'include'}", str(SEARCH / "bench/benchmark.cpp"), str(FROZEN_LIB),
           f"-L{MKL_ROOT / 'lib'}", f"-Wl,-rpath,{MKL_ROOT / 'lib'}", "-Wl,--no-as-needed", "-l:libmkl_rt.so.3", "-ldl", "-o", str(binary)]
    run_logged(cmd, root / "logs/frozen_v3_driver_build.log")
    (bdir / "build_identity.json").write_text(json.dumps({"reference": "immutable V3 release", "library_sha256": sha(FROZEN_LIB),
      "driver_sha256": sha(binary), "driver_source_sha256": sha(SEARCH / "bench/benchmark.cpp"), "mkl_runtime_sha256": sha(MKL_LIB)}, indent=2)+"\n")
    return binary


def ctest_and_gate(mode: int, lib: Path, bdir: Path, root: Path, label: str, full: bool) -> None:
    run_logged(["ctest", "--test-dir", str(bdir), "--output-on-failure"], root / "logs" / f"{label}_ctest.log", common_env())
    gate(lib, root, label, ALL_CASES if full else QUICK_CASES)


def run_screen(out: Path) -> None:
    check_freeze()
    out.mkdir(parents=True, exist_ok=False)
    initial = {"schema": "ozamx-v4-search-dataset-1", "phase": "screen", "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "seed_base": SEED, "threads": THREADS, "cpuset": CPUS, "workspace_cache_bytes": 2147483648,
               "frozen_library_sha256": sha(FROZEN_LIB), "mkl_runtime_sha256": sha(MKL_LIB),
               "search_source_sha256": {str(p.relative_to(SEARCH)): sha(p) for p in sorted(SEARCH.rglob("*")) if p.is_file() and "/builds/" not in str(p) and "/results/" not in str(p)}}
    (out / "dataset.json").write_text(json.dumps(initial, indent=2) + "\n")
    v3 = build_v3_driver(out)
    run_benchmark(v3, "frozen_v3_initial", out, 0, [8192], 7)
    defaults = knobs()
    baseline_bins = {}
    for mode in range(4):
        bdir, lib = build(mode, defaults, out, f"baseline_mode{mode}")
        if mode in (0, 3):
            ctest_and_gate(mode, lib, bdir, out, f"baseline_mode{mode}_full", True)
        baseline_bins[mode] = bdir / "ozamx_benchmark"
        run_benchmark(baseline_bins[mode], f"baseline_mode{mode}", out, mode, [8192], 7)
    (out / "stage1_plan.json").write_text(json.dumps([{"id": candidate_id(k), **k} for k in stage1_candidates()], indent=2) + "\n")
    for i, k in enumerate(stage1_candidates(), 1):
        cid = candidate_id(k)
        bdir, lib = build(3, k, out, f"stage1_{i:02d}_{cid}")
        ctest_and_gate(3, lib, bdir, out, f"stage1_{cid}_quick", False)
        run_benchmark(bdir / "ozamx_benchmark", f"{cid}__mode3_screen", out, 3, [8192], REPS_SCREEN)
        if i % 5 == 0:
            # Re-anchor shared-host drift against the immutable static V3 lib.
            run_benchmark(v3, f"drift_v3_after_{i:02d}", out, 0, [8192], REPS_SCREEN)
    run_benchmark(v3, "frozen_v3_final", out, 0, [8192], 7)
    initial["completed_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    initial["candidate_ids"] = [candidate_id(k) for k in stage1_candidates()]
    (out / "dataset.json").write_text(json.dumps(initial, indent=2) + "\n")


def check_candidate_eligible(screen_dir: Path, candidate: str) -> None:
    gates = list((screen_dir / "gates").glob(f"*{candidate}*quick.json"))
    if not gates or any(json.loads(p.read_text()).get("status") != "pass" for p in gates):
        raise RuntimeError(f"candidate {candidate} has no passing quick-gate record in {screen_dir}")
    result_csv = screen_dir / "records" / f"{candidate}__mode3_screen" / "result.csv"
    if not result_csv.is_file():
        raise RuntimeError(f"candidate {candidate} has no completed N=8192 screen record in {screen_dir}")
    with result_csv.open(newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        columns = len(reader.fieldnames or [])
    if columns != 37 or len(rows) != 5 or any(r.get("N") != "8192" or r.get("repetitions") != str(REPS_SCREEN) or r.get("status") != "ok" or r.get("accuracy_scope") != "numeric_gate_pending" for r in rows):
        raise RuntimeError(f"candidate screen record is incomplete or malformed: {result_csv}")
    validate_csv(result_csv, result_csv.parent / "checkpoint", 3, [8192], REPS_SCREEN, 5)


def run_screen_resume(screen_dir: Path, start_index: int, skip_candidate_ids: list[str] | None = None,
                      skip_reason: str | None = None, skip_bridge: bool = False) -> None:
    """Continue a verified partial screen in place without repeating candidates."""
    check_freeze()
    candidates = stage1_candidates()
    if not 2 <= start_index <= len(candidates):
        raise ValueError(f"resume start index must be in 2..{len(candidates)}")
    dataset_path = screen_dir / "dataset.json"
    prior = json.loads(dataset_path.read_text())
    if prior.get("schema") != "ozamx-v4-search-dataset-1" or prior.get("phase") != "screen":
        raise RuntimeError(f"not a V4 screen dataset: {dataset_path}")
    if prior.get("seed_base") != SEED or prior.get("threads") != THREADS or prior.get("cpuset") != CPUS:
        raise RuntimeError("prior screen environment does not match the fixed protocol")
    if prior.get("frozen_library_sha256") != FROZEN_SHA or prior.get("mkl_runtime_sha256") != sha(MKL_LIB):
        raise RuntimeError("prior screen library or MKL runtime identity does not match")
    manifest_path = screen_dir / "screen_resume_manifest.json"
    existing_manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
    if existing_manifest and existing_manifest.get("status") not in ("running", "interrupted"):
        raise RuntimeError("existing screen continuation is already finalized")
    if existing_manifest and existing_manifest.get("prior_dataset_sha256") != sha(dataset_path):
        raise RuntimeError("existing continuation manifest points at a different prior dataset")
    skip_ids = set(skip_candidate_ids or [])
    if skip_ids and not skip_reason:
        raise RuntimeError("explicitly skipped candidates require --skip-reason")
    expected_before = {candidate_id(k) for k in candidates[:start_index - 1]}
    if not skip_ids <= expected_before:
        raise RuntimeError("every explicitly skipped candidate must precede the resume start index")
    reused = []
    excluded = []
    for index, k in enumerate(candidates[:start_index - 1], 1):
        cid = candidate_id(k)
        gate_path = screen_dir / "gates" / f"stage1_{cid}_quick.json"
        gate_data = json.loads(gate_path.read_text())
        ctest_path = screen_dir / "logs" / f"stage1_{cid}_quick_ctest.log"
        if not ctest_path.is_file():
            raise RuntimeError(f"candidate {cid} is missing its CTest evidence")
        if "100% tests passed" not in ctest_path.read_text():
            raise RuntimeError(f"candidate {cid} CTest record is not a complete pass")
        identity_options = []
        for identity_path in sorted((screen_dir / "builds").glob("*/build_identity.json")):
            identity = json.loads(identity_path.read_text())
            if identity.get("candidate_id") == cid and identity.get("mode") == 3:
                lib = identity_path.parent / "libozamx.a"
                if lib.is_file() and sha(lib) == identity.get("library_sha256"):
                    identity_options.append((identity_path, identity, lib))
        if cid in skip_ids:
            if gate_data.get("status") != "failed" or gate_data.get("candidate_library_sha256") is None:
                raise RuntimeError(f"explicitly skipped candidate {cid} has no recorded failed gate")
            diagnostic_path = screen_dir / "gates" / f"stage1_{cid}_execution_failure_diagnostic.json"
            if not diagnostic_path.is_file():
                raise RuntimeError(f"explicitly skipped candidate {cid} has no execution-failure diagnostic record")
            diagnostic = json.loads(diagnostic_path.read_text())
            if (diagnostic.get("candidate_id") != cid or
                diagnostic.get("official_child_reproduction", {}).get("signal") != "SIGSEGV" or
                diagnostic.get("diagnostic_only_reproduction", {}).get("OMP_STACKSIZE") != "8M"):
                raise RuntimeError(f"candidate {cid} failure is not documented as the confirmed stack resource failure")
            if (screen_dir / "records" / f"{cid}__mode3_screen" / "result.csv").exists():
                raise RuntimeError(f"failed candidate {cid} unexpectedly has timed screen data")
            matching = [(ip, ident, lib) for ip, ident, lib in identity_options
                        if ident.get("library_sha256") == gate_data["candidate_library_sha256"]]
            if not matching:
                raise RuntimeError(f"failed candidate {cid} gate library SHA has no matching build identity")
            identity_path, identity, lib = matching[0]
            excluded.append({"ordinal": index, "candidate_id": cid, "reason": skip_reason,
                             "gate": str(gate_path.relative_to(screen_dir)), "gate_sha256": sha(gate_path),
                             "ctest_log": str(ctest_path.relative_to(screen_dir)), "ctest_log_sha256": sha(ctest_path),
                             "build_identity": str(identity_path.relative_to(screen_dir)), "build_identity_sha256": sha(identity_path),
                             "library_sha256": sha(lib), "failure": gate_data.get("failure"),
                             "diagnostic_record": str(diagnostic_path.relative_to(screen_dir)),
                             "diagnostic_record_sha256": sha(diagnostic_path)})
            continue

        check_candidate_eligible(screen_dir, cid)
        result_csv = screen_dir / "records" / f"{cid}__mode3_screen" / "result.csv"
        metadata_path = result_csv.parent / "metadata.json"
        metadata = json.loads(metadata_path.read_text())
        matching = [(ip, ident, lib) for ip, ident, lib in identity_options
                    if ident.get("library_sha256") == metadata.get("library_sha256")]
        if not matching:
            raise RuntimeError(f"candidate {cid} library SHA does not match any recorded build identity")
        identity_path, identity, lib = matching[0]
        if gate_data.get("status") != "pass" or len(gate_data.get("cases", [])) != len(QUICK_CASES.split(",")):
            raise RuntimeError(f"candidate {cid} quick binary gate is incomplete")
        if sha(lib) != metadata.get("library_sha256") or sha(lib) != identity.get("library_sha256"):
            raise RuntimeError(f"candidate {cid} library SHA does not match its records")
        if metadata.get("source_sha256") != prior["search_source_sha256"].get("src/gemm.cpp"):
            raise RuntimeError(f"candidate {cid} core-source SHA does not match prior dataset")
        reused.append({"ordinal": index, "candidate_id": cid,
                       "result_csv": str(result_csv.relative_to(screen_dir)), "result_csv_sha256": sha(result_csv),
                       "metadata": str(metadata_path.relative_to(screen_dir)), "metadata_sha256": sha(metadata_path),
                       "gate": str(gate_path.relative_to(screen_dir)), "gate_sha256": sha(gate_path),
                       "ctest_log": str(ctest_path.relative_to(screen_dir)), "ctest_log_sha256": sha(ctest_path),
                       "build_identity": str(identity_path.relative_to(screen_dir)), "build_identity_sha256": sha(identity_path),
                       "library_sha256": sha(lib), "core_source_sha256": metadata["source_sha256"]})

    # Validate the existing starting/periodic controls before linking them into
    # the continuation manifest.
    controls = []
    control_specs = [("frozen_v3_initial", 7)] + [(f"drift_v3_after_{i:02d}", REPS_SCREEN)
                                                   for i in (5, 10) if i < start_index]
    for label, reps in control_specs:
        csv_path = screen_dir / "records" / label / "result.csv"
        validate_csv(csv_path, csv_path.parent / "checkpoint", 0, [8192], reps, 5)
        controls.append({"label": label, "result_csv": str(csv_path.relative_to(screen_dir)),
                         "result_csv_sha256": sha(csv_path), "repetitions": reps})
    for mode in (0, 3):
        gate_path = screen_dir / "gates" / f"baseline_mode{mode}_full.json"
        gate_data = json.loads(gate_path.read_text())
        ctest_path = screen_dir / "logs" / f"baseline_mode{mode}_full_ctest.log"
        if gate_data.get("status") != "pass" or len(gate_data.get("cases", [])) != 20:
            raise RuntimeError(f"baseline mode {mode} full gate is not a complete pass")
        if "100% tests passed" not in ctest_path.read_text():
            raise RuntimeError(f"baseline mode {mode} CTest is not a complete pass")
        csv_path = screen_dir / "records" / f"baseline_mode{mode}" / "result.csv"
        validate_csv(csv_path, csv_path.parent / "checkpoint", mode, [8192], 7, 5)
        controls.append({"label": f"baseline_mode{mode}", "result_csv": str(csv_path.relative_to(screen_dir)),
                         "result_csv_sha256": sha(csv_path), "gate": str(gate_path.relative_to(screen_dir)),
                         "gate_sha256": sha(gate_path), "ctest_log": str(ctest_path.relative_to(screen_dir)),
                         "ctest_log_sha256": sha(ctest_path), "repetitions": 7})

    v3 = screen_dir / "builds" / "frozen_v3_driver" / "ozamx_benchmark"
    v3_identity = json.loads((v3.parent / "build_identity.json").read_text())
    if not v3.is_file() or v3_identity.get("library_sha256") != FROZEN_SHA or sha(FROZEN_LIB) != FROZEN_SHA:
        raise RuntimeError("existing frozen-V3 control driver does not match immutable release identity")
    if existing_manifest:
        continuation = existing_manifest
        continuation.setdefault("resume_attempts", [])
        already_reused = {x["candidate_id"] for x in continuation.get("reused_candidates", [])}
        continuation["reused_candidates"].extend(x for x in reused if x["candidate_id"] not in already_reused)
        continuation.setdefault("excluded_candidates", []).extend(excluded)
    else:
        continuation = {"schema": "ozamx-v4-search-continuation-1", "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "prior_dataset_sha256": sha(dataset_path), "prior_search_driver_sha256": prior["search_source_sha256"].get("tools/search.py"),
                        "frozen_library_sha256": FROZEN_SHA, "mkl_runtime_sha256": sha(MKL_LIB),
                        "seed_base": SEED, "threads": THREADS, "cpuset": CPUS, "workspace_cache_bytes": 2147483648,
                        "reused_candidates": reused, "reused_controls": controls, "excluded_candidates": excluded,
                        "resume_attempts": []}
    attempt = {"started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "start_candidate_ordinal": start_index,
               "skip_candidate_ids": sorted(skip_ids),
               "skip_reason": skip_reason, "bridge_policy": "reuse_previous_bridge" if skip_bridge else "fresh_bridge",
               "continuation_search_driver_sha256": sha(SEARCH / "tools/search.py"),
               "continuation_source_sha256": {str(p.relative_to(SEARCH)): sha(p) for p in sorted(SEARCH.rglob("*"))
                                               if p.is_file() and "/builds/" not in str(p) and "/results/" not in str(p)},
               "reused_candidate_ids_verified_this_attempt": [x["candidate_id"] for x in reused],
               "excluded_candidate_ids_verified_this_attempt": [x["candidate_id"] for x in excluded],
               "candidate_ids_to_run": [candidate_id(k) for k in candidates[start_index - 1:]]}
    continuation["status"] = "running"
    continuation["resume_attempts"].append(attempt)
    manifest_path.write_text(json.dumps(continuation, indent=2) + "\n")
    bridge_label = f"frozen_v3_bridge_before_candidate{start_index}"
    if skip_bridge:
        prior_bridge_labels = [x["label"] for x in continuation.get("bridge_controls", [])]
        if not prior_bridge_labels and continuation.get("bridge_control"):
            prior_bridge_labels = [continuation["bridge_control"]]
        if not prior_bridge_labels:
            raise RuntimeError("--skip-bridge requested but no earlier V3 bridge control is recorded")
        bridge_label = prior_bridge_labels[-1]
        bridge_path = screen_dir / "records" / bridge_label / "result.csv"
        validate_csv(bridge_path, bridge_path.parent / "checkpoint", 0, [8192], 7, 5)
        attempt["bridge_control_reused"] = bridge_label
    elif (screen_dir / "records" / bridge_label / "result.csv").is_file():
        bridge_path = screen_dir / "records" / bridge_label / "result.csv"
        validate_csv(bridge_path, bridge_path.parent / "checkpoint", 0, [8192], 7, 5)
    else:
        run_benchmark(v3, bridge_label, screen_dir, 0, [8192], 7)
        bridge_path = screen_dir / "records" / bridge_label / "result.csv"
    bridge_entry = {"label": bridge_label, "result_csv": str(bridge_path.relative_to(screen_dir)),
                    "result_csv_sha256": sha(bridge_path), "repetitions": 7}
    continuation.setdefault("bridge_controls", [])
    if not any(x["label"] == bridge_label for x in continuation["bridge_controls"]):
        continuation["bridge_controls"].append(bridge_entry)
    manifest_path.write_text(json.dumps(continuation, indent=2) + "\n")
    for i, k in enumerate(candidates[start_index - 1:], start_index):
        cid = candidate_id(k)
        bdir, lib = build(3, k, screen_dir, f"stage1_{i:02d}_{cid}")
        ctest_and_gate(3, lib, bdir, screen_dir, f"stage1_{cid}_quick", False)
        run_benchmark(bdir / "ozamx_benchmark", f"{cid}__mode3_screen", screen_dir, 3, [8192], REPS_SCREEN)
        if i % 5 == 0:
            run_benchmark(v3, f"drift_v3_after_{i:02d}", screen_dir, 0, [8192], REPS_SCREEN)
    run_benchmark(v3, "frozen_v3_final", screen_dir, 0, [8192], 7)
    continuation["completed_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    continuation["status"] = "complete"
    continuation["final_control_sha256"] = sha(screen_dir / "records/frozen_v3_final/result.csv")
    manifest_path.write_text(json.dumps(continuation, indent=2) + "\n")


def run_layout(out: Path, base_id: str, screen_dir: Path) -> None:
    check_freeze()
    check_candidate_eligible(screen_dir, base_id)
    base = parse_candidate_id(base_id)
    out.mkdir(parents=True, exist_ok=False)
    (out / "dataset.json").write_text(json.dumps({"schema": "ozamx-v4-search-dataset-1", "phase": "layout",
        "base_candidate_id": base_id, "seed_base": SEED, "threads": THREADS, "cpuset": CPUS,
        "frozen_library_sha256": sha(FROZEN_LIB), "mkl_runtime_sha256": sha(MKL_LIB),
        "search_gemm_sha256": sha(SEARCH / "src/gemm.cpp")}, indent=2) + "\n")
    for k in layout_candidates(base):
        cid = candidate_id(k)
        bdir, lib = build(3, k, out, f"layout_{cid}")
        ctest_and_gate(3, lib, bdir, out, f"layout_{cid}_quick", False)
        run_benchmark(bdir / "ozamx_benchmark", f"{cid}__mode3_layout_screen", out, 3, [8192], REPS_SCREEN)


def run_final(out: Path, candidate: str, screen_dir: Path | None) -> None:
    check_freeze()
    k = parse_candidate_id(candidate)
    if screen_dir is None:
        raise RuntimeError("finalist validation requires its screening dataset")
    check_candidate_eligible(screen_dir, candidate)
    out.mkdir(parents=True, exist_ok=False)
    v3 = build_v3_driver(out)
    modes = {}
    for mode in (0, 3):
        bdir, lib = build(mode, k, out, f"final_mode{mode}_{candidate}")
        ctest_and_gate(mode, lib, bdir, out, f"final_mode{mode}_{candidate}_full", True)
        modes[mode] = (bdir, lib)
    # 18 paired rows: six workload definitions at each of three sizes.
    workload_specs = [(0, "fp32", "6"), (3, "fp32", "6"),
                      *((3, "fp64", str(b)) for b in (6, 10, 15, 21))]
    manifest = {"schema": "ozamx-v4-final-recheck-1", "candidate_id": candidate, "knobs": k,
                "sizes": SIZES_MATCHED, "repetitions": REPS_MATCHED, "pairs": [],
                "frozen_library_sha256": sha(FROZEN_LIB), "mkl_runtime_sha256": sha(MKL_LIB),
                "seed_base": SEED, "threads": THREADS, "cpuset": CPUS,
                "timing_scopes": {"V3_API": "full API call wall", "oneMKL": "GEMM only"}, "outlier_removal": False}
    for n in SIZES_MATCHED:
        for mode, precision, budget in workload_specs:
            label = f"n{n}_mode{mode}_{precision}_p{budget}"
            kwargs = {"precision": precision, "budgets": budget}
            ref = run_benchmark(v3, f"pair_{label}_v3", out, 0, [n], REPS_MATCHED, **kwargs)
            bdir, lib = modes[mode]
            cand = run_benchmark(bdir / "ozamx_benchmark", f"pair_{label}_candidate", out, mode, [n], REPS_MATCHED, **kwargs)
            manifest["pairs"].append({"label": label, "mode": mode, "precision": precision, "budget": int(budget),
                                      "N": n, "v3_csv": str(ref.relative_to(out)), "candidate_csv": str(cand.relative_to(out)),
                                      "candidate_library_sha256": sha(lib)})
    run_benchmark(v3, "frozen_v3_final_control", out, 0, [8192], 7)
    manifest["completed_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    (out / "final_recheck.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan", action="store_true", help="print the deterministic plan; never runs builds/tests/benchmarks")
    ap.add_argument("--phase", choices=("screen", "layout", "final"))
    ap.add_argument("--result-dir", type=Path)
    ap.add_argument("--resume-dir", type=Path, help="continue a partially completed screen in place")
    ap.add_argument("--start-index", type=int, help="1-based candidate ordinal for screen continuation")
    ap.add_argument("--skip-candidate-id", action="append", default=[], help="explicitly exclude a previously failed candidate")
    ap.add_argument("--skip-reason", help="document why explicitly skipped candidates are excluded")
    ap.add_argument("--skip-bridge", action="store_true", help="reuse the latest already validated V3 bridge control")
    ap.add_argument("--base-candidate", help="layout phase base candidate id")
    ap.add_argument("--candidate-id", help="final candidate id")
    ap.add_argument("--screen-dir", type=Path, help="prior screen dataset required for finalist eligibility")
    ap.add_argument("--execute", action="store_true", help="explicit opt-in to configure/build/run tests/gates/benchmarks")
    args = ap.parse_args()
    if args.plan:
        print(json.dumps(plan(), indent=2))
        return 0
    if not args.execute:
        ap.error("all executable phases require explicit --execute; use --plan for a source-only preview")
    if not args.phase:
        ap.error("--phase is required for execution")
    if args.resume_dir:
        if args.phase != "screen" or args.start_index is None or args.result_dir:
            ap.error("screen continuation requires --phase screen --resume-dir DIR --start-index N and no --result-dir")
        if args.skip_candidate_id and not args.skip_reason:
            ap.error("--skip-candidate-id requires --skip-reason")
        if (args.skip_candidate_id or args.skip_bridge) and not args.resume_dir:
            ap.error("skip options are only valid with --resume-dir")
    elif not args.result_dir:
        ap.error("--result-dir is required unless using --resume-dir")
    if args.phase == "layout" and not args.base_candidate:
        ap.error("--base-candidate is required for layout phase")
    if args.phase in ("layout", "final") and not args.screen_dir:
        ap.error("--screen-dir is required to establish candidate screening eligibility")
    if args.phase == "final" and not args.candidate_id:
        ap.error("--candidate-id is required for final phase")
    if args.resume_dir:
        args.resume_dir = args.resume_dir.resolve()
    else:
        args.result_dir = args.result_dir.resolve()
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if args.resume_dir: run_screen_resume(args.resume_dir, args.start_index, args.skip_candidate_id, args.skip_reason, args.skip_bridge)
        elif args.phase == "screen": run_screen(args.result_dir)
        elif args.phase == "layout": run_layout(args.result_dir, args.base_candidate, args.screen_dir.resolve())
        else: run_final(args.result_dir, args.candidate_id, args.screen_dir.resolve() if args.screen_dir else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
