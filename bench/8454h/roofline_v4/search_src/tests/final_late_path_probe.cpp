#include "ozamx/gemm.hpp"

#include <cstring>
#include <iostream>
#include <vector>

bool run(std::size_t k) {
    constexpr std::size_t m=3,n=5,lda_extra=2,ldb_extra=3,ldc_extra=4;
    const std::size_t lda=k+lda_extra,ldb=n+ldb_extra,ldc=n+ldc_extra;
    std::vector<double> a(m*lda,0.0),b(k*ldb,0.0),c(m*ldc+7,981.75);
    for(std::size_t i=0;i<m;++i)for(std::size_t q=0;q<k;++q)a[i*lda+q]=((q&1)?-1.0:1.0)*1.0e30;
    for(std::size_t q=0;q<k;++q)for(std::size_t j=0;j<n;++j)b[q*ldb+j]=1.0e30;
    const auto original=c;
    bool threw=false;
    try { ozamx::gemm_fp64(m,n,k,a.data(),lda,b.data(),ldb,c.data(),ldc,ozamx::ProductBudget::p6); }
    catch(const ozamx::Error&) { threw=true; }
    bool unchanged=c.size()==original.size();
    for(std::size_t i=0;i<c.size();++i)unchanged &= std::memcmp(&c[i],&original[i],sizeof(double))==0;
    std::cout<<"{\"case\":\"late_overflow_k"<<k<<"\",\"threw\":"<<(threw?"true":"false")
             <<",\"c_unchanged\":"<<(unchanged?"true":"false")<<"}\n";
    return threw&&unchanged;
}
int main(){return run(4096)&&run(4097)?0:1;}
