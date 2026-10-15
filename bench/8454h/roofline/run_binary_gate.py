#!/usr/bin/env python3
"""Stream full GEMM result buffers from frozen and adaptive builds and compare byte-for-byte."""
import argparse
import fcntl
import hashlib
import json
import os
import pathlib
import struct
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]
DRIVER = ROOT / "tools/roofline_binary_gate.cpp"
HEADER_ROOT = ROOT / "bench/8454h/versions/v2/include"
FROZEN_LIB = pathlib.Path("/tmp/ozamx-production-final/libozamx.a")
ADAPTIVE_ROOT = pathlib.Path("/tmp/ozamx-roof-adaptive")
DEFAULT_CANDIDATE_LIB = ADAPTIVE_ROOT / "build/libozamx.a"
DEFAULT_CANDIDATE_HEADER = ADAPTIVE_ROOT / "include/ozamx/gemm.hpp"
FROZEN_HEADER = HEADER_ROOT / "ozamx/gemm.hpp"
LOCK = pathlib.Path("/tmp/ozamx-perf.lock")
HEADER = struct.Struct("<8sIIIIQQII")
CHUNK = 64 * 1024
TRAIL = 8

CASES = [
    (1, "f32_4096_cube", 1, 0, 4096, 4096, 4096, 4, 0),
    (2, "f64_4096_cube_p6", 2, 6, 4096, 4096, 4096, 8, 0),
    (3, "f64_4096_cube_p10", 2, 10, 4096, 4096, 4096, 8, 0),
    (4, "f64_4096_cube_p15", 2, 15, 4096, 4096, 4096, 8, 0),
    (5, "f64_4096_cube_p21", 2, 21, 4096, 4096, 4096, 8, 0),
    (6, "f32_4096x4097x257", 1, 0, 4096, 4097, 257, 4, 0),
    (7, "f64_4096x4097x257_p21", 2, 21, 4096, 4097, 257, 8, 0),
    (8, "f64_4097x4096x4097_p21", 2, 21, 4097, 4096, 4097, 8, 0),
    (9, "f64_wide_overflow_k512", 2, 6, 4096, 4096, 512, 8, 1),
    (10, "f64_wide_cancellation_k512", 2, 6, 4096, 4096, 512, 8, 2),
    (11, "f64_alias_a_equals_c_p6", 2, 6, 4096, 4096, 256, 8, 3),
    (12, "f64_alias_b_equals_c_p6", 2, 6, 4096, 4096, 256, 8, 4),
]


