#!/usr/bin/env python
import sys

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
    def __init__(self, log, description):
        self.log = log
        self.description = description

    def __call__(self, address, bytemode, oldvalue, newvalue):
        if newvalue:    #for writes
            self.log.write(
                ('WATCHr: @0x%%04x: 0x%%0%dx -> 0x%%0%dx: %%s\n' % (
                    bytemode and 2 or 4, bytemode and 2 or 4)
                ) % (
                    address, oldvalue, newvalue, self.description
                ))
        else:           #for reads
            self.log.write(
                ('WATCHr: @0x%%04x: 0x%%0%dx: %%s\n' % (
                    bytemode and 2 or 4)
                ) % (
                    address, oldvalue, self.description
                ))

class MemoryAccessWatch:
    def __init__(self, log, condition_fu, description):
        self.log = log
        self.description = description
        self.condition_fu = condition_fu

    def __call__(self, memory, bytemode, writing, address):
        if self.condition_fu(memory, writing, address):
            self.log.write('WATCHx: @0x%04x: %s %s\n' % (
                address, bytemode and 'b' or 'w', self.description
            ))

##################################################################
## CPU registers
##################################################################

class Register(Subject):
    """generic register"""
    def __init__(self, core, reg=0, regnum=None, log=None):
        Subject.__init__(self)          #init model for observer pattern
        self.core = core
        self.reg = reg
        self.regnum = regnum
        self.log = log

    def set(self, value, bytemode=0, am=0):
        """write value to register"""
        if self.log: self.log.write('REGSTR: write    0x%04x -> R%02d mode:%s\n' % (value, self.regnum, bytemode and 'b' or 'w'))
        self.reg = value & (bytemode and 0xff or 0xffff)
        self.notify()

    def get(self, bytemode=0, am=0):
        """read register"""
        value = self.reg & (bytemode and 0xff or 0xffff)
        if self.log: self.log.write('REGSTR: read     R%02d -> 0x%04x mode:%s\n' % (self.regnum, value, bytemode and 'b' or 'w'))
        return value
    
    def __getitem__(self,index):
        """indexed memory access"""
        return self.core.memory.get(bytemode=0, address=self.reg+index)

    def __int__(self):
        """return value of register as number"""
        return self.reg

    def __repr__(self):
        """return register name and contents"""
        return "R%02d = 0x%04x" % (self.regnum, self.reg)

    def __str__(self):
        """return register name"""
        return "R%02d" % (self.regnum)

#programm counter
class PC(Register):
    """Program counter"""
    def next(self):
        value = self.core.memory.get(bytemode=0, address=self.reg)
        self.set( self.get() + 2)
        if self.log: self.log.write('REGSTR: next @PC, PC+\n')
        return value

    def __repr__(self):
        """return register name and contents"""
        return "PC  = 0x%04x" % (self.reg)

    def __str__(self):
        return "PC"


class SP(Register):
    """Stack pointer"""
    def push(self,value):
        self.reg -= 2
        if self.log: self.log.write('REGSTR: push @-SP,      0x%04x\n' % (value))
        self.core.memory.set(bytemode=0, address=self.reg, value=value)
        self.notify()
    
    def pop(self):
        value = self.core.memory.get(bytemode=0, address=self.reg)
        self.reg += 2
        if self.log: self.log.write('REGSTR: pop  @SP+       0x%04x\n' % (value))
        self.notify()
        return value

    def __repr__(self):
        """return register name and contents"""
        return "SP  = 0x%04x" % (self.reg)
    
    def __str__(self):
        return "SP"

#status register/CG1
class SR(Register):
    """SR combined with Constant Generator Register 1"""
    consts = (None,None,4,8)

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
            return (self.reg & mask) != 0
        else:
            return self.__dict__[name]

    def __setattr__(self, name, value):
        if self.bits.has_key(name):
            mask = self.bits[name]
            if value:
                self.reg  |= mask
            else:
                self.reg  &= ~mask
            self.notify()
        else:
            self.__dict__[name] = value

    #custom get for CG1
    def get(self, bytemode=0, am=0):
        if am == 0: return self.reg & (bytemode and 0xff or 0xffff)
        value = self.consts[am] & (bytemode and 0xff or 0xffff)
        if self.log: self.log.write('REGSTR: read     R%02d -> 0x%04x mode:%s\n' % (self.regnum, value, bytemode and 'b' or 'w'))
        return value

    def __repr__(self):
        """return register name and contents"""
        res = "SR  = 0x%04x " % (self.reg)
        #then append deatiled bit display
        for key in ('C', 'Z', 'N', 'V', 'GIE'):
            res += '%s:%s ' % (key, (self.reg & self.bits[key]) and '1' or '0')
        return res

    def __str__(self):
        return "SR"


