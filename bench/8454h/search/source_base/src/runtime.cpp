#include "ozamx/gemm.hpp"

#include <cerrno>
#include <algorithm>
#include <atomic>
#include <chrono>
#include <limits>
#include <cstring>
#include <cpuid.h>
#include <sys/syscall.h>
#include <unistd.h>
#include <asm/prctl.h>

#ifndef ARCH_REQ_XCOMP_PERM
#define ARCH_REQ_XCOMP_PERM 0x1023
#endif
#ifndef ARCH_GET_XCOMP_PERM
#define ARCH_GET_XCOMP_PERM 0x1022
#endif
#ifndef XFEATURE_XTILEDATA
#define XFEATURE_XTILEDATA 18
#endif

namespace ozamx {
namespace detail {
GemmTimings gemm_fp32_native(std::size_t,std::size_t,std::size_t,const float*,std::size_t,const float*,std::size_t,float*,std::size_t);
GemmTimings gemm_fp64_native(std::size_t,std::size_t,std::size_t,const double*,std::size_t,const double*,std::size_t,double*,std::size_t,ProductBudget);
}
namespace {
struct Capabilities {bool tile=false,bf16=false,simd=false;};
Capabilities capabilities(){
    Capabilities c;unsigned a=0,b=0,e=0,d=0;
    if(__get_cpuid_max(0,nullptr)<7)return c;
    __get_cpuid_count(7,0,&a,&b,&e,&d);
    c.tile=(d&(1u<<24))!=0;c.bf16=(d&(1u<<22))!=0;
    constexpr unsigned required=(1u<<5)|(1u<<16)|(1u<<17)|(1u<<30)|(1u<<31);
    const bool vector_features=(b&required)==required;
    __get_cpuid_count(7,1,&a,&b,&e,&d);const bool vector_bf16=(a&(1u<<5))!=0;
    __get_cpuid(1,&a,&b,&e,&d);
    if(!(e&(1u<<27)))return c;
    unsigned low=0,high=0;asm volatile("xgetbv":"=a"(low),"=d"(high):"c"(0));
    c.simd=vector_features&&vector_bf16&&(low&0x600e6u)==0x600e6u;
    return c;
}
template<class T>GemmTimings zero_product(std::size_t m,std::size_t n,std::size_t ldb,T* c,std::size_t ldc){
    if(!m||!n)throw Error("M and N must be positive");
    if(ldb<n||ldc<n)throw Error("row-major leading dimensions are too small");
    if(!c)throw Error("C pointer is null");
    const auto max=std::numeric_limits<std::size_t>::max()/sizeof(T);
    if(m>max/n || (m-1)>max/ldc || (m-1)*ldc>max-n)throw Error("matrix address span overflow");
    const auto t0=std::chrono::steady_clock::now();
    for(std::size_t i=0;i<m;++i)std::fill(c+i*ldc,c+i*ldc+n,T(0));
    GemmTimings t;t.total_seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-t0).count();return t;
}
void require_optimized_cpu(){const auto s=request_amx_permission_for_current_thread();if(!s.permission_available)throw Error("optimized AMX-BF16 is unavailable: "+s.message);}
}

AmxStatus request_amx_permission_for_current_thread() {
    AmxStatus s;
    static const auto cpu=capabilities();
    s.cpu_amx_tile=cpu.tile;s.cpu_amx_bf16=cpu.bf16;
    if (!s.cpu_amx_tile || !s.cpu_amx_bf16) {
        s.message = "CPU does not report both AMX-TILE and AMX-BF16";
        return s;
    }
    if(!cpu.simd){s.message="AVX2/AVX-512 F,DQ,BW,VL,BF16 and OS ZMM state are required";return s;}
    // Permission belongs to the Linux process. A changed PID invalidates this
    // successful-request cache after fork; exec starts with fresh static state.
    static std::atomic<pid_t> permitted_pid{0};const pid_t pid=getpid();
    if(permitted_pid.load(std::memory_order_acquire)==pid){s.permission_available=true;s.message="XTILEDATA permission available for this process";return s;}
    unsigned long mask = 0;
    if (syscall(SYS_arch_prctl, ARCH_GET_XCOMP_PERM, &mask) == 0 && (mask & (1ul << XFEATURE_XTILEDATA))) {
        s.permission_available = true;
        permitted_pid.store(pid,std::memory_order_release);
        s.message = "XTILEDATA permission already available for this process";
        return s;
    }
    s.permission_requested = true;
    if (syscall(SYS_arch_prctl, ARCH_REQ_XCOMP_PERM, XFEATURE_XTILEDATA) == 0) {
        s.permission_available = true;
        permitted_pid.store(pid,std::memory_order_release);
        s.message = "XTILEDATA permission granted for this process";
    } else {
        s.message = std::string("ARCH_REQ_XCOMP_PERM failed: ") + std::strerror(errno);
    }
    return s;
}

// Generic dispatch is a separate translation unit, compiled without the
// Sapphire Rapids target. Unsupported processors never enter vector/tile code.
GemmTimings gemm_fp32_profiled(std::size_t m,std::size_t n,std::size_t k,const float* a,std::size_t lda,const float* b,std::size_t ldb,float* c,std::size_t ldc){
    if(!k)return zero_product(m,n,ldb,c,ldc);
    require_optimized_cpu();
    return detail::gemm_fp32_native(m,n,k,a,lda,b,ldb,c,ldc);
}
GemmTimings gemm_fp64_profiled(std::size_t m,std::size_t n,std::size_t k,const double* a,std::size_t lda,const double* b,std::size_t ldb,double* c,std::size_t ldc,ProductBudget budget){
    switch(budget){case ProductBudget::p6:case ProductBudget::p10:case ProductBudget::p15:case ProductBudget::p21:break;default:throw Error("invalid FP64 product budget");}
    if(!k)return zero_product(m,n,ldb,c,ldc);
    require_optimized_cpu();
    return detail::gemm_fp64_native(m,n,k,a,lda,b,ldb,c,ldc,budget);
}
void gemm_fp32(std::size_t m,std::size_t n,std::size_t k,const float* a,std::size_t lda,const float* b,std::size_t ldb,float* c,std::size_t ldc){(void)gemm_fp32_profiled(m,n,k,a,lda,b,ldb,c,ldc);}
void gemm_fp64(std::size_t m,std::size_t n,std::size_t k,const double* a,std::size_t lda,const double* b,std::size_t ldb,double* c,std::size_t ldc,ProductBudget budget){(void)gemm_fp64_profiled(m,n,k,a,lda,b,ldb,c,ldc,budget);}
const char* product_order_fp32()noexcept{return "11,10,20,00,01,02";}
const char* product_order_fp64(ProductBudget b)noexcept{switch(b){case ProductBudget::p6:return "00;01,10;02,11,20";case ProductBudget::p10:return "00;01,10;02,11,20;03,12,21,30";case ProductBudget::p15:return "00;01,10;02,11,20;03,12,21,30;04,13,22,31,40";case ProductBudget::p21:return "00;01,10;02,11,20;03,12,21,30;04,13,22,31,40;05,14,23,32,41,50";}return "invalid";}

} // namespace ozamx
