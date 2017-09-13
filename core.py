#!/usr/bin/env python
#
# MSP430 simulator core.
#
# (C) 2002-2004 Chris Liechti <cliechti@gmx.net>
# this is distributed under a free software license, see license.txt
#
# $Id: core.py,v 1.20 2008/05/29 13:48:17 cliechti Exp $

import sys
import logging

try:
    import psyco
except ImportError:
    pass
else:
    psyco.full()

##################################################################
## Observer Pattern
##################################################################
# for update messages

class Observer:
    """base class for views in the Observer Pattern"""
    def update(self, subject, *args, **kwargs):
        """Implement this method in a concrete observer."""
        raise NotImplementedError

class Subject:
    """base class for a model in the Observer Pattern."""
    def __init__(self):
        """don't forget to call this in derrived classes.
        it initalizes the list of observers"""
        self.observerList = []
    def attach(self, observer):
        """attach an observer to this model."""
        self.observerList.append(observer)
    def detach(self, observer):
        """detach an observer from this model."""
        self.observerList.remove(observer)
    def notify(self, *args, **kwargs):
        """for use by the model. this method is called to notify
        observers about changes in the model."""
        for observer in self.observerList:
            observer.update(self, *args, **kwargs)

##################################################################
## Watches
##################################################################
# watches log access on specific addresses in memory

class AddressWatch:
    def __init__(self, description):
        self.log = logging.getLogger('watch')
        self.description = description

    def __call__(self, address, bytemode, oldvalue, newvalue=None):
        if newvalue is not None:    #for writes
            self.log.info(
                ('write: @0x%%04x: 0x%%0%dx -> 0x%%0%dx: %%s' % (
                    bytemode and 2 or 4, bytemode and 2 or 4)
                ) % (
                    address, oldvalue, newvalue, self.description
                ))
        else:           #for reads
            self.log.info(
                ('read: @0x%%04x: 0x%%0%dx: %%s' % (
                    bytemode and 2 or 4)
                ) % (
                    address, oldvalue, self.description
                ))

class MemoryAccessWatch:
    def __init__(self, condition_fu, description):
        self.log = logging.getLogger('watch')
        self.description = description
        self.condition_fu = condition_fu

    def __call__(self, memory, bytemode, writing, address):
        if self.condition_fu(memory, writing, address):
            self.log.info('access: @0x%04x: %s %s' % (
                address, bytemode and 'b' or 'w', self.description
            ))

##################################################################
## CPU registers
##################################################################

class Register(Subject):
    """generic register"""
    def __init__(self, core, value=0, regnum=None):
        Subject.__init__(self)          #init model for observer pattern
        self.core = core
        self.value = value
        self.regnum = regnum
        self.log = logging.getLogger('register')
        self.log.debug('initiliaize R%02d -> 0x%04x' % (self.regnum, value))

    def set(self, value, bytemode=0, am=0):
        """write value to register"""
        self.log.debug('write 0x%04x -> R%02d mode:%s' % (value, self.regnum, bytemode and 'b' or 'w'))
        self.value = value & (bytemode and 0xff or 0xffff)
        self.notify()

    def get(self, bytemode=0, am=0):
        """read register"""
        value = self.value & (bytemode and 0xff or 0xffff)
        self.log.debug('read R%02d -> 0x%04x mode:%s' % (self.regnum, value, bytemode and 'b' or 'w'))
        return value
    
    def __getitem__(self, index):
        """indexed memory access"""
        return self.core.memory.get(bytemode=0, address=self.value+index)

    def __int__(self):
        """return value of register as number"""
        return self.value

    def __repr__(self):
        """return register name and contents"""
        return "R%02d = 0x%04x" % (self.regnum, self.value)

    def __str__(self):
        """return register name"""
        return "R%02d" % (self.regnum)

#programm counter
class PC(Register):
    """Program counter"""
    
    def __init__(self, core, value=0):
        Register.__init__(self, core, value, regnum=0)

    def next(self):
        """fetch a value and advance one word"""
        if self.log: self.log.debug('next @PC+')
        value = self.core.memory.get(bytemode=0, address=self.value)
        self.set(self.value + 2)
        return value

    def __repr__(self):
        """return register name and contents"""
        return "PC  = 0x%04x" % (self.value)

    def __str__(self):
        return "PC"
    
    def __iadd__(self, other):
        """inplace add (+=)"""
        self.set(self.value + int(other))
        return self


class SP(Register):
    """Stack pointer"""
    
    def __init__(self, core, value=0):
        Register.__init__(self, core, value, regnum=1)
    
    def push(self, value):
        self.set(self.value - 2)
        self.log.debug('push @-SP, 0x%04x' % (value))
        self.core.memory.set(bytemode=0, address=self.value, value=value)
        self.notify()
    
    def pop(self):
        value = self.core.memory.get(bytemode=0, address=self.value)
        self.set(self.value + 2)
        self.log.debug('pop @SP+ -> 0x%04x' % (value))
        self.notify()
        return value

    def __repr__(self):
        """return register name and contents"""
        return "SP  = 0x%04x" % (self.value)
    
    def __str__(self):
        return "SP"

