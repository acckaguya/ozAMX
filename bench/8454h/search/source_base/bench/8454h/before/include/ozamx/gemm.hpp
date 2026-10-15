#pragma once

#include <cstddef>
#include <stdexcept>
#include <string>

namespace ozamx {

enum class ProductBudget { p6 = 6, p10 = 10, p15 = 15, p21 = 21 };

class Error : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

struct AmxStatus {
    bool cpu_amx_tile = false;
    bool cpu_amx_bf16 = false;
    bool permission_requested = false;
    bool permission_available = false;
    std::string message;
};

struct GemmTimings {
    double split_seconds = 0.0;
    double pack_seconds = 0.0;
    // FP64 component GEMM store, widen, and ordered FP64 addition are grouped
    // here with the product kernel; the paper makes them one ordered workflow.
    double compute_and_reconstruct_seconds = 0.0;
    double total_seconds = 0.0;
};

// Requests/checks XTILEDATA permission for the calling thread only. This does
// not execute an AMX instruction. Every worker thread must call it before use.
AmxStatus request_amx_permission_for_current_thread();

// Row-major GEMM: A[M,K], B[K,N], C[M,N]. No alpha/beta or transpose modes.
// Implemented kernels use AMX-BF16 and report unsupported CPU/OS or input
// domains through ozamx::Error; they never silently fall back to scalar math.
void gemm_fp32(std::size_t m, std::size_t n, std::size_t k,
               const float* a, std::size_t lda,
               const float* b, std::size_t ldb,
               float* c, std::size_t ldc);
GemmTimings gemm_fp32_profiled(std::size_t m, std::size_t n, std::size_t k,
                               const float* a, std::size_t lda,
                               const float* b, std::size_t ldb,
                               float* c, std::size_t ldc);

void gemm_fp64(std::size_t m, std::size_t n, std::size_t k,
               const double* a, std::size_t lda,
               const double* b, std::size_t ldb,
               double* c, std::size_t ldc,
               ProductBudget budget);
GemmTimings gemm_fp64_profiled(std::size_t m, std::size_t n, std::size_t k,
                               const double* a, std::size_t lda,
                               const double* b, std::size_t ldb,
                               double* c, std::size_t ldc,
                               ProductBudget budget);

const char* product_order_fp32() noexcept;
const char* product_order_fp64(ProductBudget budget) noexcept;

} // namespace ozamx
