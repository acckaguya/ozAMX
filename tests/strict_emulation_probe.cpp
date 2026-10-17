// Full-output mathematical checks for staging, padded edges and BK boundaries.
// The oracle does not include any production split/packing/kernel implementation.
#include "ozamx/gemm.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>
#include <vector>

namespace {
using Quad = __float128;
using Planes = std::array<std::vector<double>, 6>;
std::uint64_t random_word(std::uint64_t& state) {
    auto x = (state += 0x9e3779b97f4a7c15ULL);
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}
double bf16(double x) {
    float f = float(x);
    std::uint32_t u;
    std::memcpy(&u, &f, sizeof(u));
    u = (u + 0x7fffU + ((u >> 16) & 1U)) & 0xffff0000U;
    std::memcpy(&f, &u, sizeof(u));
    return double(f);
}
Planes split(const std::vector<double>& input) {
    auto residual = input;
    Planes planes;
    for (auto& plane : planes) {
        double maximum = 0;
        for (double x : residual) maximum = std::max(maximum, std::abs(x));
        plane.resize(input.size(), 0);
        if (maximum == 0) continue;
        int exponent;
        const double fraction = std::frexp(maximum, &exponent);
        const double sigma = std::ldexp(1.0, exponent - (fraction == .5) + 45);
        for (std::size_t q = 0; q < input.size(); ++q) {
            plane[q] = bf16((residual[q] + sigma) - sigma);
            residual[q] -= plane[q];
        }
    }
    return planes;
}
bool fp64(std::size_t m, std::size_t n, std::size_t k, std::uint64_t seed) {
    std::vector<double> a(m*k), b(k*n);
    for (auto* input : {&a, &b})
        for (auto& x : *input)
            x = double(std::int64_t(random_word(seed) >> 11) - 4503599627370496LL) /
                4503599627370496.0;
    const auto a_before = a, b_before = b;
    const auto sa = split(a), sb = split(b);
    std::array<std::vector<double>, 4> reference;
    for (auto& r : reference) r.resize(m*n, 0);
    std::size_t component_rounding = 0;
    for (std::size_t kb = 0; kb < k; kb += 256)
        for (int diagonal = 0; diagonal < 6; ++diagonal)
            for (int ai = 0; ai <= diagonal; ++ai)
                for (std::size_t i = 0; i < m; ++i)
                    for (std::size_t j = 0; j < n; ++j) {
                        Quad dot = 0;
                        for (std::size_t q = kb; q < std::min(k, kb+256); ++q)
                            dot += Quad(sa[ai][i*k+q]) * Quad(sb[diagonal-ai][q*n+j]);
                        const float component = float(dot);
                        component_rounding += Quad(component) != dot;
                        for (int mode = 0; mode < 4; ++mode)
                            if (diagonal < mode+3)
                                reference[mode][i*n+j] += double(component);
                    }
    bool ok = component_rounding == 0;
    const int budgets[] = {6, 10, 15, 21};
    for (int mode = 0; mode < 4; ++mode) {
        const std::size_t ldc = n+7;
        std::vector<double> output(m*ldc, std::numeric_limits<double>::quiet_NaN());
        ozamx::gemm_fp64(m,n,k,a.data(),k,b.data(),n,output.data(),ldc,
                         static_cast<ozamx::ProductBudget>(budgets[mode]));
        std::size_t mismatches = 0;
        for (std::size_t i = 0; i < m; ++i) {
            for (std::size_t j = 0; j < n; ++j)
                mismatches += std::memcmp(&output[i*ldc+j], &reference[mode][i*n+j], sizeof(double)) != 0;
            for (std::size_t j = n; j < ldc; ++j) ok &= std::isnan(output[i*ldc+j]);
        }
        ok &= mismatches == 0;
        std::cout << "fp64 " << m << 'x' << n << 'x' << k << " p" << budgets[mode]
                  << " bit_mismatches=" << mismatches << " component_rounding=" << component_rounding << '\n';
    }
    return ok && a == a_before && b == b_before;
}
bool fp32() {
    constexpr std::size_t m=65, n=289, k=513, lda=k+3, ldb=n+5, ldc=n+7;
    std::vector<float> a(m*lda), b(k*ldb), c(m*ldc, std::numeric_limits<float>::quiet_NaN());
    std::uint64_t seed=20261016;
    for (std::size_t i=0;i<m;++i)for(std::size_t q=0;q<k;++q)
        a[i*lda+q]=float(int(random_word(seed)%17)-8)/16;
    for (std::size_t q=0;q<k;++q)for(std::size_t j=0;j<n;++j)
        b[q*ldb+j]=float(int(random_word(seed)%17)-8)/16;
    const auto aa=a, bb=b;
    ozamx::gemm_fp32(m,n,k,a.data(),lda,b.data(),ldb,c.data(),ldc);
    std::size_t mismatches=0;
    for(std::size_t i=0;i<m;++i) {
        for(std::size_t j=0;j<n;++j) {
            std::int64_t exact=0;
            for(std::size_t q=0;q<k;++q)
                exact+=std::int64_t(a[i*lda+q]*16)*std::int64_t(b[q*ldb+j]*16);
            mismatches+=c[i*ldc+j] != float(exact)/256;
        }
        for(std::size_t j=n;j<ldc;++j)mismatches+=!std::isnan(c[i*ldc+j]);
    }
    std::cout << "fp32 65x289x513 exact_mismatches=" << mismatches << '\n';
    return mismatches==0 && a==aa && b==bb;
}
} // namespace
int main() {
    const bool a=fp32();
    const bool b=fp64(25,41,289,260904);
    const bool c=fp64(257,33,65,8454);
    const bool d=fp64(17,263,257,20261016);
    return a && b && c && d ? 0 : 1;
}
