#!/usr/bin/env python
#
# GDB server for the MSP430 simulator. This meas that msp430-gdb can
# connect to the simulator and manipulate the simulated core.
# An unllimited number of breakpoints is supported.
#
# (C) 2002-2004 Chris Liechti <cliechti@gmx.net>
# this is distributed under a free software license, see license.txt
#
# $Id: gdbserver.py,v 1.2 2005/12/31 00:25:06 cliechti Exp $

import sys, socket, threading, binascii
import Queue
import core
import logging
import time

def checksum(data):
    checksum = 0
    for c in data:
        checksum = (checksum + ord(c)) & 0xff
    return checksum


class BreakpointRunner(threading.Thread):
    def __init__(self, core):
        self.log = logging.getLogger("runner")
        self.core = core
        self.interrupted = False
        self.breakpoints = {}
        self.cmd_queue = Queue.Queue(1)
        threading.Thread.__init__(self)
        self.setName('msp430 core')
        self.setDaemon(1)
        
    def set_breakpoint(self, address):
        self.breakpoints[address] = True

    def remove_breakpoint(self, address):
        if address in self.breakpoints:
            del self.breakpoints[address]
            
    def command(self, cmd, action):
        self.log.info('queing remote command %r' % cmd)
        self.cmd_queue.put((cmd, action))
    
    def interrupt(self):
        self.interrupted = True

    def run(self):
        """worker thread"""
        self.log.debug('worker thread started')
        while True:
            try:
                command, action = self.cmd_queue.get()
                self.log.info('executing remote command %r' % command)
                if command == 'run':
                    self.interrupted = False
                    last_time = time.time()
                    step_delta = 0
                    self.log.info('continuing from 0x%04x (cycle %d)' % (self.core.PC.get(), self.core.cycles))
                    while not self.interrupted:
                        self.core.step()
                        if self.core.PC.get() in self.breakpoints:
                            self.log.info('breakpoint @0x%04x (cycle %d)' % (self.core.PC.get(), self.core.cycles))
                            action()
                            break
                        step_delta += 1
                        if step_delta > 1000:          #after a few steps..
                            #time check is not done at every step for better performance
                            step_delta = 0
                            if time.time() - last_time > 3:     #check time, more than 1s passed?
                                #yes, make a log message so that the user knows we're alive
                                last_time = time.time()
                                self.log.info('still running @0x%04x (cycle %d)' % (self.core.PC.get(), self.core.cycles))
                    else:
                        self.log.info('interrupted @0x%04x (cycle %d)' % (self.core.PC.get(), self.core.cycles))
                        action()
                elif command == 'step':
                    self.log.info('single step @0x%04x (cycle %d)' % (self.core.PC.get(), self.core.cycles))
                    self.core.step()
                    if self.core.PC.get() in self.breakpoints:
                        self.log.info('breakpoint @0x%04x (cycle %d)' % (self.core.PC.get(), self.core.cycles))
                    action()
                else:
                    self.log.error('unknown command %r' % (command, ))
            except:
                self.log.exception('error in runner')

class GDBServer(threading.Thread):
    def __init__(self, core, port = 3333):
        self.core = core
        self.port = port
        threading.Thread.__init__(self)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind( ('localhost', port) )

    def run(self):
        print "gdbserver listening on port %d" % self.port
        self.sock.listen(1)
        while 1:
            conn, addr = self.sock.accept()
            print 'connected by', addr
            GDBClientHandler(self.core, conn).start()