class CG2(Register):
    """Constant Generator Register 2"""
    consts = (0,1,2,0xffff)

    def get(self, bytemode=0, am=0):
        value = self.consts[am] & (bytemode and 0xff or 0xffff)
        if self.log: self.log.write('REGSTR: read     R%02d -> 0x%04x mode:%s\n' % (self.regnum, value, bytemode and 'b' or 'w'))
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
    def __init__(self, log):
        self.log = log
        self.reset()        #init device

    def __contains__(self, address):
        """return true if address is handled by this peripheral"""
        raise NotImplementedError

    def reset(self):
        """perform a power up reset"""
        raise NotImplementedError

    def set(self, address, value, bytemode=0):
        """read from address"""
        raise NotImplementedError

    def get(self, address, bytemode=0):
        """write value to address"""
        raise NotImplementedError

class Flash(Peripheral):
    """flash memory"""
    color = (0xff, 0xaa, 0x88)      #color for graphical representation

    def __init__(self, log, startaddress = 0xf000, endaddress = 0xffff):
        self.startaddress = startaddress
        self.endaddress = endaddress
        Peripheral.__init__(self, log)
    
    def __contains__(self, address):
        """return true if address is handled by this peripheral"""
        return self.startaddress <= address <= self.endaddress

    def reset(self):
        """perform a power up reset"""
        self.values = [0] * (self.endaddress - self.startaddress + 1)

    def set(self, address, value, bytemode=0):
        """read from address"""
        if bytemode:
            self.values[address-self.startaddress] = value & 0xff
        else:
            self.values[address-self.startaddress  ] =  value     & 0xff
            self.values[address-self.startaddress+1] = (value>>8) & 0xff

    def get(self, address, bytemode=0):
        """write value to address"""
        if bytemode:
            value = self.values[address-self.startaddress]
        else:
            value = (self.values[address-self.startaddress+1]<<8) |\
                     self.values[address-self.startaddress]
        return value

class RAM(Peripheral):
    """flash memory"""
    color = (0xaa, 0xff, 0x88)      #color for graphical representation

    def __init__(self, log, startaddress = 0x0200, endaddress = 0x02ff):
        self.startaddress = startaddress
        self.endaddress = endaddress
        Peripheral.__init__(self, log)
    
    def __contains__(self, address):
        """return true if address is handled by this peripheral"""
        return self.startaddress <= address <= self.endaddress

    def reset(self):
        """perform a power up reset"""
        self.values = [0] * (self.endaddress - self.startaddress + 1)

    def set(self, address, value, bytemode=0):
        """read from address"""
        if bytemode:
            self.values[address-self.startaddress] = value & 0xff
        else:
            self.values[address-self.startaddress  ] =  value     & 0xff
            self.values[address-self.startaddress+1] = (value>>8) & 0xff

    def get(self, address, bytemode=0):
        """write value to address"""
        if bytemode:
            value = self.values[address-self.startaddress]
        else:
            value = (self.values[address-self.startaddress+1]<<8) |\
                     self.values[address-self.startaddress]
        return value

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
        """read from address"""
        if not bytemode and self.log:
            self.log.write('PERIPH: Access Error - expected byte but got word access\n')
        self.values[address] = value & 0xff

    def get(self, address, bytemode=0):
        """write value to address"""
        if not bytemode and self.log:
            self.log.write('PERIPH: Access Error - expected byte but got word access\n')
        return self.values[address]

