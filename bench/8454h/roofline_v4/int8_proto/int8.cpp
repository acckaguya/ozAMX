#include "int8.hpp"

#include "ozamx/gemm.hpp"

#include <algorithm>
#include <array>
#include <atomic>
#include <cerrno>
#include <chrono>
#include <cmath>
#include <cpuid.h>
#include <cstdint>
#include <cstddef>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <new>
#include <string>
#include <utility>

#if defined(_OPENMP)
#include <omp.h>
#endif

#if defined(__x86_64__)
#include <immintrin.h>
#endif

#ifndef OZAMX_I8_BM
#define OZAMX_I8_BM 128
#endif
#ifndef OZAMX_I8_BN
#define OZAMX_I8_BN 128
#endif
#ifndef OZAMX_I8_BK
#define OZAMX_I8_BK 256
#endif
#ifndef OZAMX_I8_TILELOAD_HINT
#define OZAMX_I8_TILELOAD_HINT 1
#endif

namespace ozamx_int8_36 {
namespace {

using Clock = std::chrono::steady_clock;
using i128 = __int128_t;
using u128 = __uint128_t;

static_assert(OZAMX_I8_BM == 64 || OZAMX_I8_BM == 128 || OZAMX_I8_BM == 256,
              "BM must be 64, 128, or 256");
static_assert(OZAMX_I8_BN == 64 || OZAMX_I8_BN == 128 || OZAMX_I8_BN == 256,
              "BN must be 64, 128, or 256");
static_assert(OZAMX_I8_BK == 64 || OZAMX_I8_BK == 128 ||
              OZAMX_I8_BK == 256 || OZAMX_I8_BK == 512,
              "BK must be 64, 128, 256, or 512");
static_assert(OZAMX_I8_BM % 32 == 0 && OZAMX_I8_BN % 32 == 0 &&
              OZAMX_I8_BK % 64 == 0, "AMX macroblocks have invalid alignment");

constexpr std::size_t kPanelBytes = 2048; // 32x64 A or 64x32 B bytes.
constexpr std::size_t kDigitSlices = 8;
constexpr std::size_t kMaxK = 32768;
constexpr std::size_t kMaxWorkers = 64;
constexpr std::size_t kWorkspaceLimitDefault = std::size_t(2) << 30;

[[noreturn]] void invalid(const char* message) {
    throw std::invalid_argument(message);
}

std::size_t checked_mul(std::size_t a, std::size_t b, const char* what) {
    if (b && a > std::numeric_limits<std::size_t>::max() / b)
        throw std::overflow_error(what);
    return a * b;
}

std::size_t checked_add(std::size_t a, std::size_t b, const char* what) {
    if (a > std::numeric_limits<std::size_t>::max() - b)
        throw std::overflow_error(what);
    return a + b;
}

std::size_t round_up(std::size_t value, std::size_t alignment) {
    const auto rem = value % alignment;
    return rem ? checked_add(value, alignment - rem, "round-up overflow") : value;
}

std::size_t matrix_bytes(std::size_t rows, std::size_t cols, std::size_t ld,
                         const void* ptr, const char* label) {
    if (!rows || !cols) return 0;
    const auto prefix = checked_mul(rows - 1, ld, "matrix address span overflow");
    const auto elements = checked_add(prefix, cols, "matrix address span overflow");
    const auto bytes = checked_mul(elements, sizeof(double), "matrix byte span overflow");
    const auto start = reinterpret_cast<std::uintptr_t>(ptr);
    if (bytes && start > std::numeric_limits<std::uintptr_t>::max() - (bytes - 1))
        throw std::overflow_error(std::string(label) + " address span wraps uintptr_t");
    return bytes;
}

std::size_t workspace_limit() noexcept {
    static const std::size_t cached = [] {
        const char* text = std::getenv("OZAMX_WORKSPACE_CACHE_BYTES");
        if (!text || !*text || *text == '-') return kWorkspaceLimitDefault;
        errno = 0;
        char* end = nullptr;
        const unsigned long long value = std::strtoull(text, &end, 10);
        if (errno || end == text || *end ||
            value > std::numeric_limits<std::size_t>::max())
            return kWorkspaceLimitDefault;
        return static_cast<std::size_t>(value);
    }();
    return cached;
}

struct WorkspacePool {
    struct Slot {
        void* ptr = nullptr;
        std::size_t bytes = 0;
        std::uint64_t age = 0;
    };
    std::array<Slot, 64> slots{};
    std::size_t retained = 0;
    std::uint64_t next_age = 1;

