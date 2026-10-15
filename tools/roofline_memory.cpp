#include <immintrin.h>
#include <omp.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using Clock = std::chrono::steady_clock;
constexpr int kRepetitions = 5;
// Aim above the 0.1 s contract to absorb ordinary timing jitter in later reps.
constexpr double kMinimumSeconds = 0.150;

struct Level {
    const char* name;
    std::size_t elements_per_worker;
};

// Three independently aligned arrays per worker. These names describe the
// intended footprint only; actual cache residency/misses are not measured.
constexpr Level kLevels[] = {
    {"L1_footprint", 8 * 1024 / sizeof(double)},
    {"L2_footprint", 256 * 1024 / sizeof(double)},
    {"LLC_candidate", 768 * 1024 / sizeof(double)},
    {"DRAM_footprint", 8 * 1024 * 1024 / sizeof(double)},
};

struct WorkerArrays {
    double* a = nullptr;
    double* b = nullptr;
    double* c = nullptr;
};

bool allocate_aligned(double** result, std::size_t count) {
    void* memory = nullptr;
    if (posix_memalign(&memory, 64, count * sizeof(double)) != 0)
        return false;
    *result = static_cast<double*>(memory);
    return true;
}

void release(std::vector<WorkerArrays>& workers) {
    for (auto& worker : workers) {
        std::free(worker.a);
        std::free(worker.b);
        std::free(worker.c);
        worker = {};
    }
}

bool allocate_and_first_touch(int threads, std::size_t elements,
                              std::vector<WorkerArrays>& workers) {
    workers.assign(static_cast<std::size_t>(threads), {});
    int allocation_failed = 0;
#pragma omp parallel num_threads(threads) shared(allocation_failed, workers)
    {
        const int tid = omp_get_thread_num();
        WorkerArrays& own = workers[static_cast<std::size_t>(tid)];
        if (!allocate_aligned(&own.a, elements) || !allocate_aligned(&own.b, elements) ||
            !allocate_aligned(&own.c, elements)) {
#pragma omp atomic write
            allocation_failed = 1;
        }
#pragma omp barrier
        // Static, one-worker-per-partition initialization: the thread that owns
        // each allocation also writes every page on its first touch.
#pragma omp for schedule(static, 1)
        for (int owner = 0; owner < threads; ++owner) {
            WorkerArrays& arrays = workers[static_cast<std::size_t>(owner)];
            if (!arrays.a || !arrays.b || !arrays.c)
                continue;
            for (std::size_t i = 0; i < elements; ++i) {
                arrays.a[i] = 0.0;
                arrays.b[i] = 0.25 + static_cast<double>(i % 17) * 0.001;
                arrays.c[i] = 0.50 + static_cast<double>(i % 19) * 0.002;
            }
        }
    }
    if (allocation_failed) {
        release(workers);
        return false;
    }
    return true;
}

// One AVX-512 vector iteration: 2 x 64-byte loads, 1 packed-double FMA
// (2 floating-point operations per element), and 1 x 64-byte store.
__attribute__((noinline)) void triad_pass(double* __restrict a, const double* __restrict b,
                                          const double* __restrict c, std::size_t elements) {
    const __m512d scale = _mm512_set1_pd(0.5);
    for (std::size_t i = 0; i < elements; i += 8) {
        const __m512d vb = _mm512_load_pd(b + i);
        const __m512d vc = _mm512_load_pd(c + i);
        const __m512d va = _mm512_fmadd_pd(vc, scale, vb);
        _mm512_store_pd(a + i, va);
    }
}

struct TimedBatch {
    double seconds;
    double checksum;
};

TimedBatch run_batch(int threads, std::size_t elements, std::vector<WorkerArrays>& workers,
                     std::uint64_t passes) {
    std::vector<double> elapsed(static_cast<std::size_t>(threads), 0.0);
#pragma omp parallel num_threads(threads) shared(elapsed, workers)
    {
        const int tid = omp_get_thread_num();
        WorkerArrays& own = workers[static_cast<std::size_t>(tid)];
#pragma omp barrier
        const auto start = Clock::now();
        for (std::uint64_t pass = 0; pass < passes; ++pass) {
            triad_pass(own.a, own.b, own.c, elements);
            // Prevent dead-store elimination/hoisting across complete passes.
            asm volatile("" ::: "memory");
        }
#pragma omp barrier
        const auto stop = Clock::now();
        elapsed[static_cast<std::size_t>(tid)] =
            std::chrono::duration<double>(stop - start).count();
    }

    double team_max_seconds = 0.0;
    for (double value : elapsed)
        team_max_seconds = std::max(team_max_seconds, value);

    // Full output checksum is outside the timed OpenMP region.
    double checksum = 0.0;
    for (const auto& worker : workers) {
        for (std::size_t i = 0; i < elements; ++i)
            checksum += worker.a[i];
    }
    return {team_max_seconds, checksum};
}

