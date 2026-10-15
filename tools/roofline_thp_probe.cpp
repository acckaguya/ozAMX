#include "ozamx/gemm.hpp"
#include <vector>
#include <random>
#include <fstream>
#include <iostream>
#include <chrono>
#include <string>
#include <sstream>
#include <iomanip>
#include <omp.h>
// 这是进程全部匿名映射的 THP 计数，用来观察 GEMM 前后变化，不是单个矩阵的归属量。
static long huge_kib() {
    std::ifstream f("/proc/self/smaps_rollup");
    std::string line;
    while (std::getline(f, line)) {
        if (line.rfind("AnonHugePages:", 0) == 0) {
            std::istringstream s(line.substr(14));
            long kib = 0;
            s >> kib;
            return kib;
        }
    }
    return -1;
}
int main() {
    const size_t n = 4096;
    omp_set_num_threads(64);
    std::vector<double> a(n * n), b(n * n), c(n * n);
    std::mt19937_64 rng(0x8454);
    std::uniform_real_distribution<double> u(-1, 1);
    for (auto& x : a)
        x = u(rng);
    for (auto& x : b)
        x = u(rng);
    const auto before = huge_kib();
    double sum = 0;
    std::cout << "{\"before_huge_kib\":" << before << ",\"samples\":[";
    for (int rep = 0; rep < 4; ++rep) {
        const auto start = std::chrono::steady_clock::now();
        auto t = ozamx::gemm_fp64_profiled(n, n, n, a.data(), n, b.data(), n, c.data(), n,
                                           ozamx::ProductBudget::p21);
        const auto stop = std::chrono::steady_clock::now();
        if (rep)
            std::cout << ',';
        std::cout << "{\"rep\":" << rep
                  << ",\"api_wall\":" << std::chrono::duration<double>(stop - start).count()
                  << ",\"compute\":" << t.compute_and_reconstruct_seconds
                  << ",\"AnonHugePagesKiB\":" << huge_kib() << '}';
    }
    for (double x : c)
        sum += x;
    std::cout << "],\"checksum\":" << std::setprecision(17) << sum << "}\n";
}
