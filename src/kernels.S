/* AMX-BF16 microkernels. SysV ABI; tmm0..7 belong to this tile region.
 * A/B contiguous tile row stride 64 bytes, output stride 128.
 * tmm0..1 hold A halves, tmm2..3 hold B halves, and tmm4..7 are four C quadrants.
 * The six-product chain preserves the original per-K32 accumulation order. */
.text
#ifndef OZAMX_TILELOAD_HINT
#define OZAMX_TILELOAD_HINT 1
#endif
#if OZAMX_TILELOAD_HINT
#define input_load tileloaddt1
#else
#define input_load tileloadd
#endif
.macro quadrant_products
    tdpbf16ps %tmm2, %tmm0, %tmm4
    tdpbf16ps %tmm3, %tmm0, %tmm5
    tdpbf16ps %tmm2, %tmm1, %tmm6
    tdpbf16ps %tmm3, %tmm1, %tmm7
.endm
.macro store_result
    movl $128, %r10d
    tilestored %tmm4, (%rdx,%r10,1)
    tilestored %tmm5, 64(%rdx,%r10,1)
    tilestored %tmm6, 2048(%rdx,%r10,1)
    tilestored %tmm7, 2112(%rdx,%r10,1)
.endm
.p2align 5
.globl ozamx_bf16_six
.hidden ozamx_bf16_six
.type ozamx_bf16_six,@function
ozamx_bf16_six:
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
    movq 0(%rdi), %r12
    movq 8(%rdi), %r13
    movq 16(%rdi), %r14
    movq 0(%rsi), %r15
    movq 8(%rsi), %rbx
    movq 16(%rsi), %rbp
    /* r12-r14: A0-A2; r15/rbx/rbp: B0-B2; r8/r9: 64-byte row strides. */
    movl $64, %r8d
    movl $64, %r9d
    tilezero %tmm4
    tilezero %tmm5
    tilezero %tmm6
    tilezero %tmm7
.p2align 4
.Lsix_k:
    /* A1 B1 */
    input_load (%r13,%r8,1), %tmm0
    input_load 1024(%r13,%r8,1), %tmm1
    input_load (%rbx,%r9,1), %tmm2
    input_load 1024(%rbx,%r9,1), %tmm3
    quadrant_products
    /* A1 B0 */
    input_load (%r15,%r9,1), %tmm2
    input_load 1024(%r15,%r9,1), %tmm3
    quadrant_products
    /* A2 B0 */
    input_load (%r14,%r8,1), %tmm0
    input_load 1024(%r14,%r8,1), %tmm1
    quadrant_products
    /* A0 B0 */
    input_load (%r12,%r8,1), %tmm0
    input_load 1024(%r12,%r8,1), %tmm1
    quadrant_products
    /* A0 B1 */
    input_load (%rbx,%r9,1), %tmm2
    input_load 1024(%rbx,%r9,1), %tmm3
    quadrant_products
    /* A0 B2 */
    input_load (%rbp,%r9,1), %tmm2
    input_load 1024(%rbp,%r9,1), %tmm3
    quadrant_products
    addq $2048, %r12
    addq $2048, %r13
    addq $2048, %r14
    addq $2048, %r15
    addq $2048, %rbx
    addq $2048, %rbp
    decl %ecx
    jnz .Lsix_k
    store_result
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
.size ozamx_bf16_six,.-ozamx_bf16_six
.p2align 5
.globl ozamx_bf16_product
.hidden ozamx_bf16_product
.type ozamx_bf16_product,@function
ozamx_bf16_product:
    .cfi_startproc
    movl $64, %r8d
    movl $64, %r9d
    tilezero %tmm4
    tilezero %tmm5
    tilezero %tmm6
    tilezero %tmm7
    /* rdi/rsi point to the selected A/B projection pair. */
.p2align 4
.Lproduct_k:
#if OZAMX_LOAD_SCHEDULE
    input_load (%rdi,%r8,1), %tmm0
    input_load 1024(%rdi,%r8,1), %tmm1
    input_load (%rsi,%r9,1), %tmm2
    input_load 1024(%rsi,%r9,1), %tmm3
    quadrant_products
#else
    input_load (%rdi,%r8,1), %tmm0
    input_load (%rsi,%r9,1), %tmm2
    tdpbf16ps %tmm2, %tmm0, %tmm4
    input_load 1024(%rsi,%r9,1), %tmm3
    tdpbf16ps %tmm3, %tmm0, %tmm5
    input_load 1024(%rdi,%r8,1), %tmm1
    tdpbf16ps %tmm2, %tmm1, %tmm6
    tdpbf16ps %tmm3, %tmm1, %tmm7
#endif
    addq $2048, %rdi
    addq $2048, %rsi
    decl %ecx
    jnz .Lproduct_k
    store_result
    ret
    .cfi_endproc
.size ozamx_bf16_product,.-ozamx_bf16_product
.section .note.GNU-stack,"",@progbits
