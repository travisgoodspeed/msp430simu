/**
This source shows an example on how to use the testing peripheral in the
simulator.

(C) 2002 cliechti@gmx.net
*/

#include <io.h>
#include "testing.h"

char a,b;
int r;
int ix, iy;
unsigned int uix, uiy;
long lx, ly;
unsigned long ulx, uly;

int main() {
    static char st = 0;
    TEST("Example tests for mspgcc\n");    //all test files MUST start with that one
    
    SUBTEST("Subtest 1\n");       //Begin with a new test
    //set up test inputs
    a = '0';
    b = 'A';
    //perform the calculation to be tested
    r = (a << 8) | b;
    CHECK("leftshift:", r == 0x3041);


    SUBTEST("boolean not\n");       //Begin with a new test
    //set up test inputs
    //perform the calculation to be tested
    st = 0;
    st = !st;
    st = !st;
    r = 1;
    CHECK("st == !!st:\t", st == !!st );
    CHECK("st == 0:\t", st == 0 );
    CHECK("r  == 1:\t", r == 1 );
    CHECK("r is true?:\t", r);
    CHECK("!r == 0:\t", !r == 0);

    SUBTEST("int division\n");       //Begin with a new test
    ix = 10;  iy = -2;  CHECK("pos/neg:\t", (ix/iy) == -5 );
    ix = -10; iy = 2;   CHECK("neg/pos:\t", (ix/iy) == -5 );
    ix = 10;  iy = 2;   CHECK("pos/pos:\t", (ix/iy) == 5 );
    ix = -10; iy = -2;  CHECK("neg/neg:\t", (ix/iy) == 5 );
    
    SUBTEST("signed long division\n");       //Begin with a new test
    lx = 10L; ly = -2L; CHECK("pos/neg:\t", (lx/ly) == -5 );
    lx = -10L;ly = 2L;  CHECK("neg/pos:\t", (lx/ly) == -5 );
    lx = 10L; ly = 2L;  CHECK("pos/pos:\t", (lx/ly) == 5 );
    lx = -10L;ly = -2L; CHECK("neg/neg:\t", (lx/ly) == 5 );

    SUBTEST("unsigned long division\n");       //Begin with a new test
    ulx = 10L;uly = 2L; CHECK("10/2:\t\t", (ulx/uly) == 5 );
    ulx = 11L;uly = 2L; CHECK("11/2:\t\t", (ulx/uly) == 5 );
    ulx = 1234L;uly = 1234L;CHECK("1234/1234:\t", (ulx/uly) == 1 );
    ulx = 12345L;uly = 12345L;CHECK("12345/12345:\t", (ulx/uly) == 1 );
    ulx = 0L;uly = 99L; CHECK("0/99:\t\t", (ulx/uly) == 0 );
    ulx = 27L;uly = 4L; CHECK("27/4:\t\t", (ulx/uly) == 6 );

    SUBTEST("unsigned long shift left\n");       //Begin with a new test
    ulx = 1L;
    CHECK("1<<0:\t\t", (ulx<<0) == 1L );
    CHECK("1<<1:\t\t", (ulx<<1) == 2L );
    CHECK("1<<2:\t\t", (ulx<<2) == 4L );
    CHECK("1<<3:\t\t", (ulx<<3) == 8L );
    CHECK("1<<5:\t\t", (ulx<<5) == 32L );
    CHECK("1<<8:\t\t", (ulx<<8) == 256L );
    CHECK("1<<11:\t\t", (ulx<<11) == 2048L );
    CHECK("1<<12:\t\t", (ulx<<12) == 4096L );
    CHECK("1<<15:\t\t", (ulx<<15) == 32768L );
    CHECK("1<<16:\t\t", (ulx<<16) == 65536L );
    CHECK("1<<20:\t\t", (ulx<<20) == 1048576L );
    CHECK("1<<31:\t\t", (ulx<<31) == 2147483648L );
    CHECK("1<<32:\t\t", (ulx<<32) == 0 );

    SUBTEST("signed long shift left\n");       //Begin with a new test
    lx = 1L;
    CHECK("1<<0:\t\t", (lx<<0) == 1L );
    CHECK("1<<1:\t\t", (lx<<1) == 2L );
    CHECK("1<<2:\t\t", (lx<<2) == 4L );
    CHECK("1<<3:\t\t", (lx<<3) == 8L );
    CHECK("1<<5:\t\t", (lx<<5) == 32L );
    CHECK("1<<8:\t\t", (lx<<8) == 256L );
    CHECK("1<<11:\t\t", (lx<<11) == 2048L );
    CHECK("1<<12:\t\t", (lx<<12) == 4096L );
    CHECK("1<<15:\t\t", (lx<<15) == 32768L );
    CHECK("1<<16:\t\t", (lx<<16) == 65536L );
    CHECK("1<<20:\t\t", (lx<<20) == 1048576L );
    CHECK("1<<31:\t\t", (lx<<31) == 2147483648L );
    CHECK("1<<32:\t\t", (lx<<32) == 0 );

    SUBTEST("unsigned int shift left\n");       //Begin with a new test
    uix = 1;
    CHECK("1<<0:\t\t", (uix<<0) == 1 );
    CHECK("1<<1:\t\t", (uix<<1) == 2 );
    CHECK("1<<2:\t\t", (uix<<2) == 4 );
    CHECK("1<<3:\t\t", (uix<<3) == 8 );
    CHECK("1<<5:\t\t", (uix<<5) == 32 );
    CHECK("1<<8:\t\t", (uix<<8) == 256 );
    CHECK("1<<11:\t\t", (uix<<11) == 2048 );
    CHECK("1<<12:\t\t", (uix<<12) == 4096 );
    CHECK("1<<15:\t\t", (uix<<15) == 32768 );
    CHECK("1<<16:\t\t", (uix<<16) == 0 );

    SUBTEST("signed int shift left\n");       //Begin with a new test
    ix = 1;
    CHECK("1<<0:\t\t", (ix<<0) == 1 );
    CHECK("1<<1:\t\t", (ix<<1) == 2 );
    CHECK("1<<2:\t\t", (ix<<2) == 4 );
    CHECK("1<<3:\t\t", (ix<<3) == 8 );
    CHECK("1<<5:\t\t", (ix<<5) == 32 );
    CHECK("1<<8:\t\t", (ix<<8) == 256 );
    CHECK("1<<11:\t\t", (ix<<11) == 2048 );
    CHECK("1<<12:\t\t", (ix<<12) == 4096 );
    CHECK("1<<15:\t\t", (ix<<15) == 1<<15 );    //32768
    CHECK("1<<16:\t\t", (ix<<16) == 0 );

    SUBTEST("unsigned int shift right\n");       //Begin with a new test
    uix = 0x8000;
    CHECK("0x8000>>0:\t\t", (uix>>0) == 0x8000 );
    CHECK("0x8000>>1:\t\t", (uix>>1) == 0x4000 );
    CHECK("0x8000>>2:\t\t", (uix>>2) == 0x2000 );
    CHECK("0x8000>>3:\t\t", (uix>>3) == 0x1000 );
    CHECK("0x8000>>5:\t\t", (uix>>5) ==  0x0400);
    CHECK("0x8000>>8:\t\t", (uix>>8) ==  0x0080);
    CHECK("0x8000>>11:\t\t", (uix>>11) == 0x0010 );
    CHECK("0x8000>>12:\t\t", (uix>>12) == 0x0008 );
    CHECK("0x8000>>15:\t\t", (uix>>15) == 0x0001 );
    CHECK("0x8000>>16:\t\t", (uix>>16) == 0 );

    SUBTEST("signed int shift right\n");       //Begin with a new test
    ix = 0x8000;
    CHECK("0x8000>>0:\t\t", (ix>>0) == 0x8000 );
    CHECK("0x8000>>1:\t\t", (ix>>1) == 0x4000 );
    CHECK("0x8000>>2:\t\t", (ix>>2) == 0x2000 );
    CHECK("0x8000>>3:\t\t", (ix>>3) == 0x1000 );
    CHECK("0x8000>>5:\t\t", (ix>>5) ==  0x0400);
    CHECK("0x8000>>8:\t\t", (ix>>8) ==  0x0080);
    CHECK("0x8000>>11:\t\t", (ix>>11) == 0x0010 );
    CHECK("0x8000>>12:\t\t", (ix>>12) == 0x0008 );
    CHECK("0x8000>>15:\t\t", (ix>>15) == 0x0001 );
    CHECK("0x8000>>16:\t\t", (ix>>16) == 0 );


    END_TEST;                 //finish tests. this is important for the simu that it know when it can abort
}

