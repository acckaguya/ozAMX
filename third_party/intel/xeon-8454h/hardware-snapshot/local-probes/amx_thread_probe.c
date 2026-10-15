#define _GNU_SOURCE
#include <pthread.h>
#include <stdio.h>
#include <sys/syscall.h>
#include <unistd.h>
#ifndef ARCH_REQ_XCOMP_PERM
#define ARCH_REQ_XCOMP_PERM 0x1023
#endif
#ifndef ARCH_GET_XCOMP_PERM
#define ARCH_GET_XCOMP_PERM 0x1022
#endif
static pthread_mutex_t mu=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t cv=PTHREAD_COND_INITIALIZER;
static int go=0;
static unsigned long before_mask,after_mask;
static const char *name;
static void *worker(void *p) {
 const char *label=(const char*)p; unsigned long before=0,after=0;
 syscall(SYS_arch_prctl,ARCH_GET_XCOMP_PERM,&before);
 pthread_mutex_lock(&mu); while(!go) pthread_cond_wait(&cv,&mu); pthread_mutex_unlock(&mu);
 syscall(SYS_arch_prctl,ARCH_GET_XCOMP_PERM,&after);
 printf("%s before=0x%lx after=0x%lx\n",label,before,after);
 return NULL;
}
int main(void) {
 pthread_t old,newt; unsigned long main_before=0,main_after=0;
 if(pthread_create(&old,NULL,worker,"preexisting_worker")) return 2;
 usleep(10000);
 syscall(SYS_arch_prctl,ARCH_GET_XCOMP_PERM,&main_before);
 long req=syscall(SYS_arch_prctl,ARCH_REQ_XCOMP_PERM,18UL);
 syscall(SYS_arch_prctl,ARCH_GET_XCOMP_PERM,&main_after);
 pthread_mutex_lock(&mu); go=1; pthread_cond_broadcast(&cv); pthread_mutex_unlock(&mu);
 pthread_join(old,NULL);
 pthread_create(&newt,NULL,worker,"post_request_worker"); pthread_join(newt,NULL);
 printf("main before=0x%lx request_ret=%ld after=0x%lx\n",main_before,req,main_after);
 return 0;
}
