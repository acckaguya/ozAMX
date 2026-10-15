#define _GNU_SOURCE
#include <errno.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/syscall.h>
#include <unistd.h>
#include <asm/prctl.h>
#include <immintrin.h>

#ifndef ARCH_REQ_XCOMP_PERM
#define ARCH_REQ_XCOMP_PERM 0x1023
#endif
#ifndef ARCH_GET_XCOMP_PERM
#define ARCH_GET_XCOMP_PERM 0x1022
#endif
#ifndef XFEATURE_XTILEDATA
#define XFEATURE_XTILEDATA 18
#endif

typedef struct __attribute__((packed, aligned(64))) {
    uint8_t palette_id;
    uint8_t start_row;
    uint8_t reserved[14];
    uint16_t colsb[16];
    uint8_t rows[16];
} tilecfg_t;

static void sigill(int sig) {
    (void)sig;
    static const char msg[] = "AMX_EXEC=FAIL_SIGILL\n";
    ssize_t ignored = write(STDOUT_FILENO, msg, sizeof(msg) - 1);
    (void)ignored;
    _exit(3);
}

int main(void) {
    /* 除了申请权限，还执行一次已知结果的 BF16 tile 点积来确认指令可用。 */
    signal(SIGILL, sigill);
    unsigned long mask = 0;
    if (syscall(SYS_arch_prctl, ARCH_GET_XCOMP_PERM, &mask) == 0)
        printf("xcomp_perm_before=0x%lx\n", mask);
    else
        printf("xcomp_perm_query_errno=%d (%s)\n", errno, strerror(errno));

    if (syscall(SYS_arch_prctl, ARCH_REQ_XCOMP_PERM, XFEATURE_XTILEDATA) != 0) {
        printf("AMX_PERM=FAIL errno=%d (%s)\n", errno, strerror(errno));
        return 2;
    }
    printf("AMX_PERM=OK\n");

    tilecfg_t cfg = {0};
    cfg.palette_id = 1;
    cfg.colsb[0] = 64;
    cfg.rows[0] = 16;
    cfg.colsb[1] = 64;
    cfg.rows[1] = 16;
    cfg.colsb[2] = 64;
    cfg.rows[2] = 16;
    _tile_loadconfig(&cfg);
    _tile_zero(0);
    _tile_zero(1);
    _tile_zero(2);
    uint16_t a[16 * 32], b[32 * 32];
    for (int i = 0; i < 16 * 32; i++)
        a[i] = 0x3f80; /* BF16 1.0 */
    for (int i = 0; i < 32 * 32; i++)
        b[i] = 0x4000; /* BF16 2.0 */
    _tile_loadd(1, a, 64);
    _tile_loadd(2, b, 64);
    _tile_dpbf16ps(0, 1, 2);
    float out[16 * 16] = {0};
    _tile_stored(0, out, 64);
    _tile_release();
    printf("AMX_EXEC=OK sample_c00=%.1f expected=64.0\n", out[0]);
    return out[0] == 64.0f ? 0 : 4;
}