def sha(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def read_exact(stream, count):
    pieces = bytearray()
    while len(pieces) < count:
        part = stream.read(count - len(pieces))
        if not part:
            raise EOFError(f"wanted {count} bytes, got {len(pieces)}")
        pieces.extend(part)
    return bytes(pieces)


def launch(binary, case_id, label, env):
    stderr_path = LOGS / f"{label}_{case_id:02d}.stderr.log"
    err = stderr_path.open("wb")
    proc = subprocess.Popen(["taskset", "-c", "0-63", str(binary), str(case_id)], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=err, bufsize=0, env=env)
    proc.stdin.write(b"\x01")
    proc.stdin.flush()
    try:
        header = HEADER.unpack(read_exact(proc.stdout, HEADER.size))
    except Exception:
        proc.kill()
        proc.wait()
        err.close()
        raise RuntimeError(f"{label} child produced no full result header; stderr={stderr_path}")
    return proc, err, stderr_path, header


def header_include_root(value):
    path = pathlib.Path(value).resolve()
    if path.is_file():
        if path.name != "gemm.hpp":
            raise SystemExit(f"candidate header must be gemm.hpp or its include directory: {path}")
        return path.parent.parent
    return path


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-library", type=pathlib.Path, default=DEFAULT_CANDIDATE_LIB)
    parser.add_argument("--candidate-header", type=pathlib.Path, default=DEFAULT_CANDIDATE_HEADER,
                        help="gemm.hpp path or its include root")
    parser.add_argument("--output", type=pathlib.Path, default=ROOT / "bench/8454h/roofline/binary_gate.json")
    parser.add_argument("--threads", type=int, default=64)
    parser.add_argument("--case-ids", default=",".join(str(row[0]) for row in CASES),
                        help="comma-separated case IDs; default is every case")
    return parser.parse_args()


def main(args):
    global OUT, LOGS
    OUT = args.output.resolve()
    candidate_lib = args.candidate_library.resolve()
    candidate_include = header_include_root(args.candidate_header)
    logs = OUT.parent / f"{OUT.stem}_logs"
    logs.mkdir(parents=True, exist_ok=True)
    LOGS = logs
    selected_ids = {int(x) for x in args.case_ids.split(",") if x.strip()}
    selected_cases = [row for row in CASES if row[0] in selected_ids]
    if not selected_cases or {r[0] for r in selected_cases} != selected_ids:
        raise SystemExit(f"unknown or empty case ID selection: {args.case_ids}")
    if args.threads < 1:
        raise SystemExit("--threads must be positive")
    for path in (DRIVER, FROZEN_LIB, candidate_lib, FROZEN_HEADER, candidate_include / "ozamx/gemm.hpp"):
        if not path.is_file():
            raise SystemExit(f"required input is missing: {path}")
    if sha(FROZEN_HEADER) != sha(candidate_include / "ozamx/gemm.hpp"):
        raise SystemExit("frozen and adaptive public headers differ; refusing ABI-mismatched comparison")
    env = dict(os.environ, OMP_NUM_THREADS=str(args.threads), OMP_PLACES="cores",
               OMP_PROC_BIND="close", OMP_DYNAMIC="FALSE")
    cxx = os.environ.get("CXX", "g++")
    flags = ["-std=c++17", "-O3", "-march=sapphirerapids", "-ffp-contract=off", "-fopenmp"]
    bin_dir = pathlib.Path("/tmp/ozamx-roofline-binary-gate") / OUT.stem
    bin_dir.mkdir(parents=True, exist_ok=True)
    baseline_bin, adaptive_bin = bin_dir / "frozen", bin_dir / "adaptive"
    build_commands = []
    for name, lib, inc, exe in (("frozen", FROZEN_LIB, HEADER_ROOT, baseline_bin),
                                ("candidate", candidate_lib, candidate_include, adaptive_bin)):
        command = [cxx, *flags, f"-I{inc}", str(DRIVER), str(lib), "-o", str(exe)]
        log = logs / f"build_{name}.log"
        with log.open("wb") as f:
            p = subprocess.run(command, stdout=f, stderr=subprocess.STDOUT)
        build_commands.append({"name": name, "argv": command, "exit_code": p.returncode, "log": str(log)})
        if p.returncode:
            raise SystemExit(f"{name} driver build failed; see {log}")

    result = {
        "status": "running", "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "comparison": "Full C storage including each row's LD pad and 64-byte trailing guard is streamed from each process and compared byte-for-byte in 64 KiB chunks; no full outputs are written to files.",
        "execution": {"frozen_then_candidate_per_case": True, "affinity": "taskset -c 0-63", "threads": args.threads, "places": "cores", "proc_bind": "close", "dynamic": False, "large_compute_overlap": False},
        "header_sha256": sha(FROZEN_HEADER), "driver_sha256": sha(DRIVER),
        "frozen_library_sha256": sha(FROZEN_LIB), "candidate_library_path": str(candidate_lib),
        "candidate_header_sha256": sha(candidate_include / "ozamx/gemm.hpp"),
        "candidate_library_sha256": sha(candidate_lib), "runner_sha256": sha(__file__),
        "build_commands": build_commands, "cases": [], "failure": None,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    for cid, name, typ, budget, m, n, k, elem_size, mode in selected_cases:
        expected_slots = m * (n + 1) + 64 // elem_size
        expected_bytes = expected_slots * elem_size
        base = candidate = None
        try:
            base = launch(baseline_bin, cid, "frozen", env)
            cand = launch(adaptive_bin, cid, "candidate", env)
            candidate = cand
            bp, be, bpath, bh = base
            cp, ce, cpath, ch = cand
            expected_exception = mode in (1, 2)
            header_checks = []
            for label, h in (("frozen", bh), ("candidate", ch)):
                magic, version, got_id, got_type, status, payload_bytes, slots, guards, unchanged = h
                valid = (magic == b"OZBGATE1" and version == 1 and got_id == cid and
                         got_type == typ and status == 0 and payload_bytes == expected_bytes and
                         slots == expected_slots and guards == 0 and unchanged == int(expected_exception))
                header_checks.append({"binary": label, "valid": valid, "status": status,
                                     "payload_bytes": payload_bytes, "slots": slots,
                                     "guard_failures": guards, "unchanged": bool(unchanged)})
            bhash, chash = hashlib.sha256(), hashlib.sha256()
            compared = mismatches = 0
            first_mismatch = None
            while compared < expected_bytes:
                size = min(CHUNK, expected_bytes - compared)
                xb = read_exact(bp.stdout, size)
                xc = read_exact(cp.stdout, size)
                bhash.update(xb); chash.update(xc)
                if xb != xc:
                    diff = [i for i, (x, y) in enumerate(zip(xb, xc)) if x != y]
                    mismatches += len(diff)
                    if first_mismatch is None and diff:
                        first_mismatch = compared + diff[0]
                compared += size
            base_extra, cand_extra = bp.stdout.read(1), cp.stdout.read(1)
            brc, crc = bp.wait(), cp.wait()
            be.close(); ce.close()
            ok = (all(h["valid"] for h in header_checks) and mismatches == 0 and
                  not base_extra and not cand_extra and brc == 0 and crc == 0)
            entry = {"case": name, "id": cid, "precision": "fp32" if typ == 1 else "fp64",
                     "budget": budget or None, "shape_mnk": [m, n, k], "lda_ldb_ldc": [k+1, n+1, n+1],
                     "mode": ["normal", "overflow_transaction", "cancellation_transaction", "alias_a_equals_c", "alias_b_equals_c"][mode],
                     "expected_slot_count_including_padding_and_tail": expected_slots,
                     "expected_bytes": expected_bytes, "bytes_compared": compared,
                     "full_output_sha256": {"frozen": bhash.hexdigest(), "candidate": chash.hexdigest()},
                     "byte_mismatches": mismatches, "first_mismatch_offset": first_mismatch,
                     "headers": header_checks, "child_exit_codes": {"frozen": brc, "candidate": crc},
                     "extra_output_bytes": {"frozen": bool(base_extra), "candidate": bool(cand_extra)},
                     "stderr_logs": {"frozen": str(bpath), "candidate": str(cpath)}, "pass": ok}
            result["cases"].append(entry)
            result["status"] = "running" if ok else "failed"
            if not ok:
                result["failure"] = {"case": name, "reason": "header/status/guards, full byte compare, trailing EOF, or child exit check failed"}
            OUT.write_text(json.dumps(result, indent=2) + "\n")
            if not ok:
                break
        except Exception as ex:
            for child in (base, candidate):
                if child:
                    proc, err, _, _ = child
                    if proc.poll() is None:
                        proc.kill()
                    proc.wait()
                    if not err.closed: err.close()
            result["status"] = "failed"
            result["failure"] = {"case": name, "reason": repr(ex)}
            OUT.write_text(json.dumps(result, indent=2) + "\n")
            raise
    if result["status"] != "failed":
        result["status"] = "pass"
    result["completed_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "completed_cases": len(result["cases"]), "output": str(OUT)}))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    with LOCK.open("a+") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        sys.exit(main(parse_args()))
