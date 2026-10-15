#include "ozamx/gemm.hpp"
#include OZAMX_PREPROCESS_HEADER

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <iterator>
#include <limits>
#include <random>
#include <vector>

using namespace ozamx::detail;
struct Shape { std::size_t m,n,k; };
constexpr Shape shapes[]={{256,256,256},{512,256,512},{256,512,256}};
int main() {
    constexpr int threads=1;const char* domains[]={"zero","random","exponent_edges"};
    std::size_t checked=0,mismatches=0;
    for(std::size_t si=0;si<std::size(shapes);++si)for(int domain=0;domain<3;++domain) {
        const Shape s=shapes[si];const std::size_t lda=s.k+3,ldb=s.n+5;
        std::vector<float>a(s.m*lda,std::numeric_limits<float>::quiet_NaN()),b(s.k*ldb,std::numeric_limits<float>::quiet_NaN());
        std::mt19937_64 rng(0x32d1ULL+si*31+domain);std::uniform_int_distribution<int> u(-1000,1000);
        auto value=[&](std::size_t i){
            if(domain==0)return std::copysign(0.0f,(i&1)?-1.0f:1.0f);
            if(domain==1)return float(u(rng))/997.0f;
            const int e=i%4==0?-126:i%4==1?127:i%4==2?-30:80;
            const float m=e==-126?1.0f:0.997f+float(std::abs(u(rng))%980)/1000.0f;
            return std::copysign(std::ldexp(m,e),u(rng)<0?-1.0f:1.0f);
        };
        for(std::size_t i=0;i<s.m;++i)for(std::size_t k=0;k<s.k;++k)a[i*lda+k]=value(i*s.k+k);
        for(std::size_t k=0;k<s.k;++k)for(std::size_t j=0;j<s.n;++j)b[k*ldb+j]=value(k*s.n+j);
        const auto as=split_fp32(a.data(),s.m,s.k,lda,threads),bs=split_fp32(b.data(),s.k,s.n,ldb,threads);
        const auto ref=pack_slices(as,bs,s.m,s.n,s.k,3,threads);
        const auto got=split_pack_direct32(a.data(),b.data(),s.m,s.n,s.k,lda,ldb,threads);
        bool ok=ref.mblocks==got.mblocks&&ref.nblocks==got.nblocks&&ref.kblocks==got.kblocks&&ref.slices==got.slices;
        for(int d=0;d<3;++d)for(int side=0;side<2;++side){
            const auto& x=side?ref.b[d]:ref.a[d];const auto& y=side?got.b[d]:got.a[d];ok &= x.size()==y.size();
            const auto count=std::min(x.size(),y.size());checked+=count;
            for(std::size_t q=0;q<count;++q)if(x[q]!=y[q]){++mismatches;ok=false;}
        }
        std::cout<<"{\"m\":"<<s.m<<",\"n\":"<<s.n<<",\"k\":"<<s.k<<",\"input\":\""<<domains[domain]
                 <<"\",\"status\":\""<<(ok?"pass":"fail")<<"\"}\n";
        if(!ok)return 1;
    }
    std::cerr<<"fp32_packed_panel_audit=pass cases="<<std::size(shapes)*3<<" elements="<<checked<<" mismatches="<<mismatches<<'\n';
}
