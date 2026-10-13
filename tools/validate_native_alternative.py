#!/usr/bin/env python3
"""Fail-closed structural/numeric validation for the N=256 AMX alternative diagnostic."""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

METHODS = {"paper_literal_rho45", "direct_bf16_residual", "diagnostic_rho44"}
BUDGETS = {"6": 6, "10": 10, "15": 15, "21": 21}
HEADER = ["record_type", "method", "budget", "product", "N", "seed",
          "eF_selected_longdouble", "scaledmax_selected_longdouble",
          "eF_selected_fp32_rounded", "scaledmax_selected_fp32_rounded",
          "eF_actual_amx", "scaledmax_actual_amx", "product_store_mismatches", "max_ulp"]


def finite_tree(value) -> bool:
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(finite_tree(v) for v in value.values())
    if isinstance(value, list):
        return all(finite_tree(v) for v in value)
    return True


def validate_alternative_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not finite_tree(payload):
        raise ValueError("alternative report contains NaN/Inf")
    # diagnose_fp64_alternative.py emits a document with per-size metadata
    # nested under `sizes`; validate the actual schema rather than an older
    # flattened draft assumed by the original finalizer.
    size_records = payload.get("sizes")
    if not isinstance(size_records, list) or len(size_records) != 1:
        raise ValueError("alternative report must contain exactly one N=256 size record")
    size_record = size_records[0]
    if (not isinstance(size_record, dict) or int(size_record.get("n", -1)) != 256
            or size_record.get("longdouble_mantissa_bits") != 64):
        raise ValueError("unexpected N or longdouble format in alternative report")
    expected_slice_budgets = {"6": "i+j<3", "10": "i+j<4", "15": "i+j<5", "21": "i+j<6"}
    if payload.get("slice_count") != 6 or payload.get("slice_budgets") != expected_slice_budgets:
        raise ValueError("unexpected slice count or product budgets in alternative report")
    methods = size_record.get("methods")
    if not isinstance(methods, dict) or set(methods) != METHODS:
        raise ValueError("alternative report does not cover all three methods")
    for method, body in methods.items():
        errors = body.get("selected_product_errors", {})
        if set(errors) != set(BUDGETS):
            raise ValueError(f"{method}: missing product budgets")
        if not body.get("all_slices_exact_bf16"):
            raise ValueError(f"{method}: BF16 slice exactness check failed")
        for budget, metrics in errors.items():
            if not isinstance(metrics, dict) or not {"eF", "scaledmax", "max_abs"}.issubset(metrics):
                raise ValueError(f"{method}/p{budget}: incomplete error metrics")
    return {"n": 256, "methods": sorted(methods), "budgets": sorted(BUDGETS, key=int),
            "reference_dtype": size_record.get("reference_dtype"),
            "longdouble_storage_bytes": size_record.get("longdouble_storage_bytes"),
            "longdouble_mantissa_bits": size_record.get("longdouble_mantissa_bits")}


def validate_native_csv(path: Path) -> dict:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != HEADER:
            raise ValueError("native CSV header mismatch")
        records = list(reader)
    summaries: dict[tuple[str, str], dict] = {}
    products: dict[tuple[str, str, str], dict] = {}
    for row in records:
        method, budget, kind = row["method"], row["budget"], row["record_type"]
        if method not in METHODS or budget not in BUDGETS or row["N"] != "256":
            raise ValueError("unexpected method/budget/N in native diagnostic")
        if kind == "summary":
            key = method, budget
            if key in summaries:
                raise ValueError(f"duplicate native summary {key}")
            numeric = ("eF_selected_longdouble", "scaledmax_selected_longdouble",
                       "eF_selected_fp32_rounded", "scaledmax_selected_fp32_rounded",
                       "eF_actual_amx", "scaledmax_actual_amx")
            values = {field: float(row[field]) for field in numeric}
            if not all(math.isfinite(value) for value in values.values()):
                raise ValueError(f"nonfinite numeric result in native summary {key}")
            mismatches, max_ulp = int(row["product_store_mismatches"]), int(row["max_ulp"])
            summaries[key] = {**values, "product_store_mismatches": mismatches, "max_ulp": max_ulp}
        elif kind == "product":
            key = method, budget, row["product"]
            if key in products:
                raise ValueError(f"duplicate native product row {key}")
            mismatches, max_ulp = int(row["product_store_mismatches"]), int(row["max_ulp"])
            if mismatches < 0 or max_ulp < 0:
                raise ValueError(f"negative mismatch statistic in {key}")
            products[key] = {"mismatches": mismatches, "max_ulp": max_ulp}
        else:
            raise ValueError(f"unknown native record type: {kind}")

    expected_summaries = {(m, b) for m in METHODS for b in BUDGETS}
    if set(summaries) != expected_summaries:
        raise ValueError(f"native summary coverage mismatch: missing={expected_summaries-set(summaries)}")
    for method in METHODS:
        for budget, count in BUDGETS.items():
            expected_products = {(method, budget, f"a{ai}b{di-ai}")
                                 for di in range({"6": 3, "10": 4, "15": 5, "21": 6}[budget])
                                 for ai in range(di + 1)}
            observed = {key for key in products if key[:2] == (method, budget)}
            if observed != expected_products:
                raise ValueError(f"native product coverage mismatch for {method}/{budget}")
    mismatch_products = sum(v["mismatches"] > 0 for v in products.values())
    max_ulp_observed = max((v["max_ulp"] for v in products.values()), default=0)
    return {"n": 256, "summary_rows": len(summaries), "product_rows": len(products),
            "methods": sorted(METHODS), "budgets": sorted(BUDGETS, key=int),
            "products_with_nonzero_mismatch": mismatch_products,
            "max_product_ulp_difference": max_ulp_observed,
            "summaries": {f"{m}/p{b}": v for (m, b), v in sorted(summaries.items())}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--alternate-json", type=Path)
    group.add_argument("--native-csv", type=Path)
    args = parser.parse_args()
    result = validate_alternative_json(args.alternate_json) if args.alternate_json else validate_native_csv(args.native_csv)
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