#status register/CG1
class SR(Register):
    """SR combined with Constant Generator Register 1"""
    consts = (None,None,4,8)

    def __init__(self, core, value=0):
        Register.__init__(self, core, value, regnum=2)

    bits = {
        'C':      0x0001,
        'Z':      0x0002,
        'N':      0x0004,
        'GIE':    0x0008,
        'CPUOff': 0x0010,
        'OSCOff': 0x0020,
        'SCG0':   0x0040,
        'SCG1':   0x0080,
        'V':      0x0100,
    }

    def __getattr__(self, name):
        if self.bits.has_key(name):
            mask = self.bits[name]
            return (self.value & mask) != 0
        else:
            return self.__dict__[name]

    def __setattr__(self, name, value):
        if self.bits.has_key(name):
            mask = self.bits[name]
            if value:
                self.value  |= mask
            else:
                self.value  &= ~mask
            self.notify()
        else:
            self.__dict__[name] = value

    #custom get for CG1
    def get(self, bytemode=0, am=0):
        if am == 0: return self.value & (bytemode and 0xff or 0xffff)
        value = self.consts[am] & (bytemode and 0xff or 0xffff)
        self.log.debug('REGSTR: read     R%02d -> 0x%04x mode:%s' % (self.regnum, value, bytemode and 'b' or 'w'))
        return value

    def __repr__(self):
        """return register name and contents"""
        res = "SR  = 0x%04x " % (self.value)
        #then append deatiled bit display
        for key in ('C', 'Z', 'N', 'V', 'GIE'):
            res += '%s:%s ' % (key, (self.value & self.bits[key]) and '1' or '0')
        return res

    def __str__(self):
        return "SR"


class CG2(Register):
    """Constant Generator Register 2"""
    consts = (0,1,2,0xffff)

    def __init__(self, core, value=0):
        Register.__init__(self, core, value, regnum=3)

    def get(self, bytemode=0, am=0):
        value = self.consts[am] & (bytemode and 0xff or 0xffff)
        self.log.debug('read R%02d -> 0x%04x mode:%s' % (self.regnum, value, bytemode and 'b' or 'w'))
        return value

    def __repr__(self):
        return "CG2 = -"

    def __str__(self):
        return "CG2"

##################################################################
## Main Memory
##################################################################
class Peripheral:
    color = (0x33, 0x33, 0x33)      #color for graphical representation
    def __init__(self):
        self.log = logging.getLogger('peripheral')
        self.reset()        #init device

    def __contains__(self, address):
        """return true if address is handled by this peripheral"""
        raise NotImplementedError

    def reset(self):
        """perform a power up reset"""
        raise NotImplementedError

    def set(self, address, value, bytemode=0):
        """write value to address"""
        raise NotImplementedError

    def get(self, address, bytemode=0):
        """read from address"""
        raise NotImplementedError

class Flash(Peripheral):
    """flash memory"""
    color = (0xff, 0xaa, 0x88)      #color for graphical representation

    def __init__(self, startaddress = 0xf000, endaddress = 0xffff):
        self.startaddress = startaddress
        self.endaddress = endaddress
        Peripheral.__init__(self)  #calls self.reset()
        self.log = logging.getLogger('flash')
    
    FCTL1 = 0x0128
    FCTL2 = 0x012a
    FCTL3 = 0x012c
    #~ INFO_START = 0x1000
    #~ INFO_END   = 0x10ff

    def __contains__(self, address):
        """return true if address is handled by this peripheral"""
        return self.startaddress <= address <= self.endaddress \
            or self.FCTL1 <= address <= self.FCTL3+1

    def reset(self):
        """perform a power up reset"""
        self.values = [0xff] * (self.endaddress - self.startaddress + 1)

    def set(self, address, value, bytemode=0):
        """write value to address"""
        if self.FCTL1 <= address <= self.FCTL3+1:
            pass #xxx handle flas write/erase etc
        else:
            if bytemode:
                self.values[address-self.startaddress] = value & 0xff
            else:
                self.values[(address-self.startaddress & 0xfffe)  ] =  value     & 0xff
                self.values[(address-self.startaddress & 0xfffe)+1] = (value>>8) & 0xff

    def get(self, address, bytemode=0):
        """read from address"""
        if self.FCTL1 <= address <= self.FCTL3+1:
            value = 0
        else:
            if bytemode:
                value = self.values[address-self.startaddress]
            else:
                #word reads are allways on even addresses...
                value = (self.values[(address-self.startaddress & 0xfffe)+1]<<8) |\
                         self.values[(address-self.startaddress & 0xfffe)]
        return value

class RAM(Peripheral):
    """RAM memory"""
    color = (0xaa, 0xff, 0x88)      #color for graphical representation

    def __init__(self, startaddress = 0x0200, endaddress = 0x02ff):
        self.startaddress = startaddress
        self.endaddress = endaddress
        Peripheral.__init__(self)  #calls self.reset()
        self.log = logging.getLogger('RAM')
    
    def __contains__(self, address):
        """return true if address is handled by this peripheral"""
        return self.startaddress <= address <= self.endaddress

    def reset(self):
        """perform a power up reset"""
        self.values = [0] * (self.endaddress - self.startaddress + 1)

    def set(self, address, value, bytemode=0):
        """write value to address"""
        if bytemode:
            self.values[address-self.startaddress] = value & 0xff
        else:
            self.values[(address-self.startaddress & 0xfffe)  ] =  value     & 0xff
            self.values[(address-self.startaddress & 0xfffe)+1] = (value>>8) & 0xff

    def get(self, address, bytemode=0):
        """read from address"""
        if bytemode:
            value = self.values[address-self.startaddress]
        else:
            value = (self.values[(address-self.startaddress & 0xfffe)+1]<<8) |\
                     self.values[(address-self.startaddress & 0xfffe)]
        return value

