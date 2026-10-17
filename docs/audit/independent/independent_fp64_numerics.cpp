// Independent audit of paper Eq.(13)-(16), not a production implementation.
// Small N has a full GCC binary128 oracle. No existing benchmark/test is included.
#include "ozamx/gemm.hpp"
#include <omp.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <vector>

using Q=__float128;
constexpr std::size_t n=64, count=n*n;
using Planes=std::array<std::vector<double>,6>;
std::uint64_t next(std::uint64_t& state) {
    std::uint64_t x=(state+=0x9e3779b97f4a7c15ULL);
    x=(x^(x>>30))*0xbf58476d1ce4e5b9ULL;
    x=(x^(x>>27))*0x94d049bb133111ebULL;
    return x^(x>>31);
}
double bf_round(double x) {
    // Projection grid in this bounded case is exactly representable as FP32.
    float f=static_cast<float>(x); std::uint32_t bits;
    std::memcpy(&bits,&f,4); bits+=0x7fffU+((bits>>16)&1U);bits&=0xffff0000U;
    std::memcpy(&f,&bits,4);return double(f);
}
Planes split(const std::vector<double>& x,std::vector<double>& terminal) {
    terminal=x; Planes out;
    for(int s=0;s<6;++s) {
        double maximum=0; for(double v:terminal)maximum=std::max(maximum,std::abs(v));
        out[s].resize(count,0);
        if(maximum==0)continue;
        int exponent=0;const double fraction=std::frexp(maximum,&exponent);
        const int v=fraction==0.5?exponent-1:exponent;
        const double sigma=std::ldexp(1.0,v+45);
        for(std::size_t q=0;q<count;++q) {
            const double projected=(terminal[q]+sigma)-sigma;
            out[s][q]=bf_round(projected);
            terminal[q]-=out[s][q];
        }
    }
    return out;
}
std::vector<Q> product(const std::vector<double>& a,const std::vector<double>& b) {
    std::vector<Q> c(count,0);
    for(std::size_t i=0;i<n;++i)for(std::size_t j=0;j<n;++j)
        for(std::size_t k=0;k<n;++k)c[i*n+j]+=Q(a[i*n+k])*Q(b[k*n+j]);
    return c;
}
long double error(const std::vector<Q>& value,const std::vector<Q>& ref) {
    Q numerator=0,denominator=0;
    for(std::size_t q=0;q<count;++q) {const Q d=value[q]-ref[q];numerator+=d*d;denominator+=ref[q]*ref[q];}
    return std::sqrt(static_cast<long double>(numerator/denominator));
}
int main() {
    omp_set_dynamic(0);omp_set_num_threads(4);
    if(!ozamx::request_amx_permission_for_current_thread().permission_available)return 2;
    std::cout<<"seed,budget,independent_eF_vs_binary128,native_eF_vs_binary128,native_vs_independent_bit_mismatches,component_fp32_round_changed_entries,terminal_only_eF,omitted_tail_eF\n"<<std::setprecision(18);
    bool ok=true;
    for(std::uint64_t seed:{20261016ULL,260904ULL,8454ULL}) {
        std::uint64_t state=seed;std::vector<double>a(count),b(count),ra,rb;
        for(auto& x:a)x=double(std::int64_t(next(state)>>11)-4503599627370496LL)/4503599627370496.0;
        for(auto& x:b)x=double(std::int64_t(next(state)>>11)-4503599627370496LL)/4503599627370496.0;
        const auto sa=split(a,ra),sb=split(b,rb);const auto ref=product(a,b);
        std::vector<double> asum(count,0),bsum(count,0);
        for(std::size_t q=0;q<count;++q)for(int s=0;s<6;++s){asum[q]+=sa[s][q];bsum[q]+=sb[s][q];}
        // Keep full36 reference sums in binary128 so residuals are not rounded away.
        std::vector<Q> sumaq(count,0),sumbq(count,0),full36(count,0);
        for(std::size_t q=0;q<count;++q)for(int s=0;s<6;++s){sumaq[q]+=Q(sa[s][q]);sumbq[q]+=Q(sb[s][q]);}
        for(std::size_t i=0;i<n;++i)for(std::size_t j=0;j<n;++j)for(std::size_t k=0;k<n;++k)full36[i*n+j]+=sumaq[i*n+k]*sumbq[k*n+j];
        for(int depth:{3,4,5,6}) {
            const int budget=depth*(depth+1)/2; std::vector<double> reconstructed(count,0),native(count);
            std::vector<Q> selected(count,0);std::uint64_t rounding=0,mismatches=0;
            for(int diagonal=0;diagonal<depth;++diagonal)for(int i=0;i<=diagonal;++i) {
                const auto component=product(sa[i],sb[diagonal-i]);
                for(std::size_t q=0;q<count;++q) {
                    const float stored=static_cast<float>(component[q]);
                    rounding+=Q(stored)!=component[q];
                    reconstructed[q]+=double(stored);selected[q]+=component[q];
                }
            }
            ozamx::gemm_fp64(n,n,n,a.data(),n,b.data(),n,native.data(),n,static_cast<ozamx::ProductBudget>(budget));
            std::vector<Q> rq(count),nq(count),tail_as_value(count);
            for(std::size_t q=0;q<count;++q) {
                mismatches+=std::memcmp(&native[q],&reconstructed[q],sizeof(double))!=0;
                rq[q]=Q(reconstructed[q]);nq[q]=Q(native[q]);tail_as_value[q]=ref[q]+full36[q]-selected[q];
            }
            ok &= mismatches==0;
            std::cout<<seed<<','<<budget<<','<<error(rq,ref)<<','<<error(nq,ref)<<','<<mismatches<<','<<rounding<<','<<error(full36,ref)<<','<<error(tail_as_value,ref)<<'\n';
        }
    }
    std::cerr<<"independent_fp64_validation="<<(ok?"pass":"FAIL")<<" N="<<n<<" full_output_entries="<<count<<" binary128_significand_bits=113\n";
    return ok?0:1;
}
