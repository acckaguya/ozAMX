#!/usr/bin/env python3
"""Compare FP64 slice-budget hypotheses without calling project kernels.

The rho=45 shifted path is the paper-literal reference. Direct BF16 rounding
and rho=44 are explicitly diagnostic alternatives, not claims about the paper.
This script is prepared for a later, non-contentious N=256 run; --self-test is
scalar-only and does not execute matrix products.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from diagnose_fp64 import ceil_log2_exact_float, error_metrics, round_to_bf16_f64

SLICE_COUNT = 6
BUDGETS = {"6": 3, "10": 4, "15": 5, "21": 6}
METHODS = ("paper_literal_rho45", "direct_bf16_residual", "diagnostic_rho44")


def bf16_bits_from_slices(slices: list[np.ndarray]) -> np.ndarray:
    """Return raw BF16 words as little-endian uint16, preserving signed zero."""
    if not slices:
        raise ValueError("at least one BF16 slice is required")
    raw_layers = []
    shape = np.asarray(slices[0]).shape
    for layer in slices:
        values = np.asarray(layer, dtype=np.float64)
        if values.shape != shape:
            raise ValueError("all BF16 slices must have the same shape")
        f32 = values.astype(np.float32)
        if not np.array_equal(f32.astype(np.float64), values):
            raise ValueError("slice contains a value not exactly representable as BF16")
        words = (f32.astype("<f4", copy=False).view("<u4") >> 16).astype("<u2")
        # Verify the extracted words widen back to the exact exported values.
        widened = (words.astype("<u4") << 16).view("<f4").astype(np.float64)
        if not np.array_equal(widened, values):
            raise ValueError("BF16 bit packing failed exact-value check")
        raw_layers.append(words)
    return np.stack(raw_layers).astype("<u2", copy=False)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def export_native_inputs(export_dir: Path, n: int, seed: int, a: np.ndarray, b: np.ndarray) -> dict:
    """Persist the exact diagnostic inputs and each method's six BF16 slices."""
    if n != 256 or a.shape != (n, n) or b.shape != (n, n):
        raise ValueError("native accuracy export is defined only for N=256")
    export_dir.mkdir(parents=True, exist_ok=True)
    expected = {"metadata.json", "A.f64le", "B.f64le", "checksums.sha256"}
    for method in METHODS:
        expected.update((f"{method}_A.bf16le", f"{method}_B.bf16le"))
    if any((export_dir / name).exists() for name in expected):
        raise FileExistsError(f"refusing to overwrite an existing export in {export_dir}")

    files: dict[str, dict] = {}
    for name, array in (("A.f64le", a), ("B.f64le", b)):
        path = export_dir / name
        np.asarray(array, dtype="<f8").tofile(path)
        files[name] = {"dtype": "<f8", "shape": [n, n], "sha256": sha256_file(path)}

    method_records = {}
    for method in METHODS:
        a_slices, _, _ = decompose(a, method)
        b_slices, _, _ = decompose(b, method)
        for side, slices in (("A", a_slices), ("B", b_slices)):
            filename = f"{method}_{side}.bf16le"
            path = export_dir / filename
            bf16_bits_from_slices(slices).tofile(path)
            files[filename] = {
                "dtype": "<u2 raw BF16 bits",
                "shape": [SLICE_COUNT, n, n],
                "sha256": sha256_file(path),
            }
        method_records[method] = {
            "A_file": f"{method}_A.bf16le",
            "B_file": f"{method}_B.bf16le",
            "hypothesis_status": (
                "paper-literal reference"
                if method == "paper_literal_rho45"
                else "diagnostic alternative; not attributed to paper authors"
            ),
        }
    metadata = {
        "schema": "ozamx_fp64_alternative_export_v1",
        "n": n,
        "seed": seed,
        "random_stream": "NumPy default_rng(PCG64); uniform[-1,1]; A then B; canonical 64/128 draws advanced before N=256",
        "input_layout": "row-major IEEE-754 binary64 little-endian",
        "bf16_layout": "slice-major [6,N,N], raw BF16 uint16 little-endian; zero and subnormal bit patterns preserved",
        "methods": method_records,
        "files": files,
    }
    metadata_path = export_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
    checksum_path = export_dir / "checksums.sha256"
    checksum_path.write_text(
        "".join(f"{record['sha256']}  {filename}\n" for filename, record in files.items())
        + f"{sha256_file(metadata_path)}  metadata.json\n"
    )
    return metadata


