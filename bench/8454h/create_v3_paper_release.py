#!/usr/bin/env python3
"""Create the immutable supplementary archive after the full paper campaign passes.

This is deliberately opt-in: it refuses to run unless --freeze is present. It does
not build or run any CPU benchmark. The destination and completion marker are
write-once; an existing one is always an error.
"""
from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN = ROOT / "bench/8454h/v3_paper_alignment"
VERSIONS = ROOT / "bench/8454h/versions"
DEST = VERSIONS / "v3_paper_release"
MARKER = CAMPAIGN / "FROZEN_COMPLETE"
EXPECTED_LIBRARY_SHA = "73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c"
SOURCE_ID = "v3-paper-alignment-20261014"
SIZES = (256, 512, 1024, 2048, 4096, 8192, 16384, 32768)
THREADS = (2, 4, 8, 16, 32, 64)
BUDGETS = (6, 10, 15, 21)
MODES = (("fp32", 6), ("fp64", 6), ("fp64", 10), ("fp64", 15), ("fp64", 21))
EXPECTED_COUNT = 40 + 18 + 8

V3_CORE_FILES = (
    "repo/CMakeLists.txt",
    "repo/include/ozamx/gemm.hpp",
    "repo/src/gemm.cpp",
    "repo/src/kernels.S",
    "repo/src/main.cpp",
    "repo/src/preprocess.hpp",
    "repo/src/runtime.cpp",
    "repo/src/tuning.hpp",
)
CAMPAIGN_METADATA = (
    "environment.txt", "provenance.txt", "machine_lscpu.txt", "machine_uname.txt",
    "cpu_governor.txt", "cpu_freq_policy.txt", "perf_permissions.txt", "runner.log",
    "config_status.csv", "run.sh",
    "per_config_manifest.json", "write_manifest.py", "watch_hardware.sh",
    "host_cpu_activity_diagnostic.json", "runner.nohup.log",
    "campaign_completion.json",
)
DOC_FILES = (
    "docs/8454H_V3_PAPER_ALIGNMENT.md",
    "docs/REPRODUCTION_SPEC.md",
    "docs/REPRODUCTION_RESULTS.md",
    "docs/NATIVE_ALTERNATIVE_ACCURACY.md",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def expected_configs() -> dict[str, tuple[str, int, int, int | None]]:
    expected: dict[str, tuple[str, int, int, int | None]] = {}
    for n in SIZES:
        expected[f"main_fp32_n{n}"] = ("fp32", n, 64, 6)
        for b in BUDGETS:
            expected[f"main_fp64p{b}_n{n}"] = ("fp64", n, 64, b)
    for n in (1024, 4096, 16384):
        for t in THREADS:
            expected[f"scaling_fp32_n{n}_t{t}"] = ("fp32", n, t, 6)
    for n in SIZES:
        expected[f"raw_bf16_n{n}"] = ("raw", n, 64, None)
    assert len(expected) == EXPECTED_COUNT
    return expected


def checkpoint_for(key: str, cfg: tuple[str, int, int, int | None]) -> Path:
    precision, n, _, budget = cfg
    if precision == "raw":
        return CAMPAIGN / "checkpoints" / f"{key}.json"
    suffix = f".{precision}.{n}.{budget}.json"
    if precision == "fp32":
        suffix = f".fp32.{n}.6.json"
    return CAMPAIGN / "checkpoints" / f"{key}{suffix}"


def command_log(key: str, suffix: str) -> Path:
    ending = "command.txt" if suffix == "command" else suffix
    return CAMPAIGN / "logs" / f"{key}.{ending}"


def validate_configs(analysis: dict, expected: dict[str, tuple[str, int, int, int | None]]) -> None:
    if analysis.get("campaign_complete") is not True:
        raise RuntimeError("analysis does not mark all 40+18+8 cases and hashes complete")
    for group, count in (("main", 40), ("scaling", 18), ("raw_bf16", 8)):
        cov = analysis.get("coverage", {}).get(group, {})
        if cov.get("expected") != count or cov.get("present") != count or cov.get("valid") != count or cov.get("complete") is not True:
            raise RuntimeError(f"incomplete {group} coverage: {cov}")
    cases = analysis.get("main_cases", []) + analysis.get("scaling_cases", []) + analysis.get("raw_bf16_cases", [])
    by_key = {c.get("key"): c for c in cases}
    if len(cases) != EXPECTED_COUNT or set(by_key) != set(expected):
        raise RuntimeError("analysis case keys are missing, duplicated, or unexpected")
    bad = [key for key, case in by_key.items() if case.get("valid") is not True]
    if bad:
        raise RuntimeError("analysis invalid cases: " + ", ".join(bad))
    if analysis.get("expected_library_sha256") != EXPECTED_LIBRARY_SHA or analysis.get("library_hash_matches_expected") is not True:
        raise RuntimeError("the campaign library hash does not match the frozen V3 library")
    integrity = analysis.get("artifact_integrity", {})
    if integrity.get("source_and_runtime_hashes_match") is not True:
        raise RuntimeError("campaign source or oneMKL runtime hashes differ from provenance")

    status_path = CAMPAIGN / "config_status.csv"
    with status_path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != EXPECTED_COUNT:
        raise RuntimeError(f"config status has {len(rows)} rows; expected exactly {EXPECTED_COUNT}")
    status_by_key = {r.get("config"): r for r in rows}
    if len(status_by_key) != len(rows) or set(status_by_key) != set(expected):
        raise RuntimeError("config status keys contain duplicates, omissions, or extras")
    for key, cfg in expected.items():
        row = status_by_key[key]
        if row.get("rc") != "0":
            raise RuntimeError(f"{key} process return code is not zero")
        result = Path(row.get("result", ""))
        if not result.is_absolute() or result.resolve() != (CAMPAIGN / "results" / f"{key}.csv").resolve():
            raise RuntimeError(f"{key} status points to an unexpected results file")
        csv_path = result
        with csv_path.open(newline="") as f:
            csv_rows = list(csv.DictReader(f))
        if len(csv_rows) != 1 or csv_rows[0].get("status") != "ok":
            raise RuntimeError(f"{key} CSV is not a single successful result row")
        reps = int(csv_rows[0].get("repetitions", "0"))
        if reps != 10:
            raise RuntimeError(f"{key} has repetitions={reps}, expected 10")
        cp_path = checkpoint_for(key, cfg)
        cp = json.loads(cp_path.read_text())
        if cp.get("source_id") != SOURCE_ID or cp.get("complete") is not True:
            raise RuntimeError(f"{key} checkpoint source/completion status is invalid")
        if cp.get("requested_repetitions") != 10 or cp.get("completed_timed_repetitions") != 10:
            raise RuntimeError(f"{key} checkpoint does not have 10 timed repetitions")
        n = cfg[1]
        sample_key = "raw_seconds" if cfg[0] == "raw" else "call_wall_seconds"
        if not isinstance(cp.get(sample_key), list) or len(cp[sample_key]) != 10:
            raise RuntimeError(f"{key} checkpoint sample vector does not contain ten measurements")
        for suffix in ("command", "stdout.log", "stderr.log"):
            log_path = command_log(key, suffix)
            if not log_path.is_file():
                raise RuntimeError(f"missing {key} run record {log_path.name}")
        if cfg[0] != "raw":
            # eF_mkl/e_scaled_mkl are full-NxN metrics by the frozen driver source.
            for metric in ("eF_mkl", "e_scaled_mkl"):
                value = float(csv_rows[0][metric])
                if not (value >= 0 and value < float("inf")):
                    raise RuntimeError(f"{key} has invalid full-matrix metric {metric}")
        elif csv_rows[0].get("routine") != "raw_mkl_bf16bf16fp32":
            raise RuntimeError(f"{key} is not the raw BF16-BF16-FP32 routine")


def copy_one(src: Path, stage: Path, relative: str) -> None:
    dst = stage / relative
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def update_report_copy(report: str) -> str:
    report = re.sub(r"\| Table 4 main \| 40 \|[^\n]*", "| Table 4 main | 40 | 40 present and valid |", report)
    report = re.sub(r"\| Figure 8 FP32 scaling \| 18 \|[^\n]*", "| Figure 8 FP32 scaling | 18 | 18 present and valid |", report)
    report = re.sub(r"\| Figure 6 raw BF16 headroom \| 8 \|[^\n]*", "| Figure 6 raw BF16 headroom | 8 | 8 present and valid |", report)
    report = re.sub(
        r"At the current partial snapshot.*?all 66 rows validate\.",
        "The campaign completed with all 66 configurations validated: every row has successful process status, ten timed samples, and a complete matching checkpoint. Table 4 metrics cover full N×N output. Library, campaign source and MKL runtime hashes match the recorded provenance. No exact Figure 9 performance points are claimed.",
        report, flags=re.S)
    # In the immutable package this report lives beside `campaign/` and `tools/`,
    # rather than in the repository's docs/ tree. Keep its relative links usable.
    report = report.replace("(../bench/8454h/v3_paper_alignment/", "(../campaign/")
    report = report.replace("(../bench/8454h/create_v3_paper_release.py)", "(../tools/create_v3_paper_release.py)")
    report = report.replace(
        "this report update and analysis do not freeze or publish it.",
        "The immutable package is published only after explicit release validation.")
    return report


def build_package(stage: Path, expected: dict[str, tuple[str, int, int, int | None]], analysis: dict) -> None:
    for rel in CAMPAIGN_METADATA:
        copy_one(CAMPAIGN / rel, stage, f"campaign/{rel}")
    for src in sorted((CAMPAIGN / "hardware_samples").glob("*.txt")):
        if src.is_symlink() or not src.is_file():
            raise RuntimeError(f"unexpected hardware sample entry: {src}")
        copy_one(src, stage, f"campaign/hardware_samples/{src.name}")
    for extension in ("*.png", "*.svg"):
        for src in sorted((CAMPAIGN / "plots").glob(extension)):
            if src.is_symlink() or not src.is_file():
                raise RuntimeError(f"unexpected plot entry: {src}")
            copy_one(src, stage, f"campaign/plots/{src.name}")
    for rel in ("paper_reference.json", "analysis.json"):
        copy_one(CAMPAIGN / rel, stage, f"campaign/{rel}")
    for rel in ("source/benchmark.cpp", "source/raw_bf16.cpp", "build/ozamx_benchmark", "build/raw_bf16"):
        src = CAMPAIGN / rel
        if not src.is_file():
            raise RuntimeError(f"missing frozen driver/artifact {src}")
        copy_one(src, stage, f"campaign/{rel}")
    for key, cfg in expected.items():
        for rel in (f"results/{key}.csv",):
            copy_one(CAMPAIGN / rel, stage, f"campaign/{rel}")
        cp = checkpoint_for(key, cfg)
        copy_one(cp, stage, f"campaign/checkpoints/{cp.name}")
        for suffix in ("command", "stdout.log", "stderr.log"):
            p = command_log(key, suffix)
            copy_one(p, stage, f"campaign/logs/{p.name}")
    for rel in DOC_FILES:
        src = ROOT / rel
        dst = stage / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if rel.endswith("8454H_V3_PAPER_ALIGNMENT.md"):
            dst.write_text(update_report_copy(src.read_text()))
        else:
            shutil.copy2(src, dst)
    copy_one(ROOT / "tools/analyze_v3_paper_alignment.py", stage, "tools/analyze_v3_paper_alignment.py")
    copy_one(Path(__file__), stage, "tools/create_v3_paper_release.py")

    old = ROOT / "bench/8454h/versions/v3_release"
    archive_manifest = old / "MANIFEST.sha256"
    manifest = {}
    for line in archive_manifest.read_text().splitlines():
        digest, rel = line.split("  ", 1)
        manifest[rel] = digest
    for rel in ("artifacts/libozamx_v3.a", *V3_CORE_FILES):
        src = old / rel
        expected_hash = manifest.get(rel)
        if expected_hash is None or sha256(src) != expected_hash:
            raise RuntimeError(f"V3 release file fails original manifest check: {rel}")
        copy_one(src, stage, f"v3_release/{rel}")
    copy_one(old / "README.md", stage, "v3_release/README.md")
    copy_one(archive_manifest, stage, "v3_release/MANIFEST.sha256")
    source_manifest = "".join(f"{manifest[rel]}  {rel}\n" for rel in V3_CORE_FILES)
    (stage / "v3_release/v3_core_source_hashes.sha256").write_text(source_manifest)

    hashes = {
        "source_id": SOURCE_ID,
        "campaign_complete": True,
        "configurations": EXPECTED_COUNT,
        "main": 40, "scaling": 18, "raw_bf16": 8,
        "library_sha256": EXPECTED_LIBRARY_SHA,
        "v3_release_manifest_sha256": sha256(archive_manifest),
        "v3_core_source_hashes": {rel: manifest[rel] for rel in V3_CORE_FILES},
        "campaign_source_hashes": analysis["artifact_integrity"],
        "paper_reference_path": "campaign/paper_reference.json",
        "analysis_path": "campaign/analysis.json",
        "report_path": "docs/8454H_V3_PAPER_ALIGNMENT.md"
    }
    (stage / "frozen_provenance.json").write_text(json.dumps(hashes, indent=2) + "\n")
    (stage / "README.md").write_text(
        "# V3 paper-alignment supplemental freeze\n\n"
        "This immutable package contains the complete 40-case Table 4 campaign, 18-case Figure 8 scaling campaign, "
        "and 8-case Figure 6 raw BF16 headroom campaign, with raw rows, ten-sample checkpoints, commands, logs, "
        "environment, source drivers, analysis and paper reference. Every configuration was checked for rc=0, "
        "ten timed repetitions, a complete matching checkpoint, and (for GEMM emulation) full-NxN oneMKL accuracy fields.\n\n"
        f"The frozen V3 library SHA-256 is `{EXPECTED_LIBRARY_SHA}`. Its original release manifest and the selected "
        "core source files are included under `v3_release/`; this supplemental archive does not modify that release. "
        "The manifest `MANIFEST.sha256` covers every package file other than itself.\n"
    )


def write_manifest(stage: Path) -> str:
    entries = []
    for path in sorted(p for p in stage.rglob("*") if p.is_file() and p != stage / "MANIFEST.sha256"):
        entries.append(f"{sha256(path)}  {path.relative_to(stage).as_posix()}\n")
    (stage / "MANIFEST.sha256").write_text("".join(entries))
    for line in (stage / "MANIFEST.sha256").read_text().splitlines():
        digest, rel = line.split("  ", 1)
        if sha256(stage / rel) != digest:
            raise RuntimeError(f"new package hash verification failed: {rel}")
    return sha256(stage / "MANIFEST.sha256")


def readonly_tree(stage: Path) -> None:
    for p in stage.rglob("*"):
        if p.is_file():
            p.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    for p in sorted((x for x in stage.rglob("*") if x.is_dir()), key=lambda x: len(x.parts), reverse=True):
        p.chmod(stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    stage.chmod(stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true", help="required explicit opt-in to create the write-once package and completion marker")
    args = parser.parse_args()
    if not args.freeze:
        parser.error("refusing to create an archive without explicit --freeze")
    VERSIONS.mkdir(parents=True, exist_ok=True)
    lock_path = VERSIONS / ".v3_paper_release.lock"
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if DEST.exists() or MARKER.exists():
            raise RuntimeError("destination archive or FROZEN_COMPLETE already exists; refusing to overwrite")
        if "CAMPAIGN COMPLETE" not in (CAMPAIGN / "runner.log").read_text():
            raise RuntimeError("campaign runner has not recorded CAMPAIGN COMPLETE")
        subprocess.run([sys.executable, str(ROOT / "tools/analyze_v3_paper_alignment.py")], cwd=ROOT, check=True)
        analysis = json.loads((CAMPAIGN / "analysis.json").read_text())
        expected = expected_configs()
        validate_configs(analysis, expected)
        # Ensure the complete Table 4 reference comparison is present, full-sized and finite.
        main_rows = analysis.get("main_results", [])
        if len(main_rows) != 40 or any(r.get("accuracy_reference") != "full-NxN oneMKL SGEMM/DGEMM" for r in main_rows):
            raise RuntimeError("Table 4 accuracy analysis is not complete full-NxN data")
        stage = Path(tempfile.mkdtemp(prefix=".v3-paper-release-stage-", dir=VERSIONS))
        try:
            build_package(stage, expected, analysis)
            manifest_hash = write_manifest(stage)
            readonly_tree(stage)
            if DEST.exists() or MARKER.exists():
                raise RuntimeError("destination or marker appeared during freeze; refusing publication")
            os.rename(stage, DEST)
            marker_data = {
                "complete": True,
                "archive": str(DEST.relative_to(ROOT)),
                "manifest_sha256": manifest_hash,
                "configurations": EXPECTED_COUNT,
                "library_sha256": EXPECTED_LIBRARY_SHA,
                "completed_utc": datetime.now(timezone.utc).isoformat()
            }
            fd, tmp_name = tempfile.mkstemp(prefix=".FROZEN_COMPLETE.", dir=CAMPAIGN)
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(marker_data, f, indent=2)
                    f.write("\n")
                    f.flush()
                    os.fsync(f.fileno())
                os.link(tmp_name, MARKER)  # atomic create-if-absent; never replace an existing marker
                os.unlink(tmp_name)
                dir_fd = os.open(CAMPAIGN, os.O_RDONLY)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
            finally:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)
        except Exception:
            if stage.exists():
                for p in stage.rglob("*"):
                    if p.is_dir():
                        p.chmod(0o700)
                    else:
                        p.chmod(0o600)
                stage.chmod(0o700)
                shutil.rmtree(stage)
            raise
    print(f"Frozen supplemental archive: {DEST}\nFROZEN_COMPLETE: {MARKER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
