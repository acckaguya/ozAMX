#!/usr/bin/env python3
"""Independent numerical diagnosis of the paper's literal FP64 six-slice path.

No project kernels are imported or called. The routine models FP64 residual
projection, exact BF16 slices, and both widened and FP32 component-product
accumulation. Matrix truth and decomposition audits use numpy.longdouble.
"""

from __future__ import annotations

import argparse
import json
import math

import numpy as np


RHO = 45
SLICE_COUNT = 6


def ceil_log2_exact_float(x: float) -> int:
    """Exact ceil(log2(x)) for a positive binary64 number."""
    if not math.isfinite(x) or x <= 0:
        raise ValueError("ceil_log2 requires a finite positive input")
    mantissa, exponent = math.frexp(x)
    return exponent - 1 if mantissa == 0.5 else exponent


def round_to_bf16_f64(x: np.ndarray) -> np.ndarray:
    """Round binary64 values directly to BF16, ties-to-even, return binary64.

    Direct rounding avoids a possible binary64 -> binary32 -> BF16 double-round.
    BF16 subnormals are rounded in units of 2**-133.
    """
    values = np.asarray(x, dtype=np.float64)
    out = np.empty_like(values)
    flat = values.ravel()
    dest = out.ravel()
    magnitude = np.abs(flat)
    normal = magnitude >= math.ldexp(1.0, -126)
    if np.any(normal):
        bits = flat[normal].view(np.uint64)
        shift = 45
        mask = (1 << shift) - 1
        halfway = 1 << (shift - 1)
        lsb = (bits >> shift) & 1
        rounded = (bits + (halfway - 1) + lsb) & ~np.uint64(mask)
        dest[normal] = rounded.view(np.float64)
    subnormal = ~normal
    if np.any(subnormal):
        scaled = np.ldexp(magnitude[subnormal], 133)
        rounded_units = np.rint(scaled)
        rounded = np.ldexp(rounded_units, -133)
        dest[subnormal] = np.copysign(rounded, flat[subnormal])
    return out


def decompose_operand(x: np.ndarray) -> tuple[list[np.ndarray], np.ndarray, list[dict]]:
    residual = np.array(x, dtype=np.float64, copy=True)
    slices: list[np.ndarray] = []
    rounds: list[dict] = []
    for index in range(SLICE_COUNT):
        maxabs = float(np.max(np.abs(residual)))
        if maxabs == 0:
            component = np.zeros_like(residual)
            slices.append(component)
            rounds.append(
                {
                    "slice": index,
                    "max_residual_before": 0.0,
                    "v": None,
                    "sigma": 0.0,
                    "zero_component_count": int(component.size),
                    "component_is_exact_bf16": True,
                    "nonzero_bf16_subnormal_count": 0,
                }
            )
            residual.fill(0.0)
            continue

        v = ceil_log2_exact_float(maxabs)
        sigma = math.ldexp(1.0, v + RHO)
        shifted = np.subtract(np.add(residual, np.float64(sigma)), np.float64(sigma))
        component = round_to_bf16_f64(shifted)
        exactly_bf16 = np.array_equal(round_to_bf16_f64(component), component)
        nonzero_subnormal = np.count_nonzero(
            (component != 0) & (np.abs(component) < math.ldexp(1.0, -126))
        )
        residual = np.subtract(residual, component)
        slices.append(component)
        rounds.append(
            {
                "slice": index,
                "max_residual_before": maxabs,
                "v": v,
                "sigma": sigma,
                "zero_component_count": int(np.count_nonzero(component == 0)),
                "component_is_exact_bf16": bool(exactly_bf16),
                "nonzero_bf16_subnormal_count": int(nonzero_subnormal),
            }
        )
    return slices, residual, rounds


def norm_fro(x: np.ndarray) -> np.longdouble:
    xx = np.asarray(x, dtype=np.longdouble)
    return np.sqrt(np.sum(xx * xx, dtype=np.longdouble), dtype=np.longdouble)


def error_metrics(error: np.ndarray, reference: np.ndarray, scaled_denominator: np.ndarray) -> dict:
    err = np.asarray(error, dtype=np.longdouble)
    ref = np.asarray(reference, dtype=np.longdouble)
    den = np.asarray(scaled_denominator, dtype=np.longdouble)
    e_f = norm_fro(err) / norm_fro(ref)
    nonzero = den > 0
    scaled_max = (
        np.max(np.abs(err[nonzero]) / den[nonzero]) if np.any(nonzero) else np.longdouble(0)
    )
    return {
        "eF": float(e_f),
        "scaledmax": float(scaled_max),
        "max_abs": float(np.max(np.abs(err))),
    }


