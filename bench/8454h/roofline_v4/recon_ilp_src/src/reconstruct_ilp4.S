/* SysV: rdi=C32x32, rsi=ordered float-plane pointer array, rdx=count,
 * rcx=C row stride in bytes. C rows are 64-byte aligned. Float planes each
 * contain 32x32 contiguous floats. This preserves the addition sequence for
 * every output while interleaving eight independent double accumulator chains.
 * The caller selects this only with final nonfinite checking (Late64).
 */
.text
.p2align 6
.globl ozamx_reconstruct64_ilp4
.type ozamx_reconstruct64_ilp4,@function
ozamx_reconstruct64_ilp4:
    testq %rdx, %rdx
    jz .Lri4_return
    movq %rdi, %r8
    xorl %r9d, %r9d
    movl $16, %r10d
.p2align 5
.Lri4_rows:
    leaq (%r8,%rcx), %r11
    vmovapd   0(%r8), %zmm0
    vmovapd  64(%r8), %zmm1
    vmovapd 128(%r8), %zmm2
    vmovapd 192(%r8), %zmm3
    vmovapd   0(%r11), %zmm4
    vmovapd  64(%r11), %zmm5
    vmovapd 128(%r11), %zmm6
    vmovapd 192(%r11), %zmm7
    xorl %edi, %edi
.p2align 5
.Lri4_products:
    movq (%rsi,%rdi,8), %rax
    addq %r9, %rax
    vcvtps2pd   0(%rax), %zmm8
    vcvtps2pd  32(%rax), %zmm9
    vcvtps2pd  64(%rax), %zmm10
    vcvtps2pd  96(%rax), %zmm11
    vcvtps2pd 128(%rax), %zmm12
    vcvtps2pd 160(%rax), %zmm13
    vcvtps2pd 192(%rax), %zmm14
    vcvtps2pd 224(%rax), %zmm15
    vaddpd %zmm8,  %zmm0, %zmm0
    vaddpd %zmm9,  %zmm1, %zmm1
    vaddpd %zmm10, %zmm2, %zmm2
    vaddpd %zmm11, %zmm3, %zmm3
    vaddpd %zmm12, %zmm4, %zmm4
    vaddpd %zmm13, %zmm5, %zmm5
    vaddpd %zmm14, %zmm6, %zmm6
    vaddpd %zmm15, %zmm7, %zmm7
    incq %rdi
    cmpq %rdx, %rdi
    jb .Lri4_products
    vmovapd %zmm0,   0(%r8)
    vmovapd %zmm1,  64(%r8)
    vmovapd %zmm2, 128(%r8)
    vmovapd %zmm3, 192(%r8)
    vmovapd %zmm4,   0(%r11)
    vmovapd %zmm5,  64(%r11)
    vmovapd %zmm6, 128(%r11)
    vmovapd %zmm7, 192(%r11)
    leaq (%r8,%rcx,2), %r8
    addq $256, %r9
    decl %r10d
    jnz .Lri4_rows
.Lri4_return:
    vzeroupper
    ret
.size ozamx_reconstruct64_ilp4, .-ozamx_reconstruct64_ilp4
.section .note.GNU-stack,"",@progbits