class Memory(Subject):
#    color = (0xaa, 0xaa, 0xaa)      #color for graphical representation
    color = (0xff, 0xff, 0xff)      #color for graphical representation
    def __init__(self, log=None):
        Subject.__init__(self)          #init model for observer pattern
        self.log = log
        self.setwatches = {}        #serached on reads
        self.getwatches = {}        #serached on writes
        self.accesswatches = []     #searched allways
        self.clear()                #init memory
        self.peripherals = []

    def append(self, peripheral):
        self.peripherals.append(peripheral)

    def __getitem__(self, address):
        for p in self.peripherals:
            if address in p:
                return p
        return self

    def reset(self):
        """perform a power up reset"""
        for p in self.peripherals: p.reset()
        self.clear()
        self.notify()

    def clear(self):
        self.memory = [0]*65536
        self.notify()

    def load(self, filename):
        """load ihex file into memory"""
        if self.log: self.log.write('MEMORY: loading file %s\n' % filename)
        for l in open(filename).readlines():
            if l[0] != ':':
                raise "file format error"
            count    = int(l[1:3],16)
            address  = int(l[3:7],16)
            code     = int(l[7:9],16)
            checksum = int(l[-2:],16)
            #print l[11:].strip()
            for i in range(count):
                value = int(l[9+i*2:11+i*2],16)
                #print "%04x: %02x" % (address+i,value)
                self._set(address+i, value, bytemode=1)
        self.notify()

    def _set(self, address, value, bytemode=0):
        """quiet set without logging"""
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
        """read from address"""
        if self.log: self.log.write('MEMORY: write 0x%04x <- 0x%04x mode:%s\n' % (address, value, bytemode and 'b' or 'w'))
        if self.setwatches.has_key(address): self.setwatches[address](address, bytemode, self.memory[address], value)  #call watch
        for a in self.accesswatches: a(self, bytemode, 1, address)
        self._set(address, value, bytemode)
        self.notify(address, bytemode)

    def _get(self, address, bytemode=0):
        """quiet get without logging"""
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
        """write value to address"""
        if self.getwatches.has_key(address): self.getwatches[address](address, bytemode, self.memory[address], None)  #call watch
        for a in self.accesswatches: a(self, bytemode, 0, address)
        value = self._get(address, bytemode)
        if self.log: self.log.write('MEMORY: read  0x%04x -> 0x%04x mode:%s\n' % (address, value, bytemode and 'b' or 'w'))
        return value

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
        line += '\n'
        return res

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
        raise "not possible as destination"

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
        raise "not possible as destination"

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
        return '0x%04x' % (self.address+self.offset)

##################################################################
## argument conversion
##################################################################
# take arguments from core for insn and return wrappers
#(wrapper factory)

