#!/usr/bin/env python

#special test peripheral and io for MSP430-GCC (mspgcc) tests
#(C)2002 Chris Liechti <cliechti@gmx.net>

import sys, core

#CMD codes:
IDLE                = 0x00
TEST_START          = 0x10
TEST_END            = 0x11
SUBTEST_START       = 0x20
SUBTEST_SUCCESS     = 0x21
SUBTEST_FAIL        = 0x22

class Testing(core.Peripheral):
    color = (0x66, 0xff, 0xee)      #color for graphical representation

    def __init__(self, log, startaddress = 0x01b0):
        self.startaddress = startaddress
        core.Peripheral.__init__(self, log)  #calls self.reset()
        self.mode = IDLE
        self.testcount = 0
        self.failures = 0
    
    def __contains__(self, address):
        """return true if address is handled by this peripheral"""
        return self.startaddress <= address <= (self.startaddress + 2)

    def reset(self):
        """perform a power up reset"""
        pass

    def set(self, address, value, bytemode=0):
        """read from address"""
        if not bytemode and self.log:
            self.log.write('TESTNG: Access Error - expected byte but got word access\n')
        a = address - self.startaddress
        if a == 0:      #CMD
            if value == TEST_START:
                sys.stdout.write("***************************\n")
            elif value == SUBTEST_START:
                self.testcount += 1
                sys.stdout.write("-----------------\n")
            elif value == SUBTEST_SUCCESS:
                sys.stdout.write("SUCCESS\n")
            elif value == SUBTEST_FAIL:
                sys.stdout.write("FAIL\n")
                self.failures += 1
            self.mode = value
        elif a == 1:    #TEXT OUT
            sys.stdout.write(chr(value))

    def get(self, address, bytemode=0):
        """write value to address"""
        if not bytemode and self.log:
            self.log.write('TESTNG: Access Error - expected byte but got word access\n')
        return 0    #no functionality right now

class TestCore(core.Core):
    def __init__(self, log):
        core.Core.__init__(self, log)
        self.testing = Testing(log)
        self.memory.append(self.testing)    #insert new peripherals in MSP's address pace
        #self.reset()

    def start(self, maxsteps=1000):
        self.log.write( 'TSTCOR: set startaddress\n')
        self.PC.set(self.memory.get(0xfffe))
        self.log.write( 'TSTCOR: *** starting trace (maxsteps=%d)\n' % (maxsteps))
        step = 1
        forever = 0
        while forever or step <= maxsteps:
            self.step()
            self.log.write( 'TSTCOR: (step %d, cycle %d)\n%r\n' % (
                step, self.cycles, self))
            step += 1
            if self.testing.mode == TEST_END:
                break
            elif self.testing.mode == TEST_START:
                forever = 1
        if self.testing.mode != TEST_END:
            print "This is not a file for the tester!"

if __name__ == '__main__':
    log = open("testing.log","w")
    failures = 0
    for f in sys.argv[1:]:
        print "Running Test: %s ...\n" % f
        log.write("Running Test: %s ...\n" % f)
        msp = TestCore(log)
        msp.memory.load(f)
        msp.start()
        failures += msp.testing.failures
    if failures:
        print "%d failures" % failures
        sys.exit(1)
