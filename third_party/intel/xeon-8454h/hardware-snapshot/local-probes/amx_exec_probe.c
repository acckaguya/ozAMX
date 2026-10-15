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
 unsigned long mask=0;
 long req=syscall(SYS_arch_prctl,ARCH_REQ_XCOMP_PERM,18UL);
 long get=syscall(SYS_arch_prctl,ARCH_GET_XCOMP_PERM,&mask);
 if(req || get || (mask&(3UL<<17))!=(3UL<<17)) { printf("permission_failed req=%ld get=%ld mask=0x%lx\n",req,get,mask); return 2; }
 __asm__ volatile("tilerelease" ::: "memory");
 printf("permission=0x%lx tilerelease=executed\n",mask);
 return 0;
}