    ~WorkspacePool() {
        for (auto& slot : slots) std::free(slot.ptr);
    }

    void* acquire(std::size_t bytes) {
        Slot* best = nullptr;
        for (auto& slot : slots)
            if (slot.ptr && slot.bytes == bytes && (!best || slot.age > best->age))
                best = &slot;
        if (best) {
            void* ptr = best->ptr;
            retained -= best->bytes;
            *best = {};
            return ptr;
        }
        void* ptr = nullptr;
        if (posix_memalign(&ptr, 4096, bytes) != 0) throw std::bad_alloc();
        return ptr;
    }

    void release(void* ptr, std::size_t bytes) noexcept {
        if (!ptr) return;
        const auto limit = workspace_limit();
        if (bytes > limit) {
            std::free(ptr);
            return;
        }
        while (bytes > limit - retained) {
            Slot* oldest = nullptr;
            for (auto& slot : slots)
                if (slot.ptr && (!oldest || slot.age < oldest->age)) oldest = &slot;
            if (!oldest) break;
            retained -= oldest->bytes;
            std::free(oldest->ptr);
            *oldest = {};
        }
        Slot* empty = nullptr;
        for (auto& slot : slots)
            if (!slot.ptr) {
                empty = &slot;
                break;
            }
        if (!empty) {
            Slot* oldest = nullptr;
            for (auto& slot : slots)
                if (!oldest || slot.age < oldest->age) oldest = &slot;
            if (oldest) {
                retained -= oldest->bytes;
                std::free(oldest->ptr);
                empty = oldest;
                *empty = {};
            }
        }
        if (!empty) {
            std::free(ptr);
            return;
        }
        empty->ptr = ptr;
        empty->bytes = bytes;
        empty->age = next_age++;
        if (!next_age) next_age = 1;
        retained += bytes;
    }
};

WorkspacePool& workspace_pool() {
    thread_local WorkspacePool pool;
    return pool;
}

template<class T>
class Buffer {
public:
    Buffer() = default;
    explicit Buffer(std::size_t count, bool clear = false) { reset(count, clear); }
    ~Buffer() { workspace_pool().release(ptr_, bytes_); }
    Buffer(const Buffer&) = delete;
    Buffer& operator=(const Buffer&) = delete;
    Buffer(Buffer&& other) noexcept : ptr_(other.ptr_), count_(other.count_), bytes_(other.bytes_) {
        other.ptr_ = nullptr;
        other.count_ = 0;
        other.bytes_ = 0;
    }
    Buffer& operator=(Buffer&& other) noexcept {
        if (this != &other) {
            workspace_pool().release(ptr_, bytes_);
            ptr_ = other.ptr_;
            count_ = other.count_;
            bytes_ = other.bytes_;
            other.ptr_ = nullptr;
            other.count_ = 0;
            other.bytes_ = 0;
        }
        return *this;
    }
    void reset(std::size_t count, bool clear = false) {
        if (ptr_) workspace_pool().release(ptr_, bytes_);
        ptr_ = nullptr;
        count_ = count;
        bytes_ = checked_mul(count, sizeof(T), "workspace byte size overflow");
        if (!bytes_) return;
        ptr_ = static_cast<T*>(workspace_pool().acquire(bytes_));
        if (clear) std::memset(ptr_, 0, bytes_);
    }
    T* data() noexcept { return ptr_; }
    const T* data() const noexcept { return ptr_; }
    std::size_t size() const noexcept { return count_; }
private:
    T* ptr_ = nullptr;
    std::size_t count_ = 0;
    std::size_t bytes_ = 0;
};

struct MatrixShape {
    std::size_t mblocks;
    std::size_t nblocks;
    std::size_t k64blocks;
    std::size_t kpad;
};

class PackedInputs {
public:
    explicit PackedInputs(const MatrixShape& shape)
        : shape_(shape),
          a_(checked_mul(checked_mul(checked_mul(shape.mblocks, shape.k64blocks,
                                                "packed A size overflow"),
                                     kDigitSlices, "packed A size overflow"),
                         kPanelBytes, "packed A size overflow")),
          b_(checked_mul(checked_mul(checked_mul(shape.nblocks, shape.k64blocks,
                                                "packed B size overflow"),
                                     kDigitSlices, "packed B size overflow"),
                         kPanelBytes, "packed B size overflow")) {}

