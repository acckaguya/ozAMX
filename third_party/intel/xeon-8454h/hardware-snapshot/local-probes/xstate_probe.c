#define _GNU_SOURCE
#include <cpuid.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/syscall.h>
#include <unistd.h>
#include <asm/prctl.h>
#include <sys/prctl.h>
#ifndef ARCH_GET_XCOMP_SUPP
#define ARCH_GET_XCOMP_SUPP 0x1021
#endif
#ifndef ARCH_GET_XCOMP_PERM
#define ARCH_GET_XCOMP_PERM 0x1022
#endif
int main(void) {
 unsigned a,b,c,d; unsigned long long xcr0=0, supp=0, perm=0;
 __cpuid(1,a,b,c,d); int osxsave=(c>>27)&1;
 __cpuid_count(7,0,a,b,c,d); int avx512=(b>>16)&1, amxtile=(d>>24)&1, amxint8=(d>>25)&1, amxbf16=(d>>22)&1;
 if (osxsave) { unsigned lo,hi; __asm__ volatile("xgetbv":"=a"(lo),"=d"(hi):"c"(0)); xcr0=((unsigned long long)hi<<32)|lo; }
 long rs=syscall(SYS_arch_prctl,ARCH_GET_XCOMP_SUPP,&supp);
 long rp=syscall(SYS_arch_prctl,ARCH_GET_XCOMP_PERM,&perm);
 printf("osxsave=%d avx512f_cpuid=%d amx_tile_cpuid=%d amx_int8_cpuid=%d amx_bf16_cpuid=%d\n",osxsave,avx512,amxtile,amxint8,amxbf16);
 int avx=(xcr0>>2)&1, avx512_state=((xcr0>>5)&1)&&((xcr0>>6)&1)&&((xcr0>>7)&1), tilecfg=(xcr0>>17)&1, tiledata=(xcr0>>18)&1;
 printf("xcr0=0x%llx xcr0_avx=%d xcr0_avx512_opmask_zmm_hi=%d xcr0_amx_tilecfg=%d xcr0_amx_tiledata=%d\n", xcr0, avx, avx512_state, tilecfg, tiledata);
 printf("get_xcomp_supp_ret=%ld mask=0x%llx get_xcomp_perm_ret=%ld mask=0x%llx amx_perm_initial=%d\n",rs,supp,rp,perm,(int)((perm&(3ULL<<17))==(3ULL<<17)));
}
