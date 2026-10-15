#include "ozamx/gemm.hpp"

#include <cmath>
#include <cstring>
#include <iostream>
#include <limits>

template <class T, class F> bool probe(const char* name, T sentinel, F&& call) {
    // 每种失败输入都验证异常路径没有改写调用者的输出值。
    T c = sentinel;
    bool threw = false;
    try {
        call(&c);
    } catch (const ozamx::Error&) {
        threw = true;
    }
    const bool unchanged = std::memcmp(&c, &sentinel, sizeof(T)) == 0;
    std::cout << "{\"case\":\"" << name << "\",\"threw\":" << (threw ? "true" : "false")
              << ",\"c_unchanged\":" << (unchanged ? "true" : "false") << "}\n";
    return threw && unchanged;
}

int main() {
    bool ok = true;
    ok &= probe<float>("fp32_nan_transaction", 314.25f, [](float* c) {
        float a = std::numeric_limits<float>::quiet_NaN(), b = 1.0f;
        ozamx::gemm_fp32(1, 1, 1, &a, 1, &b, 1, c, 1);
    });
    ok &= probe<float>("fp32_overflow_transaction", 314.25f, [](float* c) {
        float a = 2.0e38f, b = 2.0f;
        ozamx::gemm_fp32(1, 1, 1, &a, 1, &b, 1, c, 1);
    });
    ok &= probe<double>("fp64_inf_transaction", -721.5, [](double* c) {
        double a = std::numeric_limits<double>::infinity(), b = 1.0;
        ozamx::gemm_fp64(1, 1, 1, &a, 1, &b, 1, c, 1, ozamx::ProductBudget::p21);
    });
    ok &= probe<double>("fp64_range_transaction", -721.5, [](double* c) {
        double a = std::ldexp(1.0, 128), b = 1.0;
        ozamx::gemm_fp64(1, 1, 1, &a, 1, &b, 1, c, 1, ozamx::ProductBudget::p21);
    });
    return ok ? 0 : 1;
}