def relative_residual_metrics(residual: np.ndarray, original: np.ndarray) -> dict:
    r = np.asarray(residual, dtype=np.longdouble)
    x = np.asarray(original, dtype=np.longdouble)
    return {
        "max_abs": float(np.max(np.abs(r))),
        "relative_fro": float(norm_fro(r) / norm_fro(x)),
    }


def sum_longdouble(matrices: list[np.ndarray]) -> np.ndarray:
    out = np.zeros(matrices[0].shape, dtype=np.longdouble)
    for matrix in matrices:
        out += np.asarray(matrix, dtype=np.longdouble)
    return out


def grouped_component_products(a_slices: list[np.ndarray], b_slices: list[np.ndarray], n: int):
    """Compute exact-arithmetic 36, 21, and omitted 15 sums by distributive groups."""
    a_ld = [np.asarray(item, dtype=np.longdouble) for item in a_slices]
    b_ld = [np.asarray(item, dtype=np.longdouble) for item in b_slices]
    sum_a = sum_longdouble(a_ld)
    sum_b = sum_longdouble(b_ld)
    all36 = sum_a @ sum_b

    selected21 = np.zeros((n, n), dtype=np.longdouble)
    for i in range(SLICE_COUNT):
        grouped_b = sum_longdouble(b_ld[: SLICE_COUNT - i])
        selected21 += a_ld[i] @ grouped_b

    omitted15 = np.zeros((n, n), dtype=np.longdouble)
    for i in range(1, SLICE_COUNT):
        first_j = SLICE_COUNT - i
        grouped_b = sum_longdouble(b_ld[first_j:])
        omitted15 += a_ld[i] @ grouped_b
    return all36, selected21, omitted15, sum_a, sum_b


def fp32_component_sum(
    a_slices: list[np.ndarray], b_slices: list[np.ndarray], selected: bool
) -> np.ndarray:
    """Approximate AMX's FP32 product reduction, widening each product in order."""
    n = a_slices[0].shape[0]
    accumulator = np.zeros((n, n), dtype=np.longdouble)
    pairs = []
    max_diagonal = 5 if selected else 10
    for diagonal in range(max_diagonal + 1):
        i_min = max(0, diagonal - 5)
        i_max = min(5, diagonal)
        for i in range(i_min, i_max + 1):
            j = diagonal - i
            pairs.append((i, j))
    for i, j in pairs:
        product = a_slices[i].astype(np.float32) @ b_slices[j].astype(np.float32)
        accumulator += np.asarray(product, dtype=np.longdouble)
    return accumulator


def decompose_metrics(slices: list[np.ndarray], terminal: np.ndarray, original: np.ndarray) -> dict:
    x = np.asarray(original, dtype=np.longdouble)
    sum_slices = sum_longdouble(slices)
    terminal_ld = np.asarray(terminal, dtype=np.longdouble)
    reconstruction = sum_slices + terminal_ld
    return {
        "terminal_residual": relative_residual_metrics(terminal_ld, x),
        "slice_sum_vs_input": relative_residual_metrics(sum_slices - x, x),
        "terminal_matches_input_minus_slices": relative_residual_metrics(
            (x - sum_slices) - terminal_ld, x
        ),
        "slices_plus_terminal_vs_input": relative_residual_metrics(reconstruction - x, x),
    }


