#include "ozamx/gemm.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <exception>
#include <iomanip>
#include <iostream>
#include <limits>
#include <random>
#include <sstream>
#include <string>
#include <vector>
#include <immintrin.h>
#ifdef _OPENMP
#include <omp.h>
#endif

namespace {
struct Metrics {
    long double fro = 0, scaled = 0, max_abs = 0;
};

Metrics metrics(const std::vector<long double>& got, const std::vector<long double>& ref,
                const std::vector<long double>& abs_bound) {
    long double e2 = 0, r2 = 0, scaled = 0, ma = 0;
    for (std::size_t i = 0; i < got.size(); ++i) {
        const long double e = std::fabs(got[i] - ref[i]);
        e2 += e * e;
        r2 += ref[i] * ref[i];
        ma = std::max(ma, e);
        if (abs_bound[i] == 0)
            scaled = std::max(scaled, e);
        else
            scaled = std::max(scaled, e / abs_bound[i]);
    }
    return {r2 == 0 ? std::sqrt(e2) : std::sqrt(e2 / r2), scaled, ma};
}

std::string shape(std::size_t m, std::size_t n, std::size_t k) {
    return std::to_string(m) + "x" + std::to_string(n) + "x" + std::to_string(k);
}

bool check_fp32_case(std::size_t m, std::size_t n, std::size_t k, std::uint64_t seed, bool padded,
                     const std::string& label) {
    const std::size_t lda = k + (padded ? 3 : 0), ldb = n + (padded ? 5 : 0),
                      ldc = n + (padded ? 7 : 0);
    std::mt19937_64 gen(seed);
    std::uniform_real_distribution<float> dist(-1.0f, 1.0f);
    std::vector<float> a(std::max<std::size_t>(1, m * lda), 0),
        b(std::max<std::size_t>(1, k * ldb), 0);
    std::vector<float> c(std::max<std::size_t>(1, m * ldc),
                         std::numeric_limits<float>::quiet_NaN());
    for (std::size_t i = 0; i < m; ++i)
        for (std::size_t q = 0; q < k; ++q)
            a[i * lda + q] = dist(gen);
    for (std::size_t q = 0; q < k; ++q)
        for (std::size_t j = 0; j < n; ++j)
            b[q * ldb + j] = dist(gen);
    std::vector<long double> ref(m * n), bound(m * n);
    for (std::size_t i = 0; i < m; ++i)
        for (std::size_t j = 0; j < n; ++j) {
            long double s = 0, ab = 0;
            for (std::size_t q = 0; q < k; ++q) {
                const long double x = a[i * lda + q], y = b[q * ldb + j];
                s += x * y;
                ab += std::fabs(x * y);
            }
            ref[i * n + j] = s;
            bound[i * n + j] = ab;
        }
    try {
        ozamx::gemm_fp32(m, n, k, a.data(), lda, b.data(), ldb, c.data(), ldc);
    } catch (const std::exception& e) {
        std::cerr << "FAIL " << label << " " << shape(m, n, k) << ": " << e.what() << '\n';
        return false;
    }
    std::vector<long double> got(m * n);
    bool padding_ok = true;
    for (std::size_t i = 0; i < m; ++i) {
        for (std::size_t j = 0; j < n; ++j)
            got[i * n + j] = c[i * ldc + j];
        for (std::size_t j = n; j < ldc; ++j)
            padding_ok &= std::isnan(c[i * ldc + j]);
    }
    const auto met = metrics(got, ref, bound);
    const bool ok = met.fro < 3e-6L && met.scaled < 3e-6L && padding_ok;
    std::cout << std::setprecision(12) << "{\"case\":\"" << label
              << "\",\"precision\":\"fp32\",\"shape\":\"" << shape(m, n, k)
              << "\",\"seed\":" << seed << ",\"eF\":" << (double)met.fro
              << ",\"e_scaled\":" << (double)met.scaled << ",\"max_abs\":" << (double)met.max_abs
              << ",\"padding_guard\":\"" << (padding_ok ? "intact" : "modified")
              << "\",\"status\":\"" << (ok ? "pass" : "fail") << "\"}\n";
    return ok;
}

bool check_fp64_case(std::size_t m, std::size_t n, std::size_t k, std::uint64_t seed,
                     ozamx::ProductBudget budget, long double limit, const char* name) {
    const std::size_t lda = k + 2, ldb = n + 3, ldc = n + 4;
    std::mt19937_64 gen(seed);
    std::uniform_real_distribution<double> dist(-1.0, 1.0);
    std::vector<double> a(std::max<std::size_t>(1, m * lda), 0),
        b(std::max<std::size_t>(1, k * ldb), 0),
        c(std::max<std::size_t>(1, m * ldc), std::numeric_limits<double>::quiet_NaN()),
        repeat(c.size(), std::numeric_limits<double>::quiet_NaN());
    for (std::size_t i = 0; i < m; ++i)
        for (std::size_t q = 0; q < k; ++q)
            a[i * lda + q] = dist(gen);
    for (std::size_t q = 0; q < k; ++q)
        for (std::size_t j = 0; j < n; ++j)
            b[q * ldb + j] = dist(gen);
    std::vector<long double> ref(m * n), bound(m * n);
    for (std::size_t i = 0; i < m; ++i)
        for (std::size_t j = 0; j < n; ++j) {
            long double s = 0, ab = 0;
            for (std::size_t q = 0; q < k; ++q) {
                const long double x = a[i * lda + q], y = b[q * ldb + j];
                s += x * y;
                ab += std::fabs(x * y);
            }
            ref[i * n + j] = s;
            bound[i * n + j] = ab;
        }
    try {
        ozamx::gemm_fp64(m, n, k, a.data(), lda, b.data(), ldb, c.data(), ldc, budget);
    } catch (const std::exception& e) {
        std::cerr << "FAIL " << name << " " << shape(m, n, k) << ": " << e.what() << '\n';
        return false;
    }
    try {
        ozamx::gemm_fp64(m, n, k, a.data(), lda, b.data(), ldb, repeat.data(), ldc, budget);
    } catch (const std::exception& e) {
        std::cerr << "FAIL " << name << " repeat: " << e.what() << '\n';
        return false;
    }
    bool repeat_ok = true;
    for (std::size_t i = 0; i < m; ++i)
        for (std::size_t j = 0; j < n; ++j)
            repeat_ok &= c[i * ldc + j] == repeat[i * ldc + j];
    std::vector<long double> got(m * n);
    bool padding_ok = true;
    for (std::size_t i = 0; i < m; ++i) {
        for (std::size_t j = 0; j < n; ++j)
            got[i * n + j] = c[i * ldc + j];
        for (std::size_t j = n; j < ldc; ++j)
            padding_ok &= std::isnan(c[i * ldc + j]);
    }
    const auto met = metrics(got, ref, bound);
    const bool ok = met.fro < limit && met.scaled < limit && padding_ok && repeat_ok;
    std::cout << std::setprecision(12) << "{\"case\":\"" << name
              << "\",\"precision\":\"fp64\",\"shape\":\"" << shape(m, n, k)
              << "\",\"seed\":" << seed << ",\"budget\":" << static_cast<int>(budget)
              << ",\"eF\":" << (double)met.fro << ",\"e_scaled\":" << (double)met.scaled
              << ",\"max_abs\":" << (double)met.max_abs << ",\"padding_guard\":\""
              << (padding_ok ? "intact" : "modified") << "\""
              << ",\"same_seed_repeat\":\"" << (repeat_ok ? "identical" : "different") << "\""
              << ",\"status\":\"" << (ok ? "pass" : "fail") << "\"}\n";
    return ok;
}

bool check_amx_bf16_ftz() {
    struct alignas(64) TileConfig {
        std::uint8_t palette_id = 1, start_row = 0;
        std::uint8_t reserved[14]{};
        std::uint16_t colsb[16]{};
        std::uint8_t rows[16]{};
    } cfg;
    static_assert(sizeof(TileConfig) == 64);
    for (int t = 0; t < 3; ++t) {
        cfg.colsb[t] = 64;
        cfg.rows[t] = 16;
    }
    alignas(64) std::uint16_t a[16 * 32]{};
    alignas(64) std::uint16_t b[16 * 32];
    for (auto& x : b)
        x = 0x3f80; // BF16 1.0
    alignas(64) float c[16 * 16]{};
    auto run = [&](std::uint16_t x) {
        a[0] = x;
        _tile_loadconfig(&cfg);
        _tile_zero(0);
        _tile_loadd(1, a, 64);
        _tile_loadd(2, b, 64);
        _tile_dpbf16ps(0, 1, 2);
        _tile_stored(0, c, 64);
        _tile_release();
        a[0] = 0;
        return c[0];
    };
    const float subnormal = run(0x0001); // smallest BF16 subnormal
    const float normal = run(0x0080);    // smallest BF16 normal
    const bool ok = (subnormal == 0.0f && normal == std::ldexp(1.0f, -126));
    std::cout << std::setprecision(12)
              << "{\"case\":\"amx_bf16_input_ftz\",\"smallest_subnormal_result\":" << subnormal
              << ",\"smallest_normal_result\":" << normal << ",\"status\":\""
              << (ok ? "pass" : "fail") << "\"}\n";
    return ok;
}

bool check_fp64_zero_slice_and_edges() {
    bool ok = true;
    const double tiny = std::ldexp(1.0, -126), one = 1.0, upper = std::ldexp(1.0, 127);
    double a[2] = {one, tiny}, b[2] = {one, one}, c[1] = {0};
    try {
        ozamx::gemm_fp64(1, 1, 2, a, 2, b, 1, c, 1, ozamx::ProductBudget::p21);
        // The tiny entry may round to zero component slices; it remains in the residual.
        // At this scale the final FP64 result rounds to 1.0, but the input must be accepted.
        ok &= (c[0] == 1.0);
    } catch (const std::exception& e) {
        std::cerr << "FAIL fp64_zero_component_slice: " << e.what() << '\n';
        ok = false;
    }
    double au[1] = {upper}, bu[1] = {1}, cu[1] = {0};
    try {
        ozamx::gemm_fp64(1, 1, 1, au, 1, bu, 1, cu, 1, ozamx::ProductBudget::p21);
        ok &= std::isfinite(cu[0]) && cu[0] == upper;
    } catch (const std::exception& e) {
        std::cerr << "FAIL fp64_upper_safe_power: " << e.what() << '\n';
        ok = false;
    }
    std::cout << "{\"case\":\"fp64_zero_slice_and_exponent_edges\",\"status\":\""
              << (ok ? "pass" : "fail") << "\"}\n";
    return ok;
}

template <class F> bool must_throw(const char* label, F&& f) {
    try {
        f();
        std::cerr << "FAIL " << label << ": expected ozamx::Error\n";
        return false;
    } catch (const ozamx::Error&) {
        std::cout << "{\"case\":\"" << label << "\",\"status\":\"expected_error\"}\n";
        return true;
    } catch (const std::exception& e) {
        std::cerr << "FAIL " << label << ": wrong exception: " << e.what() << '\n';
        return false;
    }
}

bool check_transactional_errors() {
    // 非法输入或步长报错时，检查整个输出缓冲区都保持调用前的哨兵值。
    bool ok = true;
    float af[2] = {1.0f, std::numeric_limits<float>::quiet_NaN()}, bf[2] = {1.0f, 1.0f};
    float cf[8];
    std::fill(std::begin(cf), std::end(cf), 12345.25f);
    try {
        ozamx::gemm_fp32(1, 2, 2, af, 2, bf, 2, cf, 4);
        std::cerr << "FAIL fp32_error_transaction: expected error\n";
        ok = false;
    } catch (const ozamx::Error&) {
        for (float x : cf)
            ok &= x == 12345.25f;
    } catch (const std::exception& e) {
        std::cerr << "FAIL fp32_error_transaction: " << e.what() << '\n';
        ok = false;
    }
    double ad[2] = {1.0, 2.0}, bd[4] = {1.0, 1.0, 1.0, 1.0}, cd[8];
    std::fill(std::begin(cd), std::end(cd), -9876.5);
    try {
        ozamx::gemm_fp64(1, 2, 2, ad, 1, bd, 2, cd, 4, ozamx::ProductBudget::p6);
        std::cerr << "FAIL fp64_stride_transaction: expected error\n";
        ok = false;
    } catch (const ozamx::Error&) {
        for (double x : cd)
            ok &= x == -9876.5;
    } catch (const std::exception& e) {
        std::cerr << "FAIL fp64_stride_transaction: " << e.what() << '\n';
        ok = false;
    }
    std::cout << "{\"case\":\"validation_errors_leave_output_untouched\",\"status\":\""
              << (ok ? "pass" : "fail") << "\"}\n";
    return ok;
}

bool check_fp32_ties_and_zero_sign() {
    bool ok = true;
    // 1 + 2^-24 is halfway between adjacent FP32 values; round-to-even gives 1.
    float a[2] = {1.0f, std::ldexp(1.0f, -24)}, b[2] = {1.0f, 1.0f}, c[2] = {0.0f, 0.0f};
    try {
        ozamx::gemm_fp32(1, 1, 2, a, 2, b, 1, c, 2);
        ok &= c[0] == 1.0f;
        float az[1] = {-0.0f}, bz[1] = {1.0f}, cz[1] = {1.0f};
        ozamx::gemm_fp32(1, 1, 1, az, 1, bz, 1, cz, 1);
        ok &= cz[0] == 0.0f;
        std::uint32_t bits = 0;
        std::memcpy(&bits, &c[0], sizeof(bits));
        std::cout << "{\"case\":\"fp32_rounding_tie_and_zero\",\"tie_bits\":" << bits
                  << ",\"zero_negative\":" << (std::signbit(cz[0]) ? "true" : "false")
                  << ",\"status\":\"" << (ok ? "pass" : "fail") << "\"}\n";
    } catch (const std::exception& e) {
        std::cerr << "FAIL fp32_rounding_tie_and_zero: " << e.what() << '\n';
        return false;
    }
    return ok;
}
} // namespace

