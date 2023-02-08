from pyfive import bus
import numpy as np
import types

consts = types.SimpleNamespace()

# Machine-level CSRs.
# Hardware thread ID.
consts.MHARTID = 0xf14
# Machine status register.
consts.MSTATUS = 0x300
# Machine exception delefation register.
consts.MEDELEG = 0x302
# Machine interrupt delefation register.
consts.MIDELEG = 0x303
# Machine interrupt-enable register.
consts.MIE = 0x304
# Machine trap-handler base address.
consts.MTVEC = 0x305
# Machine counter enable.
consts.MCOUNTEREN = 0x306
# Scratch register for machine trap handlers.
consts.MSCRATCH = 0x340
# Machine exception program counter.
consts.MEPC = 0x341
# Machine trap cause.
consts.MCAUSE = 0x342
# Machine bad address or instruction.
consts.MTVAL = 0x343
# Machine interrupt pending.
consts.MIP = 0x344

# Supervisor-level CSRs.
# Supervisor status register.
consts.SSTATUS = 0x100
# Supervisor interrupt-enable register.
consts.SIE = 0x104
# Supervisor trap handler base address.
consts.STVEC = 0x105
# Scratch register for supervisor trap handlers.
consts.SSCRATCH = 0x140
# Supervisor exception program counter.
consts.SEPC = 0x141
# Supervisor trap cause.
consts.SCAUSE = 0x142
# Supervisor bad address or instruction.
consts.STVAL = 0x143
# Supervisor interrupt pending.
consts.SIP = 0x144
# Supervisor address translation and protection.
consts.SATP = 0x180

class XRegisters():
    def __init__(self):
        self.xregs = [np.uint64(0)] * 32
        self._xnames = [
            "zero", "ra", "sp", "gp", "tp", "t0", "t1", "t2",
            "s0", "s1", "a0", "a1", "a2", "a3", "a4", "a5",
            "a6", "a7", "s2", "s3", "s4", "s5", "s6", "s7",
            "s8", "s9", "s10", "s11", "t3", "t4", "t5", "t6"
        ]
        
        # sp
        self.xregs[2] = np.uint64(bus.DRAM_BASE + bus.DRAM_SIZE)

        # save a0 and a1; arguments from previous boot loader stage
        # li x10, 0
        # li x11, 0

        # self.xregs[10] = 0
        # self.xregs[11] = POINTER_TO_DTB

    def read(self, index: int) -> np.uint64:
        if index >= 0 and index < 32:
            return self.xregs[index]
        else:
            return None

    def write(self, index: int, value: np.uint64):
        if not isinstance(value, np.uint64):
            raise("register value type must be uint64")
        if index > 0 and index < 32:
            self.xregs[index] = value

    def dump(self):
        for i in range(len(self.xregs)):
            print(self._xnames[i] + "[x{}]\t{}\t({});".format(i, self.xregs[i], hex(self.xregs[i])))
            
class CSRegisters():
    def __init__(self):
        self.csrs = [np.uint64(0)] * 4096

    def read(self, index: int) -> np.uint64:
        match index:
            case consts.SIE:
                return self.csrs[consts.MIE] & self.csrs[consts.MIDELEG]
            case other:
                return self.csrs[index]

    def write(self, index: int, value: np.uint64):
        match index:
            case consts.SIE:
                self.csrs[consts.MIE] = (self.csrs[consts.MIE] & ~self.csrs[consts.MIDELEG]) |\
                                 (value & self.csrs[consts.MIDELEG])
            case other:
                self.csrs[index] = value

    def dump(self):
        mregs = "mstatus\t{}\t{}\nmtvec\t{}\t{}\nmepc\t{}\t{}\nmcause\t{}\t{}".format(
            self.read(consts.MSTATUS), hex(self.read(consts.MSTATUS)),
            self.read(consts.MTVEC), hex(self.read(consts.MTVEC)),
            self.read(consts.MEPC), hex(self.read(consts.MEPC)),
            self.read(consts.MCAUSE), hex(self.read(consts.MCAUSE)))
        print(mregs)
        sregs = "sstatus\t{}\t{}\nstvec\t{}\t{}\nsepc\t{}\t{}\nscause\t{}\t{}".format(
            self.read(consts.SSTATUS), hex(self.read(consts.SSTATUS)),
            self.read(consts.STVEC), hex(self.read(consts.STVEC)),
            self.read(consts.SEPC), hex(self.read(consts.SEPC)),
            self.read(consts.SCAUSE), hex(self.read(consts.SCAUSE)))
        print(sregs)


