#ifndef TESTING_H
#define TESTING_H

//#include <iomacros.h>
void test_puts(char * text);

///address range: 0x01B0-0x1ff

#define TEST_CMD_            0x01b0
#define TEST_TEXTOUT_        0x01b1
//sfrb (TEST_CMD,CMD_);
//sfrb (TEST_TEXTOUT,TEXTOUT_);
volatile unsigned char TEST_CMD asm("0x01b0");
volatile unsigned char TEST_TEXTOUT asm("0x01b1");

//CMD consts
#define TEST_START              0x10
#define TEST_END                0x11
#define SUBTEST_START           0x20
#define SUBTEST_SUCCESS         0x21
#define SUBTEST_FAIL            0x22

#define TEST(desc)              TEST_CMD = TEST_START, test_puts(desc)
#define END_TEST                TEST_CMD = TEST_END
#define SUBTEST(desc)           TEST_CMD = SUBTEST_START, test_puts(desc)
#define FAIL(desc)              TEST_CMD = SUBTEST_FAIL, test_puts(desc)
#define SUCCESS(desc)           TEST_CMD = SUBTEST_SUCCESS, test_puts(desc)
#define OK SUCCESS
#define CHECK(text, expr)       test_puts(text), TEST_CMD = ((expr)?SUBTEST_SUCCESS:SUBTEST_FAIL)
#define WRITE(text)             test_puts(text)

//not so nice to put c in a h...
void test_puts(char * text) {
    while (*text) TEST_TEXTOUT = *text++;
}

#endif //TESTING_H