int main() {
    bool ok = true;
    const auto status = ozamx::request_amx_permission_for_current_thread();
    std::cout << "{\"case\":\"amx_main_thread_permission\",\"cpu_amx_tile\":"
              << (status.cpu_amx_tile ? "true" : "false")
              << ",\"cpu_amx_bf16\":" << (status.cpu_amx_bf16 ? "true" : "false")
              << ",\"permission\":" << (status.permission_available ? "true" : "false") << "}\n";
    if (!status.permission_available) {
        std::cerr << "AMX unavailable; kernel validation cannot run\n";
        return 2;
    }

    ok &= std::string(ozamx::product_order_fp32()) == "11,10,20,00,01,02";
    ok &= std::string(ozamx::product_order_fp64(ozamx::ProductBudget::p6)) == "00;01,10;02,11,20";
    ok &= std::string(ozamx::product_order_fp64(ozamx::ProductBudget::p10)) ==
          "00;01,10;02,11,20;03,12,21,30";
    ok &= std::string(ozamx::product_order_fp64(ozamx::ProductBudget::p15)) ==
          "00;01,10;02,11,20;03,12,21,30;04,13,22,31,40";
    ok &= std::string(ozamx::product_order_fp64(ozamx::ProductBudget::p21)) ==
          "00;01,10;02,11,20;03,12,21,30;04,13,22,31,40;05,14,23,32,41,50";
    std::cout << "{\"case\":\"documented_product_orders\",\"status\":\"" << (ok ? "pass" : "fail")
              << "\"}\n";

    // Irregular dimensions and padded leading dimensions exercise 16/32-edge paths.
    ok &= check_fp32_case(19, 23, 21, 0x260904, true, "fp32_irregular");
    ok &= check_fp32_case(5, 7, 3, 0x260905, true, "fp32_small_padded");
    ok &= check_fp32_case(3, 5, 255, 0x26090a, true, "fp32_k255_tail");
    ok &= check_fp32_case(3, 5, 256, 0x26090b, true, "fp32_k256_exact_panel");
    ok &= check_fp32_case(3, 5, 257, 0x260907, true, "fp32_cross_bk256");
    ok &= check_fp32_case(3, 5, 512, 0x26090c, true, "fp32_two_bk_panels");
    // The same deterministic BF16-range input is checked at all four truncation budgets.
    ok &= check_fp64_case(17, 19, 21, 0x260906, ozamx::ProductBudget::p6, 2e-6L, "fp64_p6");
    ok &= check_fp64_case(17, 19, 21, 0x260906, ozamx::ProductBudget::p10, 2e-8L, "fp64_p10");
    ok &= check_fp64_case(17, 19, 21, 0x260906, ozamx::ProductBudget::p15, 2e-10L, "fp64_p15");
    ok &= check_fp64_case(17, 19, 21, 0x260906, ozamx::ProductBudget::p21, 2e-10L, "fp64_p21");
    ok &= check_fp64_case(3, 5, 257, 0x260908, ozamx::ProductBudget::p6, 2e-6L,
                          "fp64_cross_bk256_p6");
    ok &= check_fp64_case(3, 5, 257, 0x260908, ozamx::ProductBudget::p21, 2e-10L,
                          "fp64_cross_bk256_p21");
    ok &= check_fp64_case(3, 5, 255, 0x26090d, ozamx::ProductBudget::p21, 2e-10L,
                          "fp64_k255_tail_p21");
    ok &= check_fp64_case(3, 5, 256, 0x26090e, ozamx::ProductBudget::p21, 2e-10L,
                          "fp64_k256_exact_panel_p21");
    ok &= check_fp64_case(3, 5, 512, 0x26090f, ozamx::ProductBudget::p21, 2e-10L,
                          "fp64_two_bk_panels_p21");

    // K=0 is defined as a zero product; M or N zero is rejected.
    {
        float a[1] = {0}, b[1] = {0}, c[8];
        std::fill(std::begin(c), std::end(c), -41.0f);
        try {
            ozamx::gemm_fp32(2, 3, 0, a, 0, b, 3, c, 4);
            for (int i = 0; i < 2; ++i) {
                for (int j = 0; j < 3; ++j)
                    ok &= c[i * 4 + j] == 0.0f;
                ok &= c[i * 4 + 3] == -41.0f;
            }
        } catch (const std::exception& e) {
            std::cerr << "FAIL fp32_k_zero: " << e.what() << '\n';
            ok = false;
        }
        double ad[1] = {0}, bd[1] = {0}, cd[8];
        std::fill(std::begin(cd), std::end(cd), -42.0);
        try {
            ozamx::gemm_fp64(2, 2, 0, ad, 0, bd, 2, cd, 4, ozamx::ProductBudget::p21);
            for (int i = 0; i < 2; ++i) {
                for (int j = 0; j < 2; ++j)
                    ok &= cd[i * 4 + j] == 0.0;
                for (int j = 2; j < 4; ++j)
                    ok &= cd[i * 4 + j] == -42.0;
            }
        } catch (const std::exception& e) {
            std::cerr << "FAIL fp64_k_zero: " << e.what() << '\n';
            ok = false;
        }
    }
    ok &= must_throw("zero_m", [] {
        float a = 1, b = 1, c = 0;
        ozamx::gemm_fp32(0, 1, 1, &a, 1, &b, 1, &c, 1);
    });
    ok &= must_throw("zero_n", [] {
        double a = 1, b = 1, c = 0;
        ozamx::gemm_fp64(1, 0, 1, &a, 1, &b, 1, &c, 1, ozamx::ProductBudget::p6);
    });
    ok &= must_throw("fp32_nan", [] {
        float a = std::numeric_limits<float>::quiet_NaN(), b = 1, c = 0;
        ozamx::gemm_fp32(1, 1, 1, &a, 1, &b, 1, &c, 1);
    });
    ok &= must_throw("fp32_subnormal_input", [] {
        float a = std::numeric_limits<float>::denorm_min(), b = 1, c = 0;
        ozamx::gemm_fp32(1, 1, 1, &a, 1, &b, 1, &c, 1);
    });
    ok &= must_throw("fp32_inf", [] {
        float a = std::numeric_limits<float>::infinity(), b = 1, c = 0;
        ozamx::gemm_fp32(1, 1, 1, &a, 1, &b, 1, &c, 1);
    });
    ok &= must_throw("fp64_nan", [] {
        double a = std::numeric_limits<double>::quiet_NaN(), b = 1, c = 0;
        ozamx::gemm_fp64(1, 1, 1, &a, 1, &b, 1, &c, 1, ozamx::ProductBudget::p6);
    });
    ok &= must_throw("fp64_inf", [] {
        double a = std::numeric_limits<double>::infinity(), b = 1, c = 0;
        ozamx::gemm_fp64(1, 1, 1, &a, 1, &b, 1, &c, 1, ozamx::ProductBudget::p6);
    });
    ok &= must_throw("fp64_below_bf16_range", [] {
        double a = std::ldexp(1.0, -127), b = 1, c = 0;
        ozamx::gemm_fp64(1, 1, 1, &a, 1, &b, 1, &c, 1, ozamx::ProductBudget::p6);
    });
    ok &= must_throw("fp32_output_overflow", [] {
        float a = 2.0e38f, b = 2.0f, c = 0;
        ozamx::gemm_fp32(1, 1, 1, &a, 1, &b, 1, &c, 1);
    });
    ok &= must_throw("fp64_outside_bf16_range", [] {
        double a = std::ldexp(1.0, 128), b = 1, c = 0;
        ozamx::gemm_fp64(1, 1, 1, &a, 1, &b, 1, &c, 1, ozamx::ProductBudget::p6);
    });

    ok &= check_fp64_zero_slice_and_edges();
    ok &= check_amx_bf16_ftz();
    ok &= check_transactional_errors();
    ok &= check_fp32_ties_and_zero_sign();

    // Each OpenMP worker requests its own XTILEDATA permission and invokes GEMM,
    // which executes a real tile kernel on that calling worker.
#ifdef _OPENMP
    const int requested_threads = std::min(64, omp_get_num_procs());
    std::vector<int> worker_ok(requested_threads, 0);
#pragma omp parallel num_threads(requested_threads)
    {
        const int tid = omp_get_thread_num();
        const auto s = ozamx::request_amx_permission_for_current_thread();
        if (s.permission_available) {
            float a[4] = {1, 2, 3, 4}, b[4] = {1, 0, 0, 1}, c[4] = {0, 0, 0, 0};
            try {
                ozamx::gemm_fp32(2, 2, 2, a, 2, b, 2, c, 2);
                worker_ok[tid] = (c[0] == 1 && c[1] == 2 && c[2] == 3 && c[3] == 4) ? 1 : 0;
            } catch (...) {
                worker_ok[tid] = 0;
            }
        }
    }
    int actual = 0;
    for (int x : worker_ok)
        actual += x;
    std::cout << "{\"case\":\"amx_worker_threads\",\"requested\":" << requested_threads
              << ",\"passed\":" << actual << "}\n";
    ok &= actual == requested_threads;
#endif
    std::cout << "{\"summary\":\"validation\",\"status\":\"" << (ok ? "pass" : "fail") << "\"}\n";
    return ok ? 0 : 1;
}
