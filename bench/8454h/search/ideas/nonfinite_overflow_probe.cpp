#include "ozamx/gemm.hpp"
#include <vector>
#include <cmath>
#include <iostream>
#include <cstring>
template<class T> void probe(bool cancel){const size_t m=3,n=5,k=512,ldc=8;std::vector<T>a(m*k,T(std::ldexp(1.0,60))),b(k*n),c(m*ldc,T(17));for(size_t q=0;q<k;q++)for(size_t j=0;j<n;j++)b[q*n+j]=T(std::ldexp(1.0,60))*(cancel&&q>=256?T(-1):T(1));bool rejected=false;try{if constexpr(sizeof(T)==4)ozamx::gemm_fp32(m,n,k,a.data(),k,b.data(),n,c.data(),ldc);else ozamx::gemm_fp64(m,n,k,a.data(),k,b.data(),n,c.data(),ldc,ozamx::ProductBudget::p21);}catch(const ozamx::Error&e){rejected=true;}if(!rejected)throw std::runtime_error("overflow was accepted");for(T x:c)if(x!=T(17))throw std::runtime_error("overflow changed C");}
int main(){try{probe<float>(false);probe<float>(true);probe<double>(false);probe<double>(true);std::cout<<"4 overflow/cancellation cases rejected; C unchanged\n";}catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
