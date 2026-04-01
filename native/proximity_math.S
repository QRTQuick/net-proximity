.text
.global abs_int_diff
.type abs_int_diff, @function
abs_int_diff:
    movl %edi, %eax
    subl %esi, %eax
    cdq
    xorl %edx, %eax
    subl %edx, %eax
    ret