class Multiplier(Peripheral):
    """hardware mutiplier"""
    #op1, op2 contain signed numbers
    #acc is the 32 bit result, sumext the overflow register
    #mpy,mpys,mac,mac are saved for later reads from that addresses
    #mode is used to store the multiplication type

    color = (0xee, 0xaa, 0xff)      #color for graphical representation

    MUL, SIGNEDMUL, MULANDACCUM, SIGNEDMULANDACCUM = range(4)
    
    def __contains__(self, address):
        """return true if address is handled by this peripheral"""
        return 0x0130 <= address <= 0x013f

    def reset(self):
        """perform a power up reset"""
        self.mode = 0
        self.op1  = 0
        self.op2  = 0
        self.acc  = 0
        self.sumext = 0
        self.mpy  = 0
        self.mpys = 0
        self.mac  = 0
        self.macs = 0

    def _makesigned(self, value, bytemode):
        if bytemode:
            if value & 0x80:    #negative?
                return -((~value + 1) & 0xff)
            else:
                return value & 0xff
        else:
            if value & 0x8000:    #negative?
                return -((~value + 1) & 0xffff)
            else:
                return value & 0xffff

    def set(self, address, value, bytemode=0):
        """write value to address"""
        if address == 0x130:    #MPY
            self.mode = self.MUL
            self.op1 = self.mpy = value
        elif address == 0x132:    #MPYS
            self.mode = self.SIGNEDMUL
            self.mpys = value
            self.op1 = self._makesigned(value, bytemode)
        elif address == 0x134:    #MPYS
            self.mode = self.MULANDACCUM
            self.op1 = self.mac = value
        elif address == 0x136:    #MPYS
            self.mode = self.SIGNEDMULANDACCUM
            self.op1 = self.macs = value
            self.op1 = self._makesigned(value, bytemode)
        elif address == 0x138:    #OP2
            if self.mode == self.SIGNEDMUL or self.mode == self.SIGNEDMULANDACCUM:
                self.op2 = self._makesigned(value, bytemode)
            else:
                self.op2 = value
            #multiply...
            r = abs(self.op1) * abs(self.op2)
            if self.mode == self.MUL:
                self.acc = r
                self.sumext = 0
            elif self.mode == self.SIGNEDMUL:
                if self.op1 < 0:    r = -r
                if self.op2 < 0:    r = -r
                self.acc = r
                if (self.op1 < 0 and not self.op2 < 0) or (not self.op1 < 0 and self.op2 < 0):
                    self.sumext = 0xffff
                else:
                    self.sumext = 0
            elif self.mode == self.MULANDACCUM:
                self.acc += r
                if self.acc > 0xffffffffL:
                    self.sumext = 0x0001
                else:
                    self.sumext = 0
            elif self.mode == self.SIGNEDMULANDACCUM:
                if self.op1 < 0:    r = -r
                if self.op2 < 0:    r = -r
                self.acc += r
                if self.acc > 0x7fffffff:
                    self.sumext = 0xffff
                else:
                    self.sumext = 0
            else:
                raise ValueError('invalid internal state %s' % self.mode)
            #XXX TODO: broken!!
        elif address == 0x13a:    #ResLo/acc
            self.acc = (self.acc & 0xffff0000L) | value
        elif address == 0x13c:    #ResHi/acc
            self.acc = (self.acc & 0x0000ffff) | (value<<16)
        elif address == 0x13e:    #SumExt
            self.log.error('Access Error - SUMEXT is read only')

    def get(self, address, bytemode=0):
        """read from address"""
        if bytemode:
            self.log.error('Access Error - byte access not allowed')
        if address == 0x130:    value = self.mpy
        elif address == 0x132:  value = self.mpys
        elif address == 0x134:  value = self.mac
        elif address == 0x136:  value = self.macs
        elif address == 0x138:  value = self.op2
        elif address == 0x13a:  value = self.acc
        elif address == 0x13c:  value = self.acc >> 16
        elif address == 0x13e:  value = self.sumext
        else: value = 0
        return value & (bytemode and 0xff or 0xffff)

class ExtendedPorts(Peripheral):
    """class for port 1 and 2"""
    color = (0xaa, 0x88, 0xff)      #color for graphical representation

    def __contains__(self, address):
        """return true if address is handled by this peripheral"""
        return self.values.has_key(address)

    def reset(self):
        """perform a power up reset"""
        self.values = {
            0x20: 0, 0x21: 0, 0x22: 0, 0x23: 0, 0x24: 0, 0x25: 0, 0x26: 0,
            0x28: 0, 0x29: 0, 0x2a: 0, 0x2b: 0, 0x2c: 0, 0x2d: 0, 0x2e: 0}

    def set(self, address, value, bytemode=0):
        """write value to address"""
        if not bytemode:
            self.log.error('Access Error - expected byte but got word access')
        self.values[address] = value & 0xff

    def get(self, address, bytemode=0):
        """read from address"""
        if not bytemode:
            self.log.error('Access Error - expected byte but got word access')
        return self.values[address]