def decompose(x: np.ndarray, method: str) -> tuple[list[np.ndarray], np.ndarray, list[dict]]:
    if method not in METHODS:
        raise ValueError(f"unknown decomposition method: {method}")
    residual = np.array(x, dtype=np.float64, copy=True)
    slices: list[np.ndarray] = []
    layer_info: list[dict] = []
    for layer in range(SLICE_COUNT):
        maxabs = float(np.max(np.abs(residual)))
        if maxabs == 0.0:
            component = np.zeros_like(residual)
            v = None
            sigma = None
        else:
            v = ceil_log2_exact_float(maxabs)
            sigma = None
            projected = residual
            if method != "direct_bf16_residual":
                rho = 45 if method == "paper_literal_rho45" else 44
                sigma = math.ldexp(1.0, v + rho)
                projected = np.subtract(np.add(residual, np.float64(sigma)), np.float64(sigma))
            component = round_to_bf16_f64(projected)

        exact_bf16 = bool(np.array_equal(round_to_bf16_f64(component), component))
        residual_next = np.subtract(residual, component)
        slices.append(component)
        layer_info.append(
            {
                "slice": layer,
                "v_before": v,
                "max_residual_before": maxabs,
                "sigma": sigma,
                "zero_component_count": int(np.count_nonzero(component == 0.0)),
                "component_is_exact_bf16": exact_bf16,
                "max_abs_residual_after": float(np.max(np.abs(residual_next))),
                "v_after": (
                    ceil_log2_exact_float(float(np.max(np.abs(residual_next))))
                    if np.any(residual_next != 0.0)
                    else None
                ),
            }
        )
        residual = residual_next
    return slices, residual, layer_info


def sum_longdouble(parts: list[np.ndarray]) -> np.ndarray:
    result = np.zeros(parts[0].shape, dtype=np.longdouble)
    for part in parts:
        result += np.asarray(part, dtype=np.longdouble)
    return result


def selected_products(a_slices, b_slices, n: int, diagonal_count: int) -> np.ndarray:
    """High-precision sum of products with i+j < diagonal_count."""
    a_ld = [np.asarray(item, dtype=np.longdouble) for item in a_slices]
    b_ld = [np.asarray(item, dtype=np.longdouble) for item in b_slices]
    result = np.zeros((n, n), dtype=np.longdouble)
    for i, a_part in enumerate(a_ld):
        permitted_b = b_ld[: max(0, min(SLICE_COUNT, diagonal_count - i))]
        if permitted_b:
            result += a_part @ sum_longdouble(permitted_b)
    return result


def diagnose_method(a, b, ref, denominator, method: str) -> dict:
    a_slices, a_terminal, a_layers = decompose(a, method)
    b_slices, b_terminal, b_layers = decompose(b, method)
    budgets = {}
    for name, diagonal_count in BUDGETS.items():
        approximate = selected_products(a_slices, b_slices, a.shape[0], diagonal_count)
        budgets[name] = error_metrics(approximate - ref, ref, denominator)
    return {
        "method": method,
        "hypothesis_status": (
            "paper-literal reference"
            if method == "paper_literal_rho45"
            else "diagnostic alternative; not attributed to paper authors"
        ),
        "A_layers": a_layers,
        "B_layers": b_layers,
        "all_slices_exact_bf16": all(x["component_is_exact_bf16"] for x in a_layers + b_layers),
        "terminal_A_relative_fro": float(
            np.sqrt(np.sum(np.asarray(a_terminal, dtype=np.longdouble) ** 2))
            / np.sqrt(np.sum(np.asarray(a, dtype=np.longdouble) ** 2))
        ),
        "terminal_B_relative_fro": float(
            np.sqrt(np.sum(np.asarray(b_terminal, dtype=np.longdouble) ** 2))
            / np.sqrt(np.sum(np.asarray(b, dtype=np.longdouble) ** 2))
        ),
        "selected_product_errors": budgets,
    }


