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
#if defined(__linux__)
#include <sys/syscall.h>
#include <unistd.h>
#endif
#include <immintrin.h>
#ifdef _OPENMP
#include <omp.h>
#endif

extern "C" void ozamx_bf16_six(const std::uint16_t* const*,const std::uint16_t* const*,float*,unsigned);
extern "C" void ozamx_bf16_product(const std::uint16_t*,const std::uint16_t*,float*,unsigned);
namespace ozamx {
namespace {
constexpr std::size_t BM=256,BN=256,BK=256,TM=32,TN=32,TK=32,CACHE_BLOCK=tuning::cache_block;
using Clock=std::chrono::steady_clock;
double elapsed(Clock::time_point a,Clock::time_point b){return std::chrono::duration<double>(b-a).count();}
std::size_t checked_mul(std::size_t a,std::size_t b){return detail::mul(a,b);}
std::size_t ceil_div(std::size_t a,std::size_t b){return detail::divup(a,b);}
[[maybe_unused]] float bf16_to_float(std::uint16_t h){return detail::bf_float(h);}
int requested_threads(){
#ifdef _OPENMP
    return omp_in_parallel()?1:omp_get_max_threads();
#else
    return 1;
#endif
}
int preprocessing_threads(std::size_t count){return detail::team_size(requested_threads(),std::max<std::size_t>(1,ceil_div(count,tuning::prep_grain)));}
struct alignas(64) TileConfig {std::uint8_t palette_id=1,start_row=0,reserved[14]{};std::uint16_t colsb[16]{};std::uint8_t rows[16]{};};
static_assert(sizeof(TileConfig)==64);
constexpr TileConfig make_config(){TileConfig x{};for(int i=0;i<8;++i){x.colsb[i]=64;x.rows[i]=16;}return x;}
void load_config(){static constexpr auto cfg=make_config();_tile_loadconfig(&cfg);}
[[maybe_unused]] void zero_accumulators(){_tile_zero(4);_tile_zero(5);_tile_zero(6);_tile_zero(7);}
[[maybe_unused]] void store_32x32(float* out){_tile_stored(4,out,128);_tile_stored(5,out+16,128);_tile_stored(6,out+512,128);_tile_stored(7,out+528,128);}
using Packed32=detail::Packed;
using Packed64=detail::Packed;
// Panel storage consists of contiguous 1 KiB tiles. These mappings also expose
// logical element addresses to the independent packing/layout diagnostics.
template<int S>std::size_t apanel_index(std::size_t mb,std::size_t kb,std::size_t mi,std::size_t kk,std::size_t kblocks){
    (void)S;
    return (mb*kblocks+kb)*BM*BK+(mi/TM)*TM*BK+(kk/TK)*TM*TK+
           ((mi%TM)/16)*16*TK+(mi%16)*TK+kk%TK;
}
std::size_t bpanel_index(std::size_t kb,std::size_t nb,std::size_t kp,std::size_t nj,std::size_t nblocks){
    return (kb*nblocks+nb)*BK*BN+(nj/TN)*TN*BK+(kp/(TK/2))*TN*TK+
           ((nj%TN)/16)*512+(kp%(TK/2))*32+(nj%16)*2;
}
using BReplicas=std::array<std::array<detail::AlignedBuffer<std::uint16_t>,6>,2>;
int current_numa_node() noexcept {
#if defined(__linux__) && defined(SYS_getcpu)
    unsigned cpu=0,node=0;
    if(::syscall(SYS_getcpu,&cpu,&node,nullptr)==0)return static_cast<int>(node);
#endif
    return -1;
}
void replicate_packed_b(const Packed32& p,BReplicas& replicas,int nt,GemmTimings& timing){
    for(int node=0;node<2;++node)for(int s=0;s<p.slices;++s)
        replicas[node][s]=detail::AlignedBuffer<std::uint16_t>(p.b[s].size());
    std::vector<int> nodes(std::size_t(nt),-1),ranks(std::size_t(nt),-1);
    int counts[2]={0,0},fallback=0;
    const auto begin=Clock::now();
#pragma omp parallel num_threads(nt) if(nt>1) shared(nodes,ranks,counts,fallback)
    {
        int tid=0,team=1;
#ifdef _OPENMP
        tid=omp_get_thread_num();team=omp_get_num_threads();
#endif
        nodes[std::size_t(tid)]=current_numa_node();
#pragma omp barrier
#pragma omp single
        {
            for(int q=0;q<team;++q){const int node=nodes[std::size_t(q)];
                if(node==0||node==1)ranks[std::size_t(q)]=counts[node]++;
                else ++fallback;
            }
        }
#pragma omp barrier
        for(int node=0;node<2;++node){
            const bool no_local_workers=counts[node]==0;
            if(no_local_workers||nodes[std::size_t(tid)]==node){
                const std::size_t workers=no_local_workers?std::size_t(team):std::size_t(counts[node]);
                const std::size_t rank=no_local_workers?std::size_t(tid):std::size_t(ranks[std::size_t(tid)]);
                for(int s=0;s<p.slices;++s){
                    const std::size_t size=p.b[s].size(),lines=detail::divup(size,std::size_t(32));
                    const std::size_t per=detail::divup(lines,workers),first=std::min(lines,rank*per),last=std::min(lines,first+per);
                    const auto* src=p.b[s].data();auto* dst=replicas[node][s].data();
                    std::size_t i=first*32,end=std::min(size,last*32);
                    for(;i+32<=end;i+=32){const auto v=_mm512_load_si512(src+i);_mm512_store_si512(dst+i,v);}
                    for(;i<end;++i)dst[i]=src[i];
                }
            }
#pragma omp barrier
        }
    }
    timing.replicate_b_seconds=elapsed(begin,Clock::now());
    timing.replicate_node0_workers=counts[0];timing.replicate_node1_workers=counts[1];
    timing.replicate_fallback_workers=fallback;
}
template<std::size_t NS>
void run_fp32_micro(const Packed32& p,std::size_t mb,std::size_t nb,std::size_t kb,std::size_t mi,std::size_t nj,float* out,unsigned steps=BK/TK,const std::array<const std::uint16_t*,6>* bbase=nullptr){
    (void)NS;const auto ai=apanel_index<0>(mb,kb,mi,0,p.kblocks),bi=bpanel_index(kb,nb,0,nj,p.nblocks);
    const std::uint16_t* aa[3]={p.a[0].data()+ai,p.a[1].data()+ai,p.a[2].data()+ai};
    const std::uint16_t* bb[3]={ (bbase?(*bbase)[0]:p.b[0].data())+bi,
                                  (bbase?(*bbase)[1]:p.b[1].data())+bi,
                                  (bbase?(*bbase)[2]:p.b[2].data())+bi};
    ozamx_bf16_six(aa,bb,out,steps);
}
template<std::size_t NS>
void run_fp64_product(const Packed64& p,int ai,int bi,std::size_t mb,std::size_t nb,std::size_t kb,std::size_t mi,std::size_t nj,float* out,unsigned steps=BK/TK,const std::array<const std::uint16_t*,6>* bbase=nullptr){
    (void)NS;ozamx_bf16_product(p.a[ai].data()+apanel_index<0>(mb,kb,mi,0,p.kblocks),(bbase?(*bbase)[bi]:p.b[bi].data())+bpanel_index(kb,nb,0,nj,p.nblocks),out,steps);
}
// Independent diagnostics retain their existing private split/pack API.
// Production uses aligned slices directly and does not take these copy paths.
[[maybe_unused]] void split32(const float* p,std::size_t count,std::vector<std::uint16_t>& out){auto s=detail::split_fp32(p,1,count,count,preprocessing_threads(count));out.assign(s.data.data(),s.data.data()+s.data.size());}
[[maybe_unused]] void split64(const double* p,std::size_t count,std::vector<std::uint16_t>& out){auto s=detail::split_fp64(p,1,count,count,preprocessing_threads(count));out.assign(s.data.data(),s.data.data()+s.data.size());}
template<std::size_t NS>detail::Packed pack_compat(const std::vector<std::uint16_t>& a,const std::vector<std::uint16_t>& b,std::size_t m,std::size_t n,std::size_t k){
    detail::Slices sa,sb;sa.count=checked_mul(m,k);sb.count=checked_mul(k,n);sa.slices=sb.slices=NS;
    sa.data=detail::AlignedBuffer<std::uint16_t>(a.size());sb.data=detail::AlignedBuffer<std::uint16_t>(b.size());
    std::copy(a.begin(),a.end(),sa.data.data());std::copy(b.begin(),b.end(),sb.data.data());
    return detail::pack_slices(sa,sb,m,n,k,NS,preprocessing_threads(std::max(sa.count,sb.count)));
}
template<std::size_t NS>Packed32 pack32(const std::vector<std::uint16_t>& a,const std::vector<std::uint16_t>& b,std::size_t m,std::size_t n,std::size_t k){return pack_compat<NS>(a,b,m,n,k);}
template<std::size_t NS>Packed64 pack64(const std::vector<std::uint16_t>& a,const std::vector<std::uint16_t>& b,std::size_t m,std::size_t n,std::size_t k){return pack_compat<NS>(a,b,m,n,k);}

inline bool nonfinite(__m512 x){return _mm512_cmpeq_epi32_mask(_mm512_and_si512(_mm512_castps_si512(x),_mm512_set1_epi32(0x7f800000)),_mm512_set1_epi32(0x7f800000))!=0;}
inline bool nonfinite(__m512d x){return _mm512_cmpeq_epi64_mask(_mm512_and_si512(_mm512_castpd_si512(x),_mm512_set1_epi64(0x7ff0000000000000LL)),_mm512_set1_epi64(0x7ff0000000000000LL))!=0;}
inline void accumulate32(float* block,const float* micro,std::size_t stride,int& bad){
    for(std::size_t i=0;i<TM;++i)for(std::size_t j=0;j<TN;j+=16){const auto r=_mm512_add_ps(_mm512_load_ps(block+i*stride+j),_mm512_load_ps(micro+i*TN+j));bad|=nonfinite(r);_mm512_store_ps(block+i*stride+j,r);}
}
template<bool Late64=false>
inline void accumulate64(double* block,const float* micro,std::size_t stride,int& bad){
    (void)bad;
    for(std::size_t i=0;i<TM;++i)for(std::size_t j=0;j<TN;j+=16){
        const auto f=_mm512_load_ps(micro+i*TN+j);if constexpr(!Late64)bad|=nonfinite(f);
        const auto lo=_mm512_cvtps_pd(_mm512_castps512_ps256(f)),hi=_mm512_cvtps_pd(_mm512_extractf32x8_ps(f,1));
        const auto r0=_mm512_add_pd(_mm512_load_pd(block+i*stride+j),lo),r1=_mm512_add_pd(_mm512_load_pd(block+i*stride+j+8),hi);
        if constexpr(!Late64)bad|=nonfinite(r0)|nonfinite(r1);
        _mm512_store_pd(block+i*stride+j,r0);_mm512_store_pd(block+i*stride+j+8,r1);
    }
}
template<class T>inline void zero_block(T* p,std::size_t count){for(std::size_t i=0;i<count;i+=64/sizeof(T))_mm512_store_si512(p+i,_mm512_setzero_si512());}
template<class T>void copy_row(T* dst,const T* src,std::size_t n){
    constexpr std::size_t lanes=64/sizeof(T);std::size_t j=0;for(;j+lanes<=n;j+=lanes)_mm512_storeu_si512(dst+j,_mm512_loadu_si512(src+j));
    if(j<n){if constexpr(sizeof(T)==4){const auto mask=__mmask16((1u<<(n-j))-1);_mm512_mask_storeu_ps(dst+j,mask,_mm512_maskz_loadu_ps(mask,src+j));}else{const auto mask=__mmask8((1u<<(n-j))-1);_mm512_mask_storeu_pd(dst+j,mask,_mm512_maskz_loadu_pd(mask,src+j));}}
}
template<class T>void validate_layout(std::size_t m,std::size_t n,std::size_t k,const T* a,std::size_t lda,const T* b,std::size_t ldb,T* c,std::size_t ldc){
    if(!m||!n)throw Error("M and N must be positive");
    if(lda<k||ldb<n||ldc<n)throw Error("row-major leading dimensions are too small");
    if(k&&!a)throw Error("A pointer is null");
    if(k&&!b)throw Error("B pointer is null");
    if(!c)throw Error("C pointer is null");
    (void)checked_mul(m,k);(void)checked_mul(k,n);(void)checked_mul(m,n);
    const auto span=[](std::size_t rows,std::size_t cols,std::size_t ld){if(!rows||!cols)return;const auto off=checked_mul(rows-1,ld);if(off>std::numeric_limits<std::size_t>::max()-cols)throw Error("matrix address span overflow");(void)checked_mul(off+cols,sizeof(T));};
    span(m,k,lda);span(k,n,ldb);span(m,n,ldc);
}
int budget_depth(ProductBudget b){switch(b){case ProductBudget::p6:return 3;case ProductBudget::p10:return 4;case ProductBudget::p15:return 5;case ProductBudget::p21:return 6;}throw Error("invalid FP64 product budget");}
template<class T,bool Late64=false>GemmTimings gemm_impl(std::size_t m,std::size_t n,std::size_t k,const T* a,std::size_t lda,const T* b,std::size_t ldb,T* c,std::size_t ldc,int depth){
    validate_layout(m,n,k,a,lda,b,ldb,c,ldc);GemmTimings t;
    if(!k){const auto z0=Clock::now();for(std::size_t i=0;i<m;++i)std::fill(c+i*ldc,c+i*ldc+n,T(0));t.total_seconds=elapsed(z0,Clock::now());return t;}
    const auto t0=Clock::now();const int prep=preprocessing_threads(std::max(checked_mul(m,k),checked_mul(k,n)));detail::Slices sa,sb;detail::Packed p;bool direct=false;
    if constexpr(std::is_same_v<T,float>){
        if(std::min(m,n)>=1024&&m%256==0&&n%256==0&&k%256==0){p=detail::split_pack_direct32(a,b,m,n,k,lda,ldb,prep);direct=true;}
        else{sa=detail::split_fp32(a,m,k,lda,prep);sb=detail::split_fp32(b,k,n,ldb,prep);}
    }else{
        // All six projections and validations still execute; only slices that
        // participate in this product budget need persistent storage.
        if(std::min(m,n)>=1024&&m%256==0&&n%256==0&&k%256==0){p=detail::split_pack_direct64(a,b,m,n,k,lda,ldb,depth,prep);direct=true;}
        else{sa=detail::split_fp64(a,m,k,lda,prep,depth);sb=detail::split_fp64(b,k,n,ldb,prep,depth);}
    }
    const auto t1=Clock::now();t.split_seconds=elapsed(t0,t1);if(!direct)p=detail::pack_slices(sa,sb,m,n,k,depth,prep);sa={};sb={};
    const std::size_t cb=std::min(m,n)<1024?32:CACHE_BLOCK,nr=ceil_div(m,cb),nc=ceil_div(n,cb),work=checked_mul(nr,nc);
    const auto granularity=std::min(m,n)<1024?tuning::min_compute_work:1;const int nt=detail::team_size(requested_threads(),std::max<std::size_t>(1,ceil_div(work,granularity)));
    BReplicas b_replicas;bool replicas_active=false;
    if constexpr(tuning::numa_replicate_b){
        if(nt>32&&std::min(m,n)>=4096){replicate_packed_b(p,b_replicas,nt,t);replicas_active=true;}
    }
    const auto t2=Clock::now();t.pack_seconds=elapsed(t1,t2);detail::AlignedBuffer<T> result(checked_mul(m,n));
    int bad=0;
#pragma omp parallel num_threads(nt) if(nt>1) reduction(|:bad)
    {
        // Process permission was granted before entry; each task configures its tile state.
        load_config();
        const int node=replicas_active?current_numa_node():-1;
        std::array<const std::uint16_t*,6> bbase{};
        for(int s=0;s<p.slices;++s)bbase[s]=(replicas_active&&(node==0||node==1))?b_replicas[node][s].data():p.b[s].data();
        alignas(64) T block[CACHE_BLOCK*CACHE_BLOCK];alignas(64) float micro[TM*TN];
#pragma omp for schedule(static)
        for(std::size_t w=0;w<work;++w){
            const auto row=(tuning::mn_order?w%nr:w/nc)*cb;
            const auto col=(tuning::mn_order?w/nr:w%nc)*cb;
            const auto rows=std::min(cb,m-row),cols=std::min(cb,n-col);zero_block(block,cb*cb);
            const auto compute_at=[&](std::size_t kb,std::size_t i,std::size_t j){
                    const unsigned steps=unsigned(ceil_div(std::min(BK,k-kb*BK),TK));
                    const auto mb=(row+i)/BM,nb=(col+j)/BN,mi=(row+i)%BM,nj=(col+j)%BN;
                    if constexpr(std::is_same_v<T,float>){run_fp32_micro<3>(p,mb,nb,kb,mi,nj,micro,steps,&bbase);accumulate32(block+i*cb+j,micro,cb,bad);}else{
                        for(int diagonal=0;diagonal<depth;++diagonal)for(int ai=0;ai<=diagonal;++ai){run_fp64_product<6>(p,ai,diagonal-ai,mb,nb,kb,mi,nj,micro,steps,&bbase);accumulate64<Late64>(block+i*cb+j,micro,cb,bad);}
                    }
            };
            if constexpr(tuning::loop_order==0){
                for(std::size_t kb=0;kb<p.kblocks;++kb)
                    for(std::size_t i=0;i<rows;i+=TM)for(std::size_t j=0;j<cols;j+=TN)compute_at(kb,i,j);
            }else{
                for(std::size_t i=0;i<rows;i+=TM)for(std::size_t j=0;j<cols;j+=TN)
                    for(std::size_t kb=0;kb<p.kblocks;++kb)compute_at(kb,i,j);
            }
            // Pure addition cannot turn an Inf/NaN component back into a finite
            // value. Long-K calls classify the finished private block once.
            if constexpr(Late64)for(std::size_t q=0;q<cb*cb;q+=8)bad|=nonfinite(_mm512_load_pd(block+q));
            for(std::size_t i=0;i<rows;++i)copy_row(result.data()+(row+i)*n+col,block+i*cb,cols);
        }
        _tile_release();
    }
    if(bad)throw Error("AMX component product or reconstructed output became non-finite");
#pragma omp parallel for num_threads(nt) if(nt>1) schedule(static)
    for(std::size_t i=0;i<m;++i)copy_row(c+i*ldc,result.data()+i*n,n);
    const auto t3=Clock::now();t.compute_and_reconstruct_seconds=elapsed(t2,t3);t.total_seconds=elapsed(t0,t3);return t;
}
} // namespace
namespace detail {
GemmTimings gemm_fp32_native(std::size_t m,std::size_t n,std::size_t k,const float* a,std::size_t lda,const float* b,std::size_t ldb,float* c,std::size_t ldc){return gemm_impl(m,n,k,a,lda,b,ldb,c,ldc,3);}
GemmTimings gemm_fp64_native(std::size_t m,std::size_t n,std::size_t k,const double* a,std::size_t lda,const double* b,std::size_t ldb,double* c,std::size_t ldc,ProductBudget budget){const auto depth=budget_depth(budget);
    if(k>=4096)return gemm_impl<double,true>(m,n,k,a,lda,b,ldb,c,ldc,depth);
    return gemm_impl<double,false>(m,n,k,a,lda,b,ldb,c,ldc,depth);}
}
} // namespace ozamx
