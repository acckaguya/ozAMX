#include "ozamx/gemm.hpp"
#include "preprocess.hpp"

#include <algorithm>
#include <cstring>
#include <iostream>
#include <limits>
#include <vector>

namespace {
bool run(const char* name, bool cancel) {
    constexpr std::size_t m = 1024, n = 1024, k = 256, lda = k, ldb = n, ldc = n + 3;
    std::vector<double> a(m * lda), b(k * ldb), c(m * ldc, 771.25);
    for (std::size_t i = 0; i < m; ++i)
        for (std::size_t q = 0; q < k; ++q)
            a[i * lda + q] = cancel && ((q & 1) != 0) ? -1.0e30 : 1.0e30;
    std::fill(b.begin(), b.end(), 1.0e30);
    auto packed = ozamx::detail::split_pack_direct64(a.data(), b.data(), m, n, k, lda, ldb, 3, 1);
    const long double bound = static_cast<long double>(packed.max_a) * packed.max_b * k;
    const bool guard_enabled =
        k <= 65536 && bound < static_cast<long double>(std::numeric_limits<float>::max()) / 64.0L;
    // 这些输入会触发后段溢出；无论何时拒绝，C 的数据和填充区都必须原样保留。
    bool threw = false;
    try {
        ozamx::gemm_fp64(m, n, k, a.data(), lda, b.data(), ldb, c.data(), ldc,
                         ozamx::ProductBudget::p6);
    } catch (const ozamx::Error&) {
        threw = true;
    }
    const double sentinel = 771.25;
    bool unchanged = true;
    for (double x : c)
        unchanged &= std::memcmp(&x, &sentinel, sizeof(double)) == 0;
    std::cout << "{\"case\":\"" << name << "\",\"threw\":" << (threw ? "true" : "false")
              << ",\"c_unchanged\":" << (unchanged ? "true" : "false")
              << ",\"guard_enabled\":" << (guard_enabled ? "true" : "false") << "}\n";
    return threw && unchanged && !guard_enabled;
}
} // namespace
int main() {
    return run("high_amplitude_overflow", false) && run("cancellation_overflow", true) ? 0 : 1;
}
