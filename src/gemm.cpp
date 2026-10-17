#include "ozamx/gemm.hpp"
#include "preprocess.hpp"
#include "tuning.hpp"
#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <limits>
#include <vector>
#include <immintrin.h>
#ifdef _OPENMP
#include <omp.h>
#endif

// 声明两个由汇编实现的函数
// 计算 FP32 分解后选出的六项 BF16 乘积
extern "C" void ozamx_bf16_six(const std::uint16_t* const*, const std::uint16_t* const*, float*, unsigned);
// 计算一对 BF16 分量面板的乘积
extern "C" void ozamx_bf16_product(const std::uint16_t*, const std::uint16_t*, float*, unsigned);

namespace ozamx {
namespace {
// 多级分块：BM/BN/BK 是面板块，TM/TN/TK 是 AMX 微块；CACHE_BLOCK 控制外层 C 块。
// 内核每次沿 K 处理 BK=256，再拆成 TK=32 的步进。
constexpr std::size_t BM = 256, BN = 256, BK = 256, TM = 32, TN = 32, TK = 32,
                      CACHE_BLOCK = tuning::cache_block; // 缓存分块参数，用于调优
using Clock = std::chrono::steady_clock; //


// 以下是部分工具函数
// 计算时刻 a 到 b 之间的秒数
double elapsed(Clock::time_point a, Clock::time_point b) {
    return std::chrono::duration<double>(b - a).count();
}
// 调用 detail::mul 计算两个尺寸的乘积，并检查溢出
std::size_t checked_mul(std::size_t a, std::size_t b) {
    return detail::mul(a, b);
}
// 向上取整整数乘法
std::size_t ceil_div(std::size_t a, std::size_t b) {
    return detail::divup(a, b);
}
// 把 h 保存的 BF16 位格式数值转换成 FP32
[[maybe_unused]] float bf16_to_float(std::uint16_t h) {
    return detail::bf_float(h);
}
// 根据 OpenMP 环境确定可请求的线程数
int requested_threads() {
#ifdef _OPENMP
    return omp_in_parallel() ? 1 : omp_get_max_threads();
#else
    return 1;
#endif
}
// 根据预处理数据量,进一步限制线程数
// 先预估预处理有多少工作,再结合可请求的线程数确定最终线程团队大小
int preprocessing_threads(std::size_t count) {
    return detail::team_size(requested_threads(),
                             std::max<std::size_t>(1, ceil_div(count, tuning::prep_grain)));
}
// 该结构体按照硬件要求组织, 作为配置表,要求结构体在内存中的起始地址必须按 64 字节组织
// palette_id: 选择 AMX 支持的 Tile 配置模式
// start_row: 正常从第 0 行开始
// reserved[14]{}: 硬件保留字段，初始化为0
struct alignas(64) TileConfig {
    std::uint8_t palette_id = 1, start_row = 0, reserved[14]{};
    std::uint16_t colsb[16]{}; // 每个 tile 一行占多少字节, 不等于列数
    std::uint8_t rows[16]{};   // 每个 tile 有多少行
};
static_assert(sizeof(TileConfig) == 64);
// 生成配置表, 将 8 个 tile 都设置为 64 字节 × 16 行 = 1024 字节 / tile
constexpr TileConfig make_config() {
    TileConfig x{};
    for (int i = 0; i < 8; ++i) {
        x.colsb[i] = 64;
        x.rows[i] = 16;
    }
    return x;
}
// 把配置加载到当前线程的 AMX 状态中
void load_config() {
    static constexpr auto cfg = make_config(); // cfg 在编译期生成
    _tile_loadconfig(&cfg); // 实际执行加载配置的硬件操作
}
// 将 tmm4 到 tmm7 清零, 这 4 个 tile 用来保存乘加结果
// 每个 tile 保存 16 × 16 个 FP32, 四个拼成 32 × 32 输出块
[[maybe_unused]] void zero_accumulators() {
    _tile_zero(4);
    _tile_zero(5);
    _tile_zero(6);
    _tile_zero(7);
}
// 上述清零操作对应的保存操作
[[maybe_unused]] void store_32x32(float* out) {
    _tile_stored(4, out,       128);
    _tile_stored(5, out + 16,  128); // 128 是相邻输出行之间的距离, 单位为字节
    _tile_stored(6, out + 512, 128); // out + ... 是 float* 指针运算, 偏移单位是 float 元素
    _tile_stored(7, out + 528, 128);
}
using Packed32 = detail::Packed; // 用于 FP32 路径的打包, 打包对象为 BF16 元素
using Packed64 = detail::Packed; // 用于 FP64 路径的打包, 打包对象为 BF16 元素
// 一个 Panel 存储包含 1 KiB 连续tile
// 这里的布局是 宏块 → 微块 → 连续保存的 tile → tile 内的元素
// 计算 A Panel 中某个元素的位置
template <int S>
std::size_t apanel_index(std::size_t mb, std::size_t kb, std::size_t mi, std::size_t kk,
                         std::size_t kblocks) {
    (void)S;
    // mb kb: A 位于第几个 M 宏块, 第几个 K 宏块
    // mi kk: 元素在当前宏块内的行坐标, K 坐标
    // kblocks: K 方向共有多少个宏块
    return (mb * kblocks + kb) * BM * BK + (mi / TM) * TM * BK + (kk / TK) * TM * TK +
           ((mi % TM) / 16) * 16 * TK + (mi % 16) * TK + kk % TK;
}
// 计算 B Panel 中某个元素的位置
std::size_t bpanel_index(std::size_t kb, std::size_t nb, std::size_t kp, std::size_t nj,
                         std::size_t nblocks) {
    return (kb * nblocks + nb) * BK * BN + (nj / TN) * TN * BK + (kp / (TK / 2)) * TN * TK +
           ((nj % TN) / 16) * 512 + (kp % (TK / 2)) * 32 + (nj % 16) * 2;
}
// 准备三片输入, 计算六项乘积
// FP32 路径将 A、B 各拆分成三片 BF16, 保存在 p 中
template <std::size_t NS>
void run_fp32_micro(const Packed32& p, std::size_t mb, std::size_t nb, std::size_t kb,
                    std::size_t mi, std::size_t nj, float* out, unsigned steps = BK / TK) {
    (void)NS;
    // 先找到当前微块在打包缓冲区中的位置
    const auto ai = apanel_index<0>(mb, kb, mi, 0, p.kblocks),
               bi = bpanel_index(kb, nb, 0, nj, p.nblocks);
    // ai 和 bi 是元素偏移量
    const std::uint16_t* aa[3] = {p.a[0].data() + ai, p.a[1].data() + ai, p.a[2].data() + ai};
    const std::uint16_t* bb[3] = {p.b[0].data() + bi, p.b[1].data() + bi, p.b[2].data() + bi};
    // 六个 BF16 投影按汇编中的 A1B1、A1B0、A2B0、A0B0、A0B1、A0B2 顺序累加
    // 最后将 32 × 32 FP32 输出写入 out
    ozamx_bf16_six(aa, bb, out, steps);
}
// FP64 路径需要按预算计算不同的分量组合, 因此增加了 ai 和 bi 两个参数, 表示分量的编号
template <std::size_t NS>
void run_fp64_product(const Packed64& p, int ai, int bi, std::size_t mb, std::size_t nb,
                      std::size_t kb, std::size_t mi, std::size_t nj, float* out,
                      unsigned steps = BK / TK) {
    (void)NS;
    // 找到指定 A 和 B 分量的当前面板, 并计算分量乘积
    ozamx_bf16_product(p.a[ai].data() + apanel_index<0>(mb, kb, mi, 0, p.kblocks),
                       p.b[bi].data() + bpanel_index(kb, nb, 0, nj, p.nblocks), out, steps);
}
// Independent diagnostics retain their existing private split/pack API.
// Production uses aligned slices directly and does not take these copy paths.
[[maybe_unused]] void split32(const float* p, std::size_t count, std::vector<std::uint16_t>& out) {
    auto s = detail::split_fp32(p, 1, count, count, preprocessing_threads(count));
    out.assign(s.data.data(), s.data.data() + s.data.size());
}
[[maybe_unused]] void split64(const double* p, std::size_t count, std::vector<std::uint16_t>& out) {
    auto s = detail::split_fp64(p, 1, count, count, preprocessing_threads(count));
    out.assign(s.data.data(), s.data.data() + s.data.size());
}

// 打包流程的适配层: 把普通 vector 中已经拆好的 BF16 分量, 装入内部使用的数据结构, 再调用真正的打包函数
template <std::size_t NS>
detail::Packed pack_compat(const std::vector<std::uint16_t>& a, const std::vector<std::uint16_t>& b,
                           std::size_t m, std::size_t n, std::size_t k) {
    // 将 vector 中的 BF16 分量复制到对齐的缓冲区
    detail::Slices sa, sb;
    sa.count = checked_mul(m, k);
    sb.count = checked_mul(k, n);
    sa.slices = sb.slices = NS; // NS 在编译期确定表示分片数量
    sa.data = detail::AlignedBuffer<std::uint16_t>(a.size());
    sb.data = detail::AlignedBuffer<std::uint16_t>(b.size());
    std::copy(a.begin(), a.end(), sa.data.data());
    std::copy(b.begin(), b.end(), sb.data.data());
    // 重排、补齐
    return detail::pack_slices(sa, sb, m, n, k, NS,
                               preprocessing_threads(std::max(sa.count, sb.count)));
}
template <std::size_t NS>
Packed32 pack32(const std::vector<std::uint16_t>& a, const std::vector<std::uint16_t>& b,
                std::size_t m, std::size_t n, std::size_t k) {
    return pack_compat<NS>(a, b, m, n, k);
}
template <std::size_t NS>
Packed64 pack64(const std::vector<std::uint16_t>& a, const std::vector<std::uint16_t>& b,
                std::size_t m, std::size_t n, std::size_t k) {
    return pack_compat<NS>(a, b, m, n, k);
}

// 判断一个 SIMD 向量中是否至少有一个非有限值, 也就是 NaN 或正负无穷大
// _m512 一次检查 16 个 FP32
inline bool nonfinite(__m512 x) {
    // 将掩码复制到全部 16 个位置, 按位与后只剩指数部分, 检查哪些位置的指数为全 1
    return _mm512_cmpeq_epi32_mask(
               _mm512_and_si512(_mm512_castps_si512(x), _mm512_set1_epi32(0x7f800000)),
               _mm512_set1_epi32(0x7f800000)) != 0;
}
// _m512d 一次检查 8 个 FP64
inline bool nonfinite(__m512d x) {
    // 同 FP32 路径
    return _mm512_cmpeq_epi64_mask(
               _mm512_and_si512(_mm512_castpd_si512(x), _mm512_set1_epi64(0x7ff0000000000000LL)),
               _mm512_set1_epi64(0x7ff0000000000000LL)) != 0;
}

// 数值累加还原: 将 AMX 计算得到的 32 × 32 FP32 临时结果加到对应输出块中
template <bool DeferredCheck = false>
inline void accumulate32(float* block, const float* micro, std::size_t stride, int& bad) {
    /*
     * block: 正在累加的私有输出块
     * micro: 一个连续的 32 × 32 FP32 临时输出结果
     * stride: block 相邻两行之间的元素数量
     * bad: 错误标记, 发现 NaN 或 Inf 时置位
    */
    // 16 个 FP32 一起累加, AVX-512 寄存器有 512 位, 可以容纳 16 个 float
    for (std::size_t i = 0; i < TM; ++i)
        for (std::size_t j = 0; j < TN; j += 16) {
            // 读取两组 float, 并逐元素相加
            const auto r = _mm512_add_ps(_mm512_load_ps(block + i * stride + j),
                                         _mm512_load_ps(micro + i * TN + j));
            // 检查相加结果
            if constexpr (!DeferredCheck)
                bad |= nonfinite(r);
            // 写回累加结果
            _mm512_store_ps(block + i * stride + j, r);
        }
}
template <bool Late64 = false>
inline void accumulate64(double* block, const float* micro, std::size_t stride, int& bad) {
    (void)bad;
    for (std::size_t i = 0; i < TM; ++i)
        for (std::size_t j = 0; j < TN; j += 16) {
            // 每个单精度 product 完成后立即逐元素拓宽为 FP64，再加入私有块。
            const auto f = _mm512_load_ps(micro + i * TN + j);
            if constexpr (!Late64)
                bad |= nonfinite(f);
            // 读取了 16 个 FP32, 拆成高低 8 个 float, 分别转成 double
            const auto lo = _mm512_cvtps_pd(_mm512_castps512_ps256(f)),
                       hi = _mm512_cvtps_pd(_mm512_extractf32x8_ps(f, 1));
            const auto r0 = _mm512_add_pd(_mm512_load_pd(block + i * stride + j), lo),
                       r1 = _mm512_add_pd(_mm512_load_pd(block + i * stride + j + 8), hi);
            if constexpr (!Late64)
                bad |= nonfinite(r0) | nonfinite(r1);
            _mm512_store_pd(block + i * stride + j, r0);
            _mm512_store_pd(block + i * stride + j + 8, r1);
        }
}
// 多个临时结果共用一次输出读写
template <bool Late64, std::size_t Batch>
inline void accumulate64_batch(double* block, const float* const (&micros)[Batch],
                               std::size_t count, std::size_t stride, int& bad) {
    // 普通版本每次加一个 micro, batch 版本把当前 16 个 double 保存在两个向量寄存器中
    // 减少了对 block 的读写
    // const float* const (&micros)[Batch] 表示饮用一个长度为 Batch 的数组
    // count 时本次实际使用的数量 count <= Batch
    static_assert(Batch >= 2);
    for (std::size_t i = 0; i < TM; ++i)
        for (std::size_t j = 0; j < TN; j += 16) {
            // 先读取输出
            __m512d lo = _mm512_load_pd(block + i * stride + j),
                    hi = _mm512_load_pd(block + i * stride + j + 8);
            for (std::size_t q = 0; q < count; ++q) {
                // 逐个读取 micro, 转为 double, 再按 q 的顺序相加
                const auto f = _mm512_load_ps(micros[q] + i * TN + j);
                if constexpr (!Late64)
                    bad |= nonfinite(f);
                const auto fl = _mm512_cvtps_pd(_mm512_castps512_ps256(f)),
                           fh = _mm512_cvtps_pd(_mm512_extractf32x8_ps(f, 1));
                lo = _mm512_add_pd(lo, fl);
                hi = _mm512_add_pd(hi, fh);
                if constexpr (!Late64)
                    bad |= nonfinite(lo) | nonfinite(hi);
            }
            // 全部加完之后才写回
            _mm512_store_pd(block + i * stride + j, lo);
            _mm512_store_pd(block + i * stride + j + 8, hi);
        }
}

template <bool Late64, std::size_t Batch>
inline void run_fp64_batch(double* block, std::size_t stride, const Packed64& p, std::size_t mb,
                           std::size_t nb, std::size_t kb, std::size_t mi, std::size_t nj,
                           unsigned steps, int depth, int& bad) {
    // 先用 AMX 计算各对 BF16 分片的乘积, 再按规定顺序转换成 double, 累加到输出块
    // 为减少对 block 的读写, 使用 Batch 决定一次收集多个乘积结果再累加
    if constexpr (Batch == 1) {
        alignas(64) float micro[TM * TN];
        for (int diagonal = 0; diagonal < depth; ++diagonal)
            for (int ai = 0; ai <= diagonal; ++ai) {
                // A 的分片编号 ai
                // B 的分片编号 diagonal - ai
                run_fp64_product<6>(p, ai, diagonal - ai, mb, nb, kb, mi, nj, micro, steps);
                accumulate64<Late64>(block, micro, stride, bad);
                // micro 保存一个 32×32 的 FP32 临时结果, 并按 64 字节对齐
            }
    } else {
        // Batch > 1 则使用 Batch 版的累加方式
        // Product order remains diagonal-major, then ai-major. Flush a short tail
        // without changing the sequence of float-to-double additions.
        constexpr std::size_t MaxBatch = Batch;
        alignas(64) float scratch[MaxBatch][TM * TN];   // 多个临时结果的缓冲区
        std::size_t count = 0;
        for (int diagonal = 0; diagonal < depth; ++diagonal)
            for (int ai = 0; ai <= diagonal; ++ai) {
                // 编号先按对角线, 再按 ai 排序, depth 决定遍历多少条对角线(直接决定分片乘积数量)
                run_fp64_product<6>(p, ai, diagonal - ai, mb, nb, kb, mi, nj, scratch[count],
                                    steps);
                if (++count == Batch) {
                    // 缓冲区装满后准备一个指针数组
                    const float* micros[MaxBatch];
                    for (std::size_t q = 0; q < count; ++q)
                        micros[q] = scratch[q]; // 只复制地址
                    // 实际执行累加
                    accumulate64_batch<Late64, MaxBatch>(block, micros, count, stride, bad);
                    count = 0;
                }
            }
        // 处理没装满的尾块
        if (count) {
            if (count == 1)
                accumulate64<Late64>(block, scratch[0], stride, bad);
            else {
                const float* micros[MaxBatch];
                for (std::size_t q = 0; q < count; ++q)
                    micros[q] = scratch[q];
                accumulate64_batch<Late64, MaxBatch>(block, micros, count, stride, bad);
            }
        }
    }
}

// 清零一块内存, 没处理尾部, 要求按 64 字节对齐
template <class T> inline void zero_block(T* p, std::size_t count) {
    for (std::size_t i = 0; i < count; i += 64 / sizeof(T))
        _mm512_store_si512(p + i, _mm512_setzero_si512());
}
// 复制一行, 包含不足一个向量的尾部
template <class T> void copy_row(T* dst, const T* src, std::size_t n) {
    constexpr std::size_t lanes = 64 / sizeof(T); // 一行向量能装多少元素
    std::size_t j = 0;
    for (; j + lanes <= n; j += lanes)
        _mm512_storeu_si512(dst + j, _mm512_loadu_si512(src + j));
    if (j < n) {
        if constexpr (sizeof(T) == 4) {
            const auto mask = __mmask16((1u << (n - j)) - 1);
            _mm512_mask_storeu_ps(dst + j, mask, _mm512_maskz_loadu_ps(mask, src + j));
        } else {
            const auto mask = __mmask8((1u << (n - j)) - 1);
            _mm512_mask_storeu_pd(dst + j, mask, _mm512_maskz_loadu_pd(mask, src + j));
        }
    }
}
// 检查尺寸、行间距、指针和整数溢出
template <class T>
void validate_layout(std::size_t m, std::size_t n, std::size_t k, const T* a, std::size_t lda,
                     const T* b, std::size_t ldb, T* c, std::size_t ldc) {
    if (!m || !n)
        throw Error("M and N must be positive");
    if (lda < k || ldb < n || ldc < n)
        throw Error("row-major leading dimensions are too small");
    if (k && !a)
        throw Error("A pointer is null");
    if (k && !b)
        throw Error("B pointer is null");
    if (!c)
        throw Error("C pointer is null");
    (void)checked_mul(m, k);
    (void)checked_mul(k, n);
    (void)checked_mul(m, n);
    // 检查包含行间填充后的地址跨度
    const auto span = [](std::size_t rows, std::size_t cols, std::size_t ld) {
        if (!rows || !cols)
            return;
        const auto off = checked_mul(rows - 1, ld);
        if (off > std::numeric_limits<std::size_t>::max() - cols)
            throw Error("matrix address span overflow");
        (void)checked_mul(off + cols, sizeof(T));
    };
    span(m, k, lda);
    span(k, n, ldb);
    span(m, n, ldc);
}
// 把乘积数量映射为分片深度, 对应 run_fp64_batch() 的对角线遍历
int budget_depth(ProductBudget b) {
    switch (b) {
    case ProductBudget::p6:
        return 3;
    case ProductBudget::p10:
        return 4;
    case ProductBudget::p15:
        return 5;
    case ProductBudget::p21:
        return 6;
    }
    throw Error("invalid FP64 product budget");
}

#if OZAMX_STRICT_PREP_FUSED_DIRECT
// Two-stage prep kept as the fused path's fallback for shapes whose rows or
// columns are not multiples of 256 (the direct writer requires full panels).
template <class T>
detail::Packed strict_prep_split_pack(const T* a, std::size_t lda, const T* b, std::size_t ldb,
                                     std::size_t m, std::size_t n, std::size_t k, int slices,
                                     int depth, int threads, detail::Slices& sa, detail::Slices& sb,
                                     Clock::time_point& t1) {
    if constexpr (std::is_same_v<T, float>) {
#if OZAMX_PREP_SINGLE_REGION
        detail::split_fp32_pair(a, m, k, lda, b, k, n, ldb, threads, true, sa, sb);
#else
        sa = detail::split_fp32(a, m, k, lda, threads, true);
        sb = detail::split_fp32(b, k, n, ldb, threads, true);
#endif
    } else {
        sa = detail::split_fp64(a, m, k, lda, threads, slices, true);
        sb = detail::split_fp64(b, k, n, ldb, threads, slices, true);
    }
    t1 = Clock::now();
    const int packed_slices = tuning::research_pack_used_slices ? depth : slices;
    return detail::pack_slices(sa, sb, m, n, k, packed_slices, threads, true);
}
#endif

// The reference execution follows reference Sections 6.1--6.3. Keep the older
// adaptive path below available for controlled comparisons. Neither path
// changes the public API's transactional output or aliasing guarantees.
template <class T>
GemmTimings gemm_strict_emulation_impl(std::size_t m, std::size_t n, std::size_t k, const T* a,
                           std::size_t lda, const T* b, std::size_t ldb, T* c,
                           std::size_t ldc, int depth) {
    validate_layout(m, n, k, a, lda, b, ldb, c, ldc);
    const auto t0 = Clock::now();
    const int threads = requested_threads();
    // All six FP64 planes are computed by split at every product budget.
    // The experimental OZAMX_RESEARCH_PACK_USED_SLICES option can additionally
    // skip packing planes that the selected budget never reads; split still
    // produces all six so the run-time domain checks are unchanged.
    constexpr int slices = std::is_same_v<T, float> ? 3 : 6;
#if OZAMX_STRICT_PREP_FUSED_DIRECT
    // The fused prep writes the BF16 components directly into the packed AMX
    // panels for aligned shapes, so no dense Slices buffer is materialized; the
    // direct writers were audited byte-identical to split+pack_slices
    // (tests/packed_panel_audit.cpp). Unaligned shapes keep the two-stage prep.
    // Fused work stays on the split_seconds clock; pack_seconds keeps the
    // allocations only (risk D-3 in the pack optimization proposal).
    detail::Slices sa, sb;
    detail::Packed p;
    Clock::time_point t1;
    if (m % 256 == 0 && n % 256 == 0 && k % 256 == 0) {
        if constexpr (std::is_same_v<T, float>) {
            p = detail::split_pack_direct32(a, b, m, n, k, lda, ldb, threads);
        } else {
            // Strict contract: all six planes are stored (slices, never the
            // product-budget depth); the six projection rounds keep their
            // global max scope and only the destination is the panel layout.
            p = detail::split_pack_direct64(a, b, m, n, k, lda, ldb, slices, threads);
        }
        t1 = Clock::now();
    } else {
        p = strict_prep_split_pack(a, lda, b, ldb, m, n, k, slices, depth, threads, sa, sb, t1);
    }
#else
    // With OZAMX_STRICT_PREP_FUSED_DIRECT off this block is the pre-change
    // two-stage prep verbatim ("split+pack" plus sa={};sb={}; below), so the
    // OFF build stays single-variable against the frozen tree.
    detail::Slices sa, sb;
    if constexpr (std::is_same_v<T, float>) {
#if OZAMX_PREP_SINGLE_REGION
        detail::split_fp32_pair(a, m, k, lda, b, k, n, ldb, threads, true, sa, sb);
#else
        sa = detail::split_fp32(a, m, k, lda, threads, true);
        sb = detail::split_fp32(b, k, n, ldb, threads, true);
#endif
    } else {
        sa = detail::split_fp64(a, m, k, lda, threads, slices, true);
        sb = detail::split_fp64(b, k, n, ldb, threads, slices, true);
    }
    const auto t1 = Clock::now();
    const int packed_slices = tuning::research_pack_used_slices ? depth : slices;
    auto p = detail::pack_slices(sa, sb, m, n, k, packed_slices, threads, true);
#endif
    const int compute_threads = detail::strict_team_size(threads, checked_mul(p.mblocks, p.nblocks));
    sa = {};
    sb = {};
    detail::AlignedBuffer<T> result(checked_mul(m, n));
    // Three pooled allocations contain disjoint worker regions. Allocating
    // each panel separately would overflow the pool's slot count at 64 workers
    // and reintroduce avoidable allocation/first-touch costs on every call.
    // Allocation failures remain outside OpenMP; workers first-touch their own
    // regions, with no multi-megabyte thread-stack arrays.
    // The private block can optionally pad each row by whole cache lines. This
    // changes only the accumulator address mapping; the logical BM x BN block,
    // product order, and FP64 addition order are unchanged.
    constexpr std::size_t block_pad_elems =
        std::is_same_v<T, double> ? tuning::strict_fp64_row_pad_bytes / sizeof(T) : 0;
    const std::size_t block_stride = BN + block_pad_elems;
    const std::size_t block_elems = BM * block_stride;
    detail::AlignedBuffer<T> blocks(checked_mul(std::size_t(compute_threads), block_elems));
#if OZAMX_STRICT_LOCAL_STAGING
    const auto worker_panels = checked_mul(std::size_t(depth), BM * BK);
#if OZAMX_RESEARCH_STAGING_PIPELINE
    // Double buffering keeps two panel slots per worker ((kb & 1) selects the
    // slot) so the copy of kb+1 can run before the micro loop of kb. Same
    // pooled allocation shape with twice the per-worker extent; OFF keeps the
    // single-slot layout unchanged. The option is inert without local staging.
    const auto worker_slots = checked_mul(std::size_t(2), worker_panels);
    detail::AlignedBuffer<std::uint16_t> local_a(checked_mul(std::size_t(compute_threads), worker_slots));
    detail::AlignedBuffer<std::uint16_t> local_b(checked_mul(std::size_t(compute_threads), worker_slots));
#else
    detail::AlignedBuffer<std::uint16_t> local_a(checked_mul(std::size_t(compute_threads), worker_panels));
    detail::AlignedBuffer<std::uint16_t> local_b(checked_mul(std::size_t(compute_threads), worker_panels));
#endif
#endif
    const auto t2 = Clock::now();
    int bad = 0;
#if OZAMX_SINGLE_TASK_SERIAL
    // Output-task gate: exactly one (mb,nb) block means the 64-thread compute
    // region would fork a team for a single task. Run the identical body on
    // the main thread instead (the orphaned `omp for` executes serially with a
    // team of one); every other shape keeps the existing parallel region.
    const bool single_task = checked_mul(p.mblocks, p.nblocks) == 1;
    // Small commits stay serial after the bad check (no commit region fork).
    const bool small_commit = checked_mul(m, n) <= std::size_t(BM * BN);
#endif
    // Shared compute body. `bad_ref` is the reduction-private copy inside the
    // parallel region and the plain accumulator on the single-task serial path;
    // staging slots, per-block/micro/product order and the scan are unchanged.
    const auto compute_body = [&](int worker, int& bad_ref) __attribute__((always_inline)) {
        auto* block = blocks.data() + std::size_t(worker) * block_elems;
        alignas(64) float micro[TM * TN];
        load_config();
#pragma omp for collapse(2) schedule(static)
        for (std::size_t mb = 0; mb < p.mblocks; ++mb)
            for (std::size_t nb = 0; nb < p.nblocks; ++nb) {
                for (std::size_t br = 0; br < BM; ++br)
                    zero_block(block + br * block_stride, BN);
                const auto rows = std::min(BM, m - mb * BM);
                const auto cols = std::min(BN, n - nb * BN);
#if OZAMX_STRICT_LOCAL_STAGING && OZAMX_RESEARCH_STAGING_PIPELINE
                // Staging pipeline: slot (kb & 1) holds the panels of the KB
                // being multiplied and slot ((kb + 1) & 1) is filled with the
                // next KB before this KB's micro loop runs. Copied bytes, copy
                // counts and copy order equal the single-buffer loop's; only
                // the destination slot moves. The first KB of each output
                // block is staged here, before the loop.
                const auto stage_panels = [&](unsigned slot, std::size_t plane_kb) {
                    for (int s = 0; s < depth; ++s) {
                        const auto* ap = p.a[s].data() + (mb * p.kblocks + plane_kb) * BM * BK;
                        const auto* bp = p.b[s].data() + (plane_kb * p.nblocks + nb) * BK * BN;
                        auto* staged_a = local_a.data() + std::size_t(worker) * worker_slots +
                                         std::size_t(slot) * worker_panels + s * BM * BK;
                        auto* staged_b = local_b.data() + std::size_t(worker) * worker_slots +
                                         std::size_t(slot) * worker_panels + s * BK * BN;
                        std::memcpy(staged_a, ap, BM * BK * sizeof(std::uint16_t));
                        std::memcpy(staged_b, bp, BK * BN * sizeof(std::uint16_t));
                    }
                };
                const auto bind_panels = [&](unsigned slot, const std::uint16_t** panel_a,
                                             const std::uint16_t** panel_b) {
                    for (int s = 0; s < depth; ++s) {
                        panel_a[s] = local_a.data() + std::size_t(worker) * worker_slots +
                                     std::size_t(slot) * worker_panels + s * BM * BK;
                        panel_b[s] = local_b.data() + std::size_t(worker) * worker_slots +
                                     std::size_t(slot) * worker_panels + s * BK * BN;
                    }
                };
                if (p.kblocks)
                    stage_panels(0u, 0); // no previous iteration to hide behind
#endif
                for (std::size_t kb = 0; kb < p.kblocks; ++kb) {
                    const unsigned steps = unsigned(ceil_div(std::min(BK, k - kb * BK), TK));
                    const std::uint16_t* aa[6]{};
                    const std::uint16_t* bb[6]{};
#if OZAMX_STRICT_LOCAL_STAGING && OZAMX_RESEARCH_STAGING_PIPELINE
                    const unsigned cur = unsigned(kb & 1u);
                    if (kb + 1 < p.kblocks)
                        stage_panels(cur ^ 1u, kb + 1u); // one KB ahead, before the micro loop
                    bind_panels(cur, aa, bb);
#else
                    for (int s = 0; s < depth; ++s) {
                        const auto* ap = p.a[s].data() + (mb * p.kblocks + kb) * BM * BK;
                        const auto* bp = p.b[s].data() + (kb * p.nblocks + nb) * BK * BN;
#if OZAMX_STRICT_LOCAL_STAGING
                        auto* staged_a = local_a.data() + std::size_t(worker) * worker_panels + s * BM * BK;
                        auto* staged_b = local_b.data() + std::size_t(worker) * worker_panels + s * BK * BN;
                        std::memcpy(staged_a, ap, BM * BK * sizeof(std::uint16_t));
                        std::memcpy(staged_b, bp, BK * BN * sizeof(std::uint16_t));
                        aa[s] = staged_a;
                        bb[s] = staged_b;
#else
                        aa[s] = ap;
                        bb[s] = bp;
#endif
                    }
#endif
                    for (std::size_t i = 0; i < rows; i += TM)
                        for (std::size_t j = 0; j < cols; j += TN) {
                            const auto ai = i * BK, bi = j * BK;
                            if constexpr (std::is_same_v<T, float>) {
                                const std::uint16_t* am[3] = {aa[0] + ai, aa[1] + ai, aa[2] + ai};
                                const std::uint16_t* bm[3] = {bb[0] + bi, bb[1] + bi, bb[2] + bi};
                                ozamx_bf16_six(am, bm, micro, steps);
                                accumulate32<true>(block + i * block_stride + j, micro, block_stride,
                                                   bad_ref);
                            } else {
                                for (int diagonal = 0; diagonal < depth; ++diagonal)
                                    for (int s = 0; s <= diagonal; ++s) {
                                        ozamx_bf16_product(aa[s] + ai, bb[diagonal - s] + bi,
                                                           micro, steps);
                                        accumulate64<true>(block + i * block_stride + j, micro,
                                                           block_stride, bad_ref);
                                    }
                            }
                        }
                }
                // Reconstruction only widens and adds. Once a component or
                // partial sum is NaN/Inf, later additions cannot make it finite.
                // One scan preserves rejection and transactional C semantics
                // while keeping classification out of every component add.
                for (std::size_t i = 0; i < BM; ++i)
                    for (std::size_t q = 0; q < BN; q += 64 / sizeof(T)) {
                        if constexpr (std::is_same_v<T, float>)
                            bad_ref |= nonfinite(_mm512_load_ps(block + i * block_stride + q));
                        else
                            bad_ref |= nonfinite(_mm512_load_pd(block + i * block_stride + q));
                    }
                for (std::size_t i = 0; i < rows; ++i)
                    copy_row(result.data() + (mb * BM + i) * n + nb * BN,
                             block + i * block_stride, cols);
            }
        _tile_release();
    };
#if OZAMX_SINGLE_TASK_SERIAL
    if (single_task) {
        // Worker slot 0 mirrors what the old serialized inner region reported
        // (the buffers are per-call, so concurrent callers never share them).
        const int worker = 0;
        int nested = 0;
#ifdef _OPENMP
        nested = omp_in_parallel();
#endif
        if (nested) {
            // Called from inside an existing team: the orphaned worksharing
            // loop would bind to that outer team, so bind it to a serialized
            // inner region instead (if(false) forks no threads).
#pragma omp parallel num_threads(1) if (false)
            { compute_body(worker, bad); }
        } else {
            // Plain top-level call: no parallel region at all; the orphaned
            // `omp for` executes serially with a team of one.
            compute_body(worker, bad);
        }
    } else
#endif
    {
#if OZAMX_COMMIT_IN_COMPUTE
        // Shared commit gate: every thread ORs its private `bad` reduction copy
        // here before the barrier; the region commits C only when no thread found
        // a non-finite component. The throw stays outside the region.
        int bad_commit = 0;
#pragma omp parallel num_threads(compute_threads) if (compute_threads > 1) reduction(| : bad) shared(bad_commit)
#else
#pragma omp parallel num_threads(compute_threads) if (compute_threads > 1) reduction(| : bad)
#endif
        {
            int worker = 0;
#ifdef _OPENMP
            worker = omp_get_thread_num();
#endif
            compute_body(worker, bad);
#if OZAMX_COMMIT_IN_COMPUTE
#if OZAMX_SINGLE_TASK_SERIAL
            if (!small_commit) {
#endif
                if (bad) {
#pragma omp atomic
                    bad_commit |= 1;
                }
#pragma omp barrier
                if (!bad_commit) {
#pragma omp for schedule(static)
                    for (std::size_t i = 0; i < m; ++i)
                        copy_row(c + i * ldc, result.data() + i * n, n);
                }
#if OZAMX_SINGLE_TASK_SERIAL
            }
#endif
#endif
        }
    }
    if (bad)
        throw Error("AMX component product or reconstructed output became non-finite");
#if OZAMX_SINGLE_TASK_SERIAL
    if (small_commit) {
        for (std::size_t i = 0; i < m; ++i)
            copy_row(c + i * ldc, result.data() + i * n, n);
    }
#if !OZAMX_COMMIT_IN_COMPUTE
    else
#endif
#endif
#if !OZAMX_COMMIT_IN_COMPUTE
    {
#pragma omp parallel for num_threads(compute_threads) if (compute_threads > 1) schedule(static)
        for (std::size_t i = 0; i < m; ++i)
            copy_row(c + i * ldc, result.data() + i * n, n);
    }
#endif
    const auto t3 = Clock::now();
    return {elapsed(t0, t1), elapsed(t1, t2), elapsed(t2, t3), elapsed(t0, t3)};
}

// 矩阵乘法的主调度函数
// 流程为: 检查参数, 分片并打包 A、B, 将 C 划分成多个输出任务, 多个线程分别计算自己的输出块
//        检查结果并汇总到临时结果矩阵, 全部通过后写入用户指定的 C
// CompactWide: 对非小矩阵使用 256×256 输出块
template <class T, bool Late64 = false, bool Wide = false, bool CompactWide = false>
GemmTimings gemm_impl(
    std::size_t m,      // M
    std::size_t n,      // N
    std::size_t k,      // K
    const T* a,         // A 的指针
    std::size_t lda,    // 行间距
    const T* b,         // B 的指针
    std::size_t ldb,    // 行间距
    T* c,               // C 的指针
    std::size_t ldc,    // 行间距
    int depth) {        // Ozaki 分片档位
    validate_layout(m, n, k, a, lda, b, ldb, c, ldc);
    GemmTimings t;
    // K 为零时每个输出都是空和, 直接清零 C 的有效元素, 不进入分片和 AMX 计算
    if (!k) {
        const auto z0 = Clock::now();
        for (std::size_t i = 0; i < m; ++i)
            std::fill(c + i * ldc, c + i * ldc + n, T(0));
        t.total_seconds = elapsed(z0, Clock::now());
        return t;
    }
    const auto t0 = Clock::now();
    const int prep = preprocessing_threads(
        std::max(checked_mul(m, k), checked_mul(k, n))); // 预处理使用的线程数量
    detail::Slices sa, sb; // 按分片保存的中间数据
    detail::Packed p; // 最终打包完成的 A、B 面板

    // 有两条路径
    // 普通路径: 原始矩阵 → BF16分片 sa/sb → 打包成 p
    // 融合路径: 原始矩阵 → 一边分片，一边直接生成 p
    bool direct = false;
    // 在编译期选择 FP32 或 FP64 的分解算法
    if constexpr (std::is_same_v<T, float>) {
        // 融合路径
        // 要求矩阵较大且尺寸整齐, 适合按完整块处理
        if (std::min(m, n) >= 1024 && m % 256 == 0 && n % 256 == 0 && k % 256 == 0) {
            p = detail::split_pack_direct32(a, b, m, n, k, lda, ldb, prep);
            direct = true;
        } else {
        // 普通路径
            sa = detail::split_fp32(a, m, k, lda, prep);
            sb = detail::split_fp32(b, k, n, ldb, prep);
        }
    } else {
        // 对于 FP64, 所有 Ozaki 档位都执行六片分片, 通过减少长期保存的分片数量来做档位区分
        if (std::min(m, n) >= 1024 && m % 256 == 0 && n % 256 == 0 && k % 256 == 0) {
            p = detail::split_pack_direct64(a, b, m, n, k, lda, ldb, depth, prep);
            direct = true;
        } else {
            sa = detail::split_fp64(a, m, k, lda, prep, depth);
            sb = detail::split_fp64(b, k, n, ldb, prep, depth);
        }
    }
    const auto t1 = Clock::now();
    t.split_seconds = elapsed(t0, t1);
    if (!direct)
        p = detail::pack_slices(sa, sb, m, n, k, depth, prep);
    sa = {};
    sb = {};
    const auto t2 = Clock::now();
    t.pack_seconds = elapsed(t1, t2);
    detail::AlignedBuffer<T> result(checked_mul(m, n));
    // 每个线程先写自己的私有 C 块并检查结果；全部通过后才统一提交到调用方的 C。
    // Compact FP32 macroblocks reduce the current-BK operand footprint in the
    // measured 4096..8192 range. BK boundaries and component-add order stay
    // unchanged. Other domains use the original wide geometry.
    const bool small = std::min(m, n) < 1024;
    // cb 和 cbn 表示一个输出任务负责多少行、多少列 C, 可以与 BM/BN =不同
    const std::size_t cb = small ? 32 : (CompactWide ? 256 : CACHE_BLOCK);
    const std::size_t cbn =
        small ? 32
              : (CompactWide
                     ? 256
                     : (Wide ? (std::is_same_v<T, float> || depth <= 4 ? 512 : 256) : CACHE_BLOCK));
    // nr 和 nc 分别表示行列的任务数, work 表示总输出任务数
    const std::size_t nr = ceil_div(m, cb), nc = ceil_div(n, cbn), work = checked_mul(nr, nc);
    // 启动 wide 时, 每行额外增加 64 字节填充, 有效输出仍只有 cbn 列
    const std::size_t stride = cbn + (Wide ? 64 / sizeof(T) : 0);
    // block_rows、block_cols 时编译器确定的缓冲区容量上界, 实际使用量由运行时的 cb、stride 决定
    constexpr std::size_t block_rows = CompactWide ? 256 : CACHE_BLOCK;
    constexpr std::size_t block_cols = CompactWide ? 256 + (Wide ? 64 / sizeof(T) : 0)
                                                   : (Wide ? 512 + 64 / sizeof(T) : CACHE_BLOCK);
    const auto granularity = std::min(m, n) < 1024 ? tuning::min_compute_work : 1;
    const int nt = detail::team_size(requested_threads(),
                                     std::max<std::size_t>(1, ceil_div(work, granularity)));
    int bad = 0;
// 并行计算时, 每个线程负责不同的输出块
#pragma omp parallel num_threads(nt) if (nt > 1) reduction(| : bad)
    {
        // Process permission was granted before entry; each task configures its tile state.
        // 此时有几个不同层次的缓冲区
        // p            打包后的 A、B 分量           所有线程只读
        // micro        一个 32×32 的FP临时结果      每个线程各一份, 供 FP32 路径使用
        // block        当前输出任务的累加结果        每个线程各一份, 完成任务后使用
        // result       完整的 M×N 结果矩阵          多线程写不同的区域
        // c            调用者提供的最终输出          最后统一写入
        load_config();
        alignas(64) T block[block_rows * block_cols];
        alignas(64) float micro[TM * TN];
#pragma omp for schedule(static)
        for (std::size_t w = 0; w < work; ++w) {
            // 每个任务先找到自己负责的 C 区域, 再从零开始累加
            const auto row = (tuning::mn_order ? w % nr : w / nc) * cb;     // 输出块的起始横坐标
            const auto col = (tuning::mn_order ? w / nr : w % nc) * cbn;    // 输出块的起始纵坐标
            const auto rows = std::min(cb, m - row), cols = std::min(cbn, n - col); // 实际有效行列数
            zero_block(block, cb * stride); // 清零鲜橙该有累加区
            // 计算一个 32×32 微块在某个 K 分块上的贡献
            const auto compute_at = [&](std::size_t kb, std::size_t i, std::size_t j) {
                // kb: 第几个 K 分块
                // i、j: 当前输出块内部的微块起始坐标
                // 确定要执行多少个 K32 步进
                const unsigned steps = unsigned(ceil_div(std::min(BK, k - kb * BK), TK));
                // 将输出位置映射到打包面板, mb、nb 时打包块编号, mi、nj 是块内位置
                const auto mb = (row + i) / BM,
                           nb = (col + j) / BN,
                           mi = (row + i) % BM,
                           nj = (col + j) % BN;
                // 不同精度的结果进行累加
                if constexpr (std::is_same_v<T, float>) {
                    run_fp32_micro<3>(p, mb, nb, kb, mi, nj, micro, steps);
                    accumulate32(block + i * stride + j, micro, stride, bad);
                } else {
                    run_fp64_batch<Late64, (Wide ? 2 : 1)>(block + i * stride + j, stride, p, mb,
                                                           nb, kb, mi, nj, steps, depth, bad);
                }
            };
            if constexpr (tuning::loop_order == 0) {
                for (std::size_t kb = 0; kb < p.kblocks; ++kb)
                    for (std::size_t i = 0; i < rows; i += TM)
                        for (std::size_t j = 0; j < cols; j += TN)
                            compute_at(kb, i, j);
            } else {
                for (std::size_t i = 0; i < rows; i += TM)
                    for (std::size_t j = 0; j < cols; j += TN)
                        for (std::size_t kb = 0; kb < p.kblocks; ++kb)
                            compute_at(kb, i, j);
            }
            // Pure addition cannot turn an Inf/NaN component back into a finite
            // value. Long-K calls classify the finished private block once.
            if constexpr (Late64)
                for (std::size_t q = 0; q < cb * stride; q += 8)
                    bad |= nonfinite(_mm512_load_pd(block + q));
            // 复制结果到 result
            for (std::size_t i = 0; i < rows; ++i)
                copy_row(result.data() + (row + i) * n + col, block + i * stride, cols);
        }
        _tile_release();
    }
    if (bad)
        throw Error("AMX component product or reconstructed output became non-finite");
    // 所有线程完成、错误标记合并后, 通过检查才可以执行最后一次并行复制
#pragma omp parallel for num_threads(nt) if (nt > 1) schedule(static)
    for (std::size_t i = 0; i < m; ++i)
        copy_row(c + i * ldc, result.data() + i * n, n);
    const auto t3 = Clock::now();
    t.compute_and_reconstruct_seconds = elapsed(t2, t3);
    t.total_seconds = elapsed(t0, t3);
    return t;
}
} // namespace
namespace detail {
GemmTimings gemm_fp32_native(std::size_t m, std::size_t n, std::size_t k, const float* a,
                             std::size_t lda, const float* b, std::size_t ldb, float* c,
                             std::size_t ldc) {
#if OZAMX_STRICT_PATH
    return gemm_strict_emulation_impl(m, n, k, a, lda, b, ldb, c, ldc, 3);
#else
    if (std::min(m, n) >= 4096) {
        // CACHE_BLOCK=128 且尺寸落在 4096..8192 时启用紧凑宽域几何，降低工作集。
        if (CACHE_BLOCK == 128 && std::max(m, n) <= 8192 && k >= 4096 && k <= 8192)
            return gemm_impl<float, false, true, true>(m, n, k, a, lda, b, ldb, c, ldc, 3);
        return gemm_impl<float, false, true>(m, n, k, a, lda, b, ldb, c, ldc, 3);
    }
    return gemm_impl<float, false, false>(m, n, k, a, lda, b, ldb, c, ldc, 3);
#endif
}
GemmTimings gemm_fp64_native(std::size_t m, std::size_t n, std::size_t k, const double* a,
                             std::size_t lda, const double* b, std::size_t ldb, double* c,
                             std::size_t ldc, ProductBudget budget) {
    const auto depth = budget_depth(budget);
#if OZAMX_STRICT_PATH
    return gemm_strict_emulation_impl(m, n, k, a, lda, b, ldb, c, ldc, depth);
#else
    if (std::min(m, n) >= 4096) {
        if (k >= 4096)
            return gemm_impl<double, true, true>(m, n, k, a, lda, b, ldb, c, ldc, depth);
        return gemm_impl<double, false, true>(m, n, k, a, lda, b, ldb, c, ldc, depth);
    }
    if (k >= 4096)
        return gemm_impl<double, true, false>(m, n, k, a, lda, b, ldb, c, ldc, depth);
    return gemm_impl<double, false, false>(m, n, k, a, lda, b, ldb, c, ldc, depth);
#endif
}
} // namespace detail
} // namespace ozamx