class Memory(Subject):
#    color = (0xaa, 0xaa, 0xaa)      #color for graphical representation
    color = (0xff, 0xff, 0xff)      #color for graphical representation
    def __init__(self):
        Subject.__init__(self)          #init model for observer pattern
        self.log = logging.getLogger('memory')
        self.setwatches = {}        #serached on reads
        self.getwatches = {}        #serached on writes
        self.accesswatches = []     #searched allways
        self.peripherals = []
        self.reset()                #init memory

    def append(self, peripheral):
        self.peripherals.append(peripheral)

    def __getitem__(self, address):
        for p in self.peripherals:
            if address in p:
                return p
        return self

    def reset(self):
        """perform a reset"""
        for p in self.peripherals: p.reset()
        self.memory = [0]*65536
        self.notify()

    def load(self, filename):
        """fill memory with the contents of a file. file type is determined from extension"""
        self.log.info('loading file %r' % filename)
        if filename[-4:].lower() == '.txt':
            self.loadTIText(open(filename, "r"))
        else:
            self.loadIHex(open(filename, "r"))

    def loadIHex(self, file):
        """load data from a (opened) file in Intel-HEX format"""
        for l in file.readlines():
            if l[0] != ':':
                raise IOError("file format error")
            l = l.strip()       #fix CR-LF issues...
            count    = int(l[1:3],16)
            address  = int(l[3:7],16)
            code     = int(l[7:9],16)
            checksum = int(l[-2:],16)

            if code == 0x00:
                for i in range(count):
                    value = int(l[9+i*2:11+i*2],16)
                    self._set(address+i, value, bytemode=1)
            elif code in [0x01, 0x02, 0x03]:
                pass        #known types but not useful?!?
            else:
                self.log.warning("Ignored unknown field (type 0x%02x) in ihex file." % (code,))
        self.notify()

    def loadTIText(self, file):
        """load data from a (opened) file in TI-Text format"""
        next        = 1
        currentAddr = 0
        startAddr   = 0
        segmentdata = []
        #Convert data for MSP430, TXT-File is parsed line by line
        while next >= 1:
            #Read one line
            l = file.readline()
            if not l: break #EOF
            l = l.strip()
            if l[0] == 'q': break
            elif l[0] == '@':        #if @ => new address => send frame and set new addr.
                address = int(l[1:],16)
            else:
                for i in l.split():
                    value = int(i,16)
                    self._set(address, value, bytemode=1)
                    address += 1


    def _set(self, address, value, bytemode=0):
        """quiet set without logging"""
        address &= 0xffff       #16 bit wrap around
        for p in self.peripherals:
            if address in p:
                p.set(address, value, bytemode)
                break
        else:
            if bytemode:
                self.memory[address] = value & 0xff
            else:
                self.memory[address  ] =  value     & 0xff
                self.memory[address+1] = (value>>8) & 0xff

    def set(self, address, value, bytemode=0):
        """write value to address"""
        if address > 0xffff:
            self.log.error('write outside valid of address range (0x%04x)' % (address, ))
            address &= 0xffff       #16 bit wrap around
        self.log.debug('write 0x%04x <- 0x%04x mode:%s' % (address, value, bytemode and 'b' or 'w'))
        if self.setwatches.has_key(address): self.setwatches[address](address, bytemode, self.memory[address], value)  #call watch
        for a in self.accesswatches: a(self, bytemode, 1, address)
        self._set(address, value, bytemode)
        self.notify(address, bytemode)

    def _get(self, address, bytemode=0):
        """quiet get without logging"""
        address &= 0xffff       #16 bit wrap around
        for p in self.peripherals:
            if address in p:
                value = p.get(address, bytemode)
                break
        else:
            if bytemode:
                value = self.memory[address]
            else:
                value = (self.memory[address+1]<<8) | self.memory[address]
        return value

    def get(self, address, bytemode=0):
        """read value from address"""
        if address > 0xffff:
            self.log.error('read outside of valid address range (0x%04x)' % (address, ))
            address &= 0xffff       #16 bit wrap around
        if self.getwatches.has_key(address): self.getwatches[address](address, bytemode, self.memory[address], None)  #call watch
        for a in self.accesswatches: a(self, bytemode, 0, address)
        value = self._get(address, bytemode)
        self.log.debug('read 0x%04x -> 0x%04x mode:%s' % (address, value, bytemode and 'b' or 'w'))
        return value

    def read(self, address, length):
        return ''.join([chr(self._get(a,1)) for a in range(address, address+length)])

    def write(self, address, data):
        for n, byte in enumerate(data):
            self._set(address+n, ord(byte), 1)

    def hexline(self, address, width=16):
        """build a tuple with (address, hex values, ascii values)"""
        bytes = [self._get(a, bytemode=1) for a in range(address, address+width)]
        return  (
            '0x%04x' % address, '%s%s' % (
                ('%02x '*len(bytes)) % tuple(bytes),
                '   '* (width-len(bytes))),  #fill
            ('%c'*len(bytes)) % tuple(map(lambda x: x>32 and x or ord('.'), bytes)) #ascii
        )
            

    def hexdump(self, fromadr, toadr=None, lines = 20):
        adr = fromadr
        res = []
        while (toadr is not None and adr < toadr+1) or (toadr is None) and len(res) < lines:
            res.append('%s  %s %s' % (self.hexline(adr)))
            adr += 16
        return '\n'.join(res)

