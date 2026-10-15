#include "ozamx/gemm.hpp"

#include <algorithm>
#include <array>
#include <cerrno>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <exception>
#include <limits>
#include <string>
#include <type_traits>
#include <vector>
#include <unistd.h>

namespace {
constexpr std::uint32_t f32 = 1, f64 = 2;
constexpr std::uint32_t normal = 0, overflow = 1, cancellation = 2, alias_a = 3, alias_b = 4;
struct Case { const char* name; std::uint32_t id, type, mode, budget; std::size_t m,n,k; };
constexpr Case cases[] = {
    {"f32_4096_cube",1,f32,normal,0,4096,4096,4096},
    {"f64_4096_cube_p6",2,f64,normal,6,4096,4096,4096},
    {"f64_4096_cube_p10",3,f64,normal,10,4096,4096,4096},
    {"f64_4096_cube_p15",4,f64,normal,15,4096,4096,4096},
    {"f64_4096_cube_p21",5,f64,normal,21,4096,4096,4096},
    {"f32_4096x4097x257",6,f32,normal,0,4096,4097,257},
    {"f64_4096x4097x257_p21",7,f64,normal,21,4096,4097,257},
    {"f64_4097x4096x4097_p21",8,f64,normal,21,4097,4096,4097},
    {"f64_wide_overflow_k512",9,f64,overflow,6,4096,4096,512},
    {"f64_wide_cancellation_k512",10,f64,cancellation,6,4096,4096,512},
    {"f64_alias_a_equals_c_p6",11,f64,alias_a,6,4096,4096,256},
    {"f64_alias_b_equals_c_p6",12,f64,alias_b,6,4096,4096,256},
};
constexpr double sentinel = -31415.25;
std::uint64_t mix(std::uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL; x = (x ^ (x >> 30))*0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27))*0x94d049bb133111ebULL; return x ^ (x >> 31);
}
template<class T> T sample(std::uint64_t i,std::uint64_t salt) {
    const int v=static_cast<int>(mix(i+salt)%2001)-1000;
    return static_cast<T>(v)/static_cast<T>(8192);
}
template<class T> void fill_matrix(std::vector<T>& x,std::size_t rows,std::size_t cols,std::size_t ld,std::uint64_t salt) {
    std::fill(x.begin(),x.end(),static_cast<T>(sentinel));
    for(std::size_t i=0;i<rows;++i)for(std::size_t j=0;j<cols;++j)x[i*ld+j]=sample<T>(i*cols+j,salt);
}
template<class T> bool tail_and_padding_ok(const std::vector<T>& c,const std::vector<T>& before,std::size_t m,std::size_t n,std::size_t ldc) {
    for(std::size_t i=0;i<m;++i)for(std::size_t j=n;j<ldc;++j)
        if(std::memcmp(&c[i*ldc+j],&before[i*ldc+j],sizeof(T))!=0)return false;
    for(std::size_t q=m*ldc;q<c.size();++q)
        if(std::memcmp(&c[q],&before[q],sizeof(T))!=0)return false;
    return true;
}
template<class T> bool same_bits(const std::vector<T>& a,const std::vector<T>& b) {
    return a.size()==b.size()&&std::memcmp(a.data(),b.data(),a.size()*sizeof(T))==0;
}
void put32(std::array<unsigned char,48>& h,std::size_t off,std::uint32_t v){for(int i=0;i<4;++i)h[off+i]=static_cast<unsigned char>(v>>(8*i));}
void put64(std::array<unsigned char,48>& h,std::size_t off,std::uint64_t v){for(int i=0;i<8;++i)h[off+i]=static_cast<unsigned char>(v>>(8*i));}
bool write_all(const void* p,std::size_t n) {
    auto* b=static_cast<const unsigned char*>(p);
    while(n){const ssize_t k=::write(STDOUT_FILENO,b,n);if(k<0){if(errno==EINTR)continue;return false;}if(k==0)return false;b+=k;n-=static_cast<std::size_t>(k);}
    return true;
}
template<class T> int execute(const Case& s) {
    constexpr std::size_t tail_elems=64/sizeof(T);
    const std::size_t lda=s.k+1,ldb=s.n+1,ldc=s.n+1;
    std::vector<T> a(s.m*lda+tail_elems,static_cast<T>(sentinel));
    std::vector<T> b(s.k*ldb+tail_elems,static_cast<T>(sentinel));
    std::vector<T> c(s.m*ldc+tail_elems,static_cast<T>(sentinel));
    if(s.mode==overflow||s.mode==cancellation){
        for(std::size_t i=0;i<s.m;++i)for(std::size_t q=0;q<s.k;++q)
            a[i*lda+q]=(s.mode==cancellation&&(q&1))?static_cast<T>(-1.0e30):static_cast<T>(1.0e30);
        for(std::size_t q=0;q<s.k;++q)for(std::size_t j=0;j<s.n;++j)b[q*ldb+j]=static_cast<T>(1.0e30);
    }else if(s.mode==alias_a){
        fill_matrix(a,s.m,s.k,lda,0x84a11ceULL);fill_matrix(b,s.k,s.n,ldb,0x84b17d3ULL);
        for(std::size_t i=0;i<s.m;++i)for(std::size_t q=0;q<s.k;++q)c[i*lda+q]=a[i*lda+q];
    }else if(s.mode==alias_b){
        fill_matrix(a,s.m,s.k,lda,0x84a11ceULL);fill_matrix(b,s.k,s.n,ldb,0x84b17d3ULL);
        for(std::size_t q=0;q<s.k;++q)for(std::size_t j=0;j<s.n;++j)c[q*ldb+j]=b[q*ldb+j];
    }else{
        fill_matrix(a,s.m,s.k,lda,0x84a11ceULL);fill_matrix(b,s.k,s.n,ldb,0x84b17d3ULL);
    }
    const std::vector<T> c_initial=c;
    const T* ap=(s.mode==alias_a)?c.data():a.data();
    const T* bp=(s.mode==alias_b)?c.data():b.data();
    bool threw=false,unexpected=false;
    try {
        if constexpr(std::is_same_v<T,float>) ozamx::gemm_fp32(s.m,s.n,s.k,ap,lda,bp,ldb,c.data(),ldc);
        else ozamx::gemm_fp64(s.m,s.n,s.k,ap,lda,bp,ldb,c.data(),ldc,static_cast<ozamx::ProductBudget>(s.budget));
    } catch(const ozamx::Error& e) { threw=true;std::fprintf(stderr,"case=%s ozamx::Error: %s\n",s.name,e.what()); }
      catch(const std::exception& e) { threw=true;unexpected=true;std::fprintf(stderr,"case=%s std::exception: %s\n",s.name,e.what()); }
      catch(...) { threw=true;unexpected=true;std::fprintf(stderr,"case=%s unknown exception\n",s.name); }
    const bool expected_throw=(s.mode==overflow||s.mode==cancellation);
    const bool unchanged=threw&&same_bits(c,c_initial);
    std::uint32_t status=0;
    if(unexpected||(threw!=expected_throw))status=2;
    else if(expected_throw&&!unchanged)status=3;
    const std::uint32_t guards=(!threw&&!tail_and_padding_ok(c,c_initial,s.m,s.n,ldc))?1:0;
    if(guards&&status==0)status=4;
    const std::uint64_t bytes=c.size()*sizeof(T),slots=c.size();
    std::array<unsigned char,48> h{};std::memcpy(h.data(),"OZBGATE1",8);
    put32(h,8,1);put32(h,12,s.id);put32(h,16,s.type);put32(h,20,status);
    put64(h,24,bytes);put64(h,32,slots);put32(h,40,guards);put32(h,44,unchanged?1:0);
    if(!write_all(h.data(),h.size())||!write_all(c.data(),static_cast<std::size_t>(bytes)))return 5;
    return status?6:0;
}
}
int main(int argc,char** argv) {
    if(argc!=2)return 2;
    const auto id=static_cast<std::uint32_t>(std::stoul(argv[1]));
    const Case* selected=nullptr;for(const auto& s:cases)if(s.id==id){selected=&s;break;}
    if(!selected)return 2;
    unsigned char go=0;if(::read(STDIN_FILENO,&go,1)!=1||go!=1)return 3;
    if(selected->type==f32)return execute<float>(*selected);
    return execute<double>(*selected);
}
