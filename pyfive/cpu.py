from pyfive import bus

class XRegisters():
    def __init__(self):
        self._xregs = [0] * 32
        self._xnames = [
            "zero", "ra", "sp", "gp", "tp", "t0", "t1", "t2",
            "s0", "s1", "a0", "a1", "a2", "a3", "a4", "a5",
            "a6", "a7", "s2", "s3", "s4", "s5", "s6", "s7",
            "s8", "s9", "s10", "s11", "t3", "t4", "t5", "t6"
        ]
        
        # sp
        # self._xregs[2] = DRAM_BASE + DRAM_SIZE

        # save a0 and a1; arguments from previous boot loader stage
        # li x10, 0
        # li x11, 0

        # self._xregs[10] = 0
        # self._xregs[11] = POINTER_TO_DTB

    def read(self, index: int) -> int:
        if index >= 0 and index < 32:
            return self._xregs[index]
        else:
            pass            

    def write(self, index: int, value: int):
        if index > 0 and index < 32:
            self._xregs[index] = value
        else:
            pass

    def dump(self):
        for i in range(len(self._xregs)):
            print(self._xnames[i] + "[x{}] = {}({})".format(i, self._xregs[i], hex(self._xregs[i])))
            

class Cpu():

    def __init__(self):
        self._xreg = XRegisters()
        self._pc = 0
        self._bus = bus.Bus()
        
    def fetch(self):
        addr = self._pc
        arr = self._bus.read(addr, 4)
        return arr[0] | arr[1] << 8 | arr[2] << 16 | arr[3] << 24

    def execute(self, inst):
        opcode = inst & 0x7f
        rd = (inst >> 7) & 0x1f
        rs1 = (inst >> 15) & 0x1f
        rs2 = (inst >> 20) & 0x1f

        match opcode:
            case 0x13:  # addi
                imm = (inst&0xfff00000)>>20
                value = self._xreg.read(rs1) + imm
                self._xreg.write(rd, value)
            case 0x33: #add
                value = self._xreg.read(rs1) + self._xreg.read(rs2)
                self._xreg.write(rd, value)
            case other:
                print("UnSupported inst", hex(inst))
                return False

        return True
               

    def dump_regs(self):
        print("pc", hex(self._pc)) 
        self._xreg.dump()

    def run(self):
        while True:
             inst = self.fetch()
             self._pc += 4
             ret = self.execute(inst)
             if not ret:
                 print("Stop with unknown inst")
                 self.dump_regs()
                 break