##################################################################
## argument wrappers
##################################################################
#all argument can be accessed by get() and set(value)
#these are used to unify memory and register access for the
#core "exec_" functions

class Argument:
    """just a baseclass common for all argument wrappers"""
    pass

class RegisterArgument(Argument):
    """get set register"""
    def __init__(self, core, reg, bytemode, am):
        self.core = core
        self.reg = reg
        self.bytemode = bytemode
        self.am = am
        
    def get(self):
        return self.reg.get(self.bytemode, self.am)
    
    def set(self, value):
        self.reg.set(value, self.bytemode, self.am)

    def __repr__(self):
        if self.reg is self.core.SR and self.am > 1:
            return '#%d {CG1}' % self.core.SR.consts[self.am]
        elif self.reg is self.core.CG2:
            return '#%d {CG2}' % self.core.CG2.consts[self.am]
        else:
            return '%s' % (self.reg)

class IndexedRegisterArgument(Argument):
    """get set memory indexed by register"""
    def __init__(self, core, reg, bytemode, offset):
        self.core = core
        self.reg = reg
        self.bytemode = bytemode
        self.offset = offset
        
    def get(self):
        return self.core.memory.get(self.offset + self.reg.get(), self.bytemode)
    
    def set(self, value):
        self.core.memory.set(self.offset + self.reg.get(), value, self.bytemode)

    def __repr__(self):
        return '0x%04x(%s)' % (self.offset, self.reg)

class IndirectRegisterArgument(Argument):
    """get value at address in register"""
    def __init__(self, core, reg, bytemode):
        self.core = core
        self.reg = reg
        self.bytemode = bytemode
        
    def get(self):
        return self.core.memory.get(self.reg.get(), self.bytemode)
    
    def set(self, value):
        raise "not possible as destination"

    def __repr__(self):
        return '@%s' % (self.reg)

class IndirectAutoincrementRegisterArgument(Argument):
    """get value at address on register, increment register"""
    def __init__(self, core, reg, bytemode):
        self.core = core
        self.reg = reg
        self.bytemode = bytemode

    def get(self):
        res = self.core.memory.get(self.reg.get(), self.bytemode)
        self.reg.set(self.reg.get() + (self.bytemode and 1 or 2))
        return res

    def set(self, value):
        raise ValueError("not possible as destination")

    def __repr__(self):
        return '@%s+' % (self.reg)

class ImmediateArgument(Argument):
    """immediate value (readonly)"""
    def __init__(self, core, bytemode, value):
        self.core = core
        self.bytemode = bytemode
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        raise ValueError("not possible as destination")

    def __repr__(self):
        return '#0x%04x' % (self.value)

class MemoryArgument(Argument):
    """get set memory"""
    def __init__(self, core, address, bytemode):
        self.core = core
        self.address = address
        self.bytemode = bytemode
        
    def get(self):
        return self.core.memory.get(self.address, self.bytemode)
    
    def set(self, value):
        self.core.memory.set(self.address, value, self.bytemode)

    def __repr__(self):
        return '0x%04x' % (self.address)


class JumpTarget:
    """jump target address"""
    def __init__(self, core, address, offset):
        self.core = core
        self.address = address  #current address, only for output
        self.offset = offset

    def __int__(self):
        return self.offset

    def __repr__(self):
        return '$%+d {->0x%04x}' % (self.offset+2, self.address+self.offset)

##################################################################
## argument conversion
##################################################################
# take arguments from core for insn and return wrappers
#(wrapper factory)

def addressMode(core, pc, bytemode, asflag = None, ad = None, src = None, dest = None):
    """return two arguments wrappers and a cycle count for the use of both"""
    x = y = None
    c = 0
    #source first
    
    if asflag is not None:  #CG2
        if src == 2 and asflag > 1:
            x = RegisterArgument(core,reg=core.R[src], bytemode=bytemode, am=asflag)
            #m = "#%d" % (None,None,4,8)[asflag]
        elif src == 3:  #CG3
            x = RegisterArgument(core,reg=core.R[src], bytemode=bytemode, am=asflag)
            #m = "#%d" % (0,1,2,0xffff)[asflag]
        else:
            if   asflag == 0:   #register mode
                #m = '%(srcname)s'
                x = RegisterArgument(core,reg=core.R[src], bytemode=bytemode, am=asflag)
            elif asflag == 1:   #pc rel
                if src == 0:
                    #m = '%%(x)04x'
                    x = IndexedRegisterArgument(core, reg=core.PC, offset=pc.next(), bytemode=bytemode)
                    c += 2  #fetch+read
                elif src == 2: #abs
                    #m = '&%%(x)04x'
                    x = MemoryArgument(core, address=pc.next(), bytemode=bytemode)
                    c += 2  #fetch+read
                else:           #indexed
                    #m = '%%(x)04x(%(srcname)s)'
                    x = IndexedRegisterArgument(core, reg=core.R[src], offset=pc.next(), bytemode=bytemode)
                    c += 2  #fetch+read
            elif asflag == 2:   #indirect
                #m = '@%(srcname)s'
                x = IndirectRegisterArgument(core, reg=core.R[src], bytemode=bytemode)
                c += 1  #target mem read
            elif asflag == 3:
                if src == 0:    #immediate
                    #m = '#%%(x)d'
                    x = ImmediateArgument(core, value=pc.next(), bytemode=bytemode)
                    c += 1  #fetch
                else:           #indirect autoincrement
                    #m = '@%(srcname)s+'
                    x = IndirectAutoincrementRegisterArgument(core, reg=core.R[src], bytemode=bytemode)
                    c += 1  #read
            else:
                raise "addressing mode error"
    #dest
    if ad is not None:
        if ad == 0:
            #m += '%(destname)s'
            y = RegisterArgument(core, reg=core.R[dest], bytemode=bytemode, am=ad)
            if dest == 0:
                c += 1  #modifying PC gives one cycle penalty
        else:
            if dest == 0:   #PC relative
                #m += '%%(y)04x'
                y = IndexedRegisterArgument(core, reg=core.PC, offset=pc.next(), bytemode=bytemode)
                c += 3  #fetch + read modify write
            elif dest == 2: #abs
                #m += '&%%(y)04x'
                y = MemoryArgument(core, address=pc.next(), bytemode=bytemode)
                c += 3  #fetch + read modify write
            else:           #indexed
                #m += '%%(y)04x(%(destname)s)'
                y = IndexedRegisterArgument(core, reg=core.R[dest], offset=pc.next(), bytemode=bytemode)
                c += 3  #fetch + read modify write

    return x,y,c