def addressMode(core, pc, bytemode, as = None, ad = None, src = None, dest = None):
    """return two arguments wrappers and a cycle count for the use of both"""
    x = y = None
    c = 0
    #source first
    if as is not None:  #CG2
        if src == 2 and as > 1:
            x = RegisterArgument(core,reg=core.R[src], bytemode=bytemode, am=as)
            #m = "#%d" % (None,None,4,8)[as]
        elif src == 3:  #CG3
            x = RegisterArgument(core,reg=core.R[src], bytemode=bytemode, am=as)
            #m = "#%d" % (0,1,2,0xffff)[as]
        else:
            if   as == 0:   #register mode
                #m = '%(srcname)s'
                x = RegisterArgument(core,reg=core.R[src], bytemode=bytemode, am=as)
            elif as == 1:   #pc rel
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
            elif as == 2:   #indirect
                #m = '@%(srcname)s'
                x = IndirectRegisterArgument(core, reg=core.R[src], bytemode=bytemode)
                c += 1  #target mem read
            elif as == 3:
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
            raise "illegal insn"
        a = arg.get()
        r = ((a & 0xff00) >> 8) | ((a & 0x00ff) << 8)
        arg.set(r)

    def execRRA(self, bytemode, arg):
        shift = bytemode and 7 or 15
        mask = bytemode and 0x7f or 0x7fff
        
        a = arg.get()
        n = a & (bytemode and 0x80 or 0x8000)
        r = (n<<shift) | ((a>>1) & mask)
        self.SR.Z = (r == 0)
        self.SR.N = r & (bytemode and 0x80 or 0x8000)
        self.SR.C = (a & 1)
        self.SR.V = 0
        arg.set(r)

    def execSXT(self, bytemode, arg):
        if bytemode: raise "illegal use of SXT" #should actualy never happen
        a = arg.get()
        sign = not not (a & 0x80)
        r = a
        for i in range(8,15):
            r |= sign << i
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
        d = dst.get()
        s = src.get()
        if takecarry:
            c = self.SR.C
        else:
            c = 1
        r = d + ((~s) & (bytemode and 0xff or 0xffff)) + c
        self.SR.Z = r & (bytemode and 0xff or 0xffff) == 0
        self.SR.N = r & (bytemode and 0x80 or 0x8000)
        self.SR.C = r < 0 or r > (bytemode and 0xff or 0xffff)
        self.SR.V = (not (r & b) and not (s & b) and (d & b)) or ((r & b) and (s & b) and not (d & b))
        if store: dst.set(r)

    def execDADD(self, bytemode, src, dst):
        raise "instruction not supported in this version of simu"

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
            self.PC.set(self.PC.get() + int(offset))

    def execJZ(self, bytemode, offset):
        if self.SR.Z:
            self.PC.set(self.PC.get() + int(offset))

    def execJC(self, bytemode, offset):
        if self.SR.C:
            self.PC.set(self.PC.get() + int(offset))

    def execJNC(self, bytemode, offset):
        if not self.SR.C:
            self.PC.set(self.PC.get() + int(offset))

    def execJN(self, bytemode, offset):
        if not self.SR.Z:
            self.PC.set(self.PC.get() + int(offset))
    
    def execJGE(self, bytemode, offset):
        if not (self.SR.N ^ self.SR.V):
            self.PC.set(self.PC.get() + int(offset))

    def execJL(self, bytemode, offset):
        if self.SR.N ^ self.SR.V:
            self.PC.set(self.PC.get() + int(offset))

    def execJMP(self, bytemode, offset):
        self.PC.set(self.PC.get() + int(offset))

    #------------------------
    # instruction tables
    #------------------------

    singleOperandInstructions = {
        0x00: ('rrc',  execRRC,  0),
        0x01: ('swpb', execSWPB, 0),
        0x02: ('rra',  execRRA,  0),
        0x03: ('sxt',  execSXT,  0),
        0x04: ('push', execPUSH, 2),    #write of stack -> 2
        0x05: ('call', execCALL, 3),    #write of stack -> 2, modify PC -> 1
        0x06: ('reti', execRETI, 4),    #pop SR -> 1, pop PC -> 1, modify PC -> 1,  +1??
    }

    doubleOperandInstructions = {
        0x4: ('mov',  execMOV,  0),
        0x5: ('add',  execADD,  0),
        0x6: ('addc', execADDC, 0),
        0x7: ('subc', execSUBC, 0),
        0x8: ('sub',  execSUB,  0),
        0x9: ('cmp',  execCMP,  0),
        0xa: ('dadd', execDADD, 0),
        0xb: ('bit',  execBIT,  0),
        0xc: ('bic',  execBIC,  0),
        0xd: ('bis',  execBIS,  0),
        0xe: ('xor',  execXOR,  0),
        0xf: ('and',  execAND,  0),
    }

    jumpInstructions = {
        0x0: ('jnz',  execJNZ,  1), #jne
        0x1: ('jz',   execJZ,   1), #jeq
        0x2: ('jnc',  execJNC,  1),
        0x3: ('jc',   execJC,   1),
        0x4: ('jn',   execJN,   1),
        0x5: ('jge',  execJGE,  1),
        0x6: ('jl',   execJL,   1),
        0x7: ('jmp',  execJMP,  1),
    }

    #------------------------
    # methods
    #------------------------

    def __init__(self, log=None):
        """initialize core with registers and memory"""
        Subject.__init__(self)          #init model for observer pattern
        self.log = log
        self.memory = Memory(log)
        self.R = (
            PC(self, regnum=0, log=log),
            SP(self, regnum=1, log=log),
            SR(self, regnum=2, log=log),
            CG2(self, regnum=3, log=log),
            Register(self, regnum=4, log=log),
            Register(self, regnum=5, log=log),
            Register(self, regnum=6, log=log),
            Register(self, regnum=7, log=log),
            Register(self, regnum=8, log=log),
            Register(self, regnum=9, log=log),
            Register(self, regnum=10, log=log),
            Register(self, regnum=11, log=log),
            Register(self, regnum=12, log=log),
            Register(self, regnum=13, log=log),
            Register(self, regnum=14, log=log),
            Register(self, regnum=15, log=log)
        )
        #alisses
        self.PC = self.R[0]
        self.SP = self.R[1]
        self.SR = self.R[2]
        self.CG2 = self.R[3]
        self.cycles = 0

    def clear(self):
        for r in self.R:
            r.set(0)
        self.memory.clear()
        self.notify()

    def disassemble(self, pc):
        """disasseble current PC location and advance PC to the next instruction.
        return a tuple with insn name, arguments (bytemode, arg1, arg2),
        core execution function for that insn and a cycle count.
        
        the programm counter PC is used and modified."""
        
        opcode = pc.next()
        cycles = 1              #count cycles, start with insn fetch
        x = y = None
        #single operand
        if ((opcode & 0xf000) == 0x1000 and
                ((opcode>>7)&0x1f in self.singleOperandInstructions.keys())
        ):
            bytemode = (opcode>>6) & 1
            x,y,c = addressMode(self, pc, bytemode,
                as=(opcode>>4) & 3,
                src=opcode & 0xf
                )
            name, fu, addcyles = self.singleOperandInstructions[(opcode>>7) & 0x1f]
            cycles += c + addcyles #some functions have additional cycles (push etc)
            return name, [bytemode, x], fu, cycles

        #double operand
        elif (opcode>>12)&0xf in self.doubleOperandInstructions.keys():
            bytemode = (opcode>>6) & 1
            x,y,c = addressMode(self, pc, bytemode,
                src=(opcode>>8) & 0xf,
                ad=(opcode>>7) & 1,
                as=(opcode>>4) & 3,
                dest=opcode & 0xf
                )
            name, fu, addcyles = self.doubleOperandInstructions[(opcode>>12) & 0xf]
            cycles += c + addcyles #some functions have additional cycles (push etc)
            return name, [bytemode, x, y], fu, cycles

        #jump instructions
        elif ((opcode & 0xe000) == 0x2000 and
             ((opcode>>10)&0x7 in self.jumpInstructions.keys())
        ):
            name, fu, addcyles = self.jumpInstructions[(opcode>>10) & 0x7]
            offset = ((opcode&0x3ff)<<1)
            if offset & 0x400:  #negative?
                offset = -((~offset + 1) & 0x7ff)
            cycles += addcyles #jumps allways have 2 cycles
            return name, [0, JumpTarget(self, int(pc), offset)], fu, cycles

        #unkown instruction
        else:
            return 'illegal insn 0x%04x' % opcode, [0], None, cycles

    def step(self):
        """perform one single step"""
        address = int(self.PC)
        name, args, execfu, cycles = self.disassemble(self.PC)
        self.cycles += cycles
        note = "%s%s %s (%d cycles)" % (
            name,
            ('','.b')[args[0]],
            ', '.join(map(str,args[1:])),
            cycles
        )
        self.log.write('#CORE#: %s\n' % (note))
        if execfu:
            apply(execfu, [self]+args)
        else:
            self.log.write("Illegal instruction 0x%04x @%r" % (opcode, address))
        self.notify()
        return note

    def __repr__(self):
        return ('%r\n'*16) % self.R

