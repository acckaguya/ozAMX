#include "ozamx/gemm.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <iterator>
#include <limits>
#include <random>
#include <string>
#include <type_traits>
#include <vector>

namespace {
struct Shape { std::size_t m, n, k; };
const Shape shapes[] = {{1, 17, 31}, {7, 33, 33}, {17, 65, 257}, {65, 129, 65},
                        {256,256,256}, {512,512,512}, {256,512,256}, {512,256,512}, {1024,1024,1024}};
constexpr std::uint64_t seed = 0x8454a11ceULL;

template<class T> std::uint64_t bits(T x) {
    std::uint64_t u=0; std::memcpy(&u,&x,sizeof(T)); return u;
}
template<class T> bool same(T a,T b) { return bits(a)==bits(b); }

template<class T> bool emit_case(const char* precision, Shape s, int budget, std::uint64_t salt, bool full_bits) {
    const std::size_t lda=s.k+3, ldb=s.n+5, ldc=s.n+7;
    std::vector<T> a(s.m*lda,T(-91)), b(s.k*ldb,T(-92));
    const T sentinel=T(12345.25);
    std::vector<T> c(s.m*ldc+11,sentinel);
    std::mt19937_64 rng(seed+salt);
    std::uniform_int_distribution<int> dist(-900,900);
    for(std::size_t i=0;i<s.m;++i) for(std::size_t k=0;k<s.k;++k)
        a[i*lda+k]=T(dist(rng))/T(997);
    for(std::size_t k=0;k<s.k;++k) for(std::size_t j=0;j<s.n;++j)
        b[k*ldb+j]=T(dist(rng))/T(991);

    bool ok=true; long double err2=0, ref2=0, scaled=0;
    try {
        if constexpr(std::is_same_v<T,float>) ozamx::gemm_fp32(s.m,s.n,s.k,a.data(),lda,b.data(),ldb,c.data(),ldc);
        else ozamx::gemm_fp64(s.m,s.n,s.k,a.data(),lda,b.data(),ldb,c.data(),ldc,static_cast<ozamx::ProductBudget>(budget));
    } catch(const std::exception& e) {
        std::cerr<<"unexpected GEMM error: "<<e.what()<<'\n'; return false;
    }
    const std::size_t outputs=s.m*s.n;
    const std::size_t samples=full_bits?outputs:std::min<std::size_t>(32,outputs);
    for(std::size_t i=0;i<s.m;++i) for(std::size_t j=0;j<s.n;++j)
        ok &= std::isfinite(c[i*ldc+j]);
    for(std::size_t sample=0;sample<samples;++sample) {
        const std::size_t flat=full_bits?sample:(sample*outputs)/samples;
        const std::size_t i=flat/s.n, j=flat%s.n;
        long double ref=0, abs_sum=0;
        for(std::size_t k=0;k<s.k;++k) {
            const long double p=static_cast<long double>(a[i*lda+k])*b[k*ldb+j];
            ref+=p; abs_sum+=std::fabs(p);
        }
        const long double delta=static_cast<long double>(c[i*ldc+j])-ref;
        err2+=delta*delta; ref2+=ref*ref;
        scaled=std::max(scaled,abs_sum==0?std::fabs(delta):std::fabs(delta)/abs_sum);
    }
    for(std::size_t i=0;i<s.m;++i) for(std::size_t j=s.n;j<ldc;++j) ok &= same(c[i*ldc+j],sentinel);
    for(std::size_t q=s.m*ldc;q<c.size();++q) ok &= same(c[q],sentinel);
    const long double rel=ref2==0?std::sqrt(err2):std::sqrt(err2/ref2);
    const long double limit=std::is_same_v<T,float>?2e-5L:(budget==6?2e-6L:budget==10?2e-8L:2e-10L);
    ok &= scaled<limit;

    const std::string name=std::string(precision)+"_"+std::to_string(s.m)+"x"+std::to_string(s.n)+"x"+std::to_string(s.k)+"_p"+std::to_string(budget);
    std::cout<<"{\"case\":\""<<name<<"\",\"m\":"<<s.m<<",\"n\":"<<s.n<<",\"k\":"<<s.k
             <<",\"ldc\":"<<ldc<<",\"budget\":"<<budget<<",\"output_slots\":"<<s.m*ldc<<",\"oracle_samples\":"<<samples
             <<",\"scaled_error\":"<<std::setprecision(12)<<static_cast<double>(scaled)
             <<",\"relative_error\":"<<static_cast<double>(rel)<<",\"guards_ok\":"<<(ok?"true":"false");
    if(full_bits) {
        std::cout<<",\"bits\":["; bool first=true;
        for(std::size_t i=0;i<s.m*ldc;++i) { if(!first)std::cout<<','; first=false; std::cout<<'"'<<std::hex<<std::setw(sizeof(T)*2)<<std::setfill('0')<<bits(c[i])<<std::dec<<'"'; }
        std::cout<<']';
    } else {
        std::uint64_t h1=1469598103934665603ULL,h2=0x6a09e667f3bcc909ULL;
        for(std::size_t i=0;i<s.m*ldc;++i) {
            const std::uint64_t v=bits(c[i]);
            h1=(h1^v)*1099511628211ULL;
            h2^=v+0x9e3779b97f4a7c15ULL+(h2<<6)+(h2>>2);
        }
        std::cout<<",\"output_digest\":\""<<std::hex<<std::setw(16)<<std::setfill('0')<<h1<<std::setw(16)<<h2<<std::dec<<'"';
    }
    std::cout<<"}\n";
    return ok;
}

bool overflow_is_transactional() {
    float a=2.0e38f,b=2.0f,c=314.25f; bool threw=false;
    try { ozamx::gemm_fp32(1,1,1,&a,1,&b,1,&c,1); }
    catch(const ozamx::Error&) { threw=true; }
    const bool ok=threw && same(c,314.25f);
    std::cout<<"{\"case\":\"fp32_overflow_transaction\",\"threw\":"<<(threw?"true":"false")
             <<",\"c_unchanged\":"<<(same(c,314.25f)?"true":"false")<<"}\n";
    return ok;
}
bool invalid_is_transactional() {
    double a=std::numeric_limits<double>::infinity(),b=1.0,c=-721.5; bool threw=false;
    try { ozamx::gemm_fp64(1,1,1,&a,1,&b,1,&c,1,ozamx::ProductBudget::p21); }
    catch(const ozamx::Error&) { threw=true; }
    const bool ok=threw && same(c,-721.5);
    std::cout<<"{\"case\":\"fp64_invalid_transaction\",\"threw\":"<<(threw?"true":"false")
             <<",\"c_unchanged\":"<<(same(c,-721.5)?"true":"false")<<"}\n";
    return ok;
}
}

int main() {
    bool ok=true;
    for(std::size_t q=0;q<std::size(shapes);++q) {
        const bool full_bits=q<4;
        ok &= emit_case<float>("f32",shapes[q],6,q*17+1,full_bits);
        for(int p:{6,10,15,21}) ok &= emit_case<double>("f64",shapes[q],p,q*17+p,full_bits);
    }
    ok &= overflow_is_transactional();
    ok &= invalid_is_transactional();
    std::cerr<<"extended_validation="<<(ok?"pass":"fail")<<" cases=47 seed="<<seed<<'\n';
    return ok?0:1;
}