class Cpu():

    def __init__(self):
        self.xreg = XRegisters()
        self.pc = np.uint64(bus.DRAM_BASE)
        self.bus = bus.Bus()
        self.csrs = CSRegisters()
        
    def fetch(self):
        addr = self.pc
        arr = self.bus.load(int(addr), 4)
        if len(arr) != 4:
            raise("inst fetch overflow!")
        return arr[0] | arr[1] << 8 | arr[2] << 16 | arr[3] << 24

    def loadint(self, addr, size):
        arr = self.bus.load(int(addr), size)
        # print("loadint", hex(addr) ,size, len(arr), arr)
        if len(arr) < size:
            raise('Loadint failed!, segmentfault')
        val = int.from_bytes(arr, byteorder='little', signed=True)
        return np.uint64(val)

    # def sext(self, val, size, bits):
    #     getbinary = lambda x, n: format(x, 'b').zfill(n)
    #     val_bit = getbinary(val, size)
    #     val_bit = val_bit[0] * (bits - size) + val_bit
    #     return int(val_bit)

    def loaduint(self, addr, size):
        arr = self.bus.load(nt(addr), size)
        val = 0
        for i in range(size):
            val = val | (arr[i] << (8 * i))
        return np.uint64(val)

    def execute(self, inst):
        opcode = inst & 0x7f
        rd = (inst >> 7) & 0x1f
        rs1 = (inst >> 15) & 0x1f
        rs2 = (inst >> 20) & 0x1f
        funct3 = (inst >> 12) & 0x7;
        funct7 = (inst >> 25) & 0x7f;

        match opcode:
            case 0x03:  # load
                imm = np.uint64((np.int32(inst) >> 20))
                # print("loadinst imm ", hex(imm))
                # print("loadinst base ", hex(self.xreg.read(rs1)))
                # print('load inst rs1 ', rs1)
                addr = int(self.xreg.read(rs1) + imm)
                # print('load inst addr  ', hex(addr))
                val = np.uint64(0)
                match funct3:
                    case 0x0:
                        # lb, load byte
                        # x[rd] = sext(M[x[rs1] + sext(offset)][7:0])
                        val = self.loadint(addr, 1)
                    case 0x1:
                        # lh, load half word
                        val = self.loadint(addr, 2)
                    case 0x2:
                        # lw, load word
                        val = self.loadint(addr, 4)
                        print("load word ", val)
                    case 0x3:
                        # ld, load double word
                        val = self.loadint(addr, 8)
                    case 0x4:
                        # lbu, load byte unsigned
                        val = self.loaduint(addr, 1)
                    case 0x5:
                        # lhu
                        val = self.loaduint(addr, 2)
                    case 0x6:
                        # lwu
                        val = self.loaduint(addr, 4)
                    case other:
                        print("UnSupported load inst: {}, funct3({}) is unknown!".format(hex(inst), hex(funct3)))
                        return False
                self.xreg.write(rd, val)
            case 0x13:
                imm = np.uint64(np.int32(inst&0xfff00000)>>20)
                shamt = (imm & np.uint64(0x3f))
                value = 0
                match funct3:
                    case 0x0:
                        # addi
                        value = np.uint64(np.uint64(self.xreg.read(rs1)) + imm)
                        print('addi immis value ',hex(imm), hex(value))
                    case 0x1:
                        # slli
                        value = self.xreg.read(rs1) << shamt
                    case 0x2:
                        # slti
                        value = 1 if np.int64(self.xreg.read(rs1)) < np.int64(imm) else 0
                    case 0x3:
                        # sltiu
                        value = 1 if self.xreg.read(rs1) < imm else 0
                    case 0x4:
                        # xori
                        value = self.xreg.read(rs1) ^ imm
                    case 0x5:
                        match funct7 >> 1:
                            case 0x00:
                                value = self.xreg.read(rs1) >> shamt
                            case 0x10:
                                value = self.xreg.read(rs1).astype('int64') >> shamt
                            case other:
                                print("Unsupport inst", hex(inst))
                                return False
                    case 0x6:
                        value = self.xreg.read(rs1) | imm
                    case 0x7:
                        value = self.xreg.read(rs1) & imm
                    case other:
                        print("Unsupport inst", hex(inst))
                        return False
                self.xreg.write(rd, np.uint64(value))
            case 0x17:  # auipc
                print("auipc*************************")
                imm = np.uint64(np.int32(inst & 0xfffff000))
                self.xreg.write(rd, self.pc + imm - np.uint64(4))
            case 0x1b:
                imm = np.uint64(np.int32(inst&0xfffff000) >> 20)
                shamt = imm & np.uint64(0x1f)
                value = np.uint64(0)
                match funct3:
                    case 0x0:
                        # addiw
                        value = (self.xreg.read(rs1) + imm).astype('int32')
                    case 0x1:
                        # slliw
                        value = (self.xreg.read(rs1) << shamt).astype('int32')
                    case 0x5:
                        match funct7:
                            case 0x00:
                                value = (self.xreg.read(rs1).astype('uint32')) >> shamt
                            case 0x20:
                                value = (self.xreg.read(rs1).astype('int32')) >> shamt
                            case other:
                                print("Unsupport inst", hex(inst))
                                return False
                    case other:
                        print("Unsupport inst", hex(inst))
                        return False
                self.xreg.write(rd, np.uint64(value))
            case 0x23:  # store
                imm = np.uint64((np.int32(inst & 0xfe000000) >> 20)) |\
                      np.uint64(((inst >> 7) & 0x1f))
                print("imm", np.int64(imm))
                addr = int(np.uint64(self.xreg.read(rs1)) + imm)
                print("addr", hex(addr))
                value = int(self.xreg.read(rs2))
                # print(hex(value))
                vbytes = value.to_bytes(8, byteorder='little', signed='True')
                match funct3:
                    case 0x0:
                        self.bus.store(addr, 1, vbytes[0:1])
                    case 0x1:
                        self.bus.store(addr, 2, vbytes[0:2])
                    case 0x2:
                        self.bus.store(addr, 4, vbytes[0:4])
                    case 0x3:
                        self.bus.store(addr, 8, vbytes[0:8])
                    case other:
                        return False
            case 0x33:  # add
                shamt = (self.xreg.read(rs2) & np.uint64(0x3f)).astype('uint32')
                value = 0
                match (funct3, funct7):
                    case (0x0, 0x00):
                        value = self.xreg.read(rs1) + self.xreg.read(rs2)
                    case (0x0, 0x01):
                        value = self.xreg.read(rs1) * self.xreg.read(rs2)
                    case (0x0, 0x20):
                        value = self.xreg.read(rs1) - self.xreg.read(rs2)
                    case (0x1, 0x00):
                        value = self.xreg.read(rs1) << shamt
                    case (0x2, 0x00):
                        cond = np.int64(self.xreg.read(rs1)) < np.int64(self.xreg.read(rs2))
                        value = 1 if cond else 0
                    case (0x3, 0x00):
                        cond = self.xreg.read(rs1) < self.xreg.read(rs2)
                        value = 1 if cond else 0
                    case (0x4, 0x00):
                        value = self.xreg.read(rs1) ^ self.xreg.read(rs2)
                    case (0x5, 0x00):
                        value = self.xreg.read(rs1) << shamt
                    case (0x5, 0x20):
                        value = np.int64(self.xreg.read(rs1)) << shamt
                    case (0x6, 0x00):
                        value = self.xreg.read(rs1) | self.xreg.read(rs2)
                    case (0x7, 0x00):
                        value = self.xreg.read(rs1) & self.xreg.read(rs2)
                    case other:
                        return False
                self.xreg.write(rd, np.uint64(value))
            case 0x37:
                value = np.uint64(np.int32(inst & 0xfffff000))
                self.xreg.write(rd, value)
            case 0x3b:
                shamt = np.uint32(self.xreg.read(rs2) & np.uint64(0x1f))
                value = 0
                print("word inst ...................")
                match (funct3, funct7):
                    case (0x0, 0x00):
                        # addw
                        value = np.int32(self.xreg.read(rs1) +  self.xreg.read(rs2))
                        print('addw ', value)
                    case (0x0, 0x20):
                        # subw
                        value = np.int32(self.xreg.read(rs1) -  self.xreg.read(rs2))
                    case (0x1, 0x00):
                        # sllw
                        value = np.uint32(self.xreg.read(rs1)) << shamt
                    case (0x5, 0x00):
                        # srlw
                        value = np.uint32(self.xreg.read(rs1)) >> shamt
                    case (0x5, 0x20):
                        # sraw
                        value = np.int32(self.xreg.read(rs1)) >> shamt
                    case other:
                        return False
                self.xreg.write(rd, np.uint64(value))
            case 0x63:
                imm = (np.int32(inst & 0x80000000) >> 19).astype('uint64') |\
                      np.uint64(((inst & 0x80) << 4)) |\
                      np.uint64(((inst >> 20) & 0x7e0)) |\
                      np.uint64(((inst >> 7) & 0x1e))
                cond = False
                match funct3:
                    case 0x0:
                        # beq
                        cond = self.xreg.read(rs1) == self.xreg.read(rs2)
                    case 0x1:
                        # bne
                        cond = self.xreg.read(rs1) != self.xreg.read(rs2)
                    case 0x4:
                        # blt
                        cond = self.xreg.read(rs1).astype('int64') < self.xreg.read(rs2).astype('int64')
                    case 0x5:
                        # bge
                        cond = self.xreg.read(rs1).astype('int64') >= self.xreg.read(rs2).astype('int64')
                    case 0x6:
                        # bltu
                        cond = self.xreg.read(rs1) < self.xreg.read(rs2)
                    case 0x7:
                        # bgeu
                        cond = self.xreg.read(rs1) >= self.xreg.read(rs2)
                    case other:
                        return False 
                if cond:
                    self.pc = np.uint64(self.pc + imm - 4)
            case 0x67:
                print("jalr inst******************************")
                self.xreg.write(rd, self.pc)
                imm = np.uint64(np.int32(inst & 0xfff00000) >> 20)
                self.pc = (np.uint64(self.xreg.read(rs1)) + imm) & np.uint64(~1)
            case 0x6f:
                print("jal inst******************************")
                self.xreg.write(rd, self.pc)
                imm = np.uint64(np.int32(inst&0x80000000)>>11) |\
                      np.uint64((inst & 0xff000)) |\
                      np.uint64(((inst >> 9) & 0x800)) |\
                      np.uint64(((inst >> 20) & 0x7fe))
                self.pc = np.uint64(self.pc) + np.uint64(imm) - np.uint64(4)
            case 0x73:
                csr_addr = int((inst & 0xfff00000) >> 20)
                match funct3:
                    case 0x1:  # csrrw
                        temp = self.csrs.read(csr_addr)
                        self.csrs.write(csr_addr, self.xreg.read(rs1))
                        self.xreg.write(rd, temp)
                    case 0x2:  # csrrs
                        temp = self.csrs.read(csr_addr)
                        self.csrs.write(csr_addr, temp | self.xreg.read(rs1))
                        self.xreg.write(rd, temp)
                    case 0x3:  # csrrc
                        temp = self.csrs.read(csr_addr)
                        self.csrs.write(csr_addr, temp & (~self.xreg.read(rs1)))
                        self.xreg.write(rd, temp)
                    case 0x5:  # csrrwi
                        imm = np.uint64(rs1)
                        self.xreg.write(rd, self.csrs.read(csr_addr))
                        self.csrs.write(csr_addr, imm)
                    case 0x6:  # csrrsi
                        imm = np.uint64(rs1)
                        temp = self.csrs.read(csr_addr)
                        self.csrs.write(csr_addr, imm | temp)
                        self.xreg.write(rd, temp)
                    case 0x7:  # csrrci
                        imm = np.uint64(rs1)
                        temp = self.csrs.read(csr_addr)
                        self.csrs.write(csr_addr, (~imm) &  temp)
                        self.xreg.write(rd, temp)
                    case other:
                        return False
            case other:
                print("UnSupported inst", hex(inst))
                return False
        return True
               

    def dump_regs(self):
        print("pc", hex(self.pc)) 
        self.xreg.dump()
        self.csrs.dump()

    def run(self):
        while True:
             if self.pc == 0:
                 print("stop with addr 0 inst")
                 self.dump_regs()
                 break
             inst = self.fetch()
             self.pc += np.uint64(4)
             print("pc", hex(self.pc))
             print("inst", hex(inst))
             ret = self.execute(inst)
             if not ret:
                 print("Stop with unknown inst")
                 self.dump_regs()
                 break