##################################################################
## CORE (CPU with Regs, Mem, insn)
##################################################################

class MSP430CoreException(Exception):
    """this exception is raised when code execution errors are detected"""
    
class Core(Subject):
    """CPU core with registers, memory and code execution logic"""

    #------------------------
    #Core instructions
    #------------------------

    #---
    # single operand insn

    def execRRC(self, bytemode, arg):
        shift = bytemode and 7 or 15
        mask = bytemode and 0x7f or 0x7fff
        a = arg.get()
        c = self.SR.C
        r = (c<<shift) | ((a>>1) & mask)
        self.SR.Z = (r == 0)
        self.SR.N = r & (bytemode and 0x80 or 0x8000)
        self.SR.C = (a & 1)
        self.SR.V = 0
        arg.set(r)

    def execSWPB(self, bytemode, arg):
        if bytemode:
            raise MSP430CoreException("illegal use of SWPB")
        a = arg.get()
        r = ((a & 0xff00) >> 8) | ((a & 0x00ff) << 8)
        arg.set(r)

    def execRRA(self, bytemode, arg):
        a = arg.get()
        n = a & (bytemode and 0x80 or 0x8000)
        r = n | ((a>>1) & (bytemode and 0x7f or 0x7fff))
        self.SR.Z = (r == 0)
        self.SR.N = r & (bytemode and 0x80 or 0x8000)
        self.SR.C = (a & 1)
        self.SR.V = 0
        arg.set(r)

    def execSXT(self, bytemode, arg):
        if bytemode: raise MSP430CoreException("illegal use of SXT") #should actualy never happen
        a = arg.get()
        r = a & 0xff
        if a & 0x80:  r |= 0xff00
        self.SR.Z = (r == 0)
        self.SR.N = r & (bytemode and 0x80 or 0x8000)
        self.SR.C = (a & 1)
        self.SR.V = 0
        arg.set(r)

    def execPUSH(self, bytemode, arg):
        self.SP.push(arg.get())

    def execCALL(self, bytemode, arg):
        self.SP.push(self.PC.get())
        self.PC.set(arg.get())

    def execRETI(self, bytemode, arg):
        self.SR.set(self.SP.pop())
        self.PC.set(self.SP.pop())

    #---
    # double operand insn

    def execMOV(self, bytemode, src, dst):
        dst.set(src.get())

    def execADD(self, bytemode, src, dst):
        self.execADDC(bytemode, src, dst, takecarry = 0)

    def execADDC(self, bytemode, src, dst, takecarry = 1):
        b = (bytemode and 0x80 or 0x8000)
        d = dst.get()
        s = src.get()
        if takecarry:
            c = self.SR.C
        else:
            c = 0
        r = d + s + c
        self.SR.Z = r & (bytemode and 0xff or 0xffff) == 0
        self.SR.N = r & (bytemode and 0x80 or 0x8000)
        self.SR.C = r < 0 or r > (bytemode and 0xff or 0xffff)
        self.SR.V = (not (r & b) and (s & b) and (d & b)) or ((r & b) and not (s & b) and not (d & b))
        dst.set(r)


    def execCMP(self, bytemode, src, dst):
        self.execSUBC(bytemode, src, dst, takecarry = 0, store = 0)

    def execSUB(self, bytemode, src, dst):
        self.execSUBC(bytemode, src, dst, takecarry = 0, store = 1)

    def execSUBC(self, bytemode, src, dst, takecarry = 1, store = 1):
        b = (bytemode and 0x80 or 0x8000)
        m = (bytemode and 0xff or 0xffff)
        d = dst.get()
        s = src.get()
        if takecarry:
            c = self.SR.C
        else:
            c = 1
        r = d + ((~s) & m) + c
        self.SR.Z = r & m == 0
        self.SR.N = r & b
        self.SR.C = r < 0 or r > m
        self.SR.V = (not (r & b) and not (s & b) and (d & b)) or ((r & b) and (s & b) and not (d & b))
        if store: dst.set(r)

    def execDADD(self, bytemode, src, dst):
        #XXX implement this one
        raise NotImplementedError("instruction not supported in this version of simu")

    def execBIT(self, bytemode, src, dst):
        d = dst.get()
        s = src.get()
        r = d & s
        self.SR.Z = (r == 0)
        self.SR.N = r & (bytemode and 0x80 or 0x8000)
        self.SR.C = (r != 0)
        self.SR.V = 0

    def execBIC(self, bytemode, src, dst):
        d = dst.get()
        s = src.get()
        r = d & ~s
        dst.set(r)

    def execBIS(self, bytemode, src, dst):
        dst.set( dst.get() | src.get() )
        d = dst.get()
        s = src.get()
        r = d | s
        dst.set(r)
        
    def execXOR(self, bytemode, src, dst):
        d = dst.get()
        s = src.get()
        r = d ^ s
        self.SR.Z = r & (bytemode and 0xff or 0xffff) == 0
        self.SR.N = r & (bytemode and 0x80 or 0x8000)
        self.SR.C = (r != 0)
        self.SR.V = s & (bytemode and 0x80 or 0x8000) and d & (bytemode and 0x80 or 0x8000)
        dst.set(r)

    def execAND(self, bytemode, src, dst):
        d = dst.get()
        s = src.get()
        r = d & s
        self.SR.Z = (r == 0)
        self.SR.N = r & (bytemode and 0x80 or 0x8000)
        self.SR.C = (r != 0)
        self.SR.V = 0
        dst.set(r)

    #---
    # jumps
    #with dummy bytemode for signature compatibility of methods
    
    def execJNZ(self, bytemode, offset):
        if not self.SR.Z:
            self.PC += offset

    def execJZ(self, bytemode, offset):
        if self.SR.Z:
            self.PC += offset

    def execJC(self, bytemode, offset):
        if self.SR.C:
            self.PC += offset

    def execJNC(self, bytemode, offset):
        if not self.SR.C:
            self.PC += offset

    def execJN(self, bytemode, offset):
        if not self.SR.N:
            self.PC += offset
    
    def execJGE(self, bytemode, offset):
        if not (self.SR.N ^ self.SR.V):
            self.PC += offset

    def execJL(self, bytemode, offset):
        if self.SR.N ^ self.SR.V:
            self.PC += offset

    def execJMP(self, bytemode, offset):
        self.PC += offset

    #------------------------
    # instruction tables
    #------------------------

    singleOperandInstructions = {
        0x00<<7: ('rrc',  execRRC,  0),
        0x01<<7: ('swpb', execSWPB, 0),
        0x02<<7: ('rra',  execRRA,  0),
        0x03<<7: ('sxt',  execSXT,  0),
        0x04<<7: ('push', execPUSH, 2),    #write of stack -> 2
        0x05<<7: ('call', execCALL, 3),    #write of stack -> 2, modify PC -> 1
        0x06<<7: ('reti', execRETI, 4),    #pop SR -> 1, pop PC -> 1, modify PC -> 1,  +1??
    }

    doubleOperandInstructions = {
        0x4000: ('mov',  execMOV,  0),
        0x5000: ('add',  execADD,  0),
        0x6000: ('addc', execADDC, 0),
        0x7000: ('subc', execSUBC, 0),
        0x8000: ('sub',  execSUB,  0),
        0x9000: ('cmp',  execCMP,  0),
        0xa000: ('dadd', execDADD, 0),
        0xb000: ('bit',  execBIT,  0),
        0xc000: ('bic',  execBIC,  0),
        0xd000: ('bis',  execBIS,  0),
        0xe000: ('xor',  execXOR,  0),
        0xf000: ('and',  execAND,  0),
    }

    jumpInstructions = (
        ('jnz',  execJNZ,  1), #jne        0x0: 
        ('jz',   execJZ,   1), #jeq        0x1: 
        ('jnc',  execJNC,  1), #           0x2: 
        ('jc',   execJC,   1), #           0x3: 
        ('jn',   execJN,   1), #           0x4: 
        ('jge',  execJGE,  1), #           0x5: 
        ('jl',   execJL,   1), #           0x6: 
        ('jmp',  execJMP,  1), #           0x7: 
    )

    #------------------------
    # methods
    #------------------------

    def __init__(self):
        """initialize core with registers and memory"""
        Subject.__init__(self)          #init model for observer pattern
        self.log = logging.getLogger('core')
        self.memory = Memory()
        self.R = (
            PC(self),
            SP(self),
            SR(self),
            CG2(self),
            Register(self, regnum=4),
            Register(self, regnum=5),
            Register(self, regnum=6),
            Register(self, regnum=7),
            Register(self, regnum=8),
            Register(self, regnum=9),
            Register(self, regnum=10),
            Register(self, regnum=11),
            Register(self, regnum=12),
            Register(self, regnum=13),
            Register(self, regnum=14),
            Register(self, regnum=15)
        )
        #aliases
        self.PC = self.R[0]
        self.SP = self.R[1]
        self.SR = self.R[2]
        self.CG2 = self.R[3]
        self.cycles = 0

    def reset(self):
        for r in self.R:
            r.set(0)
        self.memory.reset()
        self.notify()

    def disassemble(self, pc, illegal_is_fatal=False):
        """disassemble current PC location and advance PC to the next instruction.
        return a tuple with insn name, arguments (bytemode, arg1, arg2),
        core execution function for that insn and a cycle count.
        
        the programm counter PC is used and modified."""
        
        opcode = pc.next()
        cycles = 1              #count cycles, start with insn fetch
        x = y = None
        #jump instructions
        if (opcode & 0xe000) == 0x2000:
            name, fu, addcyles = self.jumpInstructions[(opcode>>10) & 0x7]
            offset = (opcode & 0x3ff) << 1
            if offset & 0x400:  #negative?
                offset = -((~offset + 1) & 0x7ff)
            cycles += addcyles #jumps allways have 2 cycles
            return name, [0, JumpTarget(self, int(pc), offset)], fu, cycles

        #single operand
        elif (opcode & 0xf000) == 0x1000:
            bytemode = bool(opcode & 0x40) #(opcode>>6) & 1
            x,y,c = addressMode(self, pc, bytemode,
                asflag=(opcode>>4) & 3,
                src=opcode & 0xf
                )
            try:
                name, fu, addcyles = self.singleOperandInstructions[opcode & 0x0f80]
            except KeyError:
                pass
            else:
                cycles += c + addcyles #some functions have additional cycles (push etc)
                return name, [bytemode, x], fu, cycles

        #double operand
        else:
            bytemode = bool(opcode & 0x40) #(opcode>>6) & 1
            x,y,c = addressMode(self, pc, bytemode,
                src=(opcode>>8) & 0xf,
                ad=(opcode>>7) & 1,
                asflag=(opcode>>4) & 3,
                dest=opcode & 0xf
                )
            try:
                name, fu, addcyles = self.doubleOperandInstructions[opcode & 0xf000]
            except KeyError:
                pass
            else:
                cycles += c + addcyles #some functions have additional cycles (push etc)
                return name, [bytemode, x, y], fu, cycles

        #unkown instruction
        if illegal_is_fatal:
            raise MSP430CoreException('illegal instruction 0x%04x' % (opcode,))
        return 'illegal insn 0x%04x' % opcode, [0], None, cycles

    def step(self, illegal_is_fatal=False):
        """perform one single step"""
        address = int(self.PC)
        name, args, execfu, cycles = self.disassemble(self.PC, illegal_is_fatal)
        self.cycles += cycles
        note = "%s%s %s (%d cycles)" % (
            name,
            ('','.b')[args[0]],
            ', '.join(map(str,args[1:])),
            cycles
        )
        if execfu:
            self.log.info('step: %s' % (note,))
            apply(execfu, [self]+args)
        else:
            self.log.warning("step: %s @0x%04x" % (name, address))
        self.notify()
        return note

    def __repr__(self):
        return ('%r\n'*15 + '%r') % self.R

