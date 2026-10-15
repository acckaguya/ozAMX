#include <immintrin.h>
#include <omp.h>
#include <cpuid.h>
#include <sys/syscall.h>
#include <asm/prctl.h>
#include <unistd.h>
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include <cmath>

#ifndef ARCH_REQ_XCOMP_PERM
#define ARCH_REQ_XCOMP_PERM 0x1023
#endif
extern "C" void ozroof_tileload(const void*,std::size_t,unsigned);
extern "C" void ozroof_tileload_t1(const void*,std::size_t,unsigned);
extern "C" void ozamx_bf16_product(const std::uint16_t*,const std::uint16_t*,float*,unsigned);
extern "C" void ozamx_bf16_six(const std::uint16_t* const*,const std::uint16_t* const*,float*,unsigned);
using Clock=std::chrono::steady_clock;
struct alignas(64) TileConfig{std::uint8_t palette=1,start=0,reserved[14]{};std::uint16_t colsb[16]{};std::uint8_t rows[16]{};};
static_assert(sizeof(TileConfig)==64);
enum Mode{LOAD,LOAD_T1,REGISTER,PRODUCT6,PRODUCT21,MIX6,MIX21,SIX,SIX_MIX,RECON64,RECON32};
struct Sample{double seconds=0,checksum=0,ops=0,bytes=0;std::uint64_t units=0;bool valid=true;};
constexpr std::size_t PANEL=32*256;
struct alignas(64) Local{alignas(64) float micro[1024];alignas(64) double block64[32*144];alignas(64) float block32[32*144];};
__attribute__((noinline)) void reconstruct64(double* block,const float* micro,unsigned stride){
 for(unsigned i=0;i<32;++i)for(unsigned j=0;j<32;j+=16){const auto f=_mm512_load_ps(micro+i*32+j);const auto lo=_mm512_cvtps_pd(_mm512_castps512_ps256(f)),hi=_mm512_cvtps_pd(_mm512_extractf32x8_ps(f,1));_mm512_store_pd(block+i*stride+j,_mm512_add_pd(_mm512_load_pd(block+i*stride+j),lo));_mm512_store_pd(block+i*stride+j+8,_mm512_add_pd(_mm512_load_pd(block+i*stride+j+8),hi));}
}
__attribute__((noinline)) void reconstruct32(float* block,const float* micro,unsigned stride){
 for(unsigned i=0;i<32;++i)for(unsigned j=0;j<32;j+=16)_mm512_store_ps(block+i*stride+j,_mm512_add_ps(_mm512_load_ps(block+i*stride+j),_mm512_load_ps(micro+i*32+j)));
}
template<Mode M> Sample measure(int threads,std::size_t footprint,unsigned stride){
 Sample s;std::uint64_t units=0;double checksum=0;int bad=0;Clock::time_point begin,end;
#pragma omp parallel num_threads(threads) reduction(+:units,checksum) reduction(|:bad) shared(begin,end)
 {
  void* storage=nullptr;const bool permitted=syscall(SYS_arch_prctl,ARCH_REQ_XCOMP_PERM,18)==0;
  if(!permitted||posix_memalign(&storage,64,footprint)!=0)bad=1;
  auto* data=static_cast<std::uint16_t*>(storage);Local own{};
  if(storage)for(std::size_t i=0;i<footprint/2;++i)data[i]=0x3f80;
  for(float&x:own.micro)x=1.f;
  TileConfig cfg{};for(unsigned t=0;t<8;++t){cfg.colsb[t]=64;cfg.rows[t]=16;}
  if(permitted&&storage){_tile_loadconfig(&cfg);_tile_loadd(0,data,64);_tile_loadd(1,data+512,64);_tile_zero(4);_tile_zero(5);_tile_zero(6);_tile_zero(7);}
#pragma omp barrier
#pragma omp master
  {begin=Clock::now();}
#pragma omp barrier
  std::uint64_t it=0;std::size_t offset=0;
  if(permitted&&storage){
   const auto stop=begin+std::chrono::milliseconds(80);
   do{
    if constexpr(M==LOAD||M==LOAD_T1){const unsigned count=unsigned(std::max<std::size_t>(1024,footprint/4096));if constexpr(M==LOAD)ozroof_tileload(data,footprint,count);else ozroof_tileload_t1(data,footprint,count);it+=count;}
    else for(unsigned batch=0;batch<64;++batch){
     if constexpr(M==REGISTER){_tile_dpbf16ps(4,0,1);_tile_dpbf16ps(5,0,1);_tile_dpbf16ps(6,0,1);_tile_dpbf16ps(7,0,1);}
     else if constexpr(M==RECON64)reconstruct64(own.block64,own.micro,stride);
     else if constexpr(M==RECON32)reconstruct32(own.block32,own.micro,stride);
     else if constexpr(M==SIX||M==SIX_MIX){const std::uint16_t* a[3]={data,data+PANEL,data+2*PANEL};const std::uint16_t* b[3]={data+3*PANEL,data+4*PANEL,data+5*PANEL};ozamx_bf16_six(a,b,own.micro,8);if constexpr(M==SIX_MIX)reconstruct32(own.block32,own.micro,stride);}
     else{
      constexpr unsigned depth=(M==PRODUCT6||M==MIX6)?3:6;
      for(unsigned d=0;d<depth;++d)for(unsigned ai=0;ai<=d;++ai){ozamx_bf16_product(data+ai*PANEL,data+(6+d-ai)*PANEL,own.micro,8);if constexpr(M==MIX6||M==MIX21)reconstruct64(own.block64,own.micro,stride);}
     }
     ++it;asm volatile("" ::: "memory");
    }
   }while(Clock::now()<stop);
  }
#pragma omp barrier
#pragma omp master
  {end=Clock::now();}
  // Consume output and check exact powers-of-two test values outside timing.
  double expected=0,actual=0;
  if constexpr(M==LOAD||M==LOAD_T1){alignas(64) std::uint16_t out[512];if(permitted)_tile_stored(0,out,64);actual=out[0];expected=0x3f80;}
  else if constexpr(M==REGISTER){if(permitted)_tile_stored(4,own.micro,64);actual=own.micro[0];expected=double(it)*32;}
  else if constexpr(M==RECON64){actual=own.block64[0];expected=double(it);}
  else if constexpr(M==RECON32){actual=own.block32[0];expected=double(it);}
  else if constexpr(M==MIX6||M==MIX21){actual=own.block64[0];expected=double(it)*(M==MIX6?6:21)*256;}
  else if constexpr(M==SIX_MIX){actual=own.block32[0];expected=double(it)*6*256;}
  else{actual=own.micro[0];expected=M==SIX?6*256:256;}
  if(!storage||!permitted||actual!=expected||!std::isfinite(actual))bad=1;
  checksum+=actual;units+=it;if(permitted)_tile_release();std::free(storage);(void)offset;
 }
 s.seconds=std::chrono::duration<double>(end-begin).count();s.units=units;s.checksum=checksum;s.valid=!bad;
 if constexpr(M==LOAD||M==LOAD_T1)s.bytes=double(units)*4096;
 else if constexpr(M==REGISTER)s.ops=double(units)*4*16384;
 else if constexpr(M==RECON64){s.ops=double(units)*1024;s.bytes=double(units)*1024*20;}
 else if constexpr(M==RECON32){s.ops=double(units)*1024;s.bytes=double(units)*1024*12;}
 else if constexpr(M==SIX||M==SIX_MIX){s.ops=double(units)*6*2*32*32*256;s.bytes=double(units)*(14*1024*8+4096+(M==SIX_MIX?1024*12:0));}
 else{constexpr unsigned p=(M==PRODUCT6||M==MIX6)?6:21;s.ops=double(units)*p*2*32*32*256;s.bytes=double(units)*p*(4*1024*8+4096+((M==MIX6||M==MIX21)?1024*20:0));}
 return s;
}
template<Mode M> void emit(std::ostream&out,const std::string&name,int threads,std::size_t footprint,unsigned stride){
 for(int rep=-1;rep<3;++rep){auto r=measure<M>(threads,footprint,stride);if(!r.valid)throw std::runtime_error("checksum/permission failed: "+name);out<<(rep<0?"warmup":"rep")<<','<<name<<','<<threads<<','<<rep<<','<<footprint<<','<<stride<<','<<r.seconds<<','<<r.units<<','<<r.ops<<','<<r.bytes<<','<<r.ops/r.seconds<<','<<r.bytes/r.seconds<<','<<r.checksum<<",passed\n";out.flush();}
}
int main(int argc,char**argv)try{
 if(argc!=2)throw std::runtime_error("usage: roofline_kernels OUTPUT.csv");unsigned a,b,c,d;if(!__get_cpuid_count(7,0,&a,&b,&c,&d)||!(d&(1u<<22))||!(d&(1u<<24)))throw std::runtime_error("AMX BF16/TILE unavailable");
 std::ofstream out(argv[1]);if(!out)throw std::runtime_error("cannot open CSV");out<<"record,kernel,threads,rep,worker_input_bytes,stride_elements,elapsed_s,units,amx_or_add_ops,logical_bytes,ops_per_s,logical_B_per_s,checksum,validation\n"<<std::setprecision(17);
 for(int th:{1,32,64}){
  for(std::size_t sz:{std::size_t(4096),std::size_t(1<<20),std::size_t(2304<<10),std::size_t(24<<20)}){emit<LOAD>(out,"tileload",th,sz,0);emit<LOAD_T1>(out,"tileload_t1",th,sz,0);}
  emit<REGISTER>(out,"amx_register",th,4096,0);
  emit<PRODUCT6>(out,"p6_no_reconstruct",th,12*PANEL*2,128);emit<MIX6>(out,"p6_with_reconstruct",th,12*PANEL*2,128);
  emit<PRODUCT21>(out,"p21_no_reconstruct",th,12*PANEL*2,128);emit<MIX21>(out,"p21_with_reconstruct",th,12*PANEL*2,128);
  emit<SIX>(out,"fp32_six_no_reconstruct",th,6*PANEL*2,128);emit<SIX_MIX>(out,"fp32_six_with_reconstruct",th,6*PANEL*2,128);
  for(unsigned st:{128,136})emit<RECON64>(out,"reconstruct64",th,4096,st);
  for(unsigned st:{128,144})emit<RECON32>(out,"reconstruct32",th,4096,st);
 }
 return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
