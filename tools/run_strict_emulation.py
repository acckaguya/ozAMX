#!/usr/bin/env python3
"""Run the paired strict-emulation campaign with immutable artifacts and provenance."""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN_ROOT = ROOT / "bench/8454h/strict_emulation"
SOURCES = ["CMakeLists.txt", "include/ozamx/gemm.hpp", "src/gemm.cpp", "src/preprocess.hpp",
           "src/tuning.hpp", "src/runtime.cpp", "src/kernels.S", "bench/benchmark.cpp",
           "tests/strict_emulation_probe.cpp", "tools/run_strict_emulation.py"]

def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda: stream.read(4*1024*1024), b""):
            h.update(data)
    return h.hexdigest()

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True,
                        help=f"new campaign directory (normally under {CAMPAIGN_ROOT})")
    parser.add_argument("--sizes", default="256,512,1024,2048,4096,8192,16384,32768")
    parser.add_argument("--precision", choices=["all", "fp32", "fp64"], default="all")
    parser.add_argument("--budgets", default="6,10,15,21")
    parser.add_argument("--reps", type=int, default=10)
    parser.add_argument("--wait", choices=["passive", "runtime"], default="passive")
    parser.add_argument("--cache-bytes", type=int, default=2147483648)
    a = parser.parse_args()
    build, out = a.build.resolve(), a.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    for key in list(env):
        if key.startswith(("OMP_", "GOMP_", "KMP_", "MKL_", "OZAMX_")):
            del env[key]
    for key in ["LD_PRELOAD", "LD_AUDIT"]:
        env.pop(key, None)
    env.update({"LD_LIBRARY_PATH": str(ROOT/"third_party/code/mkl-current/lib"),
                "OMP_NUM_THREADS": "64", "OMP_PLACES": "cores", "OMP_PROC_BIND": "close",
                "OMP_DYNAMIC": "FALSE", "MKL_NUM_THREADS": "64", "MKL_DYNAMIC": "FALSE",
                "MKL_THREADING_LAYER": "GNU", "MKL_INTERFACE_LAYER": "LP64",
                "OZAMX_WORKSPACE_CACHE_BYTES": str(a.cache_bytes)})
    if a.wait == "passive":
        env.update({"OMP_WAIT_POLICY": "PASSIVE", "GOMP_SPINCOUNT": "0"})
    for name in SOURCES:
        target = out/"source_snapshot"/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT/name, target)
    for source, target in [(build/"ozamx_benchmark", out/"candidate"),
                           (build/"libozamx.a", out/"libozamx.a"),
                           (build/"CMakeCache.txt", out/"CMakeCache.txt")]:
        shutil.copy2(source, target)
    command = ["taskset", "-c", "0-63", "/usr/bin/time", "-v", "-o", str(out/"outer_time.txt"),
               str(out/"candidate"), "--sizes", a.sizes, "--precision", a.precision,
               "--budgets", a.budgets, "--threads", "64", "--reps", str(a.reps),
               "--checkpoint", str(out/"checkpoint"), "--output", str(out/"results.csv")]
    provenance = {"created_utc": now(), "status": "waiting_for_lock", "command": command,
                  "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(),
                  "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                  "environment": {k: v for k, v in sorted(env.items()) if k.startswith(("OMP_", "GOMP_", "KMP_", "MKL_", "OZAMX_")) or k == "LD_LIBRARY_PATH"},
                  "source_sha256": {p: sha(ROOT/p) for p in SOURCES},
                  "artifact_sha256": {p: sha(out/p) for p in ["candidate", "libozamx.a", "CMakeCache.txt"]},
                  "protocol": "One warmup per routine, 10 timed pairs by default; even API first, odd MKL first; API headline includes setup and teardown.",
                  "scope": "Shared 8454H/GNU host, not the 8462Y+/Intel/fixed-frequency reference host; no Figure 7 performance success is implied."}
    manifest = out/"provenance.json"
    def save():
        temporary = out/"provenance.json.tmp"
        temporary.write_text(json.dumps(provenance, indent=2)+"\n")
        temporary.replace(manifest)
    save()
    (out/"machine_lscpu.txt").write_text(subprocess.check_output(["lscpu"], text=True))
    print(f"Waiting for performance lock: {out}", flush=True)
    with Path("/tmp/ozamx-perf.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        provenance.update(status="running", started_utc=now())
        save()
        print(f"Running {a.precision}, N={a.sizes}, reps={a.reps}: {out}", flush=True)
        with (out/"stdout.log").open("w") as stdout, (out/"stderr.log").open("w") as stderr:
            process = subprocess.run(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
        unchanged = all(sha(ROOT/p) == expected for p, expected in provenance["source_sha256"].items())
        provenance.update(returncode=process.returncode, finished_utc=now(), source_unchanged=unchanged,
                          status="complete" if process.returncode == 0 and unchanged else "failed")
        save()
    print(f'{provenance["status"]}: {out}', flush=True)
    return 0 if provenance["status"] == "complete" else 1

if __name__ == "__main__":
    raise SystemExit(main())