##################################################################
## trace control object
##################################################################

class Tracer:
    def __init__(self, core):
        self.core = core
        self.log = logging.getLogger('trace')

    def start(self, startadr, maxsteps=100):
        self.log.info('set startaddress')
        self.core.PC.set(startadr)
        self.log.info('*** starting trace (maxsteps=%d)' % (maxsteps))
        step = 1
        while step <= maxsteps:
            self.core.step()
            self.log.info('step %d, cycle %d\n%r' % (
                step, self.core.cycles, self.core))
            step += 1

##################################################################
## testing
##################################################################

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger('trace')
    
    core = Core()
    core.SR.Z = 243
    print core.SR.Z
    print repr(core.SR)

    #~ core.memory.load('tests.a43')
    core.memory.load('../examples/leds/leds.a43')
    
    #~ print "-"*40, "memory dump"
    #~ print '\n'.join(core.memory.hexdump(0xF000, 0xF086))

    #~ print "-"*40, "disassemble"
    #~ pc = PC(core, 0xf000) #, 0xf71f
    #~ while pc.get() < 0xF086:
        #~ print "0x%04x:" % pc, core.disassemble(pc)

##    print "-"*40, "single step"
##    core.PC.set(0xf000)
##    while int(core.PC) < 0xF086:
##        print core.step()
##        print repr(core)

    print "-"*40, "trace"
    core.memory.getwatches[0x200] = AddressWatch("Variable one READ")
    core.memory.setwatches[0x200] = AddressWatch("Variable one WRITE")
    core.memory.accesswatches.append(MemoryAccessWatch(
        lambda mem, wrt, adr: not(          #F1121 layout
            0x0000 <= adr <= 0x01ff or      #Peripherals (not detailed)
            0x0200 <= adr <= 0x02ff or      #RAM
            0x1000 <= adr <= 0x10ff or      #INFOMEM
            0xf000 <= adr <= 0xffff         #FLASH
        ),
        'Illegal memory access',
    ))
    core.memory.accesswatches.append(MemoryAccessWatch(
        lambda mem, wrt, adr: wrt and(      #F1121 layout
            0x1000 <= adr <= 0x10ff or      #INFOMEM
            0xf000 <= adr <= 0xffff         #FLASH
        ),
        'flash memory written',
    ))
    print core.memory.hexdump(0x0200, 0x02ff, log)
    tracer = Tracer(core)
    tracer.start(0xf000, 50) #only N steps
    print "-"*40, "end"
    print core.memory.hexdump(0x0200, 0x02ff, log)





