.text
.macro loadbench name, instruction
.p2align 5
.globl \name
.type \name,@function
\name:
    .cfi_startproc
    /* rax walks the buffer, r9 is its end, and r8d is the 64-byte row stride.
     * tmm0..3 load four tiles at successive 1 KiB offsets from each position. */
    movl $64, %r8d
    movq %rdi, %rax
    leaq (%rdi,%rsi), %r9
.p2align 4
.Lloop\@:
    \instruction (%rax,%r8,1), %tmm0
    \instruction 1024(%rax,%r8,1), %tmm1
    \instruction 2048(%rax,%r8,1), %tmm2
    \instruction 3072(%rax,%r8,1), %tmm3
    addq $4096, %rax
    cmpq %r9, %rax
    cmove %rdi, %rax
    decl %edx
    jnz .Lloop\@
    ret
    .cfi_endproc
.size \name,.-\name
.endm
loadbench ozroof_tileload, tileloadd
loadbench ozroof_tileload_t1, tileloaddt1
.section .note.GNU-stack,"",@progbits
