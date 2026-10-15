#!/usr/bin/env python3
"""Create the small, allowlisted V2 production and oneMKL release archive."""
from pathlib import Path
import hashlib
import shutil

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "bench/8454h/versions/v2_release"

# Repository-relative paths are intentionally explicit. Add files here only when
# they are required to reproduce the frozen build, validate it, or interpret it.
FILES = (
    "CMakeLists.txt",
    "include/ozamx/gemm.hpp",
    "src/gemm.cpp",
    "src/kernels.S",
    "src/main.cpp",
    "src/preprocess.hpp",
    "src/runtime.cpp",
    "src/tuning.hpp",
    "bench/benchmark.cpp",
    "bench/optimization_benchmark.cpp",
    "bench/run_8454h_baseline.sh",
    "bench/run_extended_validation.sh",
    "bench/run_packed_panel_audit.sh",
    "bench/8454h/equivalence_driver.cpp",
    "bench/8454h/run_equivalence.sh",
    "bench/8454h/create_v2_release_archive.py",
    "bench/8454h/versions/v2/README.md",
    "bench/8454h/versions/v2/MANIFEST.sha256",
    "tests/bounded_commit_alias_probe.cpp",
    "tests/bounded_commit_overflow_probe.cpp",
    "tests/extended_validation.cpp",
    "tests/final_late_path_probe.cpp",
    "tests/fp32_packed_panel_audit.cpp",
    "tests/packed_panel_audit.cpp",
    "tests/v2_transaction_probes.cpp",
    "tests/validation.cpp",
    "tools/amx_probe.c",
    "tools/native_alternative_accuracy.cpp",
    "tools/native_kernel_audit.cpp",
    "tools/native_signed_shift_accuracy.cpp",
    "tools/platform_baseline.cpp",
    "bench/8454h/V2_VALIDATION.md",
    "bench/8454h/final_production_extended47.json",
    "bench/8454h/final_production_validation_summary.json",
    "bench/8454h/machine_metadata.txt",
    "bench/8454h/final_run_metadata.txt",
    "bench/8454h/mkl_production/README.md",
    "bench/8454h/mkl_production/benchmark_production.cpp",
    "bench/8454h/mkl_production/full_production.csv",
    "bench/8454h/mkl_production/production_comparison.md",
    "bench/8454h/mkl_production/provenance.json",
    "bench/8454h/mkl_production/run_command.txt",
    "bench/8454h/mkl_production/source_hashes_pre_run.sha256",
    "docs/8454H_FINAL_PERFORMANCE_REPORT.md",
    "docs/8454H_ROOFLINE_SEARCH_LOG.md",
    "docs/8454H_SEARCH_RESULTS.md",
    "docs/8454H_KERNEL_IDEAS.md",
    "docs/8454H_PERFORMANCE_BASELINE.md",
)

CHECKPOINTS = (
    "checkpoint_final_prod.fp32.256.6.json",
    "checkpoint_final_prod.fp32.1024.6.json",
    "checkpoint_final_prod.fp32.4096.6.json",
    "checkpoint_final_prod.fp32.8192.6.json",
    "checkpoint_final_prod.fp64.256.6.json",
    "checkpoint_final_prod.fp64.256.10.json",
    "checkpoint_final_prod.fp64.256.15.json",
    "checkpoint_final_prod.fp64.256.21.json",
    "checkpoint_final_prod.fp64.1024.6.json",
    "checkpoint_final_prod.fp64.1024.10.json",
    "checkpoint_final_prod.fp64.1024.15.json",
    "checkpoint_final_prod.fp64.1024.21.json",
    "checkpoint_final_prod.fp64.4096.6.json",
    "checkpoint_final_prod.fp64.4096.10.json",
    "checkpoint_final_prod.fp64.4096.15.json",
    "checkpoint_final_prod.fp64.4096.21.json",
    "checkpoint_final_prod.fp64.8192.6.json",
    "checkpoint_final_prod.fp64.8192.10.json",
    "checkpoint_final_prod.fp64.8192.15.json",
    "checkpoint_final_prod.fp64.8192.21.json",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    copied = []
    for rel in (*FILES, *(f"bench/8454h/mkl_production/{name}" for name in CHECKPOINTS)):
        source = ROOT / rel
        if not source.is_file():
            raise FileNotFoundError(f"allowlisted input missing: {rel}")
        target = OUT / "repo" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(target)

    readme = """# V2 final production release archive\n\nThis archive freezes the current production build inputs and the complete final oneMKL experiment needed to review the reported result. Files under `repo/` retain their repository-relative paths so links in the copied report work within the archive. The explicit allowlist and generator are at `bench/8454h/create_v2_release_archive.py` in the live repository. Generated archive payload: 68 allowlisted files plus this README; `MANIFEST.sha256` covers every payload file and the README. No compiler outputs, vendor trees, or search logs are included.\n\nThe immutable source-only V2 archive remains [`../v2/`](../v2/); this release archive supplements it and does not rewrite it. V2 validation and the independent rebuild record are in `repo/bench/8454h/V2_VALIDATION.md`. The current production library was verified by SHA-256 only (no CPU rebuild): `/tmp/ozamx-production-final/libozamx.a` = `ddfe885c2ba58089accd4e747aecb53a18422554e06fc409965e2f47b7d92251`. The final oneMKL CSV, all 20 checkpoints, provenance, command, comparison table, and final report are included under `repo/`.\n\nBuild configuration: Release, OpenMP ON, `CACHE_BLOCK=128`, `PREP_GRAIN=16384`, `MIN_COMPUTE_WORK=8`, `TILELOAD_HINT=1`, `LOAD_SCHEDULE=0`, `LOOP_ORDER=0`, `MN_ORDER=0`, workspace cache default 2 GiB. Source/library and driver hashes are recorded in the included validation and provenance files. The v2 archive's `MANIFEST.sha256` uses original repository paths; its archive-relative contents were checked against that list, while `CMakeLists.txt`, `README.md`, and the historical baseline document in the live tree have since changed.\n"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")
    files = [OUT / "README.md", *copied]
    lines = [f"{sha256(path)}  {path.relative_to(OUT).as_posix()}" for path in sorted(files)]
    (OUT / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"archive={OUT}")
    print(f"payload_files={len(files)} manifest_entries={len(lines)}")
    print(f"payload_bytes={sum(path.stat().st_size for path in files)}")


if __name__ == "__main__":
    main()
