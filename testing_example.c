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
long lx, ly;

int main() {
    static char st = 0;
    TEST("Example tests for mspgcc\n");    //all test files MUST start with that one
    
    SUBTEST("Subtest 1\n");       //Begin with a new test
    //set up test inputs
    a = '0';
    b = 'A';
    //perform the calculation to be tested
    r = (a << 8) | b;
    CHECK(r == 0x3041);


    SUBTEST("boolean not\n");       //Begin with a new test
    //set up test inputs
    //perform the calculation to be tested
    st = 0;
    st = !st;
    st = !st;
    CHECK( st == 0 );

    SUBTEST("int division\n");       //Begin with a new test
    //set up test inputs
    //perform the calculation to be tested
    WRITE("neg/pos:");
    ix = -10;
    iy = 2;
    CHECK( (ix/iy) == -5 );
    WRITE("pos/pos:");
    ix = 10;
    iy = 2;
    CHECK( (ix/iy) == 5 );
    
    SUBTEST("long division\n");       //Begin with a new test
    //set up test inputs
    //perform the calculation to be tested
    WRITE("neg/pos:");
    lx = -10;
    ly = 2;
    CHECK( (lx/ly) == -5 );
    WRITE("pos/pos:");
    lx = 10;
    ly = 2;
    CHECK( (lx/ly) == 5 );

END_TEST;                 //finish tests. this is important for the simu that it know when it can abort
}

