#include "ozamx/gemm.hpp"

#include <cerrno>
#include <cstring>
#include <cpuid.h>
#include <sys/syscall.h>
#include <unistd.h>
#include <asm/prctl.h>

#ifndef ARCH_REQ_XCOMP_PERM
#define ARCH_REQ_XCOMP_PERM 0x1023
#endif
#ifndef ARCH_GET_XCOMP_PERM
#define ARCH_GET_XCOMP_PERM 0x1022
#endif
#ifndef XFEATURE_XTILEDATA
#define XFEATURE_XTILEDATA 18
#endif

namespace ozamx {

AmxStatus request_amx_permission_for_current_thread() {
    AmxStatus s;
    unsigned int eax = 0, ebx = 0, ecx = 0, edx = 0;
    if (__get_cpuid_max(0, nullptr) >= 7 && __get_cpuid_count(7, 0, &eax, &ebx, &ecx, &edx)) {
        s.cpu_amx_tile = (edx & (1u << 24)) != 0;
        s.cpu_amx_bf16 = (edx & (1u << 22)) != 0;
    }
    if (!s.cpu_amx_tile || !s.cpu_amx_bf16) {
        s.message = "CPU does not report both AMX-TILE and AMX-BF16";
        return s;
    }
    unsigned long mask = 0;
    if (syscall(SYS_arch_prctl, ARCH_GET_XCOMP_PERM, &mask) == 0 && (mask & (1ul << XFEATURE_XTILEDATA))) {
        s.permission_available = true;
        s.message = "XTILEDATA permission already available for this thread";
        return s;
    }
    s.permission_requested = true;
    if (syscall(SYS_arch_prctl, ARCH_REQ_XCOMP_PERM, XFEATURE_XTILEDATA) == 0) {
        s.permission_available = true;
        s.message = "XTILEDATA permission granted for this thread";
    } else {
        s.message = std::string("ARCH_REQ_XCOMP_PERM failed: ") + std::strerror(errno);
    }
    return s;
}

} // namespace ozamx