    std::int8_t* a_panel(std::size_t mblock, std::size_t k64block, int digit) {
        const auto index = ((mblock * shape_.k64blocks + k64block) * kDigitSlices +
                            static_cast<std::size_t>(digit)) * kPanelBytes;
        return a_.data() + index;
    }
    std::int8_t* b_panel(std::size_t nblock, std::size_t k64block, int digit) {
        const auto index = ((nblock * shape_.k64blocks + k64block) * kDigitSlices +
                            static_cast<std::size_t>(digit)) * kPanelBytes;
        return b_.data() + index;
    }
    const std::int8_t* a_panel(std::size_t mblock, std::size_t k64block, int digit) const {
        const auto index = ((mblock * shape_.k64blocks + k64block) * kDigitSlices +
                            static_cast<std::size_t>(digit)) * kPanelBytes;
        return a_.data() + index;
    }
    const std::int8_t* b_panel(std::size_t nblock, std::size_t k64block, int digit) const {
        const auto index = ((nblock * shape_.k64blocks + k64block) * kDigitSlices +
                            static_cast<std::size_t>(digit)) * kPanelBytes;
        return b_.data() + index;
    }
private:
    MatrixShape shape_;
    Buffer<std::int8_t> a_;
    Buffer<std::int8_t> b_;
};

struct OperandScale {
    double max_abs = 0.0;
    int exponent = 0;
};

constexpr double kMinInput = 0x1p-126;
constexpr double kMaxInput = (2.0 - 0x1p-7) * 0x1p127;

#if defined(__x86_64__)
#define OZAMX_AVX512_TARGET __attribute__((target("avx512f,avx512dq,avx512bw,avx512vl")))
#else
#define OZAMX_AVX512_TARGET
#endif

int threads_for_tasks(int requested, std::size_t tasks) {
#if defined(_OPENMP)
    const int available = std::max(1, omp_get_max_threads());
#else
    const int available = 1;
#endif
    const auto task_cap = tasks > static_cast<std::size_t>(std::numeric_limits<int>::max())
        ? std::numeric_limits<int>::max() : static_cast<int>(tasks);
    return std::max(1, std::min({requested, available, task_cap,
                                 static_cast<int>(kMaxWorkers)}));
}

OZAMX_AVX512_TARGET
OperandScale scan_operand(const double* matrix, std::size_t rows, std::size_t cols,
                          std::size_t ld, const char* label, int requested_threads) {
    std::array<double, kMaxWorkers> maxima{};
    std::array<int, kMaxWorkers> invalid_input{};
    const int threads = threads_for_tasks(requested_threads, rows);
#pragma omp parallel num_threads(threads) if(rows > 1)
    {
#if defined(_OPENMP)
        const std::size_t worker = static_cast<std::size_t>(omp_get_thread_num());
#else
        const std::size_t worker = 0;
#endif
        double local_max = 0.0;
        int local_bad = 0;
        __m512d max_vector = _mm512_setzero_pd();
        const __m512d minv = _mm512_set1_pd(kMinInput);
        const __m512d maxv = _mm512_set1_pd(kMaxInput);
#pragma omp for schedule(static)
        for (std::size_t row = 0; row < rows; ++row) {
            std::size_t col = 0;
            for (; col + 8 <= cols; col += 8) {
                const __m512d values = _mm512_loadu_pd(matrix + row * ld + col);
                const __m512d abs_values = _mm512_andnot_pd(_mm512_set1_pd(-0.0), values);
                const __mmask8 unordered = _mm512_cmp_pd_mask(values, values, _CMP_UNORD_Q);
                const __mmask8 nonzero = _mm512_cmp_pd_mask(abs_values, _mm512_setzero_pd(), _CMP_NEQ_OQ);
                const __mmask8 too_small = _mm512_cmp_pd_mask(abs_values, minv, _CMP_LT_OQ);
                const __mmask8 too_large = _mm512_cmp_pd_mask(abs_values, maxv, _CMP_GT_OQ);
                if (unordered || (nonzero & (too_small | too_large))) local_bad = 1;
                max_vector = _mm512_max_pd(max_vector, abs_values);
            }
#pragma omp simd reduction(max:local_max) reduction(|:local_bad)
            for (std::size_t tail = col; tail < cols; ++tail) {
                const double value = matrix[row * ld + tail];
                const double mag = std::abs(value);
                if (!std::isfinite(value) ||
                    (mag != 0.0 && (mag < kMinInput || mag > kMaxInput))) local_bad = 1;
                if (mag > local_max) local_max = mag;
            }
        }
        alignas(64) double lanes[8];
        _mm512_store_pd(lanes, max_vector);
        for (double value : lanes) if (value > local_max) local_max = value;
        maxima[worker] = local_max;
        invalid_input[worker] = local_bad;
    }
    OperandScale result;
    bool bad = false;
    for (int worker = 0; worker < threads; ++worker) {
        result.max_abs = std::max(result.max_abs, maxima[static_cast<std::size_t>(worker)]);
        bad = bad || invalid_input[static_cast<std::size_t>(worker)] != 0;
    }
    if (bad)
        throw std::invalid_argument(std::string(label) +
            " must contain only zero or finite values in the BF16-normal range");
    if (result.max_abs != 0.0) (void)std::frexp(result.max_abs, &result.exponent);
    return result;
}

std::int64_t round_rne_scaled(double value, int scale) {
    const double scaled = std::scalbn(value, scale);
    if (!std::isfinite(scaled) || std::abs(scaled) >= 0x1p55)
        throw std::invalid_argument("INT8-36 quantizer input is outside its proved range");
    const double floor_value = std::floor(scaled);
    const double fraction = scaled - floor_value;
    double rounded = floor_value;
    if (fraction > 0.5) rounded = floor_value + 1.0;
    else if (fraction == 0.5 && std::fmod(std::abs(floor_value), 2.0) == 1.0)
        rounded = floor_value + 1.0;
    return static_cast<std::int64_t>(rounded);
}

void balanced_digits_scalar(double value, int scale, std::int8_t (&digits)[8]) {
    std::int64_t quotient = round_rne_scaled(value, scale);
    std::int8_t low_first[7]{};
    for (int i = 0; i < 7; ++i) {
        std::int64_t remainder = quotient % 128;
        if (remainder < 0) remainder += 128; // Euclidean modulo.
        const std::int64_t digit = remainder >= 64 ? remainder - 128 : remainder;
        quotient = (quotient - digit) / 128;
        low_first[i] = static_cast<std::int8_t>(digit);
    }
    // The high digit has a wider positive endpoint (+64); only the seven
    // lower radix-128 digits use the symmetric balanced range [-64, 63].
    if (quotient < -64 || quotient > 64)
        throw std::invalid_argument("balanced radix-128 expansion exceeded top-digit range");
    digits[0] = static_cast<std::int8_t>(quotient);
    for (int i = 0; i < 7; ++i) digits[i + 1] = low_first[6 - i];
}

OZAMX_AVX512_TARGET
void balanced_digits8(const double* input, int scale, std::int8_t (&digits)[8][8]) {
    __m512d values = _mm512_loadu_pd(input);
    const __m512d scalev = _mm512_set1_pd(static_cast<double>(scale));
    __m512i quotient = _mm512_cvt_roundpd_epi64(
        _mm512_scalef_pd(values, scalev),
        _MM_FROUND_TO_NEAREST_INT | _MM_FROUND_NO_EXC);
    alignas(64) std::int64_t lanes[8];
    for (int step = 0; step < 7; ++step) {
        const __m512i shifted = _mm512_add_epi64(quotient, _mm512_set1_epi64(64));
        const __m512i remainder = _mm512_and_epi64(shifted, _mm512_set1_epi64(127));
        const __m512i digit = _mm512_sub_epi64(remainder, _mm512_set1_epi64(64));
        quotient = _mm512_srai_epi64(_mm512_sub_epi64(quotient, digit), 7);
        _mm512_store_si512(lanes, digit);
        for (int lane = 0; lane < 8; ++lane)
            digits[7 - step][lane] = static_cast<std::int8_t>(lanes[lane]);
    }
    const __mmask8 top_too_low = _mm512_cmp_epi64_mask(
        quotient, _mm512_set1_epi64(-64), _MM_CMPINT_LT);
    const __mmask8 top_too_high = _mm512_cmp_epi64_mask(
        quotient, _mm512_set1_epi64(64), _MM_CMPINT_GT);
    if (top_too_low | top_too_high)
        throw std::invalid_argument("balanced radix-128 expansion exceeded top-digit range");
    _mm512_store_si512(lanes, quotient);
    for (int lane = 0; lane < 8; ++lane)
        digits[0][lane] = static_cast<std::int8_t>(lanes[lane]);
}

void pack_a(const double* a, std::size_t m, std::size_t k, std::size_t lda,
            int scale, const MatrixShape& shape, PackedInputs& packed,
            int requested_threads) {
    const auto slab_bytes = checked_mul(checked_mul(shape.k64blocks, kDigitSlices,
                                                    "packed A slab overflow"),
                                        kPanelBytes, "packed A slab overflow");
    std::atomic<bool> bad_digits{false};
    const int threads = threads_for_tasks(requested_threads, shape.mblocks);
#pragma omp parallel for num_threads(threads) if(shape.mblocks > 1) schedule(static)
    for (std::size_t mblock = 0; mblock < shape.mblocks; ++mblock) {
        std::memset(packed.a_panel(mblock, 0, 0), 0, slab_bytes);
        const std::size_t row_begin = mblock * 32;
        const std::size_t row_end = std::min(m, row_begin + 32);
        for (std::size_t row = row_begin; row < row_end; ++row) {
            std::size_t kk = 0;
            for (; kk + 8 <= k; kk += 8) {
                std::int8_t digits[8][8];
                try { balanced_digits8(a + row * lda + kk, scale, digits); }
                catch (const std::exception&) { bad_digits.store(true, std::memory_order_relaxed); continue; }
                std::int8_t* panel_base[8];
                for (int digit = 0; digit < 8; ++digit)
                    panel_base[digit] = packed.a_panel(mblock, kk / 64, digit) +
                        (row % 32) * 64 + (kk % 64);
                for (int digit = 0; digit < 8; ++digit)
                    for (int lane = 0; lane < 8; ++lane)
                        panel_base[digit][lane] = digits[digit][lane];
            }
            for (; kk < k; ++kk) {
                std::int8_t digits[8];
                try { balanced_digits_scalar(a[row * lda + kk], scale, digits); }
                catch (const std::exception&) { bad_digits.store(true, std::memory_order_relaxed); continue; }
                for (int digit = 0; digit < 8; ++digit)
                    packed.a_panel(mblock, kk / 64, digit)
                        [(row % 32) * 64 + (kk % 64)] = digits[digit];
            }
        }
    }
    if (bad_digits.load(std::memory_order_relaxed))
        throw std::invalid_argument("INT8-36 A operand exceeded the proved balanced-digit range");
}

void pack_b(const double* b, std::size_t k, std::size_t n, std::size_t ldb,
            int scale, const MatrixShape& shape, PackedInputs& packed,
            int requested_threads) {
    std::atomic<bool> bad_digits{false};
    const int threads = threads_for_tasks(requested_threads, shape.nblocks);
#pragma omp parallel for num_threads(threads) if(shape.nblocks > 1) schedule(static)
    for (std::size_t nblock = 0; nblock < shape.nblocks; ++nblock) {
        const auto slab_bytes = checked_mul(checked_mul(shape.k64blocks, kDigitSlices,
                                                        "packed B slab overflow"),
                                            kPanelBytes, "packed B slab overflow");
        std::memset(packed.b_panel(nblock, 0, 0), 0, slab_bytes);
        const std::size_t col_begin = nblock * 32;
        const std::size_t col_end = std::min(n, col_begin + 32);
        for (std::size_t kk = 0; kk < k; ++kk) {
            std::size_t col = col_begin;
            for (; col + 8 <= col_end; col += 8) {
                std::int8_t digits[8][8];
                try { balanced_digits8(b + kk * ldb + col, scale, digits); }
                catch (const std::exception&) { bad_digits.store(true, std::memory_order_relaxed); continue; }
                for (int digit = 0; digit < 8; ++digit) {
                    auto* panel = packed.b_panel(nblock, kk / 64, digit);
                    for (int lane = 0; lane < 8; ++lane) {
                        const std::size_t nlocal = (col + lane) % 32;
                        const std::size_t klocal = kk % 64;
                        const std::size_t offset = (nlocal / 16) * 1024 +
                            (klocal / 4) * 64 + (nlocal % 16) * 4 + klocal % 4;
                        panel[offset] = digits[digit][lane];
                    }
                }
            }
            for (; col < col_end; ++col) {
                std::int8_t digits[8];
                try { balanced_digits_scalar(b[kk * ldb + col], scale, digits); }
                catch (const std::exception&) { bad_digits.store(true, std::memory_order_relaxed); continue; }
                for (int digit = 0; digit < 8; ++digit) {
                    const std::size_t nlocal = col % 32;
                    const std::size_t klocal = kk % 64;
                    const std::size_t offset = (nlocal / 16) * 1024 +
                        (klocal / 4) * 64 + (nlocal % 16) * 4 + klocal % 4;
                    packed.b_panel(nblock, kk / 64, digit)[offset] = digits[digit];
                }
            }
        }
    }
    if (bad_digits.load(std::memory_order_relaxed))
        throw std::invalid_argument("INT8-36 B operand exceeded the proved balanced-digit range");
}

bool cpu_has_amx_int8() {
    unsigned eax = 0, ebx = 0, ecx = 0, edx = 0;
    if (__get_cpuid_max(0, nullptr) < 7) return false;
    __get_cpuid_count(7, 0, &eax, &ebx, &ecx, &edx);
    constexpr unsigned amx_tile = 1u << 24;
    constexpr unsigned amx_int8 = 1u << 25;
    return (edx & (amx_tile | amx_int8)) == (amx_tile | amx_int8);
}

void require_amx_int8_and_permission() {
    if (!cpu_has_amx_int8())
        throw std::runtime_error("CPU does not report both AMX-TILE and AMX-INT8");
    const auto status = ozamx::request_amx_permission_for_current_thread();
    if (!status.permission_available)
        throw std::runtime_error("V3 runtime could not obtain AMX tile permission: " +
                                 status.message);
}

struct alignas(64) TileConfig {
    std::uint8_t palette = 1;
    std::uint8_t start_row = 0;
    std::uint8_t reserved0[14]{};
    std::uint16_t colsb[8]{64, 64, 64, 64, 64, 64, 64, 64};
    std::uint8_t reserved1[16]{};
    std::uint8_t rows[8]{16, 16, 16, 16, 16, 16, 16, 16};
    std::uint8_t reserved2[8]{};
};
static_assert(offsetof(TileConfig, colsb) == 16, "AMX colsb fields must begin at byte 16");
static_assert(offsetof(TileConfig, rows) == 48, "AMX rows fields must begin at byte 48");
static_assert(sizeof(TileConfig) == 64, "AMX tile config must occupy 64 bytes");

extern "C" void ozamx_i8_load_tile_config(const void*);
extern "C" void ozamx_i8_release_tiles();
extern "C" void ozamx_i8_diagonal(const std::int8_t* const*,
                                  const std::int8_t* const*, std::int32_t*,
                                  std::size_t, std::size_t, std::size_t,
                                  std::size_t);

class TileScope {
public:
    TileScope() { ozamx_i8_load_tile_config(&config_); }
    ~TileScope() { ozamx_i8_release_tiles(); }
private:
    TileConfig config_{};
};

double int128_to_double_rne(i128 value) {
    if (value == 0) return 0.0;
    const bool negative = value < 0;
    const u128 magnitude = negative
        ? static_cast<u128>(-(value + 1)) + 1
        : static_cast<u128>(value);
    const std::uint64_t high = static_cast<std::uint64_t>(magnitude >> 64);
    const std::uint64_t low = static_cast<std::uint64_t>(magnitude);
    const int bit_count = high ? 64 + (64 - __builtin_clzll(high))
                               : 64 - __builtin_clzll(low);
    int shift = std::max(0, bit_count - 53);
    u128 top = magnitude >> shift;
    if (shift) {
        const u128 mask = (static_cast<u128>(1) << shift) - 1;
        const u128 remainder = magnitude & mask;
        const u128 halfway = static_cast<u128>(1) << (shift - 1);
        if (remainder > halfway || (remainder == halfway && (top & 1))) ++top;
    }
    if (top == (static_cast<u128>(1) << 53)) {
        top >>= 1;
        ++shift;
    }
    double rounded = static_cast<double>(static_cast<std::uint64_t>(top));
    rounded = std::scalbn(rounded, shift);
    return negative ? -rounded : rounded;
}

struct PhaseResult {
    Timings timings;
};

PhaseResult execute(std::size_t m, std::size_t n, std::size_t k,
                    const double* a, std::size_t lda,
                    const double* b, std::size_t ldb,
                    double* c, std::size_t ldc, int requested_threads) {
    if (!m || !n) invalid("M and N must be positive");
    if (lda < k || ldb < n || ldc < n)
        invalid("row-major leading dimensions are too small");
    if (k > kMaxK) invalid("K exceeds the INT8-36 bound of 32768");
    if (requested_threads < 1) invalid("thread count must be positive");
    if (k && (!a || !b)) invalid("A or B pointer is null");
    if (!c) invalid("C pointer is null");
    if (k && (m % 32 || n % 32))
        invalid("the initial INT8-36 prototype requires M and N to be multiples of 32");

    matrix_bytes(m, k, lda, a, "A");
    matrix_bytes(k, n, ldb, b, "B");
    matrix_bytes(m, n, ldc, c, "C");
    const auto output_count = checked_mul(m, n, "output element count overflow");
    (void)checked_mul(output_count, sizeof(double), "output byte size overflow");

    PhaseResult result;
    if (k == 0) {
        Buffer<double> output(output_count);
        std::fill_n(output.data(), output_count, 0.0);
        for (std::size_t row = 0; row < m; ++row)
            std::memcpy(c + row * ldc, output.data() + row * n, n * sizeof(double));
        return result;
    }
    require_amx_int8_and_permission();

    auto phase_start = Clock::now();
    const OperandScale scale_a = scan_operand(a, m, k, lda, "A", requested_threads);
    const OperandScale scale_b = scan_operand(b, k, n, ldb, "B", requested_threads);
    result.timings.scan_seconds =
        std::chrono::duration<double>(Clock::now() - phase_start).count();

    Buffer<double> output(output_count);
    const auto kpad = round_up(k, 64);
    MatrixShape shape{m / 32, n / 32, kpad / 64, kpad};
    phase_start = Clock::now();
    PackedInputs packed(shape);
    pack_a(a, m, k, lda, 55 - scale_a.exponent, shape, packed, requested_threads);
    pack_b(b, k, n, ldb, 55 - scale_b.exponent, shape, packed, requested_threads);
    result.timings.pack_seconds =
        std::chrono::duration<double>(Clock::now() - phase_start).count();

    phase_start = Clock::now();
    const std::size_t row_stride_bytes = round_up(OZAMX_I8_BN * sizeof(std::int32_t), 64) + 64;
    const std::size_t plane_bytes = checked_add(
        checked_mul(OZAMX_I8_BM, row_stride_bytes, "C plane size overflow"),
        64, "C plane size overflow");
    const std::size_t all_planes_bytes =
        checked_mul(8, plane_bytes, "C plane bundle size overflow");
    const std::size_t plane_stride_words = row_stride_bytes / sizeof(std::int32_t);
    const std::size_t jobs_m = (m + OZAMX_I8_BM - 1) / OZAMX_I8_BM;
    const std::size_t jobs_n = (n + OZAMX_I8_BN - 1) / OZAMX_I8_BN;
    const std::size_t jobs = checked_mul(jobs_m, jobs_n, "output job count overflow");
    const int threads = threads_for_tasks(requested_threads, jobs);
    const std::size_t worker_stride = round_up(all_planes_bytes, 4096);
    Buffer<std::uint8_t> worker_scratch(
        checked_mul(static_cast<std::size_t>(threads), worker_stride,
                    "worker scratch bundle size overflow"));

    std::array<std::array<std::uint8_t, 8>, 8> pair_a{};
    std::array<std::array<std::uint8_t, 8>, 8> pair_b{};
    std::array<std::size_t, 8> pair_counts{};
    for (int i = 0; i < 8; ++i)
        for (int j = 0; i + j < 8; ++j) {
            const auto q = static_cast<std::size_t>(i + j);
            const auto slot = pair_counts[q]++;
            pair_a[q][slot] = static_cast<std::uint8_t>(i);
            pair_b[q][slot] = static_cast<std::uint8_t>(j);
        }

    const std::size_t k64_per_macro = OZAMX_I8_BK / 64;
    std::atomic<bool> bad_reconstruction{false};
#pragma omp parallel num_threads(threads) if(jobs > 1)
    {
    TileScope tile_scope;
#pragma omp for schedule(static)
    for (std::size_t job = 0; job < jobs; ++job) {
#if defined(_OPENMP)
        const int worker_index = omp_get_thread_num();
#else
        const int worker_index = 0;
#endif
        auto* scratch = worker_scratch.data() +
            static_cast<std::size_t>(worker_index) * worker_stride;
        std::array<const std::int8_t*, 8> a_pairs{};
        std::array<const std::int8_t*, 8> b_pairs{};
        const std::size_t mb = job / jobs_n;
        const std::size_t nb = job % jobs_n;
        const std::size_t mbase = mb * OZAMX_I8_BM;
        const std::size_t nbase = nb * OZAMX_I8_BN;
        const std::size_t msize = std::min<std::size_t>(OZAMX_I8_BM, m - mbase);
        const std::size_t nsize = std::min<std::size_t>(OZAMX_I8_BN, n - nbase);
        std::memset(scratch, 0, all_planes_bytes);

        for (std::size_t kb = 0; kb < shape.k64blocks; kb += k64_per_macro) {
            const std::size_t steps = std::min(k64_per_macro, shape.k64blocks - kb);
            for (std::size_t q = 0; q < 8; ++q) {
                for (std::size_t mi = 0; mi < msize; mi += 32)
                    for (std::size_t ni = 0; ni < nsize; ni += 32) {
                        auto* plane = reinterpret_cast<std::int32_t*>(
                            scratch + q * plane_bytes);
                        auto* c_tile = plane + mi * plane_stride_words + ni;
                        auto* ap = a_pairs.data();
                        auto* bp = b_pairs.data();
                        for (std::size_t p = 0; p < pair_counts[q]; ++p) {
                            ap[p] = packed.a_panel(mbase / 32 + mi / 32, kb,
                                                   pair_a[q][p]);
                            bp[p] = packed.b_panel(nbase / 32 + ni / 32, kb,
                                                   pair_b[q][p]);
                        }
                        ozamx_i8_diagonal(ap, bp, c_tile, row_stride_bytes,
                                          8 * kPanelBytes, steps, pair_counts[q]);
                    }
            }
        }

        for (std::size_t mi = 0; mi < msize; ++mi)
            for (std::size_t ni = 0; ni < nsize; ++ni) {
                i128 weighted = 0;
                for (int q = 0; q < 8; ++q) {
                    const auto* plane = reinterpret_cast<const std::int32_t*>(
                        scratch + static_cast<std::size_t>(q) * plane_bytes);
                    const i128 weight = static_cast<i128>(1) << (7 * (14 - q));
                    weighted += static_cast<i128>(
                        plane[mi * plane_stride_words + ni]) * weight;
                }
                const double rounded_integer = int128_to_double_rne(weighted);
                const double value = std::scalbn(
                    rounded_integer, scale_a.exponent + scale_b.exponent - 110);
                if (!std::isfinite(value) ||
                    (value != 0.0 && std::fpclassify(value) != FP_NORMAL)) {
                    bad_reconstruction.store(true, std::memory_order_relaxed);
                } else {
                    output.data()[(mbase + mi) * n + nbase + ni] = value;
                }
            }
    }
    }
    if (bad_reconstruction.load(std::memory_order_relaxed))
        throw std::runtime_error(
            "INT8-36 reconstruction left the proved finite-normal FP64 range");
    result.timings.compute_reconstruct_seconds =
        std::chrono::duration<double>(Clock::now() - phase_start).count();

    // Every input has been packed and every result reconstructed before C is
    // touched. This also makes C/A and C/B overlap well-defined.
    for (std::size_t row = 0; row < m; ++row)
        std::memcpy(c + row * ldc, output.data() + row * n, n * sizeof(double));
    return result;
}

} // namespace

Timings gemm_fp64_int8_36_profiled(
    std::size_t m, std::size_t n, std::size_t k,
    const double* a, std::size_t lda,
    const double* b, std::size_t ldb,
    double* c, std::size_t ldc, int threads) {
    const auto start = Clock::now();
    PhaseResult result = execute(m, n, k, a, lda, b, ldb, c, ldc, threads);
    // execute's buffers have been released to the workspace pool before this
    // point, so total time includes both allocation and cleanup/cache handling.
    result.timings.total_seconds =
        std::chrono::duration<double>(Clock::now() - start).count();
    return result.timings;
}

} // namespace ozamx_int8_36
