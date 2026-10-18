#pragma once

#include "ozamx/gemm.hpp"
#include "tuning.hpp"

#include <algorithm>
#include <array>
#include <cerrno>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <new>
#include <type_traits>

#if defined(__AVX512F__)
#include <immintrin.h>
#endif
#ifdef _OPENMP
#include <omp.h>
#endif

namespace ozamx::detail {

constexpr std::size_t PP_BM = 256, PP_BN = 256, PP_BK = 256;

struct WorkspacePool {
    struct Slot {
        void* ptr = nullptr;
        std::size_t bytes = 0;
        std::uint64_t age = 0;
    };
    std::array<Slot, 64> slots{};
    std::size_t retained = 0;
    std::uint64_t next_age = 1;
    WorkspacePool() = default;
    WorkspacePool(const WorkspacePool&) = delete;
    WorkspacePool& operator=(const WorkspacePool&) = delete;
    ~WorkspacePool() {
        for (auto& s : slots)
            std::free(s.ptr);
    }
    static std::size_t limit() noexcept {
        static const std::size_t value = []() noexcept {
            // This cap is per calling thread's retained cache; it is not a
            // process-wide limit or a promise about resident-set size.
            constexpr std::size_t default_limit = std::size_t(2) << 30;
            const char* text = std::getenv("OZAMX_WORKSPACE_CACHE_BYTES");
            if (!text || !*text)
                return default_limit;
            if (*text == '-')
                return default_limit;
            errno = 0;
            char* end = nullptr;
            unsigned long long v = std::strtoull(text, &end, 10);
            if (errno || end == text || *end || v > std::numeric_limits<std::size_t>::max())
                return default_limit;
            return std::size_t(v);
        }();
        return value;
    }
    void* acquire(std::size_t bytes) {
        if (!bytes)
            return nullptr;
        Slot* newest = nullptr;
        for (auto& s : slots)
            if (s.ptr && s.bytes == bytes && (!newest || s.age > newest->age))
                newest = &s;
        if (newest) {
            void* p = newest->ptr;
            retained -= newest->bytes;
            *newest = {};
            return p;
        }
        void* p = nullptr;
        if (posix_memalign(&p, 64, bytes) != 0)
            throw std::bad_alloc();
        return p;
    }
    void release(void* p, std::size_t bytes) noexcept {
        if (!p)
            return;
        const auto cap = limit();
        if (bytes > cap) {
            std::free(p);
            return;
        }
        while (bytes > cap - retained) {
            Slot* oldest = nullptr;
            for (auto& s : slots)
                if (s.ptr && (!oldest || s.age < oldest->age))
                    oldest = &s;
            if (!oldest)
                break;
            retained -= oldest->bytes;
            std::free(oldest->ptr);
            *oldest = {};
        }
        Slot* empty = nullptr;
        for (auto& s : slots)
            if (!s.ptr) {
                empty = &s;
                break;
            }
        while (!empty) {
            Slot* oldest = nullptr;
            for (auto& s : slots)
                if (s.ptr && (!oldest || s.age < oldest->age))
                    oldest = &s;
            if (!oldest)
                break;
            retained -= oldest->bytes;
            std::free(oldest->ptr);
            *oldest = {};
            empty = oldest;
        }
        if (empty) {
            empty->ptr = p;
            empty->bytes = bytes;
            empty->age = next_age++;
            if (!next_age)
                next_age = 1;
            retained += bytes;
            return;
        }
        std::free(p);
    }
};
inline WorkspacePool& workspace_pool() {
    thread_local WorkspacePool pool;
    return pool;
}

template <class T> class AlignedBuffer {
    static_assert(std::is_trivially_destructible<T>::value, "buffer elements must be trivial");
    T* ptr_ = nullptr;
    std::size_t size_ = 0;

  public:
    AlignedBuffer() noexcept = default;
    explicit AlignedBuffer(std::size_t n) : size_(n) {
        if (!n)
            return;
        if (n > std::numeric_limits<std::size_t>::max() / sizeof(T))
            throw Error("matrix size overflow");
        ptr_ = static_cast<T*>(workspace_pool().acquire(n * sizeof(T)));
    }
    ~AlignedBuffer() {
        workspace_pool().release(ptr_, size_ * sizeof(T));
    }
    AlignedBuffer(const AlignedBuffer&) = delete;
    AlignedBuffer& operator=(const AlignedBuffer&) = delete;
    AlignedBuffer(AlignedBuffer&& o) noexcept : ptr_(o.ptr_), size_(o.size_) {
        o.ptr_ = nullptr;
        o.size_ = 0;
    }
    AlignedBuffer& operator=(AlignedBuffer&& o) noexcept {
        if (this != &o) {
            workspace_pool().release(ptr_, size_ * sizeof(T));
            ptr_ = o.ptr_;
            size_ = o.size_;
            o.ptr_ = nullptr;
            o.size_ = 0;
        }
        return *this;
    }
    T* data() noexcept {
        return ptr_;
    }
    const T* data() const noexcept {
        return ptr_;
    }
    std::size_t size() const noexcept {
        return size_;
    }
    T& operator[](std::size_t i) noexcept {
        return ptr_[i];
    }
    const T& operator[](std::size_t i) const noexcept {
        return ptr_[i];
    }
};

inline std::size_t mul(std::size_t a, std::size_t b) {
    if (b && a > std::numeric_limits<std::size_t>::max() / b)
        throw Error("matrix size overflow");
    return a * b;
}
inline std::size_t divup(std::size_t a, std::size_t b) {
    return a / b + (a % b != 0);
}
inline int team_size(int requested, std::size_t work) {
    return std::max(1, std::min(requested, work > std::size_t(std::numeric_limits<int>::max())
                                               ? std::numeric_limits<int>::max()
                                               : int(work)));
}
// Experimental scheduling only: each stage supplies its own independent panel
// count. The default keeps the strict-emulation path's requested team, including idle work.
inline int strict_team_size(int requested, std::size_t tasks) {
    return tuning::research_task_teams ? team_size(requested, tasks) : requested;
}
struct Slices {
    AlignedBuffer<std::uint16_t> data;
    std::size_t count = 0;
    int slices = 0;
    const std::uint16_t* plane(int s) const {
        return data.data() + std::size_t(s) * count;
    }
    std::uint16_t* plane(int s) {
        return data.data() + std::size_t(s) * count;
    }
};
struct Packed {
    std::array<AlignedBuffer<std::uint16_t>, 6> a, b;
    std::size_t mblocks = 0, nblocks = 0, kblocks = 0;
    int slices = 0;
};

inline std::uint32_t fbits(float x) {
    std::uint32_t u;
    std::memcpy(&u, &x, 4);
    return u;
}
inline float frombits(std::uint32_t u) {
    float x;
    std::memcpy(&x, &u, 4);
    return x;
}
inline float bf_float(std::uint16_t h) {
    return frombits(std::uint32_t(h) << 16);
}
inline bool to_bf(float x, std::uint16_t& out) {
    // Round FP32 to BF16 with ties to even. Reject non-finite values and
    // nonzero FP32 subnormals before rounding; a rounded BF16 subnormal is
    // rejected too, matching the normal-value range supported by the kernels.
    std::uint32_t u = fbits(x), e = (u >> 23) & 255;
    if (e == 255 || ((u & 0x7fffffff) != 0 && e == 0))
        return false;
    u += 0x7fff + ((u >> 16) & 1);
    auto h = std::uint16_t(u >> 16);
    auto he = (h >> 7) & 255;
    if (he == 255 || ((h & 0x7fff) != 0 && he == 0))
        return false;
    out = h;
    return true;
}
inline bool valid_shape(const void* p, std::size_t rows, std::size_t cols, std::size_t ld) {
    if ((rows && cols && !p) || ld < cols)
        return false;
    if (rows && cols) {
        auto max = std::numeric_limits<std::size_t>::max();
        if ((rows - 1) > max / ld)
            return false;
        return (rows - 1) * ld <= max - cols;
    }
    return true;
}

// One static task is either one SIMD chunk (adaptive path) or a complete
// 256x256 input panel (strict-emulation path). The numeric body is shared; in particular
// panel scheduling never changes the FP64 global maximum or shift scope.
struct MatrixTraversal {
    struct Region { std::size_t row, row_end, col, col_end; };
    std::size_t rows, cols, lanes;
    bool panels;
    std::size_t tasks() const {
        return panels ? mul(divup(rows, PP_BM), divup(cols, PP_BK))
                      : mul(rows, divup(cols, lanes));
    }
    Region region(std::size_t task) const {
        if (panels) {
            const auto nc = divup(cols, PP_BK);
            const auto row = task / nc * PP_BM, col = task % nc * PP_BK;
            return {row, row + std::min(PP_BM, rows-row), col,
                    col + std::min(PP_BK, cols-col)};
        }
        const auto nc = divup(cols, lanes);
        const auto row = task/nc, col = task%nc*lanes;
        return {row, row+1, col, col+std::min(lanes, cols-col)};
    }
};

// Shared numeric loop for the FP32 split. split_fp32 drives it from its own
// parallel region; split_fp32_pair drives the A and B calls from one region
// (OZAMX_PREP_SINGLE_REGION). The worksharing construct is deliberately
// orphaned: callers must invoke this from inside an OpenMP parallel region.
inline void split_fp32_loop(const float* src, std::size_t cols, std::size_t ld,
                            const MatrixTraversal& traversal, Slices& out, int& bad) {
    const auto chunks = traversal.tasks();
#if defined(__AVX512BW__)
#pragma omp for schedule(static) reduction(| : bad)
    for (std::size_t u = 0; u < chunks; ++u) {
        const auto region = traversal.region(u);
        for (auto row = region.row; row < region.row_end; ++row)
            for (auto col = region.col; col < region.col_end; col += 16) {
                const auto q = row * cols + col;
                int lanes = int(std::min<std::size_t>(16, cols - col));
                __mmask16 mask = lanes == 16 ? __mmask16(0xffff) : __mmask16((1u << lanes) - 1);
                __m512 r = _mm512_maskz_loadu_ps(mask, src + row * ld + col);
                for (int s = 0; s < 3; ++s) {
                    __m512i u = _mm512_castps_si512(r),
                            e = _mm512_and_si512(_mm512_srli_epi32(u, 23), _mm512_set1_epi32(255));
                    __m512i mag = _mm512_and_si512(u, _mm512_set1_epi32(0x7fffffff));
                    __mmask16 invalid = _mm512_cmpeq_epi32_mask(e, _mm512_set1_epi32(255));
                    __mmask16 sub = _mm512_cmpeq_epi32_mask(e, _mm512_setzero_si512()) &
                                    _mm512_cmpneq_epi32_mask(mag, _mm512_setzero_si512());
                    invalid |= sub;
                    __m512i rounded = _mm512_add_epi32(
                        u,
                        _mm512_add_epi32(_mm512_set1_epi32(0x7fff),
                                         _mm512_and_si512(_mm512_srli_epi32(u, 16), _mm512_set1_epi32(1))));
                    __m512i h = _mm512_srli_epi32(rounded, 16),
                            he = _mm512_and_si512(_mm512_srli_epi32(h, 7), _mm512_set1_epi32(255));
                    invalid |= _mm512_cmpeq_epi32_mask(he, _mm512_set1_epi32(255));
                    invalid |= _mm512_cmpneq_epi32_mask(_mm512_and_si512(h, _mm512_set1_epi32(0x7fff)),
                                                        _mm512_setzero_si512()) &
                               _mm512_cmpeq_epi32_mask(he, _mm512_setzero_si512());
                    if (invalid)
                        bad = 1;
                    h = _mm512_maskz_mov_epi32(__mmask16(~invalid), h);
                    __m256i narrow = _mm512_cvtepi32_epi16(h);
                    _mm256_mask_storeu_epi16(out.plane(s) + q, mask, narrow);
                    __m512 bh = _mm512_castsi512_ps(_mm512_slli_epi32(h, 16));
                    __m512 safe_r = _mm512_maskz_mov_ps(__mmask16(~invalid), r);
                    r = _mm512_sub_ps(safe_r, bh);
                    auto ru = _mm512_castps_si512(r);
                    __m512i re = _mm512_and_si512(_mm512_srli_epi32(ru, 23), _mm512_set1_epi32(255)),
                            rm = _mm512_and_si512(ru, _mm512_set1_epi32(0x7fffffff));
                    __mmask16 nonzero = _mm512_cmpneq_epi32_mask(rm, _mm512_setzero_si512());
                    __mmask16 nonnormal = _mm512_cmpeq_epi32_mask(re, _mm512_setzero_si512()) |
                                          _mm512_cmpeq_epi32_mask(re, _mm512_set1_epi32(255));
                    if (nonzero & nonnormal)
                        bad = 1;
                }
            }
    }
#else
    (void)chunks;
#pragma omp for schedule(static) reduction(| : bad)
    for (std::size_t tail = 0; tail < out.count; ++tail) {
        std::size_t i = tail / cols, j = tail % cols;
        float r = src[i * ld + j];
        // Each slice stores the rounded high part; the next slice encodes the
        // FP32 residual. Nonzero subnormal residuals are unsupported (FTZ edge).
        for (int s = 0; s < 3; ++s) {
            std::uint16_t h;
            if (!to_bf(r, h)) {
                bad = 1;
                break;
            }
            out.plane(s)[tail] = h;
            r = float(r - bf_float(h));
            if (!std::isfinite(r) || (r != 0 && !std::isnormal(r))) {
                bad = 1;
                break;
            }
        }
    }
#endif
}

inline Slices split_fp32(const float* src, std::size_t rows, std::size_t cols, std::size_t ld,
                         int threads, bool panel_static = false) {
    if (threads < 1 || !valid_shape(src, rows, cols, ld))
        throw Error("invalid FP32 input shape");
    Slices out;
    out.count = mul(rows, cols);
    out.slices = 3;
    out.data = AlignedBuffer<std::uint16_t>(mul(out.count, 3));
    int bad = 0;
    const MatrixTraversal traversal{rows, cols, 16, panel_static};
    const auto chunks = traversal.tasks();
    const int nt = panel_static ? strict_team_size(threads, chunks) : team_size(threads, chunks);
#if defined(__AVX512BW__)
#pragma omp parallel num_threads(nt) if (chunks > 1)
    {
        split_fp32_loop(src, cols, ld, traversal, out, bad);
    }
#else
    (void)chunks;
#pragma omp parallel num_threads(nt) if (out.count > 16384)
    {
        split_fp32_loop(src, cols, ld, traversal, out, bad);
    }
#endif
    if (bad)
        throw Error("FP32 input/residual is non-finite or outside the supported normal range");
    return out;
}

#if OZAMX_PREP_SINGLE_REGION
// R1a: both FP32 splits share one parallel region. Each worksharing loop keeps
// the singleton's schedule(static) iteration space, so the static partition,
// the written bytes and the accept/reject behavior are unchanged.
inline void split_fp32_pair(const float* a, std::size_t arows, std::size_t acols, std::size_t lda,
                            const float* b, std::size_t brows, std::size_t bcols, std::size_t ldb,
                            int threads, bool panel_static, Slices& sa, Slices& sb) {
    if (threads < 1 || !valid_shape(a, arows, acols, lda) || !valid_shape(b, brows, bcols, ldb))
        throw Error("invalid FP32 input shape");
    sa.count = mul(arows, acols);
    sa.slices = 3;
    sa.data = AlignedBuffer<std::uint16_t>(mul(sa.count, 3));
    sb.count = mul(brows, bcols);
    sb.slices = 3;
    sb.data = AlignedBuffer<std::uint16_t>(mul(sb.count, 3));
    int bad_a = 0, bad_b = 0;
    const MatrixTraversal ta{arows, acols, 16, panel_static};
    const MatrixTraversal tb{brows, bcols, 16, panel_static};
    const auto chunks_a = ta.tasks(), chunks_b = tb.tasks();
    const int nta = panel_static ? strict_team_size(threads, chunks_a) : team_size(threads, chunks_a);
    const int ntb = panel_static ? strict_team_size(threads, chunks_b) : team_size(threads, chunks_b);
    const int nt = std::max(nta, ntb);
#if defined(__AVX512BW__)
#pragma omp parallel num_threads(nt) if (chunks_a > 1 || chunks_b > 1)
    {
        split_fp32_loop(a, acols, lda, ta, sa, bad_a);
        split_fp32_loop(b, bcols, ldb, tb, sb, bad_b);
    }
#else
    (void)chunks_a;
    (void)chunks_b;
#pragma omp parallel num_threads(nt) if (sa.count > 16384 || sb.count > 16384)
    {
        split_fp32_loop(a, acols, lda, ta, sa, bad_a);
        split_fp32_loop(b, bcols, ldb, tb, sb, bad_b);
    }
#endif
    if (bad_a || bad_b)
        throw Error("FP32 input/residual is non-finite or outside the supported normal range");
}
#endif

// Large aligned FP32 inputs generate BF16 directly in the AMX panel layout.
// Shared numeric loop for the fused FP32 direct writer, driven by an enclosing
// parallel region (see split_direct32 / split_direct32_pair).
inline void split_direct32_loop(const float* src, std::size_t rows, std::size_t cols,
                                std::size_t ld, std::array<AlignedBuffer<std::uint16_t>, 6>& output,
                                bool is_a, std::size_t panel_columns, int& bad) {
    const auto chunks = mul(rows, divup(cols, 16));
#if defined(__AVX512BW__)
#pragma omp for schedule(static) reduction(| : bad)
    for (std::size_t u = 0; u < chunks; ++u) {
        std::size_t row = u / divup(cols, 16), col = (u % divup(cols, 16)) * 16;
        int lanes = int(std::min<std::size_t>(16, cols - col));
        __mmask16 mask = lanes == 16 ? __mmask16(0xffff) : __mmask16((1u << lanes) - 1);
        __m512 r = _mm512_maskz_loadu_ps(mask, src + row * ld + col);
        for (int s = 0; s < 3; ++s) {
            __m512i u = _mm512_castps_si512(r),
                    e = _mm512_and_si512(_mm512_srli_epi32(u, 23), _mm512_set1_epi32(255));
            __m512i mag = _mm512_and_si512(u, _mm512_set1_epi32(0x7fffffff));
            __mmask16 invalid = _mm512_cmpeq_epi32_mask(e, _mm512_set1_epi32(255));
            __mmask16 sub = _mm512_cmpeq_epi32_mask(e, _mm512_setzero_si512()) &
                            _mm512_cmpneq_epi32_mask(mag, _mm512_setzero_si512());
            invalid |= sub;
            __m512i rounded = _mm512_add_epi32(
                u,
                _mm512_add_epi32(_mm512_set1_epi32(0x7fff),
                                 _mm512_and_si512(_mm512_srli_epi32(u, 16), _mm512_set1_epi32(1))));
            __m512i h = _mm512_srli_epi32(rounded, 16),
                    he = _mm512_and_si512(_mm512_srli_epi32(h, 7), _mm512_set1_epi32(255));
            invalid |= _mm512_cmpeq_epi32_mask(he, _mm512_set1_epi32(255));
            invalid |= _mm512_cmpneq_epi32_mask(_mm512_and_si512(h, _mm512_set1_epi32(0x7fff)),
                                                _mm512_setzero_si512()) &
                       _mm512_cmpeq_epi32_mask(he, _mm512_setzero_si512());
            if (invalid)
                bad = 1;
            h = _mm512_maskz_mov_epi32(__mmask16(~invalid), h);
            __m256i narrow = _mm512_cvtepi32_epi16(h);
            const auto i = row % 256, j = col % 256;
            auto* panel = output[s].data() + (row / 256 * panel_columns + col / 256) * 65536;
            if (is_a) {
                const auto dst = (i / 32) * 8192 + (j / 32) * 1024 + ((i % 32) / 16) * 512 +
                                 (i % 16) * 32 + j % 32;
                _mm256_storeu_si256(reinterpret_cast<__m256i*>(panel + dst), narrow);
            } else {
                const auto kp = i / 2, dst = (j / 32) * 8192 + (kp / 16) * 1024 +
                                             ((j % 32) / 16) * 512 + (kp % 16) * 32 + (j % 16) * 2;
                __m512i paired = _mm512_cvtepu16_epi32(narrow);
                if (i & 1) {
                    paired = _mm512_slli_epi32(paired, 16);
                    _mm512_mask_storeu_epi16(panel + dst, __mmask32(0xaaaaaaaa), paired);
                } else
                    _mm512_mask_storeu_epi16(panel + dst, __mmask32(0x55555555), paired);
            }
            __m512 bh = _mm512_castsi512_ps(_mm512_slli_epi32(h, 16));
            __m512 safe_r = _mm512_maskz_mov_ps(__mmask16(~invalid), r);
            r = _mm512_sub_ps(safe_r, bh);
            auto ru = _mm512_castps_si512(r);
            __m512i re = _mm512_and_si512(_mm512_srli_epi32(ru, 23), _mm512_set1_epi32(255)),
                    rm = _mm512_and_si512(ru, _mm512_set1_epi32(0x7fffffff));
            __mmask16 nonzero = _mm512_cmpneq_epi32_mask(rm, _mm512_setzero_si512());
            __mmask16 nonnormal = _mm512_cmpeq_epi32_mask(re, _mm512_setzero_si512()) |
                                  _mm512_cmpeq_epi32_mask(re, _mm512_set1_epi32(255));
            if (nonzero & nonnormal)
                bad = 1;
        }
    }
#else
    (void)chunks;
    const auto count = mul(rows, cols);
#pragma omp for schedule(static) reduction(| : bad)
    for (std::size_t tail = 0; tail < count; ++tail) {
        std::size_t i = tail / cols, j = tail % cols;
        float r = src[i * ld + j];
        for (int s = 0; s < 3; ++s) {
            std::uint16_t h;
            if (!to_bf(r, h)) {
                bad = 1;
                break;
            }
            const auto row = i, col = j, ri = row % 256, cj = col % 256;
            const auto dst =
                is_a ? ((ri / 32) * 8192 + (cj / 32) * 1024 + ((ri % 32) / 16) * 512 +
                        (ri % 16) * 32 + cj % 32)
                     : ((cj / 32) * 8192 + ((ri / 2) / 16) * 1024 + ((cj % 32) / 16) * 512 +
                        ((ri / 2) % 16) * 32 + (cj % 16) * 2 + ri % 2);
            output[s][(row / 256 * panel_columns + col / 256) * 65536 + dst] = h;
            r = float(r - bf_float(h));
            if (!std::isfinite(r) || (r != 0 && !std::isnormal(r))) {
                bad = 1;
                break;
            }
        }
    }
#endif
}

inline void split_direct32(const float* src, std::size_t rows, std::size_t cols, std::size_t ld,
                           int threads, std::array<AlignedBuffer<std::uint16_t>, 6>& output,
                           bool is_a, std::size_t panel_columns) {
    if (threads < 1 || rows % 256 || cols % 256 || !valid_shape(src, rows, cols, ld))
        throw Error("invalid direct FP32 input shape");
    const auto count = mul(rows, cols);
    for (int s = 0; s < 3; ++s)
        output[s] = AlignedBuffer<std::uint16_t>(count);
    int bad = 0;
    const auto chunks = mul(rows, divup(cols, 16));
    const int nt = team_size(threads, chunks);
#if defined(__AVX512BW__)
#pragma omp parallel num_threads(nt) if (chunks > 1)
    {
        split_direct32_loop(src, rows, cols, ld, output, is_a, panel_columns, bad);
    }
#else
    (void)chunks;
#pragma omp parallel num_threads(nt) if (count > 16384)
    {
        split_direct32_loop(src, rows, cols, ld, output, is_a, panel_columns, bad);
    }
#endif
    if (bad)
        throw Error("FP32 input/residual is non-finite or outside the supported normal range");
}

#if OZAMX_PREP_SINGLE_REGION
// R1a: one parallel region drives the A and B direct-writer loops. Every
// iteration writes a disjoint panel chunk, and each loop keeps the singleton's
// schedule(static) iteration space, so panels stay byte-identical.
inline void split_direct32_pair(const float* a, std::size_t arows, std::size_t acols, std::size_t lda,
                                const float* b, std::size_t brows, std::size_t bcols, std::size_t ldb,
                                int threads, std::array<AlignedBuffer<std::uint16_t>, 6>& out_a,
                                bool a_is_a, std::size_t a_panels,
                                std::array<AlignedBuffer<std::uint16_t>, 6>& out_b,
                                bool b_is_a, std::size_t b_panels) {
    if (threads < 1 || arows % 256 || acols % 256 || !valid_shape(a, arows, acols, lda) ||
        brows % 256 || bcols % 256 || !valid_shape(b, brows, bcols, ldb))
        throw Error("invalid direct FP32 input shape");
    const auto count_a = mul(arows, acols), count_b = mul(brows, bcols);
    for (int s = 0; s < 3; ++s)
        out_a[s] = AlignedBuffer<std::uint16_t>(count_a);
    for (int s = 0; s < 3; ++s)
        out_b[s] = AlignedBuffer<std::uint16_t>(count_b);
    int bad_a = 0, bad_b = 0;
    const auto chunks_a = mul(arows, divup(acols, 16)), chunks_b = mul(brows, divup(bcols, 16));
    const int nt = std::max(team_size(threads, chunks_a), team_size(threads, chunks_b));
#if defined(__AVX512BW__)
#pragma omp parallel num_threads(nt) if (chunks_a > 1 || chunks_b > 1)
    {
        split_direct32_loop(a, arows, acols, lda, out_a, a_is_a, a_panels, bad_a);
        split_direct32_loop(b, brows, bcols, ldb, out_b, b_is_a, b_panels, bad_b);
    }
#else
    (void)chunks_a;
    (void)chunks_b;
#pragma omp parallel num_threads(nt) if (count_a > 16384 || count_b > 16384)
    {
        split_direct32_loop(a, arows, acols, lda, out_a, a_is_a, a_panels, bad_a);
        split_direct32_loop(b, brows, bcols, ldb, out_b, b_is_a, b_panels, bad_b);
    }
#endif
    if (bad_a || bad_b)
        throw Error("FP32 input/residual is non-finite or outside the supported normal range");
}
#endif

inline Packed split_pack_direct32(const float* a, const float* b, std::size_t m, std::size_t n,
                                  std::size_t k, std::size_t lda, std::size_t ldb, int threads) {
    Packed p;
    p.slices = 3;
    p.mblocks = m / 256;
    p.nblocks = n / 256;
    p.kblocks = k / 256;
#if OZAMX_PREP_SINGLE_REGION
    split_direct32_pair(a, m, k, lda, b, k, n, ldb, threads, p.a, true, p.kblocks, p.b, false,
                        p.nblocks);
#else
    split_direct32(a, m, k, lda, threads, p.a, true, p.kblocks);
    split_direct32(b, k, n, ldb, threads, p.b, false, p.nblocks);
#endif
    return p;
}

inline constexpr double FP64_MIN_NORMAL = 0x1p-126;
inline constexpr double FP64_MAX_BF16 = (2.0 - 0x1p-7) * 0x1p127;
inline int ceil_log2(double x) {
    int e = 0;
    double f = std::frexp(x, &e);
    return f == 0.5 ? e - 1 : e;
}
inline Slices split_fp64(const double* src, std::size_t rows, std::size_t cols, std::size_t ld,
                         int threads, int stored_slices = 6, bool panel_static = false) {
    if (threads < 1 || stored_slices < 1 || stored_slices > 6 || !valid_shape(src, rows, cols, ld))
        throw Error("invalid FP64 input shape");
    Slices out;
    out.count = mul(rows, cols);
    out.slices = stored_slices;
    out.data = AlignedBuffer<std::uint16_t>(mul(out.count, std::size_t(stored_slices)));
    AlignedBuffer<double> residual(out.count);
    int bad = 0, input_bad = 0;
    auto n = out.count;
    const MatrixTraversal traversal{rows, cols, 8, panel_static};
    const auto chunks = traversal.tasks();
    int nt = panel_static ? strict_team_size(threads, chunks) : team_size(threads, divup(n, 8));
    double sigma = 0, global_max = 0;
    int whole_zero = 0;
#pragma omp parallel num_threads(nt) if (n > 8192)                                                 \
    shared(bad, input_bad, sigma, whole_zero, global_max)
    {
#if defined(__AVX512F__)
#pragma omp for schedule(static) reduction(| : input_bad)
        for (std::size_t u = 0; u < chunks; ++u) {
            const auto region = traversal.region(u);
            for (auto i = region.row; i < region.row_end; ++i)
                for (auto j = region.col; j < region.col_end; j += 8) {
                    const auto q = i * cols + j;
                    int lanes = int(std::min<std::size_t>(8, cols - j));
                    __mmask8 mask = lanes == 8 ? __mmask8(255) : __mmask8((1u << lanes) - 1);
                    __m512d x = _mm512_maskz_loadu_pd(mask, src + i * ld + j);
                    __m512i bits = _mm512_castpd_si512(x),
                            ex = _mm512_and_si512(_mm512_srli_epi64(bits, 52), _mm512_set1_epi64(0x7ff)),
                            mag = _mm512_and_si512(bits, _mm512_set1_epi64(0x7fffffffffffffffLL));
                    __mmask8 nonfinite = _mm512_cmpeq_epi64_mask(ex, _mm512_set1_epi64(0x7ff));
                    __mmask8 finite = mask & __mmask8(~nonfinite);
                    __m512d ax = _mm512_castsi512_pd(mag);
                    __mmask8 too_big =
                        _mm512_mask_cmp_pd_mask(finite, ax, _mm512_set1_pd(FP64_MAX_BF16), _CMP_GT_OQ);
                    __mmask8 nz = _mm512_mask_cmp_pd_mask(finite, ax, _mm512_setzero_pd(), _CMP_NEQ_OQ);
                    __mmask8 too_small =
                        _mm512_mask_cmp_pd_mask(finite, ax, _mm512_set1_pd(FP64_MIN_NORMAL), _CMP_LT_OQ);
                    __mmask8 invalid = nonfinite | too_big | (nz & too_small);
                    if (invalid & mask)
                        input_bad = 1;
                    _mm512_mask_storeu_pd(residual.data() + q, mask, x);
                }
        }
#else
#pragma omp for schedule(static) reduction(| : input_bad)
        for (std::size_t q = 0; q < n; ++q) {
            std::size_t i = q / cols, j = q % cols;
            double x = src[i * ld + j];
            if (!std::isfinite(x) ||
                (x != 0 && (std::abs(x) < FP64_MIN_NORMAL || std::abs(x) > FP64_MAX_BF16)))
                input_bad = 1;
            residual[q] = x;
        }
#endif
        for (int s = 0; s < 6 && !input_bad; ++s) {
            // sigma_s uses the global max of the residual at the start of round
            // s. With OZAMX_PREP_FUSED_MAX the max over round s-1's *updated*
            // residual is collected during that round's projection, so only
            // round 0 still runs the standalone scan. The fused value covers
            // exactly the vectors and lanes the scan reads (tail lanes and
            // invalid lanes contribute 0) and max is order-insensitive.
            if (!tuning::prep_fused_max || s == 0) {
                double local_max = 0;
#pragma omp single
                { global_max = 0; }
#if defined(__AVX512F__)
                __m512d local_maxv = _mm512_setzero_pd();
#pragma omp for schedule(static) nowait
                for (std::size_t u = 0; u < chunks; ++u) {
                    const auto region = traversal.region(u);
                    for (auto i = region.row; i < region.row_end; ++i)
                        for (auto j = region.col; j < region.col_end; j += 8) {
                            const auto lanes = std::min<std::size_t>(8, cols-j);
                            const auto mask = __mmask8((1u << lanes)-1);
                            __m512d x = _mm512_maskz_loadu_pd(mask, residual.data() + i*cols+j);
                            x = _mm512_andnot_pd(_mm512_set1_pd(-0.0), x);
                            local_maxv = _mm512_max_pd(local_maxv, x);
                        }
                }
                local_max = std::max(local_max, _mm512_reduce_max_pd(local_maxv));
#else
#pragma omp for schedule(static) nowait
                for (std::size_t q = 0; q < n; ++q)
                    local_max = std::max(local_max, std::abs(residual[q]));
#endif
#pragma omp critical
                {
                    if (local_max > global_max)
                        global_max = local_max;
                }
#pragma omp barrier
            }
#pragma omp single
            // Adding/subtracting this power-of-two sigma projects tiny residuals
            // onto FP32's representable grid before BF16 rounding; it is chosen
            // from the current maximum so the projection preserves useful bits.
            {
                whole_zero = (global_max == 0.0);
                if (!whole_zero)
                    sigma = std::ldexp(1.0, ceil_log2(global_max) + 45);
                if (tuning::prep_fused_max)
                    global_max = 0; // re-arm for the fused collection below
            }
#pragma omp barrier
            if (whole_zero) {
                if (s < stored_slices) {
#pragma omp for schedule(static)
                    for (std::size_t q = 0; q < n; ++q)
                        out.plane(s)[q] = 0;
                }
            } else {
                int slice_bad = 0;
#if defined(__AVX512BW__)
                // Second accumulator: this update's |rr| is the next round's
                // global max; the critical after the loop publishes it. It
                // mirrors the scan's masked read, so tail lanes stay 0.
                [[maybe_unused]] __m512d local_next_maxv = _mm512_setzero_pd();
#pragma omp for schedule(static)
                for (std::size_t u = 0; u < chunks; ++u) {
                    const auto region = traversal.region(u);
                    for (auto i = region.row; i < region.row_end; ++i)
                        for (auto j = region.col; j < region.col_end; j += 8) {
                            const auto q = i*cols+j, lanes = std::min<std::size_t>(8, cols-j);
                            const auto mask = __mmask8((1u << lanes)-1);
                            __m512d r = _mm512_maskz_loadu_pd(mask, residual.data() + q),
                                    z = _mm512_sub_pd(_mm512_add_pd(r, _mm512_set1_pd(sigma)),
                                                      _mm512_set1_pd(sigma));
                            __m256 f = _mm512_cvtpd_ps(z);
                            __m256i u = _mm256_castps_si256(f),
                                    e = _mm256_and_si256(_mm256_srli_epi32(u, 23), _mm256_set1_epi32(255)),
                                    mag = _mm256_and_si256(u, _mm256_set1_epi32(0x7fffffff));
                            __m256i rounded = _mm256_add_epi32(
                                u, _mm256_add_epi32(
                                       _mm256_set1_epi32(0x7fff),
                                       _mm256_and_si256(_mm256_srli_epi32(u, 16), _mm256_set1_epi32(1))));
                            __m256i h32 = _mm256_srli_epi32(rounded, 16),
                                    he =
                                        _mm256_and_si256(_mm256_srli_epi32(h32, 7), _mm256_set1_epi32(255));
                            __m256i hmag = _mm256_and_si256(h32, _mm256_set1_epi32(0x7fff));
                            __mmask8 invalid =
                                _mm256_cmp_epi32_mask(e, _mm256_set1_epi32(255), _MM_CMPINT_EQ) |
                                (_mm256_cmp_epi32_mask(e, _mm256_setzero_si256(), _MM_CMPINT_EQ) &
                                 _mm256_cmp_epi32_mask(mag, _mm256_setzero_si256(), _MM_CMPINT_NE));
                            invalid |= _mm256_cmp_epi32_mask(he, _mm256_set1_epi32(255), _MM_CMPINT_EQ) |
                                       (_mm256_cmp_epi32_mask(he, _mm256_setzero_si256(), _MM_CMPINT_EQ) &
                                        _mm256_cmp_epi32_mask(hmag, _mm256_setzero_si256(), _MM_CMPINT_NE));
                            if (invalid)
                                slice_bad = 1;
                            h32 = _mm256_maskz_mov_epi32(__mmask8(~invalid), h32);
                            if (s < stored_slices) {
                                __m128i narrow = _mm256_cvtepi32_epi16(h32);
                                _mm_mask_storeu_epi16(out.plane(s) + q, mask, narrow);
                            }
                            __m256 hfloat = _mm256_castsi256_ps(_mm256_slli_epi32(h32, 16));
                            __m512d hv = _mm512_cvtps_pd(hfloat);
                            __m512d safe_r = _mm512_maskz_mov_pd(__mmask8(~invalid), r),
                                    rr = _mm512_sub_pd(safe_r, hv);
                            _mm512_mask_storeu_pd(residual.data() + q, mask, rr);
                            if (tuning::prep_fused_max)
                                local_next_maxv = _mm512_max_pd(
                                    local_next_maxv,
                                    _mm512_maskz_mov_pd(
                                        mask, _mm512_andnot_pd(_mm512_set1_pd(-0.0), rr)));
                            __m512i bits = _mm512_castpd_si512(rr),
                                    ex = _mm512_and_si512(_mm512_srli_epi64(bits, 52),
                                                          _mm512_set1_epi64(0x7ff));
                            __m512i rmag = _mm512_and_si512(bits, _mm512_set1_epi64(0x7fffffffffffffffLL));
                            __mmask8 nz = _mm512_cmpneq_epi64_mask(rmag, _mm512_setzero_si512()),
                                     badexp = _mm512_cmpeq_epi64_mask(ex, _mm512_setzero_si512()) |
                                              _mm512_cmpeq_epi64_mask(ex, _mm512_set1_epi64(0x7ff));
                            if (nz & badexp)
                                slice_bad = 1;
                        }
                }
#else
                [[maybe_unused]] double local_next_max = 0;
#pragma omp for schedule(static)
                for (std::size_t q = 0; q < n; ++q) {
                    double r = residual[q], z = (r + sigma) - sigma;
                    std::uint16_t h;
                    if (!to_bf(static_cast<float>(z), h) || (h && ((h >> 7) & 255) == 0)) {
                        slice_bad = 1;
                        // The next scan would read this unmodified residual.
                        if (tuning::prep_fused_max)
                            local_next_max = std::max(local_next_max, std::abs(residual[q]));
                        continue;
                    }
                    if (s < stored_slices)
                        out.plane(s)[q] = h;
                    double rr = r - double(bf_float(h));
                    residual[q] = rr;
                    if (tuning::prep_fused_max)
                        local_next_max = std::max(local_next_max, std::abs(rr));
                    if (!std::isfinite(rr) || (rr != 0 && !std::isnormal(rr)))
                        slice_bad = 1;
                }
#endif
#pragma omp atomic update
                bad |= slice_bad;
                // Publish the collected max; the barrier below turns it into
                // round s+1's global max without another full scan.
                if (tuning::prep_fused_max && s + 1 < 6) {
#if defined(__AVX512BW__)
                    const double fused_max = _mm512_reduce_max_pd(local_next_maxv);
#else
                    const double fused_max = local_next_max;
#endif
#pragma omp critical
                    {
                        if (fused_max > global_max)
                            global_max = fused_max;
                    }
                }
            }
#pragma omp barrier
        }
    }
    if (input_bad)
        throw Error("FP64 inputs must be finite and lie within the normal BF16 exponent range");
    if (bad)
        throw Error("FP64 decomposition produced an unsupported slice or residual");
    return out;
}
// The residual uses panel order too, so projections and next-max collection
// stream contiguous vectors without a separate dense-slice packing pass.
// Shared FP64 residual/projection body, driven by an enclosing parallel
// region. split_packed_residual64 calls it once per operand; the merged
// split_packed_residual64_pair calls it for A and B from one region. All
// projection rounds, shift values, max scopes, barriers and the per-product
// numeric order are unchanged.
inline void split_packed_residual64_loop(const double* src, std::size_t cols, std::size_t ld,
                                         std::size_t n, int stored_slices,
                                         std::array<AlignedBuffer<std::uint16_t>, 6>& output,
                                         AlignedBuffer<double>& residual, bool is_a,
                                         std::size_t panel_columns, int& bad, int& input_bad,
                                         double& sigma, double& global_max, double& next_max,
                                         int& whole_zero) {
        const auto classify = [](__m512d x) {
            const auto bits = _mm512_castpd_si512(x),
                       ex = _mm512_and_si512(_mm512_srli_epi64(bits, 52), _mm512_set1_epi64(0x7ff)),
                       mag = _mm512_and_si512(bits, _mm512_set1_epi64(0x7fffffffffffffffLL));
            const __mmask8 nf = _mm512_cmpeq_epi64_mask(ex, _mm512_set1_epi64(0x7ff)),
                           finite = __mmask8(~nf);
            const auto ax = _mm512_castsi512_pd(mag);
            return int(
                nf |
                _mm512_mask_cmp_pd_mask(finite, ax, _mm512_set1_pd(FP64_MAX_BF16), _CMP_GT_OQ) |
                (_mm512_mask_cmp_pd_mask(finite, ax, _mm512_setzero_pd(), _CMP_NEQ_OQ) &
                 _mm512_mask_cmp_pd_mask(finite, ax, _mm512_set1_pd(FP64_MIN_NORMAL), _CMP_LT_OQ)));
        };
        __m512d input_maxv = _mm512_setzero_pd();
        const auto ic = is_a ? n / 8 : n / 16;
#pragma omp for schedule(static) reduction(| : input_bad)
        for (std::size_t u = 0; u < ic; ++u) {
            if (is_a) {
                const auto row = u / (cols / 8), col = (u % (cols / 8)) * 8, i = row % 256,
                           j = col % 256;
                const auto dst = (row / 256 * panel_columns + col / 256) * 65536 + (i / 32) * 8192 +
                                 (j / 32) * 1024 + ((i % 32) / 16) * 512 + (i % 16) * 32 + j % 32;
                const auto x = _mm512_loadu_pd(src + row * ld + col);
                input_bad |= classify(x);
                input_maxv = _mm512_max_pd(
                    input_maxv, _mm512_maskz_mov_pd(__mmask8(~classify(x)),
                                                    _mm512_andnot_pd(_mm512_set1_pd(-0.0), x)));
                _mm512_storeu_pd(residual.data() + dst, x);
            } else {
                const auto row = (u / (cols / 8)) * 2, col = (u % (cols / 8)) * 8, i = row % 256,
                           j = col % 256, kp = i / 2;
                const auto dst = (row / 256 * panel_columns + col / 256) * 65536 + (j / 32) * 8192 +
                                 (kp / 16) * 1024 + ((j % 32) / 16) * 512 + (kp % 16) * 32 +
                                 (j % 16) * 2;
                const auto x = _mm512_loadu_pd(src + row * ld + col),
                           y = _mm512_loadu_pd(src + (row + 1) * ld + col);
                input_bad |= classify(x) | classify(y);
                input_maxv = _mm512_max_pd(
                    input_maxv,
                    _mm512_max_pd(_mm512_maskz_mov_pd(__mmask8(~classify(x)),
                                                      _mm512_andnot_pd(_mm512_set1_pd(-0.0), x)),
                                  _mm512_maskz_mov_pd(__mmask8(~classify(y)),
                                                      _mm512_andnot_pd(_mm512_set1_pd(-0.0), y))));
                const auto lo = _mm512_permutex2var_pd(
                               x, _mm512_setr_epi64(0, 8, 1, 9, 2, 10, 3, 11), y),
                           hi = _mm512_permutex2var_pd(
                               x, _mm512_setr_epi64(4, 12, 5, 13, 6, 14, 7, 15), y);
                _mm512_storeu_pd(residual.data() + dst, lo);
                _mm512_storeu_pd(residual.data() + dst + 8, hi);
            }
        }
        const double input_max = _mm512_reduce_max_pd(input_maxv);
#pragma omp critical
        {
            if (input_max > global_max)
                global_max = input_max;
        }
#pragma omp barrier
        // Project each FP64 residual before converting through FP32 to BF16;
        // reject any nonzero subnormal residual because later slices cannot
        // represent it reliably under the supported normal-range contract.
        for (int s = 0; s < 6 && !input_bad; ++s) {
#pragma omp single
            {
                whole_zero = (global_max == 0.0);
                if (!whole_zero)
                    sigma = std::ldexp(1.0, ceil_log2(global_max) + 45);
                next_max = 0;
            }
#pragma omp barrier
            if (whole_zero) {
                if (s < stored_slices) {
#pragma omp for schedule(static)
                    for (std::size_t q = 0; q < n; ++q)
                        output[s].data()[q] = 0;
                }
            } else {
                int slice_bad = 0;
                double scalar_next_max = 0;
                __m512d next_maxv = _mm512_setzero_pd();
#if defined(__AVX512BW__)
                const std::size_t nv = n / 8;
#pragma omp for schedule(static)
                for (std::size_t v = 0; v < nv; ++v) {
                    std::size_t q = v * 8;
                    __m512d r = _mm512_loadu_pd(residual.data() + q),
                            z = _mm512_sub_pd(_mm512_add_pd(r, _mm512_set1_pd(sigma)),
                                              _mm512_set1_pd(sigma));
                    __m256 f = _mm512_cvtpd_ps(z);
                    __m256i u = _mm256_castps_si256(f),
                            e = _mm256_and_si256(_mm256_srli_epi32(u, 23), _mm256_set1_epi32(255)),
                            mag = _mm256_and_si256(u, _mm256_set1_epi32(0x7fffffff));
                    __m256i rounded = _mm256_add_epi32(
                        u, _mm256_add_epi32(
                               _mm256_set1_epi32(0x7fff),
                               _mm256_and_si256(_mm256_srli_epi32(u, 16), _mm256_set1_epi32(1))));
                    __m256i h32 = _mm256_srli_epi32(rounded, 16),
                            he =
                                _mm256_and_si256(_mm256_srli_epi32(h32, 7), _mm256_set1_epi32(255));
                    __m256i hmag = _mm256_and_si256(h32, _mm256_set1_epi32(0x7fff));
                    __mmask8 invalid =
                        _mm256_cmp_epi32_mask(e, _mm256_set1_epi32(255), _MM_CMPINT_EQ) |
                        (_mm256_cmp_epi32_mask(e, _mm256_setzero_si256(), _MM_CMPINT_EQ) &
                         _mm256_cmp_epi32_mask(mag, _mm256_setzero_si256(), _MM_CMPINT_NE));
                    invalid |= _mm256_cmp_epi32_mask(he, _mm256_set1_epi32(255), _MM_CMPINT_EQ) |
                               (_mm256_cmp_epi32_mask(he, _mm256_setzero_si256(), _MM_CMPINT_EQ) &
                                _mm256_cmp_epi32_mask(hmag, _mm256_setzero_si256(), _MM_CMPINT_NE));
                    if (invalid)
                        slice_bad = 1;
                    h32 = _mm256_maskz_mov_epi32(__mmask8(~invalid), h32);
                    if (s < stored_slices) {
                        __m128i narrow = _mm256_cvtepi32_epi16(h32);
                        _mm_mask_storeu_epi16(output[s].data() + q, __mmask8(255), narrow);
                    }
                    __m256 hfloat = _mm256_castsi256_ps(_mm256_slli_epi32(h32, 16));
                    __m512d hv = _mm512_cvtps_pd(hfloat);
                    __m512d safe_r = _mm512_maskz_mov_pd(__mmask8(~invalid), r),
                            rr = _mm512_sub_pd(safe_r, hv);
                    _mm512_storeu_pd(residual.data() + q, rr);
                    next_maxv =
                        _mm512_max_pd(next_maxv, _mm512_andnot_pd(_mm512_set1_pd(-0.0), rr));
                    __m512i bits = _mm512_castpd_si512(rr),
                            ex = _mm512_and_si512(_mm512_srli_epi64(bits, 52),
                                                  _mm512_set1_epi64(0x7ff));
                    __m512i rmag = _mm512_and_si512(bits, _mm512_set1_epi64(0x7fffffffffffffffLL));
                    __mmask8 nz = _mm512_cmpneq_epi64_mask(rmag, _mm512_setzero_si512()),
                             badexp = _mm512_cmpeq_epi64_mask(ex, _mm512_setzero_si512()) |
                                      _mm512_cmpeq_epi64_mask(ex, _mm512_set1_epi64(0x7ff));
                    if (nz & badexp)
                        slice_bad = 1;
                }
#pragma omp for schedule(static)
                for (std::size_t q = nv * 8; q < n; ++q) {
                    double r = residual[q], z = (r + sigma) - sigma;
                    std::uint16_t h;
                    if (!to_bf(static_cast<float>(z), h) || (h && ((h >> 7) & 255) == 0)) {
                        slice_bad = 1;
                        continue;
                    }
                    if (s < stored_slices)
                        output[s].data()[q] = h;
                    double rr = r - double(bf_float(h));
                    residual[q] = rr;
                    scalar_next_max = std::max(scalar_next_max, std::abs(rr));
                    if (!std::isfinite(rr) || (rr != 0 && !std::isnormal(rr)))
                        slice_bad = 1;
                }
#else
#pragma omp for schedule(static)
                for (std::size_t q = 0; q < n; ++q) {
                    double r = residual[q], z = (r + sigma) - sigma;
                    std::uint16_t h;
                    if (!to_bf(static_cast<float>(z), h) || (h && ((h >> 7) & 255) == 0)) {
                        slice_bad = 1;
                        continue;
                    }
                    if (s < stored_slices)
                        output[s].data()[q] = h;
                    double rr = r - double(bf_float(h));
                    residual[q] = rr;
                    scalar_next_max = std::max(scalar_next_max, std::abs(rr));
                    if (!std::isfinite(rr) || (rr != 0 && !std::isnormal(rr)))
                        slice_bad = 1;
                }
#endif
                const double thread_next_max =
                    std::max(scalar_next_max, _mm512_reduce_max_pd(next_maxv));
#pragma omp critical
                {
                    if (thread_next_max > next_max)
                        next_max = thread_next_max;
                }
#pragma omp atomic update
                bad |= slice_bad;
            }
#pragma omp barrier
#pragma omp single
            { global_max = next_max; }
        }
}

inline void split_packed_residual64(const double* src, std::size_t rows, std::size_t cols,
                                    std::size_t ld, int threads, int stored_slices,
                                    std::array<AlignedBuffer<std::uint16_t>, 6>& output, bool is_a,
                                    std::size_t panel_columns) {
    if (threads < 1 || stored_slices < 1 || stored_slices > 6 || rows % 256 || cols % 256 ||
        !valid_shape(src, rows, cols, ld))
        throw Error("invalid packed residual FP64 input shape");
    const auto count = mul(rows, cols);
    for (int s = 0; s < stored_slices; ++s)
        output[s] = AlignedBuffer<std::uint16_t>(count);
    AlignedBuffer<double> residual(count);
    int bad = 0, input_bad = 0;
    auto n = count;
    // The team sizing stays outside the shared body so the singleton call and
    // the merged R1a pair use exactly the same rule per operand.
    const int nt = tuning::strict_prep_fused_direct ? strict_team_size(threads, divup(n, 8))
                                                   : team_size(threads, divup(n, 8));
    double sigma = 0, global_max = 0, next_max = 0;
    int whole_zero = 0;
#if OZAMX_SINGLE_TASK_PREP_FP64 || OZAMX_SINGLE_TASK_SERIAL
    // R2: one 256x256 panel on this side -> same body, no team fork (the six
    // projection rounds, their barriers and criticals run with a team of one).
    if ((rows / 256) * (cols / 256) == 1) {
#pragma omp parallel num_threads(1) if (false)                                                 \
    shared(bad, input_bad, sigma, whole_zero, global_max, next_max)
        {
            split_packed_residual64_loop(src, cols, ld, n, stored_slices, output, residual, is_a,
                                         panel_columns, bad, input_bad, sigma, global_max,
                                         next_max, whole_zero);
        }
        if (input_bad)
            throw Error("FP64 inputs must be finite and lie within the normal BF16 exponent range");
        if (bad)
            throw Error("FP64 decomposition produced an unsupported slice or residual");
        return;
    }
#endif
#pragma omp parallel num_threads(nt) if (n > 8192)                                                 \
    shared(bad, input_bad, sigma, whole_zero, global_max, next_max)
    {
        split_packed_residual64_loop(src, cols, ld, n, stored_slices, output, residual, is_a,
                                     panel_columns, bad, input_bad, sigma, global_max, next_max,
                                     whole_zero);
    }
    if (input_bad)
        throw Error("FP64 inputs must be finite and lie within the normal BF16 exponent range");
    if (bad)
        throw Error("FP64 decomposition produced an unsupported slice or residual");
}

#if OZAMX_PREP_SINGLE_REGION
// R1a: one parallel region runs the A then B identical bodies. A single
// residual scratch (fully rewritten by each classification pass, bodies
// separated by the round barriers) keeps the singleton's peak footprint. The
// per-side state is private to each body, so the global-max scope per operand
// is unchanged.
inline void split_packed_residual64_pair(
    const double* a, std::size_t arows, std::size_t acols, std::size_t lda, const double* b,
    std::size_t brows, std::size_t bcols, std::size_t ldb, int threads, int stored_slices,
    std::array<AlignedBuffer<std::uint16_t>, 6>& out_a, bool a_is_a, std::size_t a_panels,
    std::array<AlignedBuffer<std::uint16_t>, 6>& out_b, bool b_is_a, std::size_t b_panels) {
    if (threads < 1 || stored_slices < 1 || stored_slices > 6 ||
        arows % 256 || acols % 256 || !valid_shape(a, arows, acols, lda) ||
        brows % 256 || bcols % 256 || !valid_shape(b, brows, bcols, ldb))
        throw Error("invalid packed residual FP64 input shape");
    const auto na = mul(arows, acols), nb = mul(brows, bcols);
    for (int s = 0; s < stored_slices; ++s)
        out_a[s] = AlignedBuffer<std::uint16_t>(na);
    for (int s = 0; s < stored_slices; ++s)
        out_b[s] = AlignedBuffer<std::uint16_t>(nb);
    AlignedBuffer<double> residual(std::max(na, nb));
    int bad_a = 0, input_bad_a = 0, bad_b = 0, input_bad_b = 0;
    const int nta = tuning::strict_prep_fused_direct ? strict_team_size(threads, divup(na, 8))
                                                    : team_size(threads, divup(na, 8));
    const int ntb = tuning::strict_prep_fused_direct ? strict_team_size(threads, divup(nb, 8))
                                                    : team_size(threads, divup(nb, 8));
    const int nt = std::max(nta, ntb);
    double sigma_a = 0, global_max_a = 0, next_max_a = 0;
    double sigma_b = 0, global_max_b = 0, next_max_b = 0;
    int whole_zero_a = 0, whole_zero_b = 0;
#pragma omp parallel num_threads(nt) if (na > 8192 || nb > 8192)                                 \
    shared(bad_a, input_bad_a, bad_b, input_bad_b, sigma_a, global_max_a, next_max_a,           \
           sigma_b, global_max_b, next_max_b, whole_zero_a, whole_zero_b)
    {
        split_packed_residual64_loop(a, acols, lda, na, stored_slices, out_a, residual, a_is_a,
                                     a_panels, bad_a, input_bad_a, sigma_a, global_max_a,
                                     next_max_a, whole_zero_a);
        split_packed_residual64_loop(b, bcols, ldb, nb, stored_slices, out_b, residual, b_is_a,
                                     b_panels, bad_b, input_bad_b, sigma_b, global_max_b,
                                     next_max_b, whole_zero_b);
    }
    if (input_bad_a)
        throw Error("FP64 inputs must be finite and lie within the normal BF16 exponent range");
    if (bad_a)
        throw Error("FP64 decomposition produced an unsupported slice or residual");
    if (input_bad_b)
        throw Error("FP64 inputs must be finite and lie within the normal BF16 exponent range");
    if (bad_b)
        throw Error("FP64 decomposition produced an unsupported slice or residual");
}
#endif

inline Packed split_pack_direct64(const double* a, const double* b, std::size_t m, std::size_t n,
                                  std::size_t k, std::size_t lda, std::size_t ldb, int depth,
                                  int threads) {
    Packed p;
    p.slices = depth;
    p.mblocks = m / 256;
    p.nblocks = n / 256;
    p.kblocks = k / 256;
#if OZAMX_PREP_SINGLE_REGION
    split_packed_residual64_pair(a, m, k, lda, b, k, n, ldb, threads, depth, p.a, true, p.kblocks,
                                 p.b, false, p.nblocks);
#else
    split_packed_residual64(a, m, k, lda, threads, depth, p.a, true, p.kblocks);
    split_packed_residual64(b, k, n, ldb, threads, depth, p.b, false, p.nblocks);
#endif
    return p;
}

inline Packed pack_slices(const Slices& as, const Slices& bs, std::size_t m, std::size_t n,
                          std::size_t k, int ns, int threads, bool panel_static = false) {
    if (threads < 1 || ns < 1 || ns > 6 || as.count != mul(m, k) || bs.count != mul(k, n) ||
        as.slices < ns || bs.slices < ns)
        throw Error("invalid packed slice dimensions");
    Packed p;
    p.slices = ns;
    p.mblocks = divup(m, PP_BM);
    p.nblocks = divup(n, PP_BN);
    p.kblocks = divup(k, PP_BK);
    auto ac = mul(m, k), bc = mul(k, n), asize = mul(mul(p.mblocks, p.kblocks), PP_BM * PP_BK),
         bsize = mul(mul(p.kblocks, p.nblocks), PP_BK * PP_BN);
    // A panels group 32-row by 32-K tiles; B panels interleave adjacent K
    // values for each 32-column tile. These are the layouts consumed by AMX.
    for (int s = 0; s < ns; ++s) {
        p.a[s] = AlignedBuffer<std::uint16_t>(asize);
        p.b[s] = AlignedBuffer<std::uint16_t>(bsize);
    }
    const auto aw = mul(mul(p.mblocks, p.kblocks), PP_BM),
               bw = mul(mul(p.kblocks, p.nblocks), PP_BK / 2);
#if defined(__AVX512BW__)
    alignas(64) static const std::uint16_t il[32] = {0,  32, 1,  33, 2,  34, 3,  35, 4,  36, 5,
                                                     37, 6,  38, 7,  39, 8,  40, 9,  41, 10, 42,
                                                     11, 43, 12, 44, 13, 45, 14, 46, 15, 47};
    alignas(64) static const std::uint16_t ih[32] = {16, 48, 17, 49, 18, 50, 19, 51, 20, 52, 21,
                                                     53, 22, 54, 23, 55, 24, 56, 25, 57, 26, 58,
                                                     27, 59, 28, 60, 29, 61, 30, 62, 31, 63};
    __m512i idxlo = _mm512_load_si512(il), idxhi = _mm512_load_si512(ih);
#endif
    const auto atasks = panel_static ? aw/PP_BM : aw;
    const auto btasks = panel_static ? bw/(PP_BK/2) : bw;
    int nt = panel_static ? strict_team_size(threads, std::max(atasks, btasks))
                          : team_size(threads, std::max(aw, bw));
#pragma omp parallel num_threads(nt) if (ac > 8192 || bc > 8192)
    {
#pragma omp for schedule(static)
        for (std::size_t u = 0; u < atasks; ++u) {
            const auto panel = panel_static ? u : u/PP_BM;
            const auto mb = panel/p.kblocks, kb = panel%p.kblocks;
            const auto first = panel_static ? 0 : u%PP_BM;
            const auto end = panel_static ? PP_BM : first+1;
            for (auto i=first; i<end; ++i) {
                const auto gi = mb*PP_BM+i;
                for (int s = 0; s < ns; ++s) {
                    auto* panel = p.a[s].data() + (mb * p.kblocks + kb) * PP_BM * PP_BK;
                    const auto* ap = as.plane(s);
#if defined(__AVX512BW__)
                    for (std::size_t q = 0; q < PP_BK; q += 32) {
                        std::size_t gk = kb * PP_BK + q;
                        int lanes = gi < m && gk < k ? int(std::min<std::size_t>(32, k - gk)) : 0;
                        __mmask32 mask = lanes == 32 ? ~__mmask32(0)
                                         : lanes     ? (__mmask32(1) << lanes) - 1
                                                     : 0;
                        __m512i v = _mm512_setzero_si512();
                        if (lanes)
                            v = _mm512_maskz_loadu_epi16(mask, ap + gi * k + gk);
                        std::size_t dst = (i / 32) * 8192 + (q / 32) * 1024 + ((i % 32) / 16) * 512 +
                                          (i % 16) * 32 + (q % 32);
#if OZAMX_PACK_NT_STORE
                        _mm512_stream_si512(reinterpret_cast<__m512i*>(panel + dst), v);
#else
                        _mm512_storeu_si512(panel + dst, v);
#endif
                    }
#else
                    for (std::size_t q = 0; q < PP_BK; ++q) {
                        std::size_t gk = kb * PP_BK + q, dst = (i / 32) * 8192 + (q / 32) * 1024 +
                                                               ((i % 32) / 16) * 512 + (i % 16) * 32 +
                                                               (q % 32);
                        panel[dst] = (gi < m && gk < k) ? ap[gi * k + gk] : 0;
                    }
#endif
                }
            }
        }
#if OZAMX_PACK_NT_STORE && defined(__AVX512BW__)
        _mm_sfence(); // flush this thread's non-temporal panel writes before the next side
#endif
#pragma omp for schedule(static)
        for (std::size_t u = 0; u < btasks; ++u) {
            const auto panel = panel_static ? u : u/(PP_BK/2);
            const auto kb = panel/p.nblocks, nb = panel%p.nblocks;
            const auto first = panel_static ? 0 : u%(PP_BK/2);
            const auto end = panel_static ? PP_BK/2 : first+1;
            for (auto kp=first; kp<end; ++kp) {
                std::size_t gk = kb * PP_BK + 2 * kp;
                for (int s = 0; s < ns; ++s) {
                    const auto* bp = bs.plane(s);
                    auto* panel = p.b[s].data() + (kb * p.nblocks + nb) * PP_BK * PP_BN;
#if defined(__AVX512BW__)
                    for (std::size_t j = 0; j < PP_BN; j += 32) {
                        std::size_t gn = nb * PP_BN + j;
                        int lanes = gn < n ? int(std::min<std::size_t>(32, n - gn)) : 0;
                        __mmask32 mask = lanes == 32 ? ~__mmask32(0)
                                         : lanes     ? (__mmask32(1) << lanes) - 1
                                                     : 0;
                        __m512i r0 = _mm512_setzero_si512(), r1 = _mm512_setzero_si512();
                        if (lanes && gk < k)
                            r0 = _mm512_maskz_loadu_epi16(mask, bp + gk * n + gn);
                        if (lanes && gk + 1 < k)
                            r1 = _mm512_maskz_loadu_epi16(mask, bp + (gk + 1) * n + gn);
                        __m512i lo = _mm512_permutex2var_epi16(r0, idxlo, r1),
                                hi = _mm512_permutex2var_epi16(r0, idxhi, r1);
                        std::size_t dst = (j / 32) * 8192 + (kp / 16) * 1024 + ((j % 32) / 16) * 512 +
                                          (kp % 16) * 32 + (j % 16) * 2;
#if OZAMX_PACK_NT_STORE
                        _mm512_stream_si512(reinterpret_cast<__m512i*>(panel + dst), lo);
                        _mm512_stream_si512(reinterpret_cast<__m512i*>(panel + dst + 512), hi);
#else
                        _mm512_storeu_si512(panel + dst, lo);
                        _mm512_storeu_si512(panel + dst + 512, hi);
#endif
                    }
#else
                    for (std::size_t j = 0; j < PP_BN; ++j) {
                        std::size_t gn = nb * PP_BN + j, dst = (j / 32) * 8192 + (kp / 16) * 1024 +
                                                               ((j % 32) / 16) * 512 + (kp % 16) * 32 +
                                                               (j % 16) * 2;
                        panel[dst] = (gk < k && gn < n) ? bp[gk * n + gn] : 0;
                        panel[dst + 1] = (gk + 1 < k && gn < n) ? bp[(gk + 1) * n + gn] : 0;
                    }
#endif
                }
            }
        }
#if OZAMX_PACK_NT_STORE && defined(__AVX512BW__)
        _mm_sfence(); // make every thread's non-temporal writes visible before leaving the region
#endif
    }
    return p;
}
} // namespace ozamx::detail
