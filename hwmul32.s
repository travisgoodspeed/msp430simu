;#include <io.h>
#include <msp430x14x.h>

#define AH r13
#define AL r12
#define BH r11
#define BL r10

#define RHH r15
#define RHL r14
#define RLH r13
#define RLL r12

.text

;------- umul32
; unsigned 32x32 multiplication with hw mutiplier
; r = ((ah*bh) << 32) + ((ah*bl + al*bh) << 16) + al*bl

.global	__umul32
	.type	__umul32,@function

__umul32:
        mov AH, &MPY
        mov BH, &OP2
        mov &RESHI, RHH
        mov &RESLO, RHL
        
        mov AH, &MPY
        mov BL, &OP2
        mov AL, &MAC
        mov BH, &OP2
        add &RESHI, RHL
        adc RHH
        mov &RESLO, RLH

        mov AL, &MPY
        mov BL, &OP2
        add &RESHI, RLH
        adc RHL
        adc RHH
        mov &RESLO, RLL
        ret

;------- umul32 wrapper for C
.global	umul32
	.type	umul32,@function

umul32:
        push BH
        push BL
        
        mov R14, BL
        mov R15, BH
        call #__umul32
        
        pop BL
        pop BH
        ret
