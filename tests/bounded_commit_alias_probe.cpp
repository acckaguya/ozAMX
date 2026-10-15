#include "ozamx/gemm.hpp"

#include <cstdint>
#include <cstring>
#include <iostream>
#include <random>
#include <vector>

bool run(bool alias_a) {
    constexpr std::size_t m = 1024, n = 1024, k = 256, lda = k, ldb = n, ldc = n;
    std::vector<double> storage(m * n, 0.0), a(m * lda), b(k * ldb), reference(m * n, 0.0);
    std::mt19937_64 rng(0x8454b00dULL);
    std::uniform_int_distribution<int> d(-20, 20);
    for (double& x : a)
        x = double(d(rng)) / 32.0;
    for (double& x : b)
        x = double(d(rng)) / 32.0;
    if (alias_a)
        for (std::size_t i = 0; i < m; ++i)
            std::memcpy(storage.data() + i * lda, a.data() + i * lda, lda * sizeof(double));
    else
        std::memcpy(storage.data(), b.data(), b.size() * sizeof(double));
    // C 与 A 或 B 共用存储时，结果仍须与独立输出逐位一致。
    ozamx::gemm_fp64(m, n, k, a.data(), lda, b.data(), ldb, reference.data(), ldc,
                     ozamx::ProductBudget::p6);
    ozamx::gemm_fp64(m, n, k, alias_a ? storage.data() : a.data(), lda,
                     alias_a ? b.data() : storage.data(), ldb, storage.data(), ldc,
                     ozamx::ProductBudget::p6);
    std::size_t mismatches = 0;
    for (std::size_t i = 0; i < m * n; ++i)
        mismatches += std::memcmp(&storage[i], &reference[i], sizeof(double)) != 0;
    std::cout << "{\"case\":\"1024_c_aliases_" << (alias_a ? "a" : "b")
              << "\",\"mismatches\":" << mismatches << "}\n";
    return mismatches == 0;
}
int main() {
    return run(true) && run(false) ? 0 : 1;
}
