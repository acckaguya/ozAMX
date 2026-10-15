.text
.p2align 4
.globl ozamx_reconstruct64_ilp4_abi_probe
.type ozamx_reconstruct64_ilp4_abi_probe,@function
ozamx_reconstruct64_ilp4_abi_probe:
    pushq %rbx
    pushq %rbp
    pushq %r12
    pushq %r13
    pushq %r14
    pushq %r15
    subq $8, %rsp
    movabsq $0x1122334400013579, %rbx
    movabsq $0x223344550002468a, %rbp
    movabsq $0x334455660003579b, %r12
    movabsq $0x44556677000468ac, %r13
    movabsq $0x55667788000579bd, %r14
    movabsq $0x6677889900068ace, %r15
    call ozamx_reconstruct64_ilp4
    xorl %eax, %eax
    movabsq $0x1122334400013579, %rax
    cmpq %rax, %rbx
    jne .Labi_done
    movabsq $0x223344550002468a, %rax
    cmpq %rax, %rbp
    jne .Labi_done
    movabsq $0x334455660003579b, %rax
    cmpq %rax, %r12
    jne .Labi_done
    movabsq $0x44556677000468ac, %rax
    cmpq %rax, %r13
    jne .Labi_done
    movabsq $0x55667788000579bd, %rax
    cmpq %rax, %r14
    jne .Labi_done
    movabsq $0x6677889900068ace, %rax
    cmpq %rax, %r15
    jne .Labi_done
    movl $1, %eax
.Labi_done:
    addq $8, %rsp
    popq %r15
    popq %r14
    popq %r13
    popq %r12
    popq %rbp
    popq %rbx
    ret
.size ozamx_reconstruct64_ilp4_abi_probe, .-ozamx_reconstruct64_ilp4_abi_probe
.section .note.GNU-stack,"",@progbits
