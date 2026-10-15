#!/usr/bin/env python3
"""One bounded N=256 signed-shift diagnostic; not a paper algorithm claim."""
import hashlib, json, math
from pathlib import Path
import numpy as np
import diagnose_fp64_alternative as alt

METHOD = "diagnostic_signed_rho44"
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "bench/diagnostics/alt_256"
OUT = ROOT / "bench/diagnostics/signed_shift_256"


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def split(x):
    r = np.array(x, dtype=np.float64, copy=True)
    slices = []
    layers = []
    for q in range(6):
        m = float(np.max(np.abs(r)))
        if m == 0:
            z = np.zeros_like(r)
            v = None
        else:
            v = alt.ceil_log2_exact_float(m)
            step = math.ldexp(1.0, v + 44)
            sigma = np.copysign(step, r)
            sigma = np.where(r == 0.0, 0.0, sigma)
            shifted = np.subtract(np.add(r, sigma, dtype=np.float64), sigma, dtype=np.float64)
            z = alt.round_to_bf16_f64(shifted)
        rn = np.subtract(r, z, dtype=np.float64)
        layers.append(
            {
                "slice": q,
                "v_before": v,
                "max_abs_residual_before": m,
                "zero_component_count": int(np.count_nonzero(z == 0)),
                "component_is_exact_bf16": bool(np.array_equal(alt.round_to_bf16_f64(z), z)),
                "max_abs_residual_after": float(np.max(np.abs(rn))),
            }
        )
        slices.append(z)
        r = rn
    return slices, r, layers


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    # 使用既有 N=256 导出矩阵，固定输入以便只比较这一种诊断分解规则。
    a = np.fromfile(SOURCE / 'A.f64le', dtype='<f8').reshape(256, 256)
    b = np.fromfile(SOURCE / 'B.f64le', dtype='<f8').reshape(256, 256)
    seed = 20261012
    ast, ar, al = split(a)
    bst, br, bl = split(b)
    files = {}
    for name, arr, dtype in [('A.f64le', a, '<f8'), ('B.f64le', b, '<f8')]:
        p = OUT / name
        np.asarray(arr, dtype=dtype).tofile(p)
        files[name] = sha(p)
    for side, ss in [('A', ast), ('B', bst)]:
        name = f'{METHOD}_{side}.bf16le'
        p = OUT / name
        alt.bf16_bits_from_slices(ss).tofile(p)
        files[name] = sha(p)
    metadata = {
        "schema": "ozamx_signed_shift_export_v1",
        "n": 256,
        "seed": seed,
        "method": METHOD,
        "status": "explicit non-author diagnostic; not attributed to paper authors",
        "rule": "global v=ceil(log2(max(abs(R)))); per-element sigma=copysign(2^(v+44),R); Z=fl64(fl64(R+sigma)-sigma); BF16 RNE; next residual fl64(R-Z)",
        "input_source": "same A/B bytes as alt_256 export; seed streamskip64/128",
        "files": files,
    }
    (OUT / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    hashes = {**files, 'metadata.json': sha(OUT / 'metadata.json')}
    (OUT / 'checksums.sha256').write_text(''.join(f'{v}  {k}\n' for k, v in hashes.items()))
    ald = np.asarray(a, dtype=np.longdouble)
    bld = np.asarray(b, dtype=np.longdouble)
    ref = ald @ bld
    den = np.abs(ald) @ np.abs(bld)
    methods = {}
    for label, ss, rr, ll, x in [('A', ast, ar, al, ald), ('B', bst, br, bl, bld)]:
        ldss = [np.asarray(s, dtype=np.longdouble) for s in ss]
        methods[label] = {
            "layers": ll,
            "terminal_residual_relative_fro": float(
                np.sqrt(np.sum(np.asarray(rr, dtype=np.longdouble) ** 2)) / np.sqrt(np.sum(x * x))
            ),
        }
    errors = {}
    for budget, d in alt.BUDGETS.items():
        value = alt.selected_products(ast, bst, 256, d)
        errors[budget] = alt.error_metrics(value - ref, ref, den)
    aldl = [np.asarray(s, dtype=np.longdouble) for s in ast]
    bldl = [np.asarray(s, dtype=np.longdouble) for s in bst]
    full = np.zeros((256, 256), dtype=np.longdouble)
    for ap in aldl:
        for bp in bldl:
            full += ap @ bp
    report = {
        "method": METHOD,
        "n": 256,
        "seed": seed,
        "status": "diagnostic only; not paper literal; no parameter search",
        "reference": "numpy.longdouble, host 80-bit extended; same exported A/B",
        "layers": {"A": al, "B": bl},
        "all_slices_exact_bf16": all(x['component_is_exact_bf16'] for x in al + bl),
        "terminal_A_relative_fro": methods['A']['terminal_residual_relative_fro'],
        "terminal_B_relative_fro": methods['B']['terminal_residual_relative_fro'],
        "selected_product_errors": errors,
        "full36_error": alt.error_metrics(full - ref, ref, den),
        "truncation21_error": errors['21'],
        "export_sha256": sha(OUT / 'checksums.sha256'),
    }
    tmp = OUT / 'signed_shift_report.json.tmp'
    tmp.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    tmp.replace(OUT / 'signed_shift_report.json')
    print(OUT)


if __name__ == '__main__':
    main()
