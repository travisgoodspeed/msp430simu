#!/usr/bin/env python
#
# GDB server for the MSP430 simulator. This meas that msp430-gdb can
# connect to the simulator and manipulate the simulated core.
# An unllimited number of breakpoints is supported.
#
# (C) 2002-2004 Chris Liechti <cliechti@gmx.net>
# this is distributed under a free software license, see license.txt
#
# $Id: gdbserver.py,v 1.3 2005/12/31 04:27:36 cliechti Exp $

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

def unescape(data):
    """decode binary packets with escapes"""
    esc_found = False
    out = []
    for byte in data:
        if esc_found:
            out.append(byte ^ 0x20)
            esc_found = False
        elif byte == 0x7d:
            esc_found = True
        else:
            out.append(byte)
    return ''.join(out)


class BreakpointRunner(threading.Thread):
    def __init__(self, core):
        self.log = logging.getLogger("runner")
        self.core = core
        self.interrupted = False
        self.breakpoints = {}
        #callback for signals
        self.sig_trap = self._signal
        self.sig_int = self._signal
        self.sig_segv = self._signal
        
        self.cmd_queue = Queue.Queue(1)
        threading.Thread.__init__(self)
        self.setName('msp430 core runner')
        self.setDaemon(1)
    
    def _signal(self):
        self.log.error('signal called but no callback registered')
        
    def set_breakpoint(self, address):
        self.breakpoints[address] = True

    def remove_breakpoint(self, address):
        if address in self.breakpoints:
            del self.breakpoints[address]
            
    def command(self, cmd):
        self.log.info('queing remote command %r' % cmd)
        self.cmd_queue.put(cmd)
    
    def interrupt(self):
        self.log.info('interruption')
        self.interrupted = True
        #empty command queue
        while self.cmd_queue.qsize():
            self.cmd_queue.get_nowait()
            

    def run(self):
        """worker thread"""
        self.log.debug('worker thread started')
        while True:
            try:
                command = self.cmd_queue.get()
                self.log.info('executing remote command %r' % command)
                if command == 'run':
                    self.interrupted = False
                    last_time = time.time()
                    step_delta = 0
                    self.log.info('continuing from 0x%04x (cycle %d)' % (self.core.PC.get(), self.core.cycles))
                    while not self.interrupted:
                        try:
                            self.core.step(illegal_is_fatal=True)
                        except core.MSP430CoreException, e:
                            self.log.warning('could not execute instruction: %s' % e)
                            self.sig_segv()
                            break
                        else:
                            if self.core.PC.get() in self.breakpoints:
                                self.log.info('breakpoint @0x%04x (cycle %d)' % (self.core.PC.get(), self.core.cycles))
                                self.sig_trap()
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
                        self.sig_int()
                elif command == 'step':
                    self.log.info('single step @0x%04x (cycle %d)' % (self.core.PC.get(), self.core.cycles))
                    self.core.step()
                    if self.core.PC.get() in self.breakpoints:
                        self.log.info('breakpoint @0x%04x (cycle %d)' % (self.core.PC.get(), self.core.cycles))
                    self.sig_trap()
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
        self.runner.sig_trap = self._sigtrap
        self.runner.sig_int = self._sigint
        self.runner.sig_segv = self._sigsegv
        self.runner.start()

    def close(self):
        self.alive = False
        self.log.info("closing...")
        self.netin.close()
        self.netout.close()
        self.clientsocket.close()
        self.log.info("closed")

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
                        self.runner.command('run')
                        #~ self.writePacket("S%02x" % (5,))    #SIGTRAP
                    elif pkt[0] == "s":     #single step
                        if len(pkt) > 1:
                            adr = int(pkt[1:],16)
                            self.core.PC.set(adr)
                        self.runner.command('step')
                    elif pkt[0] == "D":     #detach
                        self.core.reset()
                        
                    elif pkt[0] == "g":     #read registers
                        self.log.info("Reading device registers")
                        self.writePacket(''.join(["%02x%02x" % (r.get()&0xff, (r.get()>>8)&0xff) for r in self.core.R]))
                    elif pkt[0] == "G":     #write registers
                        self.log.info("Writing device registers")
                        for n, value in enumerate([int(pkt[i:i+2],16) + int(pkt[i+2:i+4],16)<<8 for i in range(1, 1+16*4, 4)]):
                            self.core.R[n].set(value)
                        self.writeOK()
                    elif pkt[0] == "p":     #read register
                        reg = int(pkt[1:], 16)
                        self.log.info("Reading device register R%d" % (reg))
                        value = int(self.core.R[reg])
                        self.writePacket("%02x%02x" % (value & 0xff, (value >> 8) & 0xff))
                    elif pkt[0] == "P":     #write register
                        reg, data = pkt[1:].split('=')
                        reg = int(reg, 16)
                        data = binascii.unhexlify(data)
                        value = ord(data[0]) | (ord(data[1]) << 8)
                        self.log.info("Writing device register R%d = 0x%04x" % (reg, value))
                        self.core.R[reg].set(value)
                        self.writeOK()
                        
                    elif pkt[0] == "H":
                        self.writeOK()
                    elif pkt[0] == "k":     #kill request
                        self.core.reset()
                        self.writeOK()
                    elif pkt[0] == "m":     #read memory
                        fromadr, length = [int(x, 16) for x in pkt[1:].split(',')]
                        self.log.info("Reading device memory @0x%04x %d bytes" % (fromadr, length))
                        mem = self.core.memory.read(fromadr, length)
                        self.writePacket(binascii.hexlify(mem))
                    elif pkt[0] == "M":     #write memory
                        meta, data = pkt.split(':')
                        fromadr, length = [int(x, 16) for x in meta[1:].split(',')]
                        self.log.info("Writing device memory @0x%04x %d bytes" % (fromadr, length))
                        sdata = binascii.unhexlify(data)
                        try:
                            self.core.memory.write(fromadr, sdata)
                        except IOError:
                            self.writeError(1) #write error
                        else:
                            self.writeOK()
                    #~ elif pkt[0] == "X":     #write memory (binary)
                        #~ meta, data = pkt.split(':')
                        #~ fromadr, length = [int(x, 16) for x in meta[1:].split(',')]
                        #~ if length:
                            #~ self.log.info("Writing device memory @0x%04x %d bytes (X)" % (fromadr, length))
                            #~ sdata = unescape(data)
                            #~ try:
                                #~ self.core.memory.write(fromadr, sdata)
                            #~ except IOError:
                                #~ self.writeError(1) #write error
                            #~ else:
                                #~ self.writeOK()
                        #~ else:
                            #~ self.writeOK()
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
                                    self.writeError(3)
                            else:
                                self.log.warning('no such monitor command ("%s")' % command)
                                self.writeError(2)
                        else:
                            self.writeError(1) #commond not known
                    
                    elif pkt[0] == "Z":     #set break or watchpoint
                        ty, adr, length = pkt[1:].split(',')
                        if ty == '0':
                            address = int(adr,16)
                            self.log.info("Setting breakpoint @0x%04x" % (address))
                            self.runner.set_breakpoint(address)
                            self.writeOK()
                        else:
                            self.writeError(1)
                    elif pkt[0] == "z":     #remove break or watchpoint
                        ty, adr, length = pkt[1:].split(',')
                        if ty == '0':
                            address = int(adr,16)
                            self.log.info("Clearing breakpoint @0x%04x" % (address))
                            if address in self.runner.breakpoints:
                                self.runner.remove_breakpoint(address)
                                self.writeOK()
                            else:
                                self.writeError(2)
                        else:
                            self.writeError(1)
                    else:   #command not supported
                        self.log.warning("Unsupported comand %r" % pkt)
                        self.writePacket("")
        finally:
            self.close()

    def readPacket(self):
        self.log.debug("readPacket")
        gdbcommand = 0
        csum = 0
        packet = []
        while True:
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

    def writeOK(self):
        self.writePacket("OK")
        
    def writeError(self, errorcode=0):
        self.writePacket("E%02x" % (errorcode,))
    
    def writeMessage(self, msg):
        self.writePacket("O%s" % binascii.hexlify(msg))

    def writeSignal(self, signal):
        self.writePacket("S%02x" % (signal,))

    def _sigtrap(self): self.writeSignal(5)
    def _sigint(self): self.writeSignal(2)
    def _sigsegv(self): self.writeSignal(11)
    
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    
    def monitor_help(self, args):
        """monitor commands help"""
        self.writeMessage("Supported commands are:\n")
        for name in dir(self):
            if name.startswith('monitor_'):
                self.writeMessage("%-10s: %s\n" % (name[8:], getattr(self, name).__doc__))
        self.writeOK()
        
    #~ def monitor_eval(self, args):
        #~ """evaluate python expression !Security risk!"""
        #~ ans = eval(args)
        #~ self.writeMessage("%r\n" % (ans,))
        #~ self.writeOK()
    
    def monitor_erase(self, args):
        """erase flash"""
        self.log.info('monitor: Erasing Flash ("%s")...' % args)
        #~ if args == 'main':
        #~ elif args == 'info':
        #~ elif args in ('', 'all'):
        #~ else: #accept "address size"
        self.writeOK()

    def monitor_puc(self, args):
        """reset target"""
        self.core.reset()
        self.writeOK()
        
    def monitor_reset(self, args):
        """reset target"""
        self.core.reset()
        self.writeOK()

    def monitor_vcc(self, args):
        """set adapter VCC, ignored. here to be compatible with the real gdbproxy"""
        self.writeOK()


if __name__ == '__main__':
    logging.basicConfig(level=logging.WARN)
    #~ logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger('gdbclient').setLevel(level=logging.INFO)
    #~ log = logging.getLogger('gdbclient').setLevel(level=logging.DEBUG)
    logging.getLogger("runner").setLevel(level=logging.INFO)

    msp430 = core.Core()
    msp430.memory.append(core.Multiplier())
    
    GDBServer(msp430).start()


