#include <immintrin.h>
#include <omp.h>
#include <sys/syscall.h>
#include <asm/prctl.h>
#include <unistd.h>
#include <cerrno>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <filesystem>

#ifndef ARCH_REQ_XCOMP_PERM
#define ARCH_REQ_XCOMP_PERM 0x1023
#endif
struct TileConfig {
    uint8_t palette_id, start_row, reserved[14];
    uint16_t colsb[16];
    uint8_t rows[16];
} __attribute__((packed, aligned(64)));
static_assert(sizeof(TileConfig) == 64);
using Clock = std::chrono::steady_clock;
static constexpr int REPS = 5;
static constexpr double TARGET = .100;
struct Result {
    double sec = 0, ops = 0, bytes = 0, checksum = 0;
    uint64_t iterations = 0;
};
static bool permit_amx() {
    return syscall(SYS_arch_prctl, ARCH_REQ_XCOMP_PERM, 18) == 0;
}
static double freq_mhz() {
    double sum = 0;
    int n = 0;
    for (int c = 0; c < 64; c++) {
        std::ifstream f("/sys/devices/system/cpu/cpu" + std::to_string(c) +
                        "/cpufreq/scaling_cur_freq");
        double x;
        if (f >> x) {
            sum += x / 1000.;
            n++;
        }
    }
    return n ? sum / n : 0.;
}
template <class F> static Result timed_parallel(int threads, F fn) {
    Result r;
    auto t0 = Clock::now();
    uint64_t total = 0;
#pragma omp parallel num_threads(threads) reduction(+ : total)
    {
#pragma omp barrier
#pragma omp master
        {}
#pragma omp barrier
        uint64_t it = fn();
        total += it;
    }
    r.sec = std::chrono::duration<double>(Clock::now() - t0).count();
    r.iterations = total;
    return r;
}
static uint64_t fma_kernel(int threads, bool fp64, double& checksum) {
    uint64_t total = 0;
    double allsum = 0;
#pragma omp parallel num_threads(threads) reduction(+ : total, allsum)
    {
        __m512 x = _mm512_set1_ps(1.00001f), y = _mm512_set1_ps(.99999f);
        // Distinct accumulators must remain eight independent dependency chains in
        // the generated code. Identical initial values let GCC merge the chains.
        __m512 a0 = _mm512_set1_ps(.10f), a1 = _mm512_set1_ps(.11f), a2 = _mm512_set1_ps(.12f),
               a3 = _mm512_set1_ps(.13f);
        __m512 a4 = _mm512_set1_ps(.14f), a5 = _mm512_set1_ps(.15f), a6 = _mm512_set1_ps(.16f),
               a7 = _mm512_set1_ps(.17f);
        __m512d xd = _mm512_set1_pd(1.00001), yd = _mm512_set1_pd(.99999);
        __m512d d0 = _mm512_set1_pd(.10), d1 = _mm512_set1_pd(.11), d2 = _mm512_set1_pd(.12),
                d3 = _mm512_set1_pd(.13);
        __m512d d4 = _mm512_set1_pd(.14), d5 = _mm512_set1_pd(.15), d6 = _mm512_set1_pd(.16),
                d7 = _mm512_set1_pd(.17);
        uint64_t it = 0;
        auto end = Clock::now() + std::chrono::duration_cast<Clock::duration>(
                                      std::chrono::duration<double>(TARGET));
        do {
            for (int batch = 0; batch < 1024; batch++) {
                if (fp64) {
                    d0 = _mm512_fmadd_pd(xd, yd, d0);
                    d1 = _mm512_fmadd_pd(xd, yd, d1);
                    d2 = _mm512_fmadd_pd(xd, yd, d2);
                    d3 = _mm512_fmadd_pd(xd, yd, d3);
                    d4 = _mm512_fmadd_pd(xd, yd, d4);
                    d5 = _mm512_fmadd_pd(xd, yd, d5);
                    d6 = _mm512_fmadd_pd(xd, yd, d6);
                    d7 = _mm512_fmadd_pd(xd, yd, d7);
                } else {
                    a0 = _mm512_fmadd_ps(x, y, a0);
                    a1 = _mm512_fmadd_ps(x, y, a1);
                    a2 = _mm512_fmadd_ps(x, y, a2);
                    a3 = _mm512_fmadd_ps(x, y, a3);
                    a4 = _mm512_fmadd_ps(x, y, a4);
                    a5 = _mm512_fmadd_ps(x, y, a5);
                    a6 = _mm512_fmadd_ps(x, y, a6);
                    a7 = _mm512_fmadd_ps(x, y, a7);
                }
                ++it;
            }
        } while (Clock::now() < end);
        alignas(64) float fv[16];
        alignas(64) double dv[8];
        double sum = 0;
        if (fp64) {
            _mm512_store_pd(dv, d0);
            for (double z : dv)
                sum += z;
            _mm512_store_pd(dv, d1);
            for (double z : dv)
                sum += z;
            _mm512_store_pd(dv, d2);
            for (double z : dv)
                sum += z;
            _mm512_store_pd(dv, d3);
            for (double z : dv)
                sum += z;
            _mm512_store_pd(dv, d4);
            for (double z : dv)
                sum += z;
            _mm512_store_pd(dv, d5);
            for (double z : dv)
                sum += z;
            _mm512_store_pd(dv, d6);
            for (double z : dv)
                sum += z;
            _mm512_store_pd(dv, d7);
            for (double z : dv)
                sum += z;
        } else {
            _mm512_store_ps(fv, a0);
            for (float z : fv)
                sum += z;
            _mm512_store_ps(fv, a1);
            for (float z : fv)
                sum += z;
            _mm512_store_ps(fv, a2);
            for (float z : fv)
                sum += z;
            _mm512_store_ps(fv, a3);
            for (float z : fv)
                sum += z;
            _mm512_store_ps(fv, a4);
            for (float z : fv)
                sum += z;
            _mm512_store_ps(fv, a5);
            for (float z : fv)
                sum += z;
            _mm512_store_ps(fv, a6);
            for (float z : fv)
                sum += z;
            _mm512_store_ps(fv, a7);
            for (float z : fv)
                sum += z;
        }
#pragma omp critical
        {
            volatile double sink = sum;
            (void)sink;
        }
        total += it;
        allsum += sum;
    }
    checksum = allsum;
    return total;
}
static uint64_t amx_kernel(int threads, bool& ok, double& checksum) {
    uint64_t total = 0;
    double check = 0;
#pragma omp parallel num_threads(threads) reduction(+ : total, check)
    {
        const bool allowed = permit_amx();
#pragma omp barrier
        if (allowed) {
            TileConfig cfg{};
            cfg.palette_id = 1;
            for (int i : {0, 1, 4, 5, 6, 7}) {
                cfg.colsb[i] = 64;
                cfg.rows[i] = 16;
            }
            _tile_loadconfig(&cfg);
            alignas(64) uint16_t aa[16 * 32], bb[16 * 32];
            for (int i = 0; i < 512; i++) {
                aa[i] = 0x3f80;
                bb[i] = 0x3f00;
            }
            _tile_loadd(0, aa, 64);
            _tile_loadd(1, bb, 64);
            _tile_zero(4);
            _tile_zero(5);
            _tile_zero(6);
            _tile_zero(7);
            uint64_t it = 0;
            auto end = Clock::now() + std::chrono::duration_cast<Clock::duration>(
                                          std::chrono::duration<double>(TARGET));
            do {
                for (int batch = 0; batch < 1024; batch++) {
                    _tile_dpbf16ps(4, 0, 1);
                    _tile_dpbf16ps(5, 0, 1);
                    _tile_dpbf16ps(6, 0, 1);
                    _tile_dpbf16ps(7, 0, 1);
                    ++it;
                }
            } while (Clock::now() < end);
            alignas(64) float out[4][16 * 16];
            _tile_stored(4, out[0], 64);
            _tile_stored(5, out[1], 64);
            _tile_stored(6, out[2], 64);
            _tile_stored(7, out[3], 64);
            double s = 0;
            for (auto& tile : out)
                for (float v : tile)
                    s += v;
            check += s;
            total += it;
            _tile_release();
        }
#pragma omp barrier
#pragma omp single
        { ok = allowed; }
    }
    checksum = check;
    return total;
}
static Result memory_copy(int threads, float* a, float* b, size_t count) {
    Result r;
    auto begin = Clock::now();
    const auto stop = begin + std::chrono::milliseconds(50);
    uint64_t passes = 0;
    do {
#pragma omp parallel for num_threads(threads) schedule(static)
        for (size_t i = 0; i < count; i++)
            b[i] = a[i];
        ++passes;
    } while (Clock::now() < stop);
    r.sec = std::chrono::duration<double>(Clock::now() - begin).count();
    r.iterations = passes;
    r.bytes = double(count) * sizeof(float) * 2 * passes;
    for (size_t i = 0; i < count; i++)
        r.checksum += b[i];
    return r;
}
static Result memory_triad(int threads, float* a, float* b, float* c, size_t count) {
    Result r;
    auto begin = Clock::now();
    const auto stop = begin + std::chrono::milliseconds(50);
    uint64_t passes = 0;
    do {
#pragma omp parallel for num_threads(threads) schedule(static)
        for (size_t i = 0; i < count; i++)
            c[i] = a[i] + 2.f * b[i];
        ++passes;
    } while (Clock::now() < stop);
    r.sec = std::chrono::duration<double>(Clock::now() - begin).count();
    r.iterations = passes;
    r.bytes = double(count) * sizeof(float) * 3 * passes;
    for (size_t i = 0; i < count; i++)
        r.checksum += c[i];
    return r;
}
static float* aligned_floats(size_t count) {
    void* p = nullptr;
    if (posix_memalign(&p, 4096, count * sizeof(float)) != 0)
        throw std::bad_alloc();
    return static_cast<float*>(p);
}
static void init_memory(int threads, float* a, float* b, float* c, size_t count) {
#pragma omp parallel for num_threads(threads) schedule(static)
    for (size_t i = 0; i < count; i++) {
        a[i] = float((i % 1024) + 1) * .001f;
        b[i] = float((i % 257) + 1) * .002f;
        c[i] = 0.f;
    }
}
int main(int argc, char** argv) try {
    std::string path = "platform_baseline.csv";
    bool memory_only = false;
    for (int i = 1; i < argc; i++) {
        std::string a = argv[i];
        if (a == "--output" && i + 1 < argc)
            path = argv[++i];
        else if (a == "--memory-only")
            memory_only = true;
        else
            throw std::runtime_error("usage: platform_baseline [--memory-only] [--output FILE]");
    }
    std::ofstream out(path);
    if (!out)
        throw std::runtime_error("cannot create output");
    out << "benchmark,threads,rep,elapsed_s,iterations,operations,bytes,rate_per_s,checksum,freq_"
           "start_avg_mhz,freq_end_avg_mhz,definition\n"
        << std::setprecision(12);
    const std::vector<int> teams{1, 32, 64};
    auto emit = [&](const std::string& name, int th, int rep, const Result& r,
                    const std::string& unit, const std::string& def, double f0, double f1) {
        out << name << ',' << th << ',' << rep << ',' << r.sec << ',' << r.iterations << ','
            << r.ops << ',' << r.bytes << ',' << (r.ops ? r.ops / r.sec : r.bytes / r.sec) << ','
            << r.checksum << ',' << f0 << ',' << f1 << ',' << unit << ":" << def << '\n';
        out.flush();
    };
    // Each array is 256 MiB: copy footprint 512 MiB, triad footprint 768 MiB, both above the 165 MiB aggregate LLC.
    const size_t count = 64u * 1024u * 1024u;
    float *a = aligned_floats(count), *b = aligned_floats(count), *c = aligned_floats(count);
    for (int th : teams) {
        init_memory(th, a, b, c, count);
        omp_set_dynamic(0);
        omp_set_num_threads(th);
        if (!memory_only)
            for (int which = 0; which < 2; which++) {
                bool d = which == 1;
                auto run = [&](double& sum) {
                    return fma_kernel(th, d, sum);
                };
                double warm = 0;
                run(warm);
                for (int rep = 0; rep < REPS; rep++) {
                    double f0 = freq_mhz(), sum = 0;
                    auto t = Clock::now();
                    uint64_t it = run(sum);
                    double sec = std::chrono::duration<double>(Clock::now() - t).count(),
                           f1 = freq_mhz();
                    Result r;
                    r.sec = sec;
                    r.iterations = it;
                    r.ops = double(it) * (d ? 8 * 8 * 2 : 8 * 16 * 2);
                    r.checksum = sum;
                    emit(d ? "avx512_fp64_fma" : "avx512_fp32_fma", th, rep, r, "FLOP/s",
                         "8 independent vector accumulators; 8 FMA/vector/loop; 2 FLOP/FMA", f0,
                         f1);
                }
            }
        if (!memory_only) {
            bool okay = false;
            double check = 0;
            amx_kernel(th, okay, check);
            if (!okay)
                throw std::runtime_error("AMX tile permission unavailable on at least one worker");
            for (int rep = 0; rep < REPS; rep++) {
                double f0 = freq_mhz();
                auto t = Clock::now();
                uint64_t it = amx_kernel(th, okay, check);
                double sec = std::chrono::duration<double>(Clock::now() - t).count(),
                       f1 = freq_mhz();
                Result r;
                r.sec = sec;
                r.iterations = it;
                r.ops = double(it) * 4 * (2. * 16 * 16 * 32);
                r.checksum = check;
                emit("amx_bf16_register_tdp", th, rep, r, "FLOP/s",
                     "two 16x32 BF16 input tiles loaded once; four 16x16 FP32 accumulators; per "
                     "TDP=2*16*16*32 FLOPs",
                     f0, f1);
            }
        }
        memory_copy(th, a, b, count);
        for (int rep = 0; rep < REPS; rep++) {
            double f0 = freq_mhz();
            auto r = memory_copy(th, a, b, count);
            double f1 = freq_mhz();
            emit("memory_copy", th, rep, r, "B/s",
                 "512 MiB footprint exceeds LLC; each pass has 256 MiB logical reads + 256 MiB "
                 "logical writes (write-allocate may add traffic)",
                 f0, f1);
        }
        memory_triad(th, a, b, c, count);
        for (int rep = 0; rep < REPS; rep++) {
            double f0 = freq_mhz();
            auto r = memory_triad(th, a, b, c, count);
            double f1 = freq_mhz();
            emit("memory_triad", th, rep, r, "B/s",
                 "768 MiB footprint exceeds LLC; each pass has 256 MiB logical reads from A + 256 "
                 "MiB from B + 256 MiB logical writes to C (write-allocate may add traffic)",
                 f0, f1);
        }
    }
    free(a);
    free(b);
    free(c);
} catch (const std::exception& e) {
    std::cerr << "platform_baseline: " << e.what() << '\n';
    return 2;
}