def diagnose_one(n: int, rng: np.random.Generator, longdouble_bits: int) -> dict:
    a = rng.uniform(-1.0, 1.0, size=(n, n)).astype(np.float64)
    b = rng.uniform(-1.0, 1.0, size=(n, n)).astype(np.float64)
    a_slices, a_terminal, a_rounds = decompose_operand(a)
    b_slices, b_terminal, b_rounds = decompose_operand(b)

    a_ld = np.asarray(a, dtype=np.longdouble)
    b_ld = np.asarray(b, dtype=np.longdouble)
    ref = a_ld @ b_ld
    denominator = np.abs(a_ld) @ np.abs(b_ld)

    all36, selected21, omitted15, sum_a, sum_b = grouped_component_products(a_slices, b_slices, n)
    # A=(sum slices)+R_A and B=(sum slices)+R_B, hence these are precisely
    # R_A*B + (sum A slices)*R_B, including R_A*R_B.
    terminal_terms = np.asarray(a_terminal, dtype=np.longdouble) @ b_ld
    terminal_terms += sum_a @ np.asarray(b_terminal, dtype=np.longdouble)
    decomposition_identity = (ref - all36) - terminal_terms

    fp32_36 = fp32_component_sum(a_slices, b_slices, selected=False)
    fp32_21 = fp32_component_sum(a_slices, b_slices, selected=True)

    sum_a_slices = sum_longdouble(a_slices)
    sum_b_slices = sum_longdouble(b_slices)
    reconstructed_a = sum_a_slices + np.asarray(a_terminal, dtype=np.longdouble)
    reconstructed_b = sum_b_slices + np.asarray(b_terminal, dtype=np.longdouble)
    input_roundtrip = {
        "A": {
            "without_terminal": relative_residual_metrics(sum_a_slices - a_ld, a_ld),
            "with_terminal": relative_residual_metrics(reconstructed_a - a_ld, a_ld),
        },
        "B": {
            "without_terminal": relative_residual_metrics(sum_b_slices - b_ld, b_ld),
            "with_terminal": relative_residual_metrics(reconstructed_b - b_ld, b_ld),
        },
    }

    all_slices = a_slices + b_slices
    bf16_check = {
        "all_12_slices_exactly_bf16": all(
            bool(np.array_equal(round_to_bf16_f64(x), x)) for x in all_slices
        ),
        "nonzero_subnormal_components": sum(
            int(np.count_nonzero((x != 0) & (np.abs(x) < math.ldexp(1.0, -126))))
            for x in all_slices
        ),
    }

    return {
        "n": n,
        "seed_sequence": "NumPy default_rng(PCG64); A then B uniform[-1,1]",
        "rounding": "binary64 literal shift, direct BF16 round-to-nearest-ties-even",
        "reference_dtype": "numpy.longdouble",
        "longdouble_mantissa_bits": longdouble_bits,
        "A_rounds": a_rounds,
        "B_rounds": b_rounds,
        "bf16_exactness": bf16_check,
        "input_slice_reconstruction": input_roundtrip,
        "terminal_decomposition_terms": {
            "R_A_times_B_plus_sum_A_times_R_B": error_metrics(terminal_terms, ref, denominator),
            "identity_check_ref_minus_full36_minus_terminal_terms": relative_residual_metrics(
                decomposition_identity, ref
            ),
        },
        "products_vs_longdouble_AB": {
            "full36_exact_grouped_products": error_metrics(all36 - ref, ref, denominator),
            "selected21_exact_grouped_products_i_plus_j_lt_6": error_metrics(
                selected21 - ref, ref, denominator
            ),
            "omitted_15_products_i_plus_j_ge_6": error_metrics(omitted15, ref, denominator),
            "full36_minus_selected21_matches_omitted": relative_residual_metrics(
                (all36 - selected21) - omitted15, ref
            ),
            "full36_fp32_products_then_widen": error_metrics(fp32_36 - ref, ref, denominator),
            "selected21_fp32_products_then_widen": error_metrics(fp32_21 - ref, ref, denominator),
            "selected21_fp32_accumulation_delta_vs_exact_selected21": error_metrics(
                fp32_21 - selected21, ref, denominator
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", nargs="+", type=int, default=[64, 128, 256])
    parser.add_argument("--seed", type=int, default=20261012)
    args = parser.parse_args()
    if any(n <= 0 for n in args.sizes):
        parser.error("sizes must be positive")
    rng = np.random.default_rng(args.seed)
    report = {
        "diagnostic": "literal rho=45 FP64 six-slice decomposition; no project kernel",
        "rho": RHO,
        "slice_count": SLICE_COUNT,
        "v_rule": "ceil(log2(global max absolute residual))",
        "selected_products": "i+j<6",
        "omitted_products": "i+j>=6",
        "seed": args.seed,
        "numpy_version": np.__version__,
        "longdouble_storage_bytes": np.dtype(np.longdouble).itemsize,
        "longdouble_mantissa_bits": int(np.finfo(np.longdouble).nmant + 1),
        "longdouble_note": "80-bit extended precision on this host, not IEEE binary128",
        "floor_v_or_more_slices_variant": "not run",
        "sizes": [diagnose_one(n, rng, int(np.finfo(np.longdouble).nmant + 1)) for n in args.sizes],
    }
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