std::uint64_t choose_passes(int threads, std::size_t elements, std::vector<WorkerArrays>& workers) {
    std::uint64_t passes = 1;
    while (true) {
        const TimedBatch trial = run_batch(threads, elements, workers, passes);
        if (!std::isfinite(trial.checksum) || trial.checksum <= 0.0) {
            throw std::runtime_error("triad checksum is invalid during calibration");
        }
        if (trial.seconds >= kMinimumSeconds)
            return passes;
        if (passes > (std::numeric_limits<std::uint64_t>::max() / 2)) {
            throw std::runtime_error("pass calibration overflow");
        }
        passes *= 2;
    }
}

std::uint64_t checksum_bits(double checksum) {
    std::uint64_t bits = 0;
    std::memcpy(&bits, &checksum, sizeof(bits));
    return bits;
}

void emit_row(std::ostream& out, const char* level, int threads, std::size_t elements,
              std::uint64_t passes, const char* kind, int repetition, const TimedBatch& result) {
    const std::uint64_t element_count =
        static_cast<std::uint64_t>(elements) * static_cast<std::uint64_t>(threads) * passes;
    const std::uint64_t logical_bytes = element_count * 3 * sizeof(double);
    const std::uint64_t logical_flops = element_count * 2;
    const double byte_rate = static_cast<double>(logical_bytes) / result.seconds;
    const double gflops = static_cast<double>(logical_flops) / result.seconds / 1.0e9;
    const std::uint64_t per_worker_bytes =
        static_cast<std::uint64_t>(elements) * 3 * sizeof(double);
    const std::uint64_t total_bytes = per_worker_bytes * static_cast<std::uint64_t>(threads);
    out << level << ',' << threads << ',' << elements << ',' << passes << ',' << kind << ','
        << repetition << ',' << per_worker_bytes << ',' << total_bytes << ',' << logical_bytes
        << ',' << logical_flops << ',' << std::setprecision(9) << result.seconds << ','
        << std::setprecision(3) << byte_rate << ',' << std::setprecision(9) << gflops << ','
        << std::setprecision(17) << result.checksum << ',' << checksum_bits(result.checksum)
        << '\n';
}

} // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "Usage: roofline_memory OUTPUT.csv\n";
        return 2;
    }
    std::FILE* csv = std::fopen(argv[1], "w");
    if (!csv) {
        std::perror("open output CSV");
        return 2;
    }
    std::fputs("level,threads,elements_per_worker,complete_passes,record_type,repetition,"
               "footprint_bytes_per_worker,footprint_bytes_total,logical_bytes,"
               "logical_flops,team_max_seconds,logical_B_per_s,logical_GFLOP_per_s,"
               "checksum,checksum_bits_u64\n",
               csv);
    std::fclose(csv);
    std::ofstream output(argv[1], std::ios::app);
    if (!output) {
        std::cerr << "failed to append output CSV\n";
        return 2;
    }

    omp_set_dynamic(0);
    omp_set_max_active_levels(1);
    const int thread_counts[] = {1, 32, 64};
    try {
        for (const int threads : thread_counts) {
            for (const Level& level : kLevels) {
                std::vector<WorkerArrays> workers;
                if (!allocate_and_first_touch(threads, level.elements_per_worker, workers)) {
                    throw std::runtime_error("aligned per-worker allocation failed");
                }
                const std::uint64_t passes =
                    choose_passes(threads, level.elements_per_worker, workers);

                const TimedBatch warmup =
                    run_batch(threads, level.elements_per_worker, workers, passes);
                const double reference_checksum = warmup.checksum;
                emit_row(output, level.name, threads, level.elements_per_worker, passes, "warmup",
                         0, warmup);
                for (int repetition = 1; repetition <= kRepetitions; ++repetition) {
                    const TimedBatch measured =
                        run_batch(threads, level.elements_per_worker, workers, passes);
                    if (checksum_bits(measured.checksum) != checksum_bits(reference_checksum)) {
                        throw std::runtime_error("checksum changed across repetitions");
                    }
                    emit_row(output, level.name, threads, level.elements_per_worker, passes,
                             "timed", repetition, measured);
                    output.flush();
                }
                release(workers);
            }
        }
    } catch (const std::exception& error) {
        std::cerr << "roofline_memory: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
