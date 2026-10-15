#pragma once

#include <cstddef>
#include <stdexcept>

namespace ozamx_int8_36 {

// Experimental FP64-shaped GEMM backed by 36 signed-INT8 digit products.
// This is a separate API: it does not implement or alias ozamx::ProductBudget.
struct Timings {
    double scan_seconds = 0.0;
    double pack_seconds = 0.0;
    double compute_reconstruct_seconds = 0.0;
    double total_seconds = 0.0;
};

// Row-major A[M,K], B[K,N], C[M,N], in double elements. M and N must be
// multiples of 32 when K is positive; K may have a tail and is padded
// internally, up to 32768. K=0 produces an all-zero output.
// lda/ldb/ldc are row strides in elements. C may overlap either input because
// both inputs and the complete output are staged before C is modified.
//
// Throws std::invalid_argument for unsupported shape/stride/domain,
// std::overflow_error for address or allocation-size overflow,
// std::runtime_error for unavailable AMX_INT8/OS permission, and
// std::bad_alloc if scratch allocation fails. On any C++ exception, C is
// unchanged. Input/output pointers must still designate valid spans.
Timings gemm_fp64_int8_36_profiled(
    std::size_t m, std::size_t n, std::size_t k,
    const double* a, std::size_t lda,
    const double* b, std::size_t ldb,
    double* c, std::size_t ldc,
    int threads = 64);

inline void gemm_fp64_int8_36(
    std::size_t m, std::size_t n, std::size_t k,
    const double* a, std::size_t lda,
    const double* b, std::size_t ldb,
    double* c, std::size_t ldc,
    int threads = 64) {
    (void)gemm_fp64_int8_36_profiled(m, n, k, a, lda, b, ldb, c, ldc, threads);
}

} // namespace ozamx_int8_36
