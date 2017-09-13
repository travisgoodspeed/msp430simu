#ifndef TESTING_H
#define TESTING_H

//#include <iomacros.h>
static void test_puts(char * text);

//peripheral address    (max range: 0x01B0-0x1ff)

#define TEST_CMD_            0x01b0     //Send commands the the testing unit in the simu
#define TEST_TEXTOUT_        0x01b1     //just write the character to stdout
//sfrb (TEST_CMD,CMD_);
//sfrb (TEST_TEXTOUT,TEXTOUT_);
volatile unsigned char TEST_CMD asm("0x01b0");
volatile unsigned char TEST_TEXTOUT asm("0x01b1");

//CMD consts
#define TEST_START              0x10    //Begin with a Test, this must be done withing the first 2000 instructions
#define TEST_END                0x11    //Finish and stop simulation
#define SUBTEST_START           0x20    //A new subtest begins
#define SUBTEST_SUCCESS         0x21    //The subtest was successful
#define SUBTEST_FAIL            0x22    //The subtest has failed
#define SUBTEST_EXECUTE         0x2e    //subtest is running
#define SUBTEST_EXECUTE_DONE    0x2f    //subtest is finished

//use the following macros in your test programms

//start you main() with 'TEST("decription\n");'
#define TEST(desc)              TEST_CMD = TEST_START, test_puts(desc)

//just write some text
#define WRITE(text)             test_puts(text)

//"END_TEST;" must be the last line (before "}") in main()
#define END_TEST                TEST_CMD = TEST_END

//not realy useful ones, look below
#define SUBTEST(desc)           test_puts(desc), TEST_CMD = SUBTEST_START, TEST_CMD = SUBTEST_EXECUTE
#define FAIL(desc)              TEST_CMD = SUBTEST_EXECUTE_DONE, test_puts(desc), TEST_CMD = SUBTEST_FAIL
#define SUCCESS(desc)           TEST_CMD = SUBTEST_EXECUTE_DONE, test_puts(desc), TEST_CMD = SUBTEST_SUCCESS
#define OK SUCCESS

//use this for the subtests: e.g. 'CHECK("is a==b?", a==b)'
#define CHECK(text, expr)       test_puts(text), TEST_CMD = ((expr)?SUBTEST_SUCCESS:SUBTEST_FAIL)

//not so nice to put C code in a h...
//but it saves linking separate sources for mostly simple tests files.
static void test_puts(char * text) {
    while (*text) TEST_TEXTOUT = *text++;
}

#endif //TESTING_H
