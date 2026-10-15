#include <array>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <limits>
#include <memory>
#include <vector>

extern "C" void ozamx_reconstruct64_ilp4(double*, const float* const*, std::size_t, std::size_t);
extern "C" int ozamx_reconstruct64_ilp4_abi_probe(double*, const float* const*, std::size_t, std::size_t);

namespace {
constexpr std::size_t rows = 32, cols = 32;
constexpr std::uint64_t canary = 0x7ff123456789abcdULL;

std::uint64_t bits(double x) {
    std::uint64_t u;
    std::memcpy(&u, &x, sizeof u);
    return u;
}
std::uint32_t bits(float x) {
    std::uint32_t u;
    std::memcpy(&u, &x, sizeof u);
    return u;
}

struct Random {
    std::uint64_t s = 0x3907abcdeffed123ULL;
    std::uint32_t next() {
        s ^= s << 13; s ^= s >> 7; s ^= s << 17;
        return static_cast<std::uint32_t>(s >> 16);
    }
};

void fail(const char* what, std::size_t stride, std::size_t count, std::size_t i, std::size_t j) {
    std::cerr << what << " stride=" << stride << " count=" << count << " at=" << i << ',' << j << '\n';
    std::exit(1);
}

enum class Pattern { finite, specials };

struct AlignedDoubles {
    std::unique_ptr<double, decltype(&std::free)> data;
    explicit AlignedDoubles(std::size_t n)
        : data(static_cast<double*>(std::aligned_alloc(64, n * sizeof(double))), &std::free) {
        if (!data) std::abort();
    }
    double& operator[](std::size_t i) { return data.get()[i]; }
    const double& operator[](std::size_t i) const { return data.get()[i]; }
};

void run(std::size_t stride, std::size_t count, Pattern pattern) {
    const std::size_t extent = rows * stride + 8;
    AlignedDoubles got(extent), ref(extent);
    for (std::size_t x = 0; x < extent; ++x) {
        double v = x >= rows * stride ? 0.0 :
                   static_cast<double>(static_cast<int>((x * 37) % 101) - 50) / 8.0;
        if (x >= rows * stride) std::memcpy(&v, &canary, sizeof v);
        got[x] = ref[x] = v;
    }
    Random rng;
    std::vector<std::vector<float>> planes(count, std::vector<float>(rows * cols));
    std::vector<const float*> ptrs(count);
    const std::array<std::uint32_t, 10> special = {
        0x00000000u, 0x80000000u, 0x3f800000u, 0xbf800000u,
        0x7f800000u, 0xff800000u, 0x7fc12345u, 0xffc54321u,
        0x00800000u, 0x7f7fffffu
    };
    for (std::size_t q = 0; q < count; ++q) {
        ptrs[q] = planes[q].data();
        for (std::size_t x = 0; x < rows * cols; ++x) {
            std::uint32_t u;
            if (pattern == Pattern::specials) u = special[(rng.next() + q + x) % special.size()];
            else {
                const std::int32_t n = static_cast<std::int32_t>(rng.next() % 2000001) - 1000000;
                u = bits(static_cast<float>(n) * (x % 3 == 0 ? 0x1p-18f : (x % 3 == 1 ? 0x1p+18f : 0x1p-4f)));
            }
            std::memcpy(&planes[q][x], &u, sizeof u);
        }
    }
    // Independent scalar reference follows each output's historical q order.
    for (std::size_t i = 0; i < rows; ++i) for (std::size_t j = 0; j < cols; ++j)
        for (std::size_t q = 0; q < count; ++q) ref[i * stride + j] += static_cast<double>(planes[q][i * cols + j]);

    ozamx_reconstruct64_ilp4(got.data.get(), ptrs.data(), count, stride * sizeof(double));
    for (std::size_t i = 0; i < rows; ++i) {
        for (std::size_t j = 0; j < cols; ++j) {
            const double a = got[i * stride + j], b = ref[i * stride + j];
            if (pattern == Pattern::finite) {
                if (bits(a) != bits(b)) fail("finite bits mismatch", stride, count, i, j);
            } else {
                if (std::isfinite(a) != std::isfinite(b) || std::isinf(a) != std::isinf(b) || std::isnan(a) != std::isnan(b))
                    fail("nonfinite class mismatch", stride, count, i, j);
                if (std::isfinite(a) && bits(a) != bits(b)) fail("finite bits mismatch with special inputs", stride, count, i, j);
                if (std::isinf(a) && std::signbit(a) != std::signbit(b)) fail("infinity sign mismatch", stride, count, i, j);
            }
        }
        for (std::size_t j = cols; j < stride; ++j)
            if (bits(got[i * stride + j]) != bits(ref[i * stride + j])) fail("row padding modified", stride, count, i, j);
    }
    for (std::size_t x = rows * stride; x < extent; ++x)
        if (bits(got[x]) != canary) fail("trailing guard modified", stride, count, rows, x - rows * stride);
}
}

int main() {
    alignas(64) double abi_c[32 * 32]{};
    alignas(64) float abi_micro[32 * 32]{};
    const float* abi_planes[] = {abi_micro};
    if (!ozamx_reconstruct64_ilp4_abi_probe(abi_c, abi_planes, 1, 32 * sizeof(double))) {
        std::cerr << "SysV callee-saved register probe failed\n";
        return 1;
    }
    for (std::size_t stride : {32u, 40u, 136u, 264u, 1032u})
        for (std::size_t count : {1u, 2u, 4u, 8u, 12u, 21u}) {
            run(stride, count, Pattern::finite);
            run(stride, count, Pattern::specials);
        }
    std::cout << "direct ordered reconstruction probe passed\n";
}
