#!/usr/bin/env python3
"""Plan or freeze an immutable archive of the V4 roofline search experiment.

Default mode only prints a copy plan.  Use --freeze to copy into a new target.
This package is an experimental search archive, not a production release.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
V4 = ROOT / "bench/8454h/roofline_v4"
DEFAULT_TARGET = ROOT / "bench/8454h/versions/v4_roofline_search_round1"
LOCK = Path("/tmp/ozamx-perf.lock")
ROUND_COMPLETE = V4 / "ROUND_COMPLETE.json"
ROUND_RESULTS = ROOT / "docs/8454H_V4_ROUND_RESULTS.md"
V3_MANIFEST = ROOT / "bench/8454h/versions/v3_release/MANIFEST.sha256"
FROZEN_LIBRARY = ROOT / "bench/8454h/versions/v3_release/artifacts/libozamx_v3.a"
MKL_RUNTIME = ROOT / "third_party/code/mkl-current/lib/libmkl_rt.so.3"

SOURCE_KITS = (
    "search_src", "diagnostic_src", "recon_ilp_src", "packed_layout_src",
    "page_layout_src", "adaptive_release_src", "adaptive_release_n512_src",
    "int8_proto", "calibration_20261014", "adopted_current_main",
)
DOCS = (
    "8454H_CURRENT_BASELINE.md", "8454H_V3_PAPER_ALIGNMENT.md",
    "8454H_FINAL_PERFORMANCE_REPORT.md", "8454H_V4_COST_MODEL.md",
    "8454H_V4_DIAGNOSTIC_RESULTS.md", "8454H_V4_INT8_EXPERIMENT.md",
    "8454H_V4_LAYOUT_RESULTS.md", "8454H_V4_MATCHED_RESULTS.md",
    "8454H_V4_PACKED_LAYOUT_RESULTS.md", "8454H_V4_PAGE_LAYOUT_RESULTS.md",
    "8454H_V4_RECON_ILP_RESULTS.md", "8454H_V4_ROOFLINE_CALIBRATION.md",
    "8454H_V4_SEARCH_LOG.md", "8454H_V4_SEARCH_PLAN.md",
    "8454H_V4_ROUND_RESULTS.md", "8454H_V4_CURRENT_MAIN_VALIDATION.md",
    "CPU_LIMITS.md", "ENVIRONMENT.md",
)
BUILD_KEEP_NAMES = {
    "libozamx.a", "libozamx_v3.a", "ozamx_benchmark", "benchmark_driver", "driver",
    "compile_commands.json",
    "CMakeCache.txt", "build_identity.json", "SOURCE_IDENTITY.json",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def want_file(path: Path) -> bool:
    parts = path.relative_to(V4).parts
    if "__pycache__" in parts or path.suffix == ".pyc":
        return False
    # Preserve complete source snapshots, excluding only generated build/result trees.
    if parts[0] in SOURCE_KITS:
        if any(p == "build" or p == "builds" or p.startswith("build_") for p in parts):
            return False
        return path.is_file()
    if parts[0] in {"search_runs", "recon_ilp_runs", "matched_calls", "adaptive_release_runs",
                    "kernel_schedule_runs", "production_validation_runs"}:
        if any(p == "build" or p == "builds" or p.startswith("build_") for p in parts):
            return path.name in BUILD_KEEP_NAMES or path.suffix in {".asm", ".dis", ".s"}
        return path.is_file()
    if len(parts) == 1:
        return path.is_file()
    return False


def collect() -> list[Path]:
    chosen: set[Path] = set()
    for path in V4.rglob("*"):
        if path.is_file() and want_file(path):
            chosen.add(path)
    docsdir = ROOT / "docs"
    for name in DOCS:
        p = docsdir / name
        if p.is_file():
            chosen.add(p)
    # Record the source bibliography and local HTML/manual references when present.
    refs = V4 / "techrefs.json"
    if refs.is_file():
        chosen.add(refs)
        try:
            obj = json.loads(refs.read_text())
            items = obj if isinstance(obj, list) else obj.get("references", obj.values())
            for item in items:
                if isinstance(item, dict):
                    candidate = item.get("local_path") or item.get("local_file") or item.get("path")
                    if candidate:
                        p = (ROOT / candidate).resolve()
                        if p.is_file() and (p.suffix.lower() in {".html", ".htm", ".json", ".pdf"}):
                            chosen.add(p)
        except (OSError, ValueError, TypeError):
            pass
    for path in (
        ROOT / "third_party/manuals/linux-transhuge.html",
        ROOT / "third_party/manuals/linux-transhuge.metadata.json",
        ROOT / "third_party/intel/manuals/manifest.json",
    ):
        if path.is_file():
            chosen.add(path)
    for path in (ROOT / "third_party/manuals").rglob("*"):
        if path.is_file():
            chosen.add(path)
    # Preserve successful Intel HTML references and their acquisition metadata.
    intel_refs = ROOT / "third_party/intel"
    for path in intel_refs.rglob("*"):
        if path.is_file() and (path.suffix.lower() in {".html", ".htm"}
                               or (path.suffix.lower() == ".json" and "metadata" in path.name.lower())):
            chosen.add(path)
    # Current roofline model source/doc artifacts used by the experiment.
    for name in ("8454H_ROOFLINE_MODEL.md", "8454H_ROOFLINE_TRAFFIC.md", "8454H_ROOFLINE_CALIBRATION.md"):
        p = docsdir / name
        if p.is_file():
            chosen.add(p)
    project_readme = ROOT / "README.md"
    if project_readme.is_file():
        chosen.add(project_readme)
    for p in (V3_MANIFEST, FROZEN_LIBRARY):
        if p.is_file():
            chosen.add(p)
    chosen.add(Path(__file__).resolve())
    return sorted(chosen, key=rel)


def readonly_tree(target: Path) -> None:
    for p in sorted(target.rglob("*"), reverse=True):
        mode = p.stat().st_mode
        p.chmod(mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    mode = target.stat().st_mode
    target.chmod(mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target", type=Path, default=DEFAULT_TARGET,
                    help=f"new archive directory (default: {DEFAULT_TARGET.relative_to(ROOT)})")
    ap.add_argument("--freeze", action="store_true", help="copy files, hash manifest, and make the new archive read-only")
    args = ap.parse_args()
    target = args.target if args.target.is_absolute() else ROOT / args.target
    target = target.resolve()
    if target.exists():
        print(json.dumps({"status": "refused", "reason": "target already exists; refusing overwrite", "target": str(target)}, indent=2))
        return 2
    if args.freeze:
        try:
            completion = json.loads(ROUND_COMPLETE.read_text())
        except (OSError, ValueError):
            completion = None
        if not isinstance(completion, dict) or completion.get("overall_status") != "complete" or not ROUND_RESULTS.is_file():
            print(json.dumps({"status": "refused", "reason": "final V4 round is not marked complete; requires ROUND_COMPLETE.json overall_status=complete and docs/8454H_V4_ROUND_RESULTS.md", "completion_marker": str(ROUND_COMPLETE), "results_document": str(ROUND_RESULTS)}, indent=2))
            return 2
    files = collect()
    total_bytes = sum(p.stat().st_size for p in files)
    plan = {"mode": "freeze" if args.freeze else "plan", "target": str(target),
            "file_count": len(files), "bytes": total_bytes,
            "files": [{"source": rel(p), "bytes": p.stat().st_size} for p in files]}
    if not args.freeze:
        print(json.dumps(plan, indent=2))
        return 0
    if not V4.is_dir() or not files:
        print("V4 source root is missing or empty", file=sys.stderr)
        return 2
    # Serialize archive I/O with benchmarks; no nested child process takes this lock.
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("a") as lockfile:
        fcntl.flock(lockfile, fcntl.LOCK_EX)
        if target.exists():
            print(json.dumps({"status": "refused", "reason": "target appeared while waiting for lock", "target": str(target)}, indent=2))
            return 2
        target.mkdir(parents=True)
        try:
            for source in files:
                dest = target / rel(source)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, dest)
            copied = sorted((p for p in target.rglob("*") if p.is_file()), key=lambda p: p.relative_to(target).as_posix())
            machine = {}
            env = ROOT / "docs/ENVIRONMENT.md"
            if env.is_file():
                machine["environment_doc"] = rel(env)
            cpuinfo = Path("/proc/cpuinfo")
            if cpuinfo.is_file():
                for line in cpuinfo.read_text(errors="replace").splitlines():
                    if line.lower().startswith("model name"):
                        machine["cpu_model"] = line.split(":", 1)[-1].strip()
                        break
            freeze_info = {
                "schema": "ozamx-v4-search-archive-freeze-1",
                "archive_kind": "v4_roofline_search_round1_experiment",
                "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "production_release": False,
                "no_production_inference": True,
                "source_root": rel(V4),
                "source_count": len(files),
                "manifest_entry_count": len(files) + 1,
                "manifest_path": "MANIFEST.json",
                "manifest_self_excluded": True,
                "frozen_v3_manifest_sha256": sha256(V3_MANIFEST) if V3_MANIFEST.is_file() else None,
                "frozen_v3_library_sha256": sha256(FROZEN_LIBRARY) if FROZEN_LIBRARY.is_file() else None,
                "host": os.uname().nodename,
                "machine": machine,
                "mkl_runtime": {"original_path": str(MKL_RUNTIME),
                                "sha256": sha256(MKL_RUNTIME) if MKL_RUNTIME.is_file() else None,
                                "copied": False},
                "archive_tool": rel(Path(__file__).resolve()),
                "omissions": ["oneMKL third-party runtime tree (identity hashes/paths are retained in run metadata)",
                              "generated build trees except selected exact libraries, executables, identities, compile commands, and disassembly"],
            }
            (target / "freeze_info.json").write_text(json.dumps(freeze_info, indent=2) + "\n")
            copied.append(target / "freeze_info.json")
            copied.sort(key=lambda p: p.relative_to(target).as_posix())
            manifest = {"schema": "ozamx-v4-search-archive-manifest-1", "self_excluded": True,
                        "entries": [{"path": p.relative_to(target).as_posix(), "size_bytes": p.stat().st_size, "sha256": sha256(p)}
                                    for p in copied]}
            (target / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
            readonly_tree(target)
        except Exception:
            # Preserve partial evidence; never delete potentially useful failed-copy output.
            raise
    print(json.dumps({"status": "frozen", "target": str(target), "copied_files": len(files),
                      "manifest_entries": len(manifest["entries"]), "bytes": total_bytes,
                      "manifest_sha256": sha256(target / "MANIFEST.json")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