def diagnose_one(
    n: int, rng: np.random.Generator, export_dir: Path | None = None, seed: int | None = None
) -> dict:
    # Same generation order/seed convention as diagnose_fp64.py: A then B.
    a = rng.uniform(-1.0, 1.0, size=(n, n)).astype(np.float64)
    b = rng.uniform(-1.0, 1.0, size=(n, n)).astype(np.float64)
    if export_dir is not None:
        export_native_inputs(export_dir, n, int(seed), a, b)
    a_ld, b_ld = np.asarray(a, dtype=np.longdouble), np.asarray(b, dtype=np.longdouble)
    ref = a_ld @ b_ld
    denominator = np.abs(a_ld) @ np.abs(b_ld)
    return {
        "n": n,
        "seed_sequence": "NumPy default_rng(PCG64); A then B uniform[-1,1]",
        "reference_dtype": "numpy.longdouble",
        "longdouble_storage_bytes": np.dtype(np.longdouble).itemsize,
        "longdouble_mantissa_bits": int(np.finfo(np.longdouble).nmant + 1),
        "methods": {method: diagnose_method(a, b, ref, denominator, method) for method in METHODS},
    }


def rng_at_canonical_size(seed: int, n: int) -> np.random.Generator:
    """Match the existing 64,128,256 diagnostic sweep's per-size stream."""
    rng = np.random.default_rng(seed)
    for prefix in (64, 128):
        if prefix < n:
            rng.uniform(-1.0, 1.0, size=(prefix, prefix))
            rng.uniform(-1.0, 1.0, size=(prefix, prefix))
    return rng


def scalar_self_test() -> None:
    # Direct binary64 -> BF16 ties-to-even around 1.0; no matrices involved.
    values = np.array([1.0, 1.0 + 2.0**-8, 1.0 + 3.0 * 2.0**-8])
    rounded = round_to_bf16_f64(values)
    expected = np.array([1.0, 1.0, 1.0 + 2.0**-6])
    if not np.array_equal(rounded, expected):
        raise AssertionError(f"direct BF16 rounding failed: {rounded!r}")
    for method in METHODS:
        slices, residual, layers = decompose(np.array([0.7], dtype=np.float64), method)
        if len(slices) != SLICE_COUNT or not all(x["component_is_exact_bf16"] for x in layers):
            raise AssertionError(f"slice projection check failed: {method}")
        if not np.isfinite(residual[0]):
            raise AssertionError(f"nonfinite scalar residual: {method}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", nargs="+", type=int, default=[256])
    parser.add_argument("--seed", type=int, default=20261012)
    parser.add_argument(
        "--export-dir",
        type=Path,
        help="persist exact N=256 inputs/slices for the independent AMX diagnostic",
    )
    parser.add_argument(
        "--self-test", action="store_true", help="scalar-only checks; no matrix products"
    )
    args = parser.parse_args()
    if args.self_test:
        scalar_self_test()
        print("scalar self-test passed; no matrix products were run")
        return 0
    if any(n <= 0 for n in args.sizes):
        parser.error("sizes must be positive")
    if args.export_dir is not None and args.sizes != [256]:
        parser.error("--export-dir requires exactly --sizes 256")
    report = {
        "diagnostic": "FP64 slice-budget alternatives; independent numerical diagnostic, no project kernel",
        "paper_hypothesis": "rho45 global ceil(log2(max(abs(R)))) literal shift",
        "alternatives": {
            "direct_bf16_residual": "round BF16 directly from binary64 residual, then FP64 subtraction; diagnostic hypothesis only",
            "diagnostic_rho44": "literal shifted procedure with rho=44; diagnostic hypothesis only",
        },
        "rho_values": {
            "paper_literal_rho45": 45,
            "diagnostic_rho44": 44,
            "direct_bf16_residual": None,
        },
        "slice_count": SLICE_COUNT,
        "slice_budgets": {"6": "i+j<3", "10": "i+j<4", "15": "i+j<5", "21": "i+j<6"},
        "seed": args.seed,
        "numpy_version": np.__version__,
        "longdouble_note": "Host numpy.longdouble; inspect reported mantissa bits; not assumed IEEE binary128",
        "random_stream_note": "Each size uses the same per-size PCG64 stream as the original 64,128,256 sweep; smaller A/B draws are advanced and discarded when running a larger size alone.",
        "sizes": [
            diagnose_one(
                n,
                rng_at_canonical_size(args.seed, n),
                args.export_dir if n == 256 else None,
                args.seed,
            )
            for n in args.sizes
        ],
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
