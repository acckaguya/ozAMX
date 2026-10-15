/* Experimental AMX-INT8 diagonal microkernel, SysV x86-64 ABI.
 *
 * A panel is 32x64 signed bytes: the two 16x64 row halves start at +0/+1024.
 * B is VNNI4-packed for N=32: the two N=16 halves start at +0/+1024.
 * Four 16x16 INT32 tiles hold the output quadrants; four more hold A/B input
 * fragments. Caller C is a padded INT32 plane with its actual row stride in bytes.
 *
 * Arguments:
 *   rdi = const int8_t *const A_panels[]
 *   rsi = const int8_t *const B_panels[]
 *   rdx = int32_t *C
 *   rcx = C row stride in bytes
 *   r8  = K64 panel step in bytes (8*2048)
 *   r9  = number of K64 steps in this BK block
 *   stack[8] = pair count (1..8)
 */
.text

#ifndef OZAMX_I8_TILELOAD_HINT
#define OZAMX_I8_TILELOAD_HINT 1
#endif
#if OZAMX_I8_TILELOAD_HINT
#define input_load tileloaddt1
#else
#define input_load tileloadd
#endif

.p2align 4
.globl ozamx_i8_load_tile_config
.hidden ozamx_i8_load_tile_config
.type ozamx_i8_load_tile_config,@function
ozamx_i8_load_tile_config:
    ldtilecfg (%rdi)
    ret
.size ozamx_i8_load_tile_config,.-ozamx_i8_load_tile_config

.p2align 4
.globl ozamx_i8_release_tiles
.hidden ozamx_i8_release_tiles
.type ozamx_i8_release_tiles,@function
ozamx_i8_release_tiles:
    tilerelease
    ret
.size ozamx_i8_release_tiles,.-ozamx_i8_release_tiles

.p2align 5
.globl ozamx_i8_diagonal
.hidden ozamx_i8_diagonal
.type ozamx_i8_diagonal,@function
ozamx_i8_diagonal:
    .cfi_startproc
    pushq %rbx
    .cfi_adjust_cfa_offset 8
    .cfi_offset %rbx, -16
    pushq %rbp
    .cfi_adjust_cfa_offset 8
    .cfi_offset %rbp, -24
    pushq %r12
    .cfi_adjust_cfa_offset 8
    .cfi_offset %r12, -32
    pushq %r13
    .cfi_adjust_cfa_offset 8
    .cfi_offset %r13, -40
    pushq %r14
    .cfi_adjust_cfa_offset 8
    .cfi_offset %r14, -48
    pushq %r15
    .cfi_adjust_cfa_offset 8
    .cfi_offset %r15, -56

    movq %rdi, %r12                 /* A panel pointer array */
    movq %rsi, %r13                 /* B panel pointer array */
    movq %rdx, %r14                 /* C tile origin */
    movq %rcx, %r15                 /* actual C row stride */
    movq %r8, %rbp                  /* K64 panel stride */
    movq 56(%rsp), %rbx             /* seventh argument after six pushes */
    movq %r9, %rsi                  /* K64 steps remaining */

    /* Read the previous BK contribution for this same diagonal. */
    movq %r15, %r10
    tileloadd (%r14,%r10,1), %tmm4
    tileloadd 64(%r14,%r10,1), %tmm5
    movq %r10, %rax
    shlq $4, %rax
    addq %r14, %rax
    tileloadd (%rax,%r10,1), %tmm6
    tileloadd 64(%rax,%r10,1), %tmm7

    xorq %r8, %r8                   /* byte offset within each K-panel list */
.Li8_k64:
    xorq %rdi, %rdi                 /* pair index */
.Li8_pair:
    movq (%r12,%rdi,8), %rax
    addq %r8, %rax
    movq (%r13,%rdi,8), %r11
    addq %r8, %r11
    movl $64, %r10d                 /* input tile row stride */
    input_load (%rax,%r10,1), %tmm0
    input_load 1024(%rax,%r10,1), %tmm1
    input_load (%r11,%r10,1), %tmm2
    input_load 1024(%r11,%r10,1), %tmm3
    tdpbssd %tmm2, %tmm0, %tmm4
    tdpbssd %tmm3, %tmm0, %tmm5
    tdpbssd %tmm2, %tmm1, %tmm6
    tdpbssd %tmm3, %tmm1, %tmm7
    incq %rdi
    cmpq %rbx, %rdi
    jb .Li8_pair

    addq %rbp, %r8
    decq %rsi
    jnz .Li8_k64

    movq %r15, %r10
    tilestored %tmm4, (%r14,%r10,1)
    tilestored %tmm5, 64(%r14,%r10,1)
    movq %r10, %rax
    shlq $4, %rax
    addq %r14, %rax
    tilestored %tmm6, (%rax,%r10,1)
    tilestored %tmm7, 64(%rax,%r10,1)

    popq %r15
    .cfi_restore %r15
    .cfi_adjust_cfa_offset -8
    popq %r14
    .cfi_restore %r14
    .cfi_adjust_cfa_offset -8
    popq %r13
    .cfi_restore %r13
    .cfi_adjust_cfa_offset -8
    popq %r12
    .cfi_restore %r12
    .cfi_adjust_cfa_offset -8
    popq %rbp
    .cfi_restore %rbp
    .cfi_adjust_cfa_offset -8
    popq %rbx
    .cfi_restore %rbx
    .cfi_adjust_cfa_offset -8
    ret
    .cfi_endproc
.size ozamx_i8_diagonal,.-ozamx_i8_diagonal

.section .note.GNU-stack,"",@progbits
