# Local oneMKL dependency (2026.1.0)

This directory contains a workspace-local, minimal runtime/header extraction for the oneMKL CBLAS benchmark. It is not installed system-wide. The runtime and headers come from Intel-maintained PyPI wheels on the official `pypi.org` index; wheel SHA-256 values were checked against PyPI release JSON and against the downloaded wheel bytes.

| Distribution | Version | Official wheel | SHA-256 | Use |
|---|---:|---|---|---|
| `mkl` | 2026.1.0 | `mkl-2026.1.0-py2.py3-none-manylinux_2_28_x86_64.whl` | `4d5a26449818a8aebd4b2aaf6b291831e691f9cf74b152df49b99cf48bbd5360` | Runtime; only `libmkl_rt.so.3` was separately extracted from the full wheel. Other required runtime DSOs were copied from this same hash-verified wheel during its initial extraction. |
| `mkl-include` | 2026.1.0 | `mkl_include-2026.1.0-py2.py3-none-manylinux_2_28_x86_64.whl` | `e64b260e67284b8a696343d58c339ad9d990cc985077dab1269d1c6d2a2e2b1b` | C/CBLAS headers in `include/`. |
| `onemkl-license` | 2026.1.0 | `onemkl_license-2026.1.0-py2.py3-none-manylinux_2_28_x86_64.whl` | `39fd829648af92c9e03c22ba228f07174d829aaa2fe3c5f6cd7073b8eb8a9805` | License metadata and text. |

The runtime wheel URL is `https://files.pythonhosted.org/packages/61/da/4921e17b1f455f7fed30d5cc0964f3289eee6a6cb03cdf7d5e20c14bd025/mkl-2026.1.0-py2.py3-none-manylinux_2_28_x86_64.whl`; the other wheel URLs and source metadata are archived in `pypi-metadata.json`. The full runtime wheel was staged only in temporary storage and is not retained because the host filesystem was nearly full. `mkl`, `mkl-include`, and `onemkl-license` declare Intel Simplified Software License (ISSL) terms. The Intel license FAQ explains that license reference: <https://www.intel.com/content/www/us/en/developer/articles/tool/onemkl-license-faq.html>.

The benchmark selects GNU threading (`MKL_THREADING_LAYER=GNU`) and relies on the host's GNU OpenMP runtime. PyPI metadata declares runtime dependencies on `onemkl-license==2026.1.0`, `intel-openmp>=2025,<2027`, and `tbb==2023.*`; the latter two packages were intentionally not installed. They are not needed for the GNU-threading CBLAS run. Runtime linkage must be checked with `ldd` before measurements to ensure `libgomp` is selected and `libiomp5` is absent.

The original `pip install --no-deps` attempt was interrupted by `ENOSPC`; see `install_logs/pip_install.txt`. It left an incomplete extraction, after which the verified runtime wheel was selectively used to add `libmkl_rt.so.3`. This minimal installation must be treated as the exact set of installed files, not as a complete Python distribution. No package manager or system paths were changed.
