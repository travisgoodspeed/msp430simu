#!/usr/bin/env python

#special test peripheral and io for MSP430-GCC (mspgcc) tests
#(C)2002 Chris Liechti <cliechti@gmx.net>

#you can call this script with many filenames. for each file a new
#msp430 is created and the file is executed.
#all failures are summed up and a total is printed at the end
#(the exit code is nonzero if there is any failure)

#a test program must write to the "sfrb CMD" within 2000 program steps
#otherwise its aborted and a message is printed for that file.close
#the tests must then end in an other write to CMD, otherwise the simu
#would run forever.

#please look at the example_tests.c and testing.h for more details on
#how to write tests

import sys, core, logging

#CMD codes:
IDLE                    = 0x00
TEST_START              = 0x10
TEST_END                = 0x11
SUBTEST_START           = 0x20
SUBTEST_SUCCESS         = 0x21
SUBTEST_FAIL            = 0x22
SUBTEST_EXECUTE         = 0x2e
SUBTEST_EXECUTE_DONE    = 0x2f

class Testing(core.Peripheral):
    color = (0x66, 0xff, 0xee)      #color for graphical representation

    def __init__(self, log, startaddress = 0x01b0):
        self.startaddress = startaddress
        core.Peripheral.__init__(self)  #calls self.reset()
        self.log = logging.getLogger('test io')
        self.mode = IDLE
        self.testcount = 0
        self.failures = 0
        self.text_buffer = []
    
    def __contains__(self, address):
        """return true if address is handled by this peripheral"""
        return self.startaddress <= address <= (self.startaddress + 2)

    def reset(self):
        """perform a power up reset"""
        pass

    def set(self, address, value, bytemode=0):
        """read from address"""
        if not bytemode and self.log:
            self.log.error('TESTNG: Access Error - expected byte but got word access')
        a = address - self.startaddress
        if a == 0:      #CMD
            if value == TEST_START:
                self.log.info("Test start")
            elif value == TEST_END:
                self.log.info("Test finished")
            elif value == SUBTEST_START:
                self.testcount += 1
                self.log.info("Test: %r" % ''.join(self.text_buffer))
                del self.text_buffer[:]
            elif value == SUBTEST_SUCCESS:
                self.log.info("SUCCESS: %r" % ''.join(self.text_buffer))
                del self.text_buffer[:]
            elif value == SUBTEST_FAIL:
                self.log.error("FAIL: %r" % ''.join(self.text_buffer))
                del self.text_buffer[:]
                self.failures += 1
            elif value == SUBTEST_EXECUTE:
                del self.text_buffer[:]
            elif value == SUBTEST_EXECUTE_DONE:
                if self.text_buffer:
                    self.log.info(''.join(self.text_buffer))
                    del self.text_buffer[:]
            else:
                self.log.error('unknown value 0x%02x written to test port' % value)
            self.mode = value
        elif a == 1:    #TEXT OUT
            self.text_buffer.append(chr(value))

    def get(self, address, bytemode=0):
        """write value to address"""
        if not bytemode and self.log:
            self.log.error('TESTNG: Access Error - expected byte but got word access')
        return 0    #no functionality right now

class TestCore(core.Core):
    def __init__(self):
        core.Core.__init__(self)
        self.testing = Testing(log)
        self.memory.append(self.testing)    #insert new peripherals in MSP's address pace
        self.memory.append(core.Multiplier())
        #self.reset()

    def start(self, maxsteps=2000):
        self.log.debug( 'TSTCOR: set startaddress')
        self.PC.set(self.memory.get(0xfffe))
        self.log.debug( 'TSTCOR: *** starting trace (maxsteps=%d)' % (maxsteps))
        step = 1
        forever = 0
        while forever or step <= maxsteps:
            self.step()
            self.log.debug( 'TSTCOR: (step %d, cycle %d)\n%r' % (
                step, self.cycles, self))
            step += 1
            if self.testing.mode == TEST_END:
                break
            elif self.testing.mode == TEST_START:
                forever = 1
        if self.testing.mode != TEST_END:
            print "This is not a file for the tester!"

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s',
                        filename='testing.log',
                        filemode='w')
    log = logging.getLogger('testing')
    
    failures = 0
    for f in sys.argv[1:]:
        print "Running Test: %s ...\n" % f
        log.info("Running Test: %s ..." % f)
        msp = TestCore()
        msp.memory.load(f)
        msp.start()
        failures += msp.testing.failures
        print "---------- Total Cycles: %d -----------" % msp.cycles
    if failures:
        print "%d failures" % failures
        sys.exit(1)
