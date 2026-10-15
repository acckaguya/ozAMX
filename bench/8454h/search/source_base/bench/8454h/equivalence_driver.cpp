#include "ozamx/gemm.hpp"
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <limits>
#include <cmath>

static std::uint64_t mix(std::uint64_t x) {
  x += 0x9e3779b97f4a7c15ULL; x = (x ^ (x >> 30))*0xbf58476d1ce4e5b9ULL;
  x = (x ^ (x >> 27))*0x94d049bb133111ebULL; return x ^ (x >> 31);
}
template<class T> static T value(std::size_t idx, std::uint64_t salt) {
  const auto u=mix(idx+salt); const int v=static_cast<int>(u%2001)-1000;
  return static_cast<T>(v)/static_cast<T>(997);
}
static void emit32(const std::vector<float>& c, std::size_t m, std::size_t n, std::size_t k, std::size_t ldc, bool pad) {
  std::cout << "{\"type\":\"f32\",\"m\":"<<m<<",\"n\":"<<n<<",\"k\":"<<k<<",\"ldc\":"<<ldc<<",\"padding_ok\":"<<(pad?"true":"false")<<",\"bits\":[";
  bool first=true; for(std::size_t i=0;i<m*ldc;++i){std::uint32_t x;std::memcpy(&x,&c[i],4);if(!first)std::cout<<',';first=false;std::cout<<'"'<<std::hex<<std::setw(8)<<std::setfill('0')<<x<<std::dec<<'"';}
  std::cout<<"]}\n";
}
static void emit64(const std::vector<double>& c, std::size_t m, std::size_t n, std::size_t k, std::size_t ldc, bool pad, int budget) {
  std::cout << "{\"type\":\"f64\",\"m\":"<<m<<",\"n\":"<<n<<",\"k\":"<<k<<",\"ldc\":"<<ldc<<",\"budget\":"<<budget<<",\"padding_ok\":"<<(pad?"true":"false")<<",\"bits\":[";
  bool first=true; for(std::size_t i=0;i<m*ldc;++i){std::uint64_t x;std::memcpy(&x,&c[i],8);if(!first)std::cout<<',';first=false;std::cout<<'"'<<std::hex<<std::setw(16)<<std::setfill('0')<<x<<std::dec<<'"';}
  std::cout<<"]}\n";
}
int main() {
  const std::size_t shapes[][3]={{3,5,0},{17,19,0},{257,129,0},{127,127,1},{128,128,1},{129,129,1},{255,255,1},{256,256,1},{257,257,1},{257,129,1},{129,257,1}};
  const std::size_t ks[]={255,256,257,513};
  for(auto sh:shapes)for(std::size_t ki=0;ki<(sh[2]?1:4);++ki){
    const std::size_t k=sh[2]?257:ks[ki];
    const std::size_t m=sh[0],n=sh[1],lda=k+3,ldb=n+5,ldc=n+7;
    std::vector<float> af(m*lda),bf(k*ldb),cf(m*ldc,12345.25f);
    std::vector<double> ad(m*lda),bd(k*ldb),cd(m*ldc,-9876.5);
    for(std::size_t i=0;i<m;++i)for(std::size_t q=0;q<k;++q){const auto z=i*k+q;af[i*lda+q]=value<float>(z,0xabc);ad[i*lda+q]=value<double>(z,0xabc);}
    for(std::size_t q=0;q<k;++q)for(std::size_t j=0;j<n;++j){const auto z=q*n+j;bf[q*ldb+j]=value<float>(z,0xdef);bd[q*ldb+j]=value<double>(z,0xdef);}
    ozamx::gemm_fp32(m,n,k,af.data(),lda,bf.data(),ldb,cf.data(),ldc);
    bool pad=true;for(std::size_t i=0;i<m;++i)for(std::size_t j=n;j<ldc;++j)pad &= cf[i*ldc+j]==12345.25f;
    emit32(cf,m,n,k,ldc,pad);
    const ozamx::ProductBudget budgets[]={ozamx::ProductBudget::p6,ozamx::ProductBudget::p10,ozamx::ProductBudget::p15,ozamx::ProductBudget::p21};
    for(auto b:budgets){std::fill(cd.begin(),cd.end(),-9876.5);ozamx::gemm_fp64(m,n,k,ad.data(),lda,bd.data(),ldb,cd.data(),ldc,b);pad=true;for(std::size_t i=0;i<m;++i)for(std::size_t j=n;j<ldc;++j)pad &= cd[i*ldc+j]==-9876.5;emit64(cd,m,n,k,ldc,pad,static_cast<int>(b));}
  }
}
