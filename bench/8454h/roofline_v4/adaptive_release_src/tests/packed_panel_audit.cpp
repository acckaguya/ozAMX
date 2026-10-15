#include "ozamx/gemm.hpp"
#include OZAMX_PREPROCESS_HEADER

#include <cmath>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <iterator>
#include <limits>
#include <random>
#include <vector>

using namespace ozamx::detail;
struct Shape { std::size_t m,n,k; };
constexpr Shape shapes[]={{256,256,256},{512,512,512},{256,512,256},{512,256,512}};

void fill(double* a,double* b,Shape s,std::size_t lda,std::size_t ldb,int domain,std::uint64_t seed) {
    std::fill(a,a+s.m*lda,std::numeric_limits<double>::quiet_NaN());
    std::fill(b,b+s.k*ldb,std::numeric_limits<double>::quiet_NaN());
    std::mt19937_64 rng(seed);std::uniform_int_distribution<int> u(-1000,1000),exp(0,6);
    for(std::size_t i=0;i<s.m;++i)for(std::size_t k=0;k<s.k;++k) {
        if(domain==0)a[i*lda+k]=std::copysign(0.0,(i+k)&1?-1.0:1.0);
        else if(domain==1)a[i*lda+k]=double(u(rng))/997.0;
        else if(domain==2) {const int e=(i+k)%7==0?-126:(i+k)%7==1?127:(i+k)%7==2?-100:(i+k)%7==3?126:(i+k)%7==4?-20:exp(rng);const double m=e==-126?1.0:e==127?1.984375:0.997+double(std::abs(u(rng))%980)/1000.0;a[i*lda+k]=std::copysign(std::ldexp(m,e),u(rng)<0?-1.0:1.0);}
        else a[i*lda+k]=std::copysign(FP64_MAX_BF16,u(rng)<0?-1.0:1.0);
    }
    for(std::size_t k=0;k<s.k;++k)for(std::size_t j=0;j<s.n;++j) {
        if(domain==0)b[k*ldb+j]=std::copysign(0.0,(k+j)&1?-1.0:1.0);
        else if(domain==1)b[k*ldb+j]=double(u(rng))/991.0;
        else if(domain==2) {const int e=(k+j)%7==0?-126:(k+j)%7==1?127:(k+j)%7==2?-100:(k+j)%7==3?126:(k+j)%7==4?-20:exp(rng);const double m=e==-126?1.0:e==127?1.984375:0.997+double(std::abs(u(rng))%980)/1000.0;b[k*ldb+j]=std::copysign(std::ldexp(m,e),u(rng)<0?-1.0:1.0);}
        else b[k*ldb+j]=std::copysign(FP64_MAX_BF16,u(rng)<0?-1.0:1.0);
    }
}

int main() {
    constexpr int threads=1;std::size_t checked=0,mismatches=0,both_rejected=0;
    const char* domains[]={"zero","random","exponent_edges","max_bf16_boundary"};
    for(std::size_t si=0;si<std::size(shapes);++si)for(int depth:{3,4,5,6})for(int domain=0;domain<4;++domain) {
        const Shape s=shapes[si];const std::size_t lda=s.k+3,ldb=s.n+5;
        std::vector<double>a(s.m*lda),b(s.k*ldb);
        fill(a.data(),b.data(),s,lda,ldb,domain,0x8454d1ULL+si*101+depth*7+domain);
        Packed ref,got;bool ref_ok=true,got_ok=true;
        try {
            auto as=split_fp64(a.data(),s.m,s.k,lda,threads,depth);
            auto bs=split_fp64(b.data(),s.k,s.n,ldb,threads,depth);
            ref=pack_slices(as,bs,s.m,s.n,s.k,depth,threads);
        } catch(...) { ref_ok=false; }
        try { got=split_pack_direct64(a.data(),b.data(),s.m,s.n,s.k,lda,ldb,depth,threads); }
        catch(...) { got_ok=false; }
        if(ref_ok!=got_ok){std::cerr<<"accept/reject mismatch m="<<s.m<<" n="<<s.n<<" k="<<s.k<<" depth="<<depth<<" input="<<domains[domain]<<'\n';return 2;}
        if(!ref_ok){++both_rejected;std::cout<<"{\"m\":"<<s.m<<",\"n\":"<<s.n<<",\"k\":"<<s.k<<",\"depth\":"<<depth<<",\"input\":\""<<domains[domain]<<"\",\"reference_accepted\":false,\"candidate_accepted\":false,\"status\":\"both_rejected\"}\n";continue;}
        bool shape_ok=ref.mblocks==got.mblocks&&ref.nblocks==got.nblocks&&ref.kblocks==got.kblocks&&ref.slices==got.slices;
        for(int d=0;d<depth;++d)for(int side=0;side<2;++side) {
            const auto& x=side?ref.b[d]:ref.a[d];const auto& y=side?got.b[d]:got.a[d];
            shape_ok &= x.size()==y.size();
            const auto count=std::min(x.size(),y.size());checked+=count;
            for(std::size_t q=0;q<count;++q)if(x[q]!=y[q]){++mismatches;shape_ok=false;}
        }
        std::cout<<"{\"m\":"<<s.m<<",\"n\":"<<s.n<<",\"k\":"<<s.k<<",\"depth\":"<<depth
                 <<",\"input\":\""<<domains[domain]<<"\",\"reference_accepted\":true,\"candidate_accepted\":true,\"status\":\""<<(shape_ok?"pass":"fail")<<"\"}\n";
        if(!shape_ok)return 1;
    }
    std::cerr<<"packed_panel_audit=pass cases="<<std::size(shapes)*4*4<<" both_rejected="<<both_rejected<<" elements="<<checked<<" mismatches="<<mismatches<<'\n';
}
