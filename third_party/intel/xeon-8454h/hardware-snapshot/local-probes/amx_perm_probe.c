#define _GNU_SOURCE
#include <stdio.h>
#include <sys/syscall.h>
#include <unistd.h>
#ifndef ARCH_REQ_XCOMP_PERM
#define ARCH_REQ_XCOMP_PERM 0x1023
#endif
#ifndef ARCH_GET_XCOMP_PERM
#define ARCH_GET_XCOMP_PERM 0x1022
#endif
int main(void) {
 unsigned long before=0, after=0;
 long b=syscall(SYS_arch_prctl,ARCH_GET_XCOMP_PERM,&before);
 long q=syscall(SYS_arch_prctl,ARCH_REQ_XCOMP_PERM,18UL);
 long a=syscall(SYS_arch_prctl,ARCH_GET_XCOMP_PERM,&after);
 printf("get_before_ret=%ld mask_before=0x%lx request_component18_ret=%ld get_after_ret=%ld mask_after=0x%lx amx_perm_after=%d\n",b,before,q,a,after,(int)((after&(3UL<<17))==(3UL<<17)));
 return q==0 && (after&(3UL<<17))==(3UL<<17) ? 0 : 1;
}