class GDBClientHandler(threading.Thread):
    def __init__(self, core, clientsocket):
        threading.Thread.__init__(self)
        self.setName('gdb remote connection %r' % clientsocket)
        self.clientsocket = clientsocket
        self.netin = clientsocket.makefile("r")
        self.netout = clientsocket.makefile("w")
        self.setDaemon(1)
        self.core = core
        self.log = logging.getLogger("gdbclient")
        self.alive = True
        self.runner = BreakpointRunner(core)
        self.runner.start()

    def close(self):
        self.alive = False
        self.log.info("closing...")
        self.netin.close()
        self.netout.close()
        self.clientsocket.close()
        self.log.info("closed")

    #~ def _answer_ok(self):
    def _answer_sigtrap(self):
        self.writePacket("S%02x" % (5,))    #SIGTRAP
        
    def run(self):
        try:
            self.log.info("client loop ready...")
            while self.alive:
                try:
                    pkt = self.readPacket()
                    self.log.debug('processing remote command %r' % pkt)
                except ValueError:
                    self.netout.write("-")
                    self.netout.flush()
                else:
                    self.netout.write("+")
                    self.netout.flush()
                    if pkt[0] == "?":
                        sig = 0
                        #self.writePacket("T%02x%02x:%04x" % (sig, 0, 0x1234))
                        self.writePacket("S%02x" % (sig,))
                    elif pkt[0] == "c":     #continue
                        if len(pkt) > 1:
                            adr = int(pkt[1:],16)
                            self.core.PC.set(adr)
                        self.runner.command('run', self._answer_sigtrap)
                        #~ self.writePacket("S%02x" % (5,))    #SIGTRAP
                    elif pkt[0] == "D":     #detach
                        self.core.reset()
                    elif pkt[0] == "g":     #Read general registers
                        self.log.debug("Reading device registers")
                        self.writePacket(''.join(["%02x%02x" % (r.get()&0xff, (r.get()>>8)&0xff) for r in self.core.R]))
                    elif pkt[0] == "G":     #write regs
                        self.log.debug("Writing device registers")
                        for n, value in enumerate([int(pkt[i:i+2],16) + int(pkt[i+2:i+4],16)<<8 for i in range(1, 1+16*4, 4)]):
                            self.core.R[n].set(value)
                        self.writePacket("OK")
                    elif pkt[0] == "H":
                        self.writePacket("OK")
                    elif pkt[0] == "k":     #kill request
                        self.core.reset()
                        self.writePacket("OK")
                    elif pkt[0] == "m":     #read memory
                        self.log.debug("Reading device memory")
                        fromadr, length = [int(x, 16) for x in pkt[1:].split(',')]
                        mem = self.core.memory.read(fromadr, length)
                        self.writePacket(''.join(["%02x" % ord(x) for x in mem]))
                    elif pkt[0] == "M":     #write memory
                        self.log.debug("Writing device memory")
                        meta, data = pkt.split(':')
                        fromadr, length = [int(x, 16) for x in meta[1:].split(',')]
                        sdata = ''.join([chr(int(data[i:i+2],16)) for i in range(0,len(data),2)])
                        try:
                            self.core.memory.write(fromadr, sdata)
                        except IOError:
                            self.writePacket("E01") #write error
                        else:
                            self.writePacket("OK")
                    elif pkt[0] == "q":     #remote commands
                        if pkt[1:5] == "Rcmd":
                            cmd = binascii.unhexlify(pkt.split(',')[1]).strip()
                            self.log.info("monitor command: %r" % cmd)
                            if ' ' in cmd:
                                command, args = cmd.split(None, 1)
                            else:
                                command = cmd
                                args = ''
                            method_name = 'monitor_%s' % command
                            if hasattr(self, method_name):
                                try:
                                    getattr(self, method_name)(args)
                                except:
                                    self.log.exception('error in monitor command')
                                    self.writePacket("E03")
                            else:
                                self.log.warning('no such monitor command ("%s")' % command)
                                self.writePacket("E02")
                        else:
                            self.writePacket("E01") #commond not known
                    elif pkt[0] == "s":     #single step
                        if len(pkt) > 1:
                            adr = int(pkt[1:],16)
                            self.core.PC.set(adr)
                        self.runner.command('step', self._answer_sigtrap)
                    elif pkt[0] == "Z":     #set break or watchpoint
                        ty, adr, length = pkt[1:].split(',')
                        if ty == '0':
                            self.log.debug("Setting breakpoint")
                            self.runner.set_breakpoint(int(adr,16))
                            self.writePacket("OK")
                        else:
                            self.writePacket("E%02x" % (1,))
                    elif pkt[0] == "z":     #remove break or watchpoint
                        ty, adr, length = pkt[1:].split(',')
                        if ty == '0':
                            self.log.debug("Clearing breakpoint")
                            adr = int(adr,16)
                            if adr in self.runner.breakpoints:
                                self.runner.remove_breakpoint(adr)
                                self.writePacket("OK")
                            else:
                                self.writePacket("E%02x" % (2,))
                        else:
                            self.writePacket("E%02x" % (1,))
                    else:   #command not supported
                        self.log.debug("Unsupported comand %r" % pkt)
                        self.writePacket("")
        finally:
            self.close()

    def readPacket(self):
        self.log.debug("readPacket")
        gdbcommand = 0
        csum = 0
        packet = []
        while 1:
            c = self.netin.read(1)
            if not c: self.close() #EOF
            if c == '\x03':     #ctrl+c
                self.runner.interrupt()
                continue
            #print repr(c),
            if gdbcommand:
                if c == '#':
                    if csum != int(self.netin.read(1) + self.netin.read(1), 16):
                        raise ValueError("wrong checksum")
                    return ''.join(packet)
                else:
                    packet.append(c)
                    csum = (csum + ord(c)) % 256
            else:
                if c == '$':
                    gdbcommand = 1

    def writePacket(self, msg):
        self.log.debug("writePacket(%r)" % msg)
        self.netout.write("$%s#%02x" % (msg, checksum(msg)))
        self.netout.flush()

    def writeMessage(self, msg):
        self.writePacket("O%s" % binascii.hexlify(msg))

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    
    def monitor_help(self, args):
        """monitor commands help"""
        self.writeMessage("Supported commands are:\n")
        for name in dir(self):
            if name.startswith('monitor_'):
                self.writeMessage("%-10s: %s\n" % (name[8:], getattr(self, name).__doc__))
        self.writePacket("OK")
        
    #~ def monitor_eval(self, args):
        #~ """evaluate python expression !Security risk!"""
        #~ ans = eval(args)
        #~ self.writeMessage("%r\n" % (ans,))
        #~ self.writePacket("OK")
    
    def monitor_erase(self, args):
        """erase flash"""
        self.log.info('monitor: Erasing Flash ("%s")...' % args)
        #~ if args == 'main':
        #~ elif args == 'info':
        #~ elif args in ('', 'all'):
        #~ else: #accept "address size"
        self.writePacket("OK")

    def monitor_puc(self, args):
        """reset target"""
        self.core.reset()
        self.writePacket("OK")
        
    def monitor_reset(self, args):
        """reset target"""
        self.core.reset()
        self.writePacket("OK")

    def monitor_vcc(self, args):
        """set adapter VCC, ignored. here to be compatible with the real gdbproxy"""
        self.writePacket("OK")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    #~ logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger('trace')
    
    msp430 = core.Core()
    msp430.memory.append(core.Multiplier())
    
    GDBServer(msp430).start()


