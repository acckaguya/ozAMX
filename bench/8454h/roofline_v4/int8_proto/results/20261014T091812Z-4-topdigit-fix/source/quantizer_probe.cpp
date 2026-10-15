#include <immintrin.h>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <random>
#include <vector>

__attribute__((target("avx512f,avx512dq,avx512bw,avx512vl")))
void vec8(const double* input, int scale, int8_t out[8][8], int64_t rem[8]) {
    __m512d values = _mm512_loadu_pd(input);
    __m512d scalev = _mm512_set1_pd((double)scale);
    __m512i q = _mm512_cvt_roundpd_epi64(_mm512_scalef_pd(values, scalev),
        _MM_FROUND_TO_NEAREST_INT | _MM_FROUND_NO_EXC);
    int64_t lanes[8];
    for (int step=0;step<7;++step) {
        __m512i shifted=_mm512_add_epi64(q,_mm512_set1_epi64(64));
        __m512i remainder=_mm512_and_epi64(shifted,_mm512_set1_epi64(127));
        __m512i digit=_mm512_sub_epi64(remainder,_mm512_set1_epi64(64));
        q=_mm512_srai_epi64(_mm512_sub_epi64(q,digit),7);
        _mm512_storeu_si512(lanes,digit);
        for(int l=0;l<8;++l) out[7-step][l]=(int8_t)lanes[l];
    }
    _mm512_storeu_si512(rem,q);
    for(int l=0;l<8;++l) out[0][l]=(int8_t)rem[l];
}
bool scalar(double v,int scale,int8_t d[8],int64_t& rem) {
    double x=std::scalbn(v,scale), fl=std::floor(x), f=x-fl, r=fl;
    if(f>.5) r=fl+1; else if(f==.5 && std::fmod(std::abs(fl),2.)==1.) r=fl+1;
    int64_t q=(int64_t)r; int8_t lo[7]{};
    for(int i=0;i<7;++i){int64_t z=q%128;if(z<0)z+=128;int64_t digit=z>=64?z-128:z;q=(q-digit)/128;lo[i]=(int8_t)digit;}
    rem=q;d[0]=(int8_t)q;for(int i=0;i<7;++i)d[i+1]=lo[6-i];return q>=-64&&q<=64;
}
bool check_one(double v,int scale) {
    alignas(64) double values[8]; values[0]=v; for(int i=1;i<8;++i)values[i]=v;
    int8_t vd[8][8];int64_t vr[8];vec8(values,scale,vd,vr);
    int8_t sd[8];int64_t sr;bool ok=scalar(v,scale,sd,sr);
    __int128 rebuilt=0;for(int i=0;i<8;++i)rebuilt=rebuilt*128+sd[i];
    bool same=true;for(int i=0;i<8;++i)same &= vd[i][0]==sd[i];
    return ok && same && vr[0]==sr && rebuilt==(__int128)std::nearbyint(std::scalbn(v,scale));
}
int main(){
  std::mt19937_64 rng(260967); std::uniform_real_distribution<double> u(-1,1);
  constexpr size_t M=32,K=63;std::vector<double>a(M*K);double mx=0;
  for(auto&x:a){x=u(rng);mx=std::max(mx,std::abs(x));}
  int e=0;std::frexp(mx,&e);int scale=55-e;std::cerr<<"mx="<<mx<<" exponent="<<e<<" scale="<<scale<<"\\n";
  int nvecbad=0,nscbad=0,ndiff=0;
  for(size_t i=0;i<M;++i) for(size_t k=0;k+8<=K;k+=8){
    int8_t vd[8][8];int64_t vr[8];vec8(&a[i*K+k],scale,vd,vr);
    for(int l=0;l<8;++l){int8_t sd[8];int64_t sr;bool sok=scalar(a[i*K+k+l],scale,sd,sr);if(vr[l]){++nvecbad;if(nvecbad<=12)std::cerr<<"vector residual value="<<a[i*K+k+l]<<" rounded="<<std::scalbn(a[i*K+k+l],scale)<<" residual="<<vr[l]<<"\\n";}if(!sok)++nscbad;
      for(int d=0;d<8;++d)if(vd[d][l]!=sd[d]){if(ndiff<10)std::cerr<<"diff i="<<i<<" k="<<k+l<<" digit="<<d<<" v="<<(int)vd[d][l]<<" s="<<(int)sd[d]<<" val="<<a[i*K+k+l]<<"\\n";++ndiff;break;}
    }
  }
  std::cout<<"vector residual lanes="<<nvecbad<<" scalar residual values="<<nscbad<<" digit mismatches="<<ndiff<<"\\n";
  const double edge_values[]={std::scalbn(1.0,55)-64.0,-std::scalbn(1.0,55)+64.0,
      std::scalbn(1.0,55)-4.0,-std::scalbn(1.0,55)+4.0,
      63.5,64.5,-63.5,-64.5,0.5,-0.5};
  bool edge_ok=true;for(double x:edge_values)edge_ok &= check_one(x,0);
  std::cout<<"top-digit and RNE edge cases="<<(edge_ok?"PASS":"FAIL")<<"\\n";
  if(!edge_ok)return 1;
}
