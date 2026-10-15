#include "int8.hpp"
#include "ozamx/gemm.hpp"
#include <omp.h>
#include <quadmath.h>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <limits>
#include <random>
#include <string>
#include <vector>

// Full binary128 references for small output matrices, including long K.
// The precision floor is stated in the result; comparisons against V3 are
// reported separately and never inferred from API success.
namespace {
constexpr double guard = -31415.25;
struct Metrics { double ef=0, scaled=0, abs=0; std::uint64_t ulp=0; };
std::uint64_t ordered(double x) {
    std::uint64_t b; std::memcpy(&b,&x,sizeof(b));
    return b >> 63 ? ~b : b | (std::uint64_t(1)<<63);
}
Metrics measure(const std::vector<double>& c, std::size_t m, std::size_t n,
                std::size_t ld, const std::vector<__float128>& ref,
                const std::vector<__float128>& denom) {
    __float128 err2=0, ref2=0, maxerr=0, maxscaled=0;
    Metrics out;
    for(std::size_t i=0;i<m;++i) for(std::size_t j=0;j<n;++j) {
        const auto p=i*n+j; const double value=c[i*ld+j];
        if(!std::isfinite(value)) throw std::runtime_error("nonfinite output");
        const __float128 e=static_cast<__float128>(value)-ref[p];
        err2+=e*e; ref2+=ref[p]*ref[p];
        maxerr=fmaxq(maxerr,fabsq(e));
        maxscaled=fmaxq(maxscaled,denom[p]?fabsq(e)/denom[p]:fabsq(e));
        const auto a=ordered(value), b=ordered(static_cast<double>(ref[p]));
        out.ulp=std::max(out.ulp,a>b?a-b:b-a);
    }
    out.abs=static_cast<double>(maxerr);
    out.ef=static_cast<double>(ref2 ? sqrtq(err2/ref2) : sqrtq(err2));
    out.scaled=static_cast<double>(maxscaled);
    return out;
}
bool untouched_padding(const std::vector<double>& c, std::size_t m,
                       std::size_t n, std::size_t ld) {
    for(std::size_t i=0;i<m;++i) for(std::size_t j=n;j<ld;++j)
        if(c[i*ld+j]!=guard) return false;
    for(std::size_t q=m*ld;q<c.size();++q) if(c[q]!=guard) return false;
    return true;
}
void metrics_json(const Metrics& v) {
    std::cout<<"{\"eF\":"<<v.ef<<",\"e_scaled\":"<<v.scaled
             <<",\"max_abs\":"<<v.abs<<",\"max_ulp\":"<<v.ulp<<"}";
}
void json_string(const std::string& text) {
    const char* hex="0123456789abcdef";
    std::cout<<'"';
    for(unsigned char c:text) {
        if(c=='"' || c=='\\') std::cout<<'\\'<<c;
        else if(c<32) std::cout<<"\\u00"<<hex[c>>4]<<hex[c&15];
        else std::cout<<c;
    }
    std::cout<<'"';
}
bool numeric_case(const std::string& kind, std::size_t k, int threads,
                  std::uint64_t seed) {
    const std::size_t m=32,n=32,lda=k+3,ldb=n+5,ldc=n+7;
    std::vector<double> a(m*lda,guard),b(k*ldb,guard),c(m*ldc+8,guard),v3(c);
    std::mt19937_64 rng(seed); std::uniform_real_distribution<double> u(-1,1);
    std::normal_distribution<double> g(0,1);
    for(std::size_t i=0;i<m;++i) for(std::size_t q=0;q<k;++q) {
        double x=kind=="gaussian"?g(rng):u(rng);
        if(kind=="zero") x=0;
        if(kind=="sparse" && (q%17)) x=0;
        if(kind=="cancellation") x=(q&1)?-1.0:1.0;
        if(kind=="dynamic") x=std::scalbn(x,static_cast<int>(q%101)-50);
        if(kind=="rne") x=std::nextafter(0.5+std::ldexp(1.0,-54),q&1?0.0:1.0);
        if(kind=="extreme") x=std::scalbn((q&1)?-0.5:0.5,120);
        a[i*lda+q]=x;
    }
    for(std::size_t q=0;q<k;++q) for(std::size_t j=0;j<n;++j) {
        double x=kind=="gaussian"?g(rng):u(rng);
        if(kind=="zero") x=0;
        if(kind=="sparse" && (q%13)) x=0;
        if(kind=="cancellation") x=1.0+(q%4==0?std::ldexp(1.0,-40):0.0);
        if(kind=="dynamic") x=std::scalbn(x,50-static_cast<int>(q%101));
        if(kind=="rne") x=std::nextafter(0.5,q&1?0.0:1.0);
        if(kind=="extreme") x=std::scalbn(0.5,120);
        b[q*ldb+j]=x;
    }
    std::vector<__float128> ref(m*n),denom(m*n);
    #pragma omp parallel for num_threads(threads) schedule(static)
    for(std::size_t i=0;i<m;++i) for(std::size_t j=0;j<n;++j) {
        __float128 s=0,d=0;
        for(std::size_t q=0;q<k;++q) {
            const auto p=static_cast<__float128>(a[i*lda+q])*b[q*ldb+j];
            s+=p; d+=fabsq(p);
        }
        ref[i*n+j]=s; denom[i*n+j]=d;
    }
    ozamx_int8_36::gemm_fp64_int8_36(m,n,k,a.data(),lda,b.data(),ldb,c.data(),ldc,threads);
    const auto cm=measure(c,m,n,ldc,ref,denom);
    bool v3ok=true;
    try { ozamx::gemm_fp64(m,n,k,a.data(),lda,b.data(),ldb,v3.data(),ldc,ozamx::ProductBudget::p21); }
    catch(const ozamx::Error&) { v3ok=false; }
    const auto vm=v3ok?measure(v3,m,n,ldc,ref,denom):Metrics{};
    const bool standard=cm.scaled<=std::numeric_limits<double>::epsilon();
    const bool comparable=v3ok && cm.scaled<=std::max(vm.scaled*1.1,std::ldexp(1.0,-55));
    const bool padding=untouched_padding(c,m,n,ldc);
    std::cout<<"{\"kind\":\""<<kind<<"\",\"K\":"<<k<<",\"seed\":"<<seed
             <<",\"full_reference_outputs\":"<<m*n<<",\"candidate\":";
    metrics_json(cm); std::cout<<",\"v3_success\":"<<(v3ok?"true":"false")<<",\"v3\":";
    if(v3ok) metrics_json(vm); else std::cout<<"null";
    std::cout<<",\"scaled_within_binary64_epsilon\":"<<(standard?"true":"false")
             <<",\"within_v3_110pct_or_2powminus55\":"<<(comparable?"true":"false")
             <<",\"padding_preserved\":"<<(padding?"true":"false")<<"}";
    return standard && padding;
}
bool transaction_checks(int threads) {
    constexpr std::size_t m=32,n=32,k=64,ld=67;
    std::vector<double> a(m*ld,0.25),b(k*ld,-0.5),c(m*ld,guard),ref(c);
    const auto invoke=[&](std::size_t kk=64) {
        ozamx_int8_36::gemm_fp64_int8_36(m,n,kk,a.data(),ld,b.data(),ld,c.data(),ld,threads);
    };
    bool ok=true;
    for(double invalid:{std::numeric_limits<double>::infinity(),
                        std::numeric_limits<double>::quiet_NaN(),
                        std::numeric_limits<double>::denorm_min(),
                        std::numeric_limits<double>::max()}) {
        a[31*ld+63]=invalid; bool threw=false;
        try { invoke(); } catch(const std::invalid_argument&) { threw=true; }
        ok &= threw && std::memcmp(c.data(),ref.data(),c.size()*sizeof(double))==0;
        a[31*ld+63]=0.25;
    }
    invoke(); ref=c;
    auto alias_a=a; const auto before_a=alias_a;
    ozamx_int8_36::gemm_fp64_int8_36(m,n,k,alias_a.data(),ld,b.data(),ld,alias_a.data(),ld,threads);
    for(std::size_t i=0;i<m;++i) {
        ok &= std::memcmp(alias_a.data()+i*ld,ref.data()+i*ld,n*sizeof(double))==0;
        ok &= std::memcmp(alias_a.data()+i*ld+n,before_a.data()+i*ld+n,(ld-n)*sizeof(double))==0;
    }
    auto alias_b=b; const auto before_b=alias_b;
    ozamx_int8_36::gemm_fp64_int8_36(m,n,k,a.data(),ld,alias_b.data(),ld,alias_b.data(),ld,threads);
    for(std::size_t i=0;i<m;++i) {
        ok &= std::memcmp(alias_b.data()+i*ld,ref.data()+i*ld,n*sizeof(double))==0;
        ok &= std::memcmp(alias_b.data()+i*ld+n,before_b.data()+i*ld+n,(ld-n)*sizeof(double))==0;
    }
    ok &= std::memcmp(alias_b.data()+m*ld,before_b.data()+m*ld,(k-m)*ld*sizeof(double))==0;
    invoke(0);
    for(std::size_t i=0;i<m;++i) for(std::size_t j=0;j<n;++j) ok &= c[i*ld+j]==0;
    return ok;
}
}
int main(int argc,char** argv) {
    const int threads=argc>1?std::stoi(argv[1]):8;
    if(threads<1 || threads>64) return 2;
    omp_set_dynamic(0); omp_set_num_threads(threads);
    std::cout<<std::setprecision(17);
    try {
        bool ok=true; std::cout<<"{\"schema\":\"int8-36-gate-v1\",\"threads\":"<<threads
                <<",\"products\":36,\"reference\":\"full_binary128\",\"numeric_cases\":[";
        bool first=true;
        const auto run=[&](const char* kind,std::size_t k,std::uint64_t seed) {
            if(!first) std::cout<<",";
            first=false;
            try { return numeric_case(kind,k,threads,seed); }
            catch(const std::exception& e) {
                std::cout<<"{\"kind\":\""<<kind<<"\",\"K\":"<<k
                         <<",\"seed\":"<<seed<<",\"exception\":";
                json_string(e.what());
                std::cout<<",\"scaled_within_binary64_epsilon\":false}";
                return false;
            }
        };
        for(std::size_t k:{1u,63u,64u,65u,255u,256u,257u,4096u,32768u}) {
            ok &= run("uniform",k,260904+k);
        }
        for(const char* kind:{"gaussian","zero","sparse","cancellation","dynamic","rne","extreme"}) {
            ok &= run(kind,257,261161);
        }
        bool transaction=false;
        try { transaction=transaction_checks(threads); }
        catch(const std::exception& e) { std::cerr<<"transaction exception: "<<e.what()<<"\n"; }
        ok &= transaction;
        std::cout<<"],\"transaction_and_alias_checks\":"<<(transaction?"true":"false")
                 <<",\"passed_scaled_accuracy_and_semantics\":"<<(ok?"true":"false")<<"}\n";
        return ok?0:1;
    } catch(const std::exception& e) {
        std::cerr<<"gate exception: "<<e.what()<<"\n"; return 3;
    }
}