##################################################################
## trace control object
##################################################################

class Tracer:
    def __init__(self, core, log):
        self.core = core
        self.log = log

    def start(self, startadr, maxsteps=100):
        self.log.write( 'TRACER: set startaddress\n')
        self.core.PC.set(startadr)
        self.log.write( 'TRACER: *** starting trace (maxsteps=%d)\n' % (maxsteps))
        step = 1
        while step <= maxsteps:
            self.core.step()
            self.log.write( 'TRACER: (step %d, cycle %d)\n%r\n' % (
                step, self.core.cycles, self.core))
            step += 1

##################################################################
## logging facility
##################################################################

class Logger:
    """Logging class with file like interface"""
    def __init__(self, filename=None, enabled=1):
        if filename is None:
            self.file = sys.stdout
        else:
            self.file = open(filename, 'w')
        self.enabled = enabled

    def write(self, s):
        if self.enabled: self.file.write(s)

##################################################################
## testing
##################################################################

if __name__ == '__main__':
    log = Logger('log.trace')
    
    core = Core(log)
    core.SR.Z = 243
    print core.SR.Z
    print repr(core.SR)

    core.memory.load('tests.a43')
    log.enabled = 0

    print "-"*40, "memory dump"
    print '\n'.join(core.memory.hexdump(0xF000, 0xF086))

    print "-"*40, "disassemble"
    pc = PC(core, 0xf000) #, 0xf71f
    while pc.get() < 0xF086:
        print "0x%04x:" % pc, core.disassemble(pc)

##    print "-"*40, "single step"
##    core.PC.set(0xf000)
##    while int(core.PC) < 0xF086:
##        print core.step()
##        print repr(core)

    print "-"*40, "trace"
    core.memory.getwatches[0x200] = AddressWatch(log, "Variable one READ")
    core.memory.setwatches[0x200] = AddressWatch(log, "Variable one WRITE")
    core.memory.accesswatches.append(MemoryAccessWatch(
        log,
        lambda mem, wrt, adr: not(          #F1121 layout
            0x0000 <= adr <= 0x01ff or      #Peripherals (not detailed)
            0x0200 <= adr <= 0x02ff or      #RAM
            0x1000 <= adr <= 0x10ff or      #INFOMEM
            0xf000 <= adr <= 0xffff         #FLASH
        ),
        'Illegal memory access',
    ))
    core.memory.accesswatches.append(MemoryAccessWatch(
        log,
        lambda mem, wrt, adr: wrt and(      #F1121 layout
            0x1000 <= adr <= 0x10ff or      #INFOMEM
            0xf000 <= adr <= 0xffff         #FLASH
        ),
        'flash memory written',
    ))
    log.enabled = 1
    core.memory.hexdump(0x0200, 0x02ff, log)
    tracer = Tracer(core, log)
    tracer.start(0xf000,43) #only N steps
    core.memory.hexdump(0x0200, 0x02ff, log)





