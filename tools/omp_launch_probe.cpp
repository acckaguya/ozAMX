// Diagnostic only: complete OpenMP fork/barrier/join latency, not GEMM FLOPS.
#include <omp.h>
#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <vector>

int main(int argc, char** argv) try {
    const int threads = argc > 1 ? std::stoi(argv[1]) : 64;
    const int repeats = argc > 2 ? std::stoi(argv[2]) : 2000;
    if (argc > 3 || threads < 1 || repeats < 1)
        throw std::runtime_error("usage: omp_launch_probe [threads>0] [repeats>0]");
    std::vector<double> raw;
    raw.reserve(repeats);
    for (int rep = -10; rep < repeats; ++rep) {
        int observed = 0;
        const auto start = std::chrono::steady_clock::now();
#pragma omp parallel num_threads(threads) shared(observed)
        {
            if (omp_get_thread_num() == 0)
                observed = omp_get_num_threads();
#pragma omp barrier
        }
        const auto end = std::chrono::steady_clock::now();
        if (observed != threads)
            throw std::runtime_error("actual team differs from requested threads");
        if (rep >= 0)
            raw.push_back(std::chrono::duration<double, std::micro>(end-start).count());
    }
    auto sorted = raw;
    std::sort(sorted.begin(), sorted.end());
    const auto mid = sorted.size()/2;
    const double median = sorted.size()%2 ? sorted[mid] : (sorted[mid-1]+sorted[mid])/2;
    std::cout << std::setprecision(17)
              << "{\"diagnostic\":\"omp_fork_barrier_join\",\"threads\":" << threads
              << ",\"actual_threads\":" << threads << ",\"warmups\":10,\"repeats\":" << repeats
              << ",\"mean_us\":" << std::accumulate(raw.begin(),raw.end(),0.0)/raw.size()
              << ",\"median_us\":" << median << ",\"min_us\":" << sorted.front()
              << ",\"max_us\":" << sorted.back() << ",\"raw_us\":[";
    for (std::size_t i=0; i<raw.size(); ++i)
        std::cout << (i ? "," : "") << raw[i];
    std::cout << "]}\n";
    return 0;
} catch (const std::exception& e) {
    std::cerr << e.what() << '\n';
    return 1;
}
