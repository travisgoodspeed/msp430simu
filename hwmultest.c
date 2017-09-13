/**
Testing the HW multiplier in the simu.

(C) 2002 cliechti@gmx.net
*/

#include <msp430.h>
#include "testing.h"

long long umul32(long b, long a);


void mpy_test(void) {
    SUBTEST("unsigned multiply 16x16\n");       //Begin with a new test
    MPY = 7;
    OP2 = 9;
    CHECK("7*9:\t\t", RESLO == 63 );

    MPY = 0xffff;
    OP2 = 0x1000;
    CHECK("0xffff*0x1000:\t", (RESLO == 0xf000) && (RESHI == 0x0fff) );
}

void mpys_test(void) {
    SUBTEST("signed multiply 16x16\n");       //Begin with a new test
    MPYS = 7;
    OP2 = 9;
    CHECK("7*9:\t\t", RESLO == 63 );
    MPYS = -7;
    OP2 = 9;
    CHECK("-7*9:\t\t", RESLO == -63 );
    MPYS = 7;
    OP2 = -9;
    CHECK("7*-9:\t\t", RESLO == -63 );
    MPYS = -7;
    OP2 = -9;
    CHECK("-7*-9:\t\t", RESLO == 63 );
}

void mac_test(void) {
    SUBTEST("unsigned multiply 16x16 and add\n");       //Begin with a new test
    RESLO = RESHI = 0;
    MAC = 1;
    OP2 = 2;
    CHECK("1*2:\t\t", RESLO == 2 );
    MAC = 3;
    OP2 = 4;
    CHECK("+ 3*4:\t\t", RESLO == 14 );
    MAC = 5;
    OP2 = 6;
    CHECK("+ 5*6:\t\t", RESLO == 44 );
}

void macs_test(void) {
    SUBTEST("signed multiply 16x16 and add\n");       //Begin with a new test
    RESLO = RESHI = 0;
    MACS = 7;
    OP2 = 9;
    CHECK("7*9:\t\t", RESLO == 63 );
    MACS = -7;
    OP2 = 9;
    CHECK("-7*9:\t\t", RESLO == 0 );
    MACS = 7;
    OP2 = -9;
    CHECK("7*-9:\t\t", RESLO == -63 );
    MACS = -7;
    OP2 = -9;
    CHECK("-7*-9:\t\t", RESLO == 0 );
}

void umul32_test(void) {
    long long r;
    long a;
    long b;
    SUBTEST("unsigned multiply 32x32\n");       //Begin with a new test
    CHECK("7*9:\t\t", umul32(7,9) == 63L );
    CHECK("70*90:\t\t", umul32(70,90) == 6300L );
    CHECK("7000*9000:\t\t", umul32(7000,9000) == 63000000L );
    CHECK("0x10000000*0x10000000:\t", umul32(0x10000000L,0x10000000L) == 0x100000000000000L );
}


int main() {
    TEST("Example tests for mspgcc\n");    //all test files MUST start with that one

    //mpy_test();
    //mpys_test();
    //mac_test();
    //macs_test();
    
    umul32_test();
    
    END_TEST;                 //finish tests. this is important for the simu that it know when it can abort
}

