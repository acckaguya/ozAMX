#!/usr/bin/env python3
"""Resume an interrupted strict-emulation campaign under its frozen identity.

`tools/run_strict_emulation.py` freezes the ten campaign sources plus the
candidate/libozamx.a/CMakeCache artifacts and records them in the campaign's
provenance.json.  If the campaign process is interrupted (for example by a
usage-limit shutdown of the supervising session), this tool continues the SAME
output directory with `--resume`:

1. every frozen source and artifact is re-hashed and must still be
   byte-identical to provenance.json;
2. the candidate is launched with `--resume`, so each existing checkpoint is
   validated against the benchmark's full run-identity record (driver source,
   executable, oneMKL runtime, loaded objects, OMP/MKL environment, affinity,
   host, schema and protocol) BEFORE any stored sample is reused;
3. the resume invocation and its environment are appended to provenance.json
   as an explicit `resume_events` entry, and the campaign status is updated.

Use --check-only to run all verifications without launching the candidate.
"""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ["CMakeLists.txt", "include/ozamx/gemm.hpp", "src/gemm.cpp", "src/preprocess.hpp",
           "src/tuning.hpp", "src/runtime.cpp", "src/kernels.S", "bench/benchmark.cpp",
           "tests/strict_emulation_probe.cpp", "tools/run_strict_emulation.py"]
ARTIFACTS = ["candidate", "libozamx.a", "CMakeCache.txt"]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(data)
    return h.hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def fail(message):
    raise SystemExit("resume refused: " + message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--wait", choices=["passive", "runtime"], default="passive")
    parser.add_argument("--cache-bytes", type=int, default=2147483648)
    parser.add_argument("--check-only", action="store_true")
    a = parser.parse_args()
    out = a.out.resolve()
    provenance_path = out / "provenance.json"
    if not provenance_path.is_file():
        fail(f"missing {provenance_path}")
    provenance = json.loads(provenance_path.read_text())
    if not provenance.get("command"):
        fail("provenance.json has no recorded command")

    def frozen_source(p):
        # New campaigns freeze paths that still exist in the live tree. Legacy
        # campaigns froze the pre-rename probe/runner paths; those files are
        # intentionally absent now, so compare against the campaign's own
        # source_snapshot copy instead of rewriting historical provenance.
        live = ROOT / p
        if live.is_file():
            return live
        snapshot = out / "source_snapshot" / p
        return snapshot if snapshot.is_file() else None

    def frozen_hash(p):
        source = frozen_source(p)
        return None if source is None else sha(source)

    changed = [p for p, digest in provenance["source_sha256"].items()
               if frozen_hash(p) != digest]
    if changed:
        fail("frozen sources changed or missing: " + ", ".join(changed))
    for name, digest in provenance["artifact_sha256"].items():
        if name not in ARTIFACTS:
            fail(f"unexpected recorded artifact {name}")
        if not (out / name).is_file() or sha(out / name) != digest:
            fail(f"campaign artifact missing or changed: {name}")

    command = list(provenance["command"])
    if "--resume" not in command:
        index = command.index("--checkpoint") if "--checkpoint" in command else len(command)
        command[index:index] = ["--resume"]

    env = os.environ.copy()
    for key in list(env):
        if key.startswith(("OMP_", "GOMP_", "KMP_", "MKL_", "OZAMX_")):
            del env[key]
    for key in ["LD_PRELOAD", "LD_AUDIT"]:
        env.pop(key, None)
    env.update({"LD_LIBRARY_PATH": str(ROOT / "third_party/code/mkl-current/lib"),
                "OMP_NUM_THREADS": "64", "OMP_PLACES": "cores", "OMP_PROC_BIND": "close",
                "OMP_DYNAMIC": "FALSE", "MKL_NUM_THREADS": "64", "MKL_DYNAMIC": "FALSE",
                "MKL_THREADING_LAYER": "GNU", "MKL_INTERFACE_LAYER": "LP64",
                "OZAMX_WORKSPACE_CACHE_BYTES": str(a.cache_bytes)})
    if a.wait == "passive":
        env.update({"OMP_WAIT_POLICY": "PASSIVE", "GOMP_SPINCOUNT": "0"})
    recorded_environment = {k: v for k, v in sorted(env.items())
                            if k.startswith(("OMP_", "GOMP_", "KMP_", "MKL_", "OZAMX_")) or
                            k == "LD_LIBRARY_PATH"}
    expected_environment = provenance.get("environment", {})
    mismatched = {k: v for k, v in expected_environment.items()
                  if recorded_environment.get(k) != v}
    if mismatched:
        fail(f"launch environment no longer matches the frozen campaign: {mismatched}")

    event = {"resumed_utc": now(),
             "runner": "tools/resume_strict_emulation.py",
             "runner_sha256": sha(ROOT / "tools/resume_strict_emulation.py"),
             "command": command,
             "environment": recorded_environment,
             "status_before": provenance.get("status")}
    print("resume verifications passed")
    print("command:", " ".join(command))
    if a.check_only:
        return 0

    provenance.setdefault("resume_events", []).append(event)
    provenance.update(status="running", resumed_utc=event["resumed_utc"])
    manifest = out / "provenance.json"
    temporary = out / "provenance.json.tmp"
    temporary.write_text(json.dumps(provenance, indent=2) + "\n")
    temporary.replace(manifest)

    print(f"Waiting for performance lock: {out}", flush=True)
    with Path("/tmp/ozamx-perf.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        print(f"Running resumed campaign: {out}", flush=True)
        with (out / "stdout.log").open("a") as stdout, (out / "stderr.log").open("a") as stderr:
            process = subprocess.run(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
        unchanged = all(sha(ROOT / p) == value
                        for p, value in provenance["source_sha256"].items())
        event.update(returncode=process.returncode, finished_utc=now(), source_unchanged=unchanged)
        provenance.update(returncode=process.returncode, finished_utc=now(),
                          source_unchanged=unchanged,
                          status="complete" if process.returncode == 0 and unchanged else "failed")
        temporary.write_text(json.dumps(provenance, indent=2) + "\n")
        temporary.replace(manifest)
    print(f'{provenance["status"]}: {out}', flush=True)
    return 0 if provenance["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
