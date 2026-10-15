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
    // NUMA B-replication copy is included in pack_seconds; these fields expose
    // its isolated cost and the placement observed by the copy team.
    double replicate_b_seconds = 0.0;
    int replicate_node0_workers = 0;
    int replicate_node1_workers = 0;
    int replicate_fallback_workers = 0;
    double total_seconds = 0.0;
};

// Requests/checks Linux process-wide XTILEDATA permission from the caller.
// This does not execute AMX. Every participating task has independent tile
// state; the GEMM implementation configures that state when entering its region.
AmxStatus request_amx_permission_for_current_thread();

// Row-major GEMM: A[M,K], B[K,N], C[M,N]. No alpha/beta or transpose modes.
// Optimized kernels require Sapphire Rapids AVX-512 and AMX-BF16 features,
// checked by generic runtime dispatch, and report unsupported CPU/OS or input
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
