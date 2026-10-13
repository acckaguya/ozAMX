#include "ozamx/gemm.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <limits>
#include <memory>
#include <sstream>
#include <vector>
#include <immintrin.h>
#ifdef _OPENMP
#include <omp.h>
#endif

namespace ozamx {
namespace {

constexpr std::size_t BM=256, BN=256, BK=256, TM=32, TN=32, TK=32;
using Clock = std::chrono::steady_clock;
double elapsed(Clock::time_point a, Clock::time_point b) {
    return std::chrono::duration<double>(b-a).count();
}
std::size_t ceil_div(std::size_t x, std::size_t y) { return x/y + (x%y != 0); }
std::size_t checked_mul(std::size_t a, std::size_t b) {
    if (b && a > std::numeric_limits<std::size_t>::max()/b) throw Error("matrix size overflow");
    return a*b;
}

bool try_float_to_bf16(float x, std::uint16_t& result) noexcept {
    std::uint32_t u;
    std::memcpy(&u, &x, sizeof(u));
    const std::uint32_t exp = (u >> 23) & 0xffu;
    if (exp == 0xffu) return false;
    if ((u & 0x7fffffffu) != 0 && exp == 0) return false;
    const std::uint32_t lsb = (u >> 16) & 1u;
    u += 0x7fffu + lsb;
    const std::uint16_t h = static_cast<std::uint16_t>(u >> 16);
    const std::uint16_t he = (h >> 7) & 0xffu;
    if (he == 0xffu) return false;
    if ((h & 0x7fffu) != 0 && he == 0) return false;
    result = h;
    return true;
}
float bf16_to_float(std::uint16_t h) {
    const std::uint32_t u = static_cast<std::uint32_t>(h) << 16;
    float x;
    std::memcpy(&x, &u, sizeof(x));
    return x;
}

constexpr double FP64_MIN_NORMAL = 0x1p-126;
constexpr double FP64_MAX_BF16 = (2.0 - 0x1p-7) * 0x1p127;

// Computes ceil(log2(max |R|)) without a libm rounding ambiguity at powers of two.
int ceil_log2(double x) {
    int e = 0;
    const double f = std::frexp(x, &e);
    return f == 0.5 ? e-1 : e;
}

void split32(const float* src, std::size_t count, std::vector<std::uint16_t>& dst) {
    dst.resize(checked_mul(count,3));
    int invalid=0;
#pragma omp parallel for reduction(|:invalid) schedule(static) if(count > 16384)
    for (std::size_t q=0; q<count; ++q) {
        float r = src[q];
        int bad=0;
        for (int s=0; s<3; ++s) {
            std::uint16_t bits;
            if (!try_float_to_bf16(r, bits)) { bad=1; break; }
            dst[static_cast<std::size_t>(s)*count+q] = bits;
            r = static_cast<float>(r - bf16_to_float(bits));
            if (!std::isfinite(r) || (r != 0.0f && !std::isnormal(r))) { bad=1; break; }
        }
        if (bad) invalid=1;
    }
    if (invalid)
        throw Error("FP32 input/residual is non-finite or outside the supported normal range");
}

void split64(const double* src, std::size_t count, std::vector<std::uint16_t>& dst) {
    dst.resize(checked_mul(count,6));
    // Leave allocation untouched here; the first parallel input pass writes
    // every element and performs the page first-touch on its owning worker.
    std::unique_ptr<double[]> residual(new double[count]);
    int input_invalid=0;
#pragma omp parallel for reduction(|:input_invalid) schedule(static) if(count > 16384)
    for (std::size_t q=0;q<count;++q) {
        const double x=src[q];
        if (!std::isfinite(x) || (x!=0.0 && (std::abs(x)<FP64_MIN_NORMAL || std::abs(x)>FP64_MAX_BF16))) input_invalid=1;
        residual[q]=x;
    }
    if (input_invalid) throw Error("FP64 inputs must be finite and lie within the normal BF16 exponent range");
    for (int s=0; s<6; ++s) {
        double maxabs = 0.0;
#pragma omp parallel for reduction(max:maxabs) schedule(static) if(count > 16384)
        for (std::size_t q=0;q<count;++q) maxabs = std::max(maxabs, std::abs(residual[q]));
        if (maxabs == 0.0) {
            std::fill(dst.begin()+static_cast<std::size_t>(s)*count,
                      dst.begin()+static_cast<std::size_t>(s+1)*count, 0);
            continue;
        }
        const int v = ceil_log2(maxabs);
        const double sigma = std::ldexp(1.0, v+45);
        int slice_invalid=0;
#pragma omp parallel for reduction(|:slice_invalid) schedule(static) if(count > 16384)
        for (std::size_t q=0; q<count; ++q) {
            const double r = residual[q];
            const double z = (r + sigma) - sigma;
            const float zf = static_cast<float>(z);
            std::uint16_t bits;
            if (!try_float_to_bf16(zf, bits) || (bits != 0 && ((bits >> 7) & 0xffu) == 0)) {
                slice_invalid = 1;
                continue;
            }
            dst[static_cast<std::size_t>(s)*count+q] = bits;
            residual[q] = r - static_cast<double>(bf16_to_float(bits));
            if (!std::isfinite(residual[q]) || (residual[q] != 0.0 && !std::isnormal(residual[q]))) slice_invalid=1;
        }
        if (slice_invalid)
            throw Error("FP64 decomposition produced an unsupported slice or residual");
    }
}

struct TileConfig {
    std::uint8_t palette_id, start_row;
    std::uint8_t reserved[14];
    std::uint16_t colsb[16];
    std::uint8_t rows[16];
} __attribute__((packed, aligned(64)));
static_assert(sizeof(TileConfig)==64, "AMX tile configuration must be 64 bytes");

void load_config() {
    TileConfig cfg{};
    cfg.palette_id=1;
    for (int i=0;i<8;++i) { cfg.colsb[i]=64; cfg.rows[i]=16; }
    _tile_loadconfig(&cfg);
}
void zero_accumulators() {
    _tile_zero(4); _tile_zero(5); _tile_zero(6); _tile_zero(7);
}
void store_32x32(float* out) {
    constexpr int stride=TN*static_cast<int>(sizeof(float));
    _tile_stored(4,out,stride);
    _tile_stored(5,out+16,stride);
    _tile_stored(6,out+16*TN,stride);
    _tile_stored(7,out+16*TN+16,stride);
}

struct Packed32 {
    std::array<std::unique_ptr<std::uint16_t[]>,3> a, b;
    std::size_t mblocks, nblocks, kblocks;
};
struct Packed64 {
    std::array<std::unique_ptr<std::uint16_t[]>,6> a, b;
    std::size_t mblocks, nblocks, kblocks;
};

template<int S>
std::size_t apanel_index(std::size_t mb, std::size_t kb, std::size_t mi,
                         std::size_t kk, std::size_t kblocks) {
    (void)S;
    return ((mb*kblocks+kb)*BM*BK + mi*BK + kk);
}
std::size_t bpanel_index(std::size_t kb, std::size_t nb, std::size_t kp,
                         std::size_t nj, std::size_t nblocks) {
    return ((kb*nblocks+nb)*BK*BN + kp*BN*2 + nj*2);
}

template<std::size_t NS>
Packed32 pack32(const std::vector<std::uint16_t>& sa, const std::vector<std::uint16_t>& sb,
                std::size_t m, std::size_t n, std::size_t k) {
    Packed32 p;
    p.mblocks=ceil_div(m,BM); p.nblocks=ceil_div(n,BN); p.kblocks=ceil_div(k,BK);
    const std::size_t ma=checked_mul(checked_mul(p.mblocks,p.kblocks),BM*BK);
    const std::size_t nb=checked_mul(checked_mul(p.kblocks,p.nblocks),BK*BN);
    const std::size_t ac=checked_mul(m,k), bc=checked_mul(k,n);
    for (std::size_t s=0;s<NS;++s) {
        // Uninitialized storage avoids serial value-initialization. The
        // parallel loops below write every element, including edge padding.
        p.a[s].reset(new std::uint16_t[ma]); p.b[s].reset(new std::uint16_t[nb]);
        const auto* as=sa.data()+s*ac;
        const auto* bs=sb.data()+s*bc;
        const std::size_t awork=checked_mul(checked_mul(p.mblocks,p.kblocks),BM);
#pragma omp parallel for schedule(static) if(ac > 16384)
        for (std::size_t u=0;u<awork;++u) {
            const std::size_t mb=u/(p.kblocks*BM), rem=u%(p.kblocks*BM);
            const std::size_t kb=rem/BM, i=rem%BM;
            for (std::size_t q=0;q<BK;++q) {
                const std::size_t gi=mb*BM+i, gk=kb*BK+q;
                p.a[s][apanel_index<0>(mb,kb,i,q,p.kblocks)] = (gi<m && gk<k) ? as[gi*k+gk] : 0;
            }
        }
        const std::size_t bwork=checked_mul(checked_mul(p.kblocks,p.nblocks),BK/2*BN);
#pragma omp parallel for schedule(static) if(bc > 16384)
        for (std::size_t u=0;u<bwork;++u) {
            const std::size_t panel_rows=(BK/2)*BN;
            const std::size_t kb=u/(p.nblocks*panel_rows), rem=u%(p.nblocks*panel_rows);
            const std::size_t nbk=rem/panel_rows, inner=rem%panel_rows;
            const std::size_t kp=inner/BN, j=inner%BN;
            const std::size_t gk=kb*BK+2*kp, gn=nbk*BN+j;
            auto* d=p.b[s].get()+bpanel_index(kb,nbk,kp,j,p.nblocks);
            d[0]=(gk<k && gn<n) ? bs[gk*n+gn] : 0;
            d[1]=(gk+1<k && gn<n) ? bs[(gk+1)*n+gn] : 0;
        }
    }
    return p;
}

template<std::size_t NS>
Packed64 pack64(const std::vector<std::uint16_t>& sa, const std::vector<std::uint16_t>& sb,
                std::size_t m, std::size_t n, std::size_t k) {
    Packed64 p;
    p.mblocks=ceil_div(m,BM); p.nblocks=ceil_div(n,BN); p.kblocks=ceil_div(k,BK);
    const std::size_t ma=checked_mul(checked_mul(p.mblocks,p.kblocks),BM*BK);
    const std::size_t nb=checked_mul(checked_mul(p.kblocks,p.nblocks),BK*BN);
    const std::size_t ac=checked_mul(m,k), bc=checked_mul(k,n);
    for (std::size_t s=0;s<NS;++s) {
        p.a[s].reset(new std::uint16_t[ma]); p.b[s].reset(new std::uint16_t[nb]);
        const auto* as=sa.data()+s*ac;
        const auto* bs=sb.data()+s*bc;
        const std::size_t awork=checked_mul(checked_mul(p.mblocks,p.kblocks),BM);
#pragma omp parallel for schedule(static) if(ac > 16384)
        for (std::size_t u=0;u<awork;++u) {
            const std::size_t mb=u/(p.kblocks*BM), rem=u%(p.kblocks*BM);
            const std::size_t kb=rem/BM, i=rem%BM;
            for (std::size_t q=0;q<BK;++q) {
                const std::size_t gi=mb*BM+i, gk=kb*BK+q;
                p.a[s][apanel_index<0>(mb,kb,i,q,p.kblocks)] = (gi<m && gk<k) ? as[gi*k+gk] : 0;
            }
        }
        const std::size_t bwork=checked_mul(checked_mul(p.kblocks,p.nblocks),BK/2*BN);
#pragma omp parallel for schedule(static) if(bc > 16384)
        for (std::size_t u=0;u<bwork;++u) {
            const std::size_t panel_rows=(BK/2)*BN;
            const std::size_t kb=u/(p.nblocks*panel_rows), rem=u%(p.nblocks*panel_rows);
            const std::size_t nbk=rem/panel_rows, inner=rem%panel_rows;
            const std::size_t kp=inner/BN, j=inner%BN;
            const std::size_t gk=kb*BK+2*kp, gn=nbk*BN+j;
            auto* d=p.b[s].get()+bpanel_index(kb,nbk,kp,j,p.nblocks);
            d[0]=(gk<k && gn<n) ? bs[gk*n+gn] : 0;
            d[1]=(gk+1<k && gn<n) ? bs[(gk+1)*n+gn] : 0;
        }
    }
    return p;
}

template<std::size_t NS>
void run_fp32_micro(const Packed32& p, std::size_t mb, std::size_t nb,
                    std::size_t kb, std::size_t mi, std::size_t nj, float* panel_out) {
    zero_accumulators();
    int olda=-1, oldb=-1;
    constexpr int ai[6]={1,1,2,0,0,0};
    constexpr int bi[6]={1,0,0,0,1,2};
    for (std::size_t kk=0;kk<BK;kk+=TK) {
      for (int t=0;t<6;++t) {
        const int x=ai[t], y=bi[t];
        const auto* abase=p.a[x].get()+apanel_index<0>(mb,kb,mi,0,p.kblocks);
        const auto* bbase=p.b[y].get()+bpanel_index(kb,nb,kk/2,nj,p.nblocks);
        if (x!=olda) {
            _tile_loadd(0,abase+kk,static_cast<int>(BK*sizeof(std::uint16_t)));
            _tile_loadd(1,abase+kk+16*BK,static_cast<int>(BK*sizeof(std::uint16_t)));
            olda=x;
        }
        if (y!=oldb) {
            _tile_loadd(2,bbase,static_cast<int>(BN*2*sizeof(std::uint16_t)));
            _tile_loadd(3,bbase+16*2,static_cast<int>(BN*2*sizeof(std::uint16_t)));
            oldb=y;
        }
        _tile_dpbf16ps(4,0,2); _tile_dpbf16ps(5,0,3);
        _tile_dpbf16ps(6,1,2); _tile_dpbf16ps(7,1,3);
      }
    }
    store_32x32(panel_out);
}

template<std::size_t NS>
void run_fp64_product(const Packed64& p, int ai, int bi,
                      std::size_t mb, std::size_t nb, std::size_t kb,
                      std::size_t mi, std::size_t nj, float* product_out) {
    zero_accumulators();
    for (std::size_t kk=0;kk<BK;kk+=TK) {
        const auto* abase=p.a[ai].get()+apanel_index<0>(mb,kb,mi,0,p.kblocks);
        const auto* bbase=p.b[bi].get()+bpanel_index(kb,nb,kk/2,nj,p.nblocks);
        _tile_loadd(0,abase+kk,static_cast<int>(BK*sizeof(std::uint16_t)));
        _tile_loadd(1,abase+kk+16*BK,static_cast<int>(BK*sizeof(std::uint16_t)));
        _tile_loadd(2,bbase,static_cast<int>(BN*2*sizeof(std::uint16_t)));
        _tile_loadd(3,bbase+16*2,static_cast<int>(BN*2*sizeof(std::uint16_t)));
        _tile_dpbf16ps(4,0,2); _tile_dpbf16ps(5,0,3);
        _tile_dpbf16ps(6,1,2); _tile_dpbf16ps(7,1,3);
    }
    store_32x32(product_out);
}

bool require_thread_permission(std::string& message) {
    const auto s=request_amx_permission_for_current_thread();
    message=s.message;
    return s.permission_available;
}

template<typename T>
void validate_layout(std::size_t m,std::size_t n,std::size_t k,
                     const T* a,std::size_t lda,const T* b,std::size_t ldb,
                     T* c,std::size_t ldc) {
    if (m==0 || n==0) throw Error("M and N must be positive");
    if (lda<k || ldb<n || ldc<n) throw Error("row-major leading dimensions are too small");
    if (m && k && !a) throw Error("A pointer is null");
    if (k && n && !b) throw Error("B pointer is null");
    if (m && n && !c) throw Error("C pointer is null");
    (void)checked_mul(m,k); (void)checked_mul(k,n); (void)checked_mul(m,n);
}

} // namespace

GemmTimings gemm_fp32_profiled(std::size_t m,std::size_t n,std::size_t k,
                               const float* a,std::size_t lda,const float* b,std::size_t ldb,
                               float* c,std::size_t ldc) {
    validate_layout(m,n,k,a,lda,b,ldb,c,ldc);
    GemmTimings timing;
    if (k==0) {
        const auto t=Clock::now();
        for (std::size_t i=0;i<m;++i) std::fill(c+i*ldc,c+i*ldc+n,0.0f);
        timing.total_seconds=elapsed(t,Clock::now());
        return timing;
    }
    const auto host_status=request_amx_permission_for_current_thread();
    if (!host_status.cpu_amx_tile || !host_status.cpu_amx_bf16 || !host_status.permission_available)
        throw Error("AMX-BF16 is unavailable for this process/thread: "+host_status.message);
    auto t0=Clock::now();
    const std::size_t asz=checked_mul(m,k), bsz=checked_mul(k,n);
    std::vector<float> acopy, bcopy;
    const float* ap=a; const float* bp=b;
    if (lda!=k) {
        acopy.resize(asz); int invalid=0;
#pragma omp parallel for reduction(|:invalid) schedule(static) if(asz > 16384)
        for(std::size_t q=0;q<asz;++q){const std::size_t i=q/k,j=q%k;const float x=a[i*lda+j];if(!std::isfinite(x)||(x!=0.0f&&!std::isnormal(x)))invalid=1;acopy[q]=x;}
        if(invalid) throw Error("FP32 inputs must be finite normal values or zero");
        ap=acopy.data();
    }
    if (ldb!=n) {
        bcopy.resize(bsz); int invalid=0;
#pragma omp parallel for reduction(|:invalid) schedule(static) if(bsz > 16384)
        for(std::size_t q=0;q<bsz;++q){const std::size_t i=q/n,j=q%n;const float x=b[i*ldb+j];if(!std::isfinite(x)||(x!=0.0f&&!std::isnormal(x)))invalid=1;bcopy[q]=x;}
        if(invalid) throw Error("FP32 inputs must be finite normal values or zero");
        bp=bcopy.data();
    }
    std::vector<std::uint16_t> as,bs;
    split32(ap,asz,as); split32(bp,bsz,bs);
    auto t1=Clock::now(); timing.split_seconds=elapsed(t0,t1);
    auto packed=pack32<3>(as,bs,m,n,k);
    auto t2=Clock::now(); timing.pack_seconds=elapsed(t1,t2);

    std::vector<float> result(checked_mul(m,n),0.0f);
    const std::size_t work=checked_mul(packed.mblocks,packed.nblocks);
    int failed=0; std::string failure;
#pragma omp parallel shared(failed,failure,packed,result)
    {
        std::string message;
        const bool permitted=require_thread_permission(message);
        if (!permitted) {
#pragma omp critical
            { if (!failed) failure=message; failed=1; }
        } else {
            load_config();
            float block[BM*BN];
            float micro[TM*TN];
#pragma omp for schedule(static)
            for (std::size_t w=0;w<work;++w) {
                const std::size_t mb=w/packed.nblocks, nb=w%packed.nblocks;
                std::fill(block,block+BM*BN,0.0f);
                for (std::size_t kb=0;kb<packed.kblocks;++kb)
                 for (std::size_t mi=0;mi<BM;mi+=TM)
                  for (std::size_t nj=0;nj<BN;nj+=TN) {
                    run_fp32_micro<3>(packed,mb,nb,kb,mi,nj,micro);
                    for (std::size_t ii=0;ii<TM;++ii)
                     for (std::size_t jj=0;jj<TN;++jj) {
                        float& out=block[(mi+ii)*BN+nj+jj];
                        out=static_cast<float>(out+micro[ii*TN+jj]);
                     }
                  }
                for (std::size_t i=0;i<BM && mb*BM+i<m;++i)
                 for (std::size_t j=0;j<BN && nb*BN+j<n;++j)
                    result[(mb*BM+i)*n+nb*BN+j]=block[i*BN+j];
            }
            _tile_release();
        }
    }
    if (failed) throw Error("AMX permission unavailable on an OpenMP worker: "+failure);
    for (float x:result) if (!std::isfinite(x)) throw Error("AMX-FP32 output overflowed or became non-finite");
    for (std::size_t i=0;i<m;++i) std::copy(result.data()+i*n,result.data()+(i+1)*n,c+i*ldc);
    auto t3=Clock::now(); timing.compute_and_reconstruct_seconds=elapsed(t2,t3);
    timing.total_seconds=elapsed(t0,t3);
    return timing;
}

GemmTimings gemm_fp64_profiled(std::size_t m,std::size_t n,std::size_t k,
                               const double* a,std::size_t lda,const double* b,std::size_t ldb,
                               double* c,std::size_t ldc,ProductBudget budget) {
    validate_layout(m,n,k,a,lda,b,ldb,c,ldc);
    int depth=0;
    switch (budget) { case ProductBudget::p6:depth=3;break; case ProductBudget::p10:depth=4;break;
        case ProductBudget::p15:depth=5;break; case ProductBudget::p21:depth=6;break;
        default:throw Error("invalid FP64 product budget"); }
    GemmTimings timing;
    if (k==0) {
        const auto t=Clock::now();
        for (std::size_t i=0;i<m;++i) std::fill(c+i*ldc,c+i*ldc+n,0.0);
        timing.total_seconds=elapsed(t,Clock::now());
        return timing;
    }
    const auto host_status=request_amx_permission_for_current_thread();
    if (!host_status.cpu_amx_tile || !host_status.cpu_amx_bf16 || !host_status.permission_available)
        throw Error("AMX-BF16 is unavailable for this process/thread: "+host_status.message);
    auto t0=Clock::now();
    const std::size_t asz=checked_mul(m,k), bsz=checked_mul(k,n);
    std::vector<double> acopy, bcopy;
    const double* ap=a; const double* bp=b;
    if (lda!=k) {
        acopy.resize(asz); int invalid=0;
#pragma omp parallel for reduction(|:invalid) schedule(static) if(asz > 16384)
        for(std::size_t q=0;q<asz;++q){const std::size_t i=q/k,j=q%k;const double x=a[i*lda+j];if(!std::isfinite(x)||(x!=0.0&&(std::abs(x)<FP64_MIN_NORMAL||std::abs(x)>FP64_MAX_BF16)))invalid=1;acopy[q]=x;}
        if(invalid) throw Error("FP64 inputs must be finite and lie within the normal BF16 exponent range");
        ap=acopy.data();
    }
    if (ldb!=n) {
        bcopy.resize(bsz); int invalid=0;
#pragma omp parallel for reduction(|:invalid) schedule(static) if(bsz > 16384)
        for(std::size_t q=0;q<bsz;++q){const std::size_t i=q/n,j=q%n;const double x=b[i*ldb+j];if(!std::isfinite(x)||(x!=0.0&&(std::abs(x)<FP64_MIN_NORMAL||std::abs(x)>FP64_MAX_BF16)))invalid=1;bcopy[q]=x;}
        if(invalid) throw Error("FP64 inputs must be finite and lie within the normal BF16 exponent range");
        bp=bcopy.data();
    }
    std::vector<std::uint16_t> as,bs;
    split64(ap,asz,as); split64(bp,bsz,bs);
    auto t1=Clock::now(); timing.split_seconds=elapsed(t0,t1);
    auto packed=pack64<6>(as,bs,m,n,k);
    auto t2=Clock::now(); timing.pack_seconds=elapsed(t1,t2);

    std::vector<double> result(checked_mul(m,n),0.0);
    const std::size_t work=checked_mul(packed.mblocks,packed.nblocks);
    int failed=0; std::string failure;
#pragma omp parallel shared(failed,failure,packed,result)
    {
        std::string message;
        const bool permitted=require_thread_permission(message);
        if (!permitted) {
#pragma omp critical
            { if (!failed) failure=message; failed=1; }
        } else {
            load_config();
            double block[BM*BN];
            float micro[TM*TN];
#pragma omp for schedule(static)
            for (std::size_t w=0;w<work;++w) {
                const std::size_t mb=w/packed.nblocks, nb=w%packed.nblocks;
                std::fill(block,block+BM*BN,0.0);
                for (std::size_t kb=0;kb<packed.kblocks;++kb)
                 for (std::size_t mi=0;mi<BM;mi+=TM)
                  for (std::size_t nj=0;nj<BN;nj+=TN) {
                    for (int diagonal=0;diagonal<depth;++diagonal)
                     for (int ai=0;ai<=diagonal;++ai) {
                        const int bi=diagonal-ai;
                        run_fp64_product<6>(packed,ai,bi,mb,nb,kb,mi,nj,micro);
                        for (std::size_t ii=0;ii<TM;++ii)
                         for (std::size_t jj=0;jj<TN;++jj) {
                            if (!std::isfinite(micro[ii*TN+jj])) {
#pragma omp critical
                                { if (!failed) failure="AMX FP32 component product overflowed"; failed=1; }
                            } else {
                                block[(mi+ii)*BN+nj+jj] += static_cast<double>(micro[ii*TN+jj]);
                            }
                         }
                     }
                  }
                for (std::size_t i=0;i<BM && mb*BM+i<m;++i)
                 for (std::size_t j=0;j<BN && nb*BN+j<n;++j)
                    result[(mb*BM+i)*n+nb*BN+j]=block[i*BN+j];
            }
            _tile_release();
        }
    }
    if (failed) throw Error("AMX worker or FP32 component product failed: "+failure);
    for (double x:result) if (!std::isfinite(x)) throw Error("AMX-FP64 output overflowed or became non-finite");
    for (std::size_t i=0;i<m;++i) std::copy(result.data()+i*n,result.data()+(i+1)*n,c+i*ldc);
    auto t3=Clock::now(); timing.compute_and_reconstruct_seconds=elapsed(t2,t3);
    timing.total_seconds=elapsed(t0,t3);
    return timing;
}

void gemm_fp32(std::size_t m,std::size_t n,std::size_t k,const float* a,std::size_t lda,
               const float* b,std::size_t ldb,float* c,std::size_t ldc) {
    (void)gemm_fp32_profiled(m,n,k,a,lda,b,ldb,c,ldc);
}
void gemm_fp64(std::size_t m,std::size_t n,std::size_t k,const double* a,std::size_t lda,
               const double* b,std::size_t ldb,double* c,std::size_t ldc,ProductBudget budget) {
    (void)gemm_fp64_profiled(m,n,k,a,lda,b,ldb,c,ldc,budget);
}

const char* product_order_fp32() noexcept { return "11,10,20,00,01,02"; }
const char* product_order_fp64(ProductBudget budget) noexcept {
    switch (budget) {
    case ProductBudget::p6:return "00;01,10;02,11,20";
    case ProductBudget::p10:return "00;01,10;02,11,20;03,12,21,30";
    case ProductBudget::p15:return "00;01,10;02,11,20;03,12,21,30;04,13,22,31,40";
    case ProductBudget::p21:return "00;01,10;02,11,20;03,12,21,30;04,13,22,31,40;05,14,23,32,41,50";
    }
    return "invalid";
}

} // namespace ozamx
