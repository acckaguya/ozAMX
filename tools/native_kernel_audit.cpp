#include "../src/gemm.cpp"
#include <random>
#include <iostream>
#include <iomanip>
#include <cstring>
#include <cmath>
#include <cstdint>
#include <limits>

namespace {
std::uint32_t fbits(float x){std::uint32_t u;std::memcpy(&u,&x,4);return u;}
std::uint32_t ordered(std::uint32_t u){return (u&0x80000000u)?~u:(u|0x80000000u);}
std::uint32_t ulp(float a,float b){auto x=ordered(fbits(a)),y=ordered(fbits(b));return x>y?x-y:y-x;}
struct Metrics{std::uint64_t n=0,not_exact=0;std::uint32_t max_ulp=0;long double max_abs=0,max_rel=0;};
void audit_case(std::size_t m,std::size_t n,std::size_t k,std::uint64_t seed,Metrics& met,
                std::uint64_t& pack_errors,std::uint64_t& padding_errors,
                std::uint64_t& reconstruction_n,std::uint64_t& reconstruction_mismatches){
  ozamx::load_config();
  std::mt19937_64 rng(seed);std::uniform_real_distribution<double> dist(-1.0,1.0);
  std::vector<double>a(m*k),b(k*n);
  for(auto&x:a)x=dist(rng);for(auto&x:b)x=dist(rng);
  std::vector<std::uint16_t> as,bs;ozamx::split64(a.data(),a.size(),as);ozamx::split64(b.data(),b.size(),bs);
  auto p=ozamx::pack64<6>(as,bs,m,n,k);
  // Verify every packed A value and every pair-interleaved B value, including all padding.
  for(int s=0;s<6;++s){
    for(std::size_t mb=0;mb<p.mblocks;++mb)for(std::size_t kb=0;kb<p.kblocks;++kb)
      for(std::size_t i=0;i<ozamx::BM;++i)for(std::size_t q=0;q<ozamx::BK;++q){
        const std::size_t gi=mb*ozamx::BM+i,gk=kb*ozamx::BK+q;
        const auto want=(gi<m&&gk<k)?as[std::size_t(s)*m*k+gi*k+gk]:0;
        const auto got=p.a[s][ozamx::apanel_index<0>(mb,kb,i,q,p.kblocks)];
        if(got!=want){++pack_errors;++padding_errors;}
      }
    for(std::size_t kb=0;kb<p.kblocks;++kb)for(std::size_t nb=0;nb<p.nblocks;++nb)
      for(std::size_t kp=0;kp<ozamx::BK/2;++kp)for(std::size_t j=0;j<ozamx::BN;++j){
        const auto gk=kb*ozamx::BK+2*kp,gn=nb*ozamx::BN+j;
        const auto off=ozamx::bpanel_index(kb,nb,kp,j,p.nblocks);
        const auto w0=(gk<k&&gn<n)?bs[std::size_t(s)*k*n+gk*n+gn]:0;
        const auto w1=(gk+1<k&&gn<n)?bs[std::size_t(s)*k*n+(gk+1)*n+gn]:0;
        if(p.b[s][off]!=w0){++pack_errors;++padding_errors;}
        if(p.b[s][off+1]!=w1){++pack_errors;++padding_errors;}
      }
  }
  for(std::size_t mb=0;mb<p.mblocks;++mb)for(std::size_t nb=0;nb<p.nblocks;++nb)
   for(std::size_t kb=0;kb<p.kblocks;++kb)for(int ai=0;ai<6;++ai)for(int bi=0;bi<6;++bi){
    float got[ozamx::TM*ozamx::TN];
    ozamx::run_fp64_product<6>(p,ai,bi,mb,nb,kb,0,0,got);
    for(std::size_t i=0;i<ozamx::TM;++i)for(std::size_t j=0;j<ozamx::TN;++j){
      const std::size_t gi=mb*ozamx::TM+i,gj=nb*ozamx::TN+j;
      long double exact=0;
      for(std::size_t q=0;q<ozamx::BK;++q){
        const auto gk=kb*ozamx::BK+q;
        if(gk>=k)continue;
        const auto av=ozamx::bf16_to_float(p.a[ai][ozamx::apanel_index<0>(mb,kb,i,q,p.kblocks)]);
        const auto bv=ozamx::bf16_to_float(p.b[bi][ozamx::bpanel_index(kb,nb,q/2,gj%ozamx::BN,p.nblocks)+(q%2)]);
        exact+=(long double)av*(long double)bv;
      }
      const float ref=(float)exact, v=got[i*ozamx::TN+j];
      ++met.n;if(fbits(ref)!=fbits(v))++met.not_exact;
      met.max_ulp=std::max(met.max_ulp,ulp(ref,v));
      const long double e=std::fabs((long double)v-(long double)ref);
      met.max_abs=std::max(met.max_abs,e);
      if(exact!=0)met.max_rel=std::max(met.max_rel,e/std::fabs(exact));
      if(gi>=m||gj>=n){if(v!=0.0f)++padding_errors;}
    }
   }
  std::vector<double> out(m*n);
  ozamx::gemm_fp64(m,n,k,a.data(),k,b.data(),n,out.data(),n,ozamx::ProductBudget::p21);
  for(std::size_t i=0;i<m;++i)for(std::size_t j=0;j<n;++j){
    double ref=0.0;
    for(std::size_t kb=0;kb<p.kblocks;++kb)for(int d=0;d<6;++d)for(int ai=0;ai<=d;++ai){
      const int bi=d-ai;long double exact=0;
      for(std::size_t q=0;q<ozamx::BK;++q){
        const auto gk=kb*ozamx::BK+q;if(gk>=k)continue;
        const auto av=ozamx::bf16_to_float(p.a[ai][ozamx::apanel_index<0>(0,kb,i,q,p.kblocks)]);
        const auto bv=ozamx::bf16_to_float(p.b[bi][ozamx::bpanel_index(kb,0,q/2,j,p.nblocks)+(q%2)]);
        exact+=(long double)av*(long double)bv;
      }
      ref+=(double)(float)exact;
    }
    ++reconstruction_n;if(std::memcmp(&ref,&out[i*n+j],sizeof(double))!=0)++reconstruction_mismatches;
  }
}
}
int main(){
  auto s=ozamx::request_amx_permission_for_current_thread();
  if(!s.cpu_amx_tile||!s.cpu_amx_bf16||!s.permission_available){std::cerr<<s.message<<"\n";return 2;}
  ozamx::load_config();Metrics m;std::uint64_t pe=0,pade=0,rn=0,rm=0;
  audit_case(5,7,7,0xabc1,m,pe,pade,rn,rm);
  audit_case(16,19,256,0xabc2,m,pe,pade,rn,rm);
  audit_case(17,23,512,0xabc3,m,pe,pade,rn,rm);
  _tile_release();
  std::cout<<std::setprecision(20)<<"{\"component_bk_fp32_stores\":"<<m.n<<",\"bitwise_equal_to_long_double_rounded_fp32\":"<<(m.n-m.not_exact)<<",\"not_bitwise_equal\":"<<m.not_exact<<",\"max_ulp\":"<<m.max_ulp<<",\"max_abs_error\":"<<(double)m.max_abs<<",\"max_rel_error\":"<<(double)m.max_rel<<",\"packing_mismatches\":"<<pe<<",\"padding_nonzero_or_mismatch\":"<<pade<<",\"reconstructed_outputs\":"<<rn<<",\"reconstruction_bitwise_mismatches\":"<<rm<<"}\n";
}
