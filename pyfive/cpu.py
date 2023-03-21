from pyfive import bus
from pyfive import trap
import sys
import numpy as np
from enum import Enum
import logging

from pyfive import uart
from pyfive import virtio
from pyfive import plic


class MODE(Enum):
    USER = 0b00
    SUPERVISOR = 0b01
    MACHINE = 0b11

class ACCESSTYPE(Enum):
    INSTRUCTION = 0
    LOAD = 1
    STORE = 2

class CSR(Enum):
    # Machine-level CSRs.
    # Hardware thread ID.
    MHARTID = 0xf14
    # Machine status register.
    MSTATUS = 0x300
    # Machine exception delefation register.
    MEDELEG = 0x302
    # Machine interrupt delefation register.
    MIDELEG = 0x303
    # Machine interrupt-enable register.
    MIE = 0x304
    # Machine trap-handler base address.
    MTVEC = 0x305
    # Machine counter enable.
    MCOUNTEREN = 0x306
    # Scratch register for machine trap handlers.
    MSCRATCH = 0x340
    # Machine exception program counter.
    MEPC = 0x341
    # Machine trap cause.
    MCAUSE = 0x342
    # Machine bad address or instruction.
    MTVAL = 0x343
    # Machine interrupt pending.
    MIP = 0x344

    # Supervisor-level CSRs.
    # Supervisor status register.
    SSTATUS = 0x100
    # Supervisor interrupt-enable register.
    SIE = 0x104
    # Supervisor trap handler base address.
    STVEC = 0x105
    # Scratch register for supervisor trap handlers.
    SSCRATCH = 0x140
    # Supervisor exception program counter.
    SEPC = 0x141
    # Supervisor trap cause.
    SCAUSE = 0x142
    # Supervisor bad address or instruction.
    STVAL = 0x143
    # Supervisor interrupt pending.
    SIP = 0x144
    # Supervisor address translation and protection.
    SATP = 0x180


class MIP(Enum):
    SSIP = 1 << 1
    MSIP = 1 << 3
    STIP = 1 << 5
    MTIP = 1 << 7
    SEIP = 1 << 9
    MEIP = 1 << 11

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
            # print("register value type must be uint64")
            value = np.uint64(value)
        if index > 0 and index < 32:
            self.xregs[index] = value

    def dump(self):
        for i in range(len(self.xregs)):
            print(self._xnames[i] + "[x{}]\t{}\t({});".format(i, self.xregs[i], hex(self.xregs[i])))

class CSRegisters():
    def __init__(self):
        self.csrs = [np.uint64(0)] * 4096

    def read(self, index: int) -> np.uint64:
        if isinstance(index, CSR):
            index = int(index.value)
        match index:
            case CSR.SIE:
                return self.csrs[CSR.MIE] & self.csrs[CSR.MIDELEG]
            case other:
                return self.csrs[index]

    def write(self, index: int, value: np.uint64):
        if isinstance(index, CSR):
            index = int(index.value)
        if not isinstance(value, np.uint64):
            # print("register value type must be uint64")
            value = np.uint64(value)
        match index:
            case CSR.SIE.value:
                self.csrs[CSR.MIE.value] = (self.csrs[CSR.MIE.value] & ~self.csrs[CSR.MIDELEG.value]) |\
                                 (value & self.csrs[CSR.MIDELEG.value])
            case other:
                self.csrs[index] = value

    def dump(self):
        mregs = "mstatus\t{}\t{}\nmtvec\t{}\t{}\nmepc\t{}\t{}\nmcause\t{}\t{}".format(
            self.read(CSR.MSTATUS), hex(self.read(CSR.MSTATUS)),
            self.read(CSR.MTVEC), hex(self.read(CSR.MTVEC)),
            self.read(CSR.MEPC), hex(self.read(CSR.MEPC)),
            self.read(CSR.MCAUSE), hex(self.read(CSR.MCAUSE)))
        print(mregs)
        sregs = "sstatus\t{}\t{}\nstvec\t{}\t{}\nsepc\t{}\t{}\nscause\t{}\t{}".format(
            self.read(CSR.SSTATUS), hex(self.read(CSR.SSTATUS)),
            self.read(CSR.STVEC), hex(self.read(CSR.STVEC)),
            self.read(CSR.SEPC), hex(self.read(CSR.SEPC)),
            self.read(CSR.SCAUSE), hex(self.read(CSR.SCAUSE)))
        print(sregs)


class Cpu():

    def __init__(self, obus):
        self.xreg = XRegisters()
        self.pc = np.uint64(bus.DRAM_BASE)
        self.bus = obus
        self.csrs = CSRegisters()
        self.mode = MODE.MACHINE
        self.enable_paging = False
        self.page_table = 0

    def fetch(self):
        ppc = self.translate(self.pc, ACCESSTYPE.INSTRUCTION)
        if isinstance(ppc, trap.EXCEPTION):
            return ppc
        addr = ppc
        arr = self.bus.load(int(addr), 4)
        if isinstance(arr, trap.EXCEPTION):
            return trap.EXCEPTION.InstructionAccessFault
        return arr[0] | arr[1] << 8 | arr[2] << 16 | arr[3] << 24



    def load(self, addr, size):
        paddr = self.translate(addr, ACCESSTYPE.LOAD)
        return self.bus.load(paddr, size)

    def store(self, addr, size, data):
        paddr = self.translate(addr, ACCESSTYPE.STORE)
        return self.bus.store(paddr, size, data)

    def loadint(self, addr, size):
        arr = self.load(int(addr), size)
        if isinstance(arr, trap.EXCEPTION):
            return arr
        val = arr
        if isinstance(arr, bytes) or isinstance(arr, bytearray):
            if len(arr) < size:
                return trap.EXCEPTION.LoadAccessFault
            val = int.from_bytes(arr, byteorder='little', signed=False)
        return np.uint64(val)

    # def sext(self, val, size, bits):
    #     getbinary = lambda x, n: format(x, 'b').zfill(n)
    #     val_bit = getbinary(val, size)
    #     val_bit = val_bit[0] * (bits - size) + val_bit
    #     return int(val_bit)

    def loaduint(self, addr, size):
        arr = self.load(int(addr), size)
        if isinstance(arr, trap.EXCEPTION):
            return arr
        val = arr
        logging.debug(f"val is {val}")
        if isinstance(arr, bytes) or isinstance(arr, bytearray):
            if len(arr) < size:
                return trap.EXCEPTION.LoadAccessFault
            val = int.from_bytes(arr, byteorder='little', signed=True)
        return np.uint64(val)

    def update_paging(self, csr_addr):
        if csr_addr != CSR.SATP.value:
            return
        self.page_table = (self.csrs.read(CSR.SATP) & np.uint64((1 << 44) - 1)) * 4096
        mode = int(self.csrs.read(CSR.SATP)) >> 60
        if mode == 8:
            self.enable_paging = True
        else:
            self.enable_paging = False

    def translate(self, addr, access_type):
        if not self.enable_paging:
            return addr
        addr = int(addr)
        levels = 3
        vpn = [(addr >> 12) & 0x1ff,
               (addr >> 21) & 0x1ff,
               (addr >> 30) & 0x1ff]

        a = self.page_table
        i = levels - 1
        while True:
            pte = self.bus.loaduint(a+vpn[i]*8, 8)
            if isinstance(pte, trap.EXCEPTION):
                return pte
            pte = int(pte)
            logging.debug(f"read pte is {hex(pte)}")
            v = pte & 1
            r = (pte >> 1) & 1
            w = (pte >> 2) & 1
            x = (pte >> 3) & 1
            if v == 0 or (r == 0 and w == 0):
                match access_type:
                    case ACCESSTYPE.INSTRUCTION:
                        return trap.EXCEPTION.InstructionPageFault
                    case ACCESSTPYE.LOAD:
                        return trap.EXCEPTION.LoadPageFault
                    case ACCESSTYPE.STORE:
                        return trap.EXCEPTION.StoreAMOPAageFault
            if r == 1 or x == 1:
                break
            i = i - 1
            ppn = (pte >> 10) & 0x0fff_ffff_ffff
            a = ppn * 4096
            if i < 0:
                match access_type:
                    case ACCESSTYPE.INSTRUCTION:
                        return trap.EXCEPTION.InstructionPageFault
                    case ACCESSTPYE.LOAD:
                        return trap.EXCEPTION.LoadPageFault
                    case ACCESSTYPE.STORE:
                        return trap.EXCEPTION.StoreAMOPAageFault

        ppn = [(pte >> 10) & 0x1ff,
               (pte >> 19) & 0x1ff,
               (pte >> 28) & 0x03ff_ffff]

        offset = addr & 0xfff
        logging.debug(f"ppn   i offset {hex(ppn[i])}  {i}  {offset}")
        match i:
            case 0:
                ppn = (pte >> 10) & 0x0fff_ffff_ffff
                return (ppn << 12) | offset
            case 1:
                return ppn[2] << 30 | ppn[1] << 21 | vpn[0] << 12 | offset
            case 2:
                return ppn[2] << 30 | vpn[1] << 21 | vpn[0] << 12 | offset

    def execute(self, inst) -> bool | trap.EXCEPTION:
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
                        # print("load word ", val)
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
                        # print("UnSupported load inst: {}, funct3({}) is unknown!".format(hex(inst), hex(funct3)))
                        return trap.EXCEPTION.IllegalInstruction
                logging.info(f"wirte {val}")
                self.xreg.write(rd, val)
            case 0x13:
                imm = np.uint64(np.int32(inst&0xfff00000)>>20)
                shamt = (imm & np.uint64(0x3f))
                value = 0
                match funct3:
                    case 0x0:
                        # addi
                        value = np.uint64(self.xreg.read(rs1) + imm)
                        # print('addi immis value ',hex(imm), hex(value))
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
                                # print("Unsupport inst", hex(inst))
                                return trap.EXCEPTION.IllegalInstruction
                    case 0x6:
                        value = self.xreg.read(rs1) | imm
                    case 0x7:
                        value = self.xreg.read(rs1) & imm
                    case other:
                        print("Unsupport inst", hex(inst))
                        return trap.EXCEPTION.IllegalInstruction
                logging.info(f"wirte {value}")
                self.xreg.write(rd, np.uint64(value))
            case 0x17:  # auipc
                # print("auipc*************************")
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
                                return trap.EXCEPTION.IllegalInstruction
                    case other:
                        print("Unsupport inst", hex(inst))
                        return trap.EXCEPTION.IllegalInstruction
                logging.info(f"wirte {value}")
                self.xreg.write(rd, np.uint64(value))
            case 0x23:  # store
                imm = np.uint64((np.int32(inst & 0xfe000000) >> 20)) |\
                      np.uint64(((inst >> 7) & 0x1f))
                # print("imm", np.int64(imm))
                addr = int(np.uint64(self.xreg.read(rs1)) + imm)
                # print("addr", hex(addr))
                # print(rs2, self.xreg.read(rs2))
                # print(type(self.xreg.read(rs2)))
                value = np.uint64(self.xreg.read(rs2))
                # 8 is not ok
                vbytes = value.tobytes()
                match funct3:
                    case 0x0:
                        self.store(addr, 1, vbytes[0:1])
                    case 0x1:
                        self.store(addr, 2, vbytes[0:2])
                    case 0x2:
                        self.store(addr, 4, vbytes[0:4])
                    case 0x3:
                        self.store(addr, 8, vbytes[0:8])
                    case other:
                        return trap.EXCEPTION.IllegalInstruction
            case 0x2f:  # rv64a
                funct5 = (funct7 & 0b1111100) >> 2
                _aq = (funct7 & 0b0000010) >> 1
                _rl = funct7 & 0b0000001
                match (funct3, funct5):
                    case (0x2, 0x00):  # amoadd.w
                        t = self.loadint(self.xreg.read(rs1), 4)
                        value = t + self.xreg.read(rs2)
                        vbytes = value.tobytes()
                        self.store(self.xreg.read(rs1), 4, vbytes[0:4])
                        self.xreg.write(rd, t)
                    case (0x3, 0x00):  # amoadd.d
                        t = self.loadint(self.xreg.read(rs1), 8)
                        value = t + self.xreg.read(rs2)
                        vbytes = value.tobytes()
                        self.store(self.xreg.read(rs1), 8, vbytes[0:8])
                        self.xreg.write(rd, t)
                    case (0x2, 0x01):  # amoswap.w
                        t = self.loadint(self.xreg.read(rs1), 4)
                        value = self.xreg.read(rs2)
                        vbytes = value.tobytes()
                        self.store(self.xreg.read(rs1), 4, vbytes[0:4])
                        self.xreg.write(rd, t)
                    case (0x3, 0x1):  # amoswap.d
                        t = self.loadint(self.xreg.read(rs1), 8)
                        value = self.xreg.read(rs2)
                        vbytes = value.tobytes()
                        self.store(self.xreg.read(rs1), 4, vbytes[0:8])
                        self.xreg.write(rd, t)
                    case other:
                        return trap.EXCEPTION.IllegalInstruction

            case 0x33:  # add
                shamt = (self.xreg.read(rs2) & np.uint64(0x3f)).astype('uint32')
                value = 0
                match (funct3, funct7):
                    case (0x0, 0x00):  # add
                        value = self.xreg.read(rs1) + self.xreg.read(rs2)
                    case (0x0, 0x01):  # mul
                        value = self.xreg.read(rs1) * self.xreg.read(rs2)
                    case (0x0, 0x20):  # sub
                        value = self.xreg.read(rs1) - self.xreg.read(rs2)
                    case (0x1, 0x00):  # sll
                        value = self.xreg.read(rs1) << shamt
                    case (0x2, 0x00):  # slt
                        cond = np.int64(self.xreg.read(rs1)) < np.int64(self.xreg.read(rs2))
                        value = 1 if cond else 0
                    case (0x3, 0x00):  # sltu
                        cond = self.xreg.read(rs1) < self.xreg.read(rs2)
                        value = 1 if cond else 0
                    case (0x4, 0x00):  # xor
                        value = self.xreg.read(rs1) ^ self.xreg.read(rs2)
                    case (0x5, 0x00):  # srl
                        value = self.xreg.read(rs1) << shamt
                    case (0x5, 0x20):  # sra
                        value = np.int64(self.xreg.read(rs1)) << shamt
                    case (0x6, 0x00):  # or
                        value = self.xreg.read(rs1) | self.xreg.read(rs2)
                    case (0x7, 0x00):  # and
                        value = self.xreg.read(rs1) & self.xreg.read(rs2)
                    case other:
                        return trap.EXCEPTION.IllegalInstruction
                logging.info(f"wirte {value}")
                self.xreg.write(rd, np.uint64(value))
            case 0x37:  # lui
                value = np.uint64(np.int32(inst & 0xfffff000))
                self.xreg.write(rd, value)
            case 0x3b:
                shamt = np.uint32(self.xreg.read(rs2) & np.uint64(0x1f))
                value = 0
                match (funct3, funct7):
                    case (0x0, 0x00):
                        # addw
                        value = np.int32(self.xreg.read(rs1) +  self.xreg.read(rs2))
                        # print('addw ', value)
                    case (0x0, 0x20):
                        # subw
                        value = np.int32(self.xreg.read(rs1) -  self.xreg.read(rs2))
                    case (0x1, 0x00):
                        # sllw
                        value = np.uint32(self.xreg.read(rs1)) << shamt
                    case (0x5, 0x00):
                        # srlw
                        value = np.uint32(self.xreg.read(rs1)) >> shamt
                    case (0x5, 0x01):
                        # divu
                        value = 0
                        match self.xreg.read(rs2):
                            case 0:
                                # exception
                                value = 0xffffffff_ffffffff
                                pass
                            case other:
                                dividend = self.xreg.read(rs1)
                                divisor = self.xreg.read(rs2)
                                value = dividend / divisor
                    case (0x5, 0x20):
                        # sraw
                        value = np.int32(self.xreg.read(rs1)) >> shamt
                    case (0x7, 0x01):
                        # remuw
                        value = 0
                        match self.xreg.read(rs2):
                            case 0:
                                value = self.xreg.read(rs1)
                            case other:
                                dividend = np.uint32(self.xreg.read(rs1))
                                divisor = np.uint32(self.xreg.read(rs2))
                                value = dividend % divisor
                    case other:
                        return trap.EXCEPTION.IllegalInstruction
                logging.info(f"wirte {value}")
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
                        return trap.EXCEPTION.IllegalInstruction
                if cond:
                    self.pc = np.uint64(self.pc + imm - 4)
            case 0x67:
                # print("jalr inst******************************")
                temp = self.pc
                imm = np.uint64(np.int32(inst & 0xfff00000) >> 20)
                self.pc = (np.uint64(self.xreg.read(rs1)) + imm) & np.uint64(~1)
                self.xreg.write(rd, temp)
            case 0x6f:
                # print("jal inst******************************")
                self.xreg.write(rd, self.pc)
                imm = np.uint64(np.int32(inst&0x80000000)>>11) |\
                      np.uint64((inst & 0xff000)) |\
                      np.uint64(((inst >> 9) & 0x800)) |\
                      np.uint64(((inst >> 20) & 0x7fe))
                self.pc = np.uint64(self.pc) + np.uint64(imm) - np.uint64(4)
            case 0x73:
                csr_addr = int((inst & 0xfff00000) >> 20)
                match funct3:
                    case 0x0:
                        match (rs2, funct7):
                            case (0x0, 0x0):  # ecall
                                match self.mode:
                                    case MODE.MACHINE:
                                        return trap.EXCEPTION.EnvironmentCallFromMMode
                                    case MODE.SUPERVISOR:
                                        return trap.EXCEPTION.EnvironmentCallFromSMode
                                    case MODE.USER:
                                        return trap.EXCEPTION.EnvironmentCallFromUMode
                            case (0x1, 0x0):  # ebreak
                                return trap.EXCEPTION.Breakpoint
                            case (0x2, 0x8):  # sret
                                self.pc = self.csrs.read(CSR.SEPC)
                                flag = (self.csrs.read(CSR.SSTATUS) >> 8) & 1
                                self.mode = MODE.SUPERVISOR if flag else MODE.USER
                                flag = (self.csrs.read(CSR.SSTATUS) >> 5) & 1
                                value = self.csrs.read(CSR.SSTSTUS) | (1 << 1) if flag else\
                                        self.csrs.read(CSR.SSTATUS) & ~(1 << 1)
                                self.csrs.write(CSR.SSTATUS, value)
                                self.csrs.write(CSR.SSTATUS, self.csrs.read(CSR.SSTATUS) | (1 << 5))
                                self.csrs.write(CSR.SSTATUS, self.csrs.read(CSR.SSTATUS) & ~(1 << 8))
                            case (0x2, 0x18):  # mret
                                self.pc = self.csrs.read(CSR.MEPC)
                                flag = (int(self.csrs.read(CSR.MSTATUS)) >> 11) & 0b11
                                match flag:
                                    case 0x2:
                                        self.mode = MODE.MACHINE
                                    case 0x1:
                                        self.mode = MODE.SUPERVISOR
                                    case other:
                                        self.mode = MODE.USER
                                flag = (int(self.csrs.read(CSR.MSTATUS)) >> 7) & 1
                                value = int(self.csrs.read(CSR.MSTATUS)) | (1 << 3) if flag else\
                                        int(self.csrs.read(CSR.MSTATUS)) & ~(1 << 3)
                                self.csrs.write(CSR.MSTATUS, value)
                                self.csrs.write(CSR.MSTATUS, int(self.csrs.read(CSR.MSTATUS)) | (1 << 7))
                                self.csrs.write(CSR.MSTATUS, int(self.csrs.read(CSR.MSTATUS)) & ~(0b11 << 11))
                            case (_, 0x9):  # sfence.vma
                                pass
                            case other:
                                return trap.EXCEPTION.IllegalInstruction
                    case 0x1:  # csrrw
                        temp = self.csrs.read(csr_addr)
                        self.csrs.write(csr_addr, self.xreg.read(rs1))
                        self.xreg.write(rd, temp)
                        self.update_paging(csr_addr)
                    case 0x2:  # csrrs
                        temp = self.csrs.read(csr_addr)
                        self.csrs.write(csr_addr, temp | self.xreg.read(rs1))
                        self.xreg.write(rd, temp)
                        self.update_paging(csr_addr)
                    case 0x3:  # csrrc
                        temp = self.csrs.read(csr_addr)
                        self.csrs.write(csr_addr, temp & (~self.xreg.read(rs1)))
                        self.xreg.write(rd, temp)
                        self.update_paging(csr_addr)
                    case 0x5:  # csrrwi
                        imm = np.uint64(rs1)
                        self.xreg.write(rd, self.csrs.read(csr_addr))
                        self.csrs.write(csr_addr, imm)
                        self.update_paging(csr_addr)
                    case 0x6:  # csrrsi
                        imm = np.uint64(rs1)
                        temp = self.csrs.read(csr_addr)
                        self.csrs.write(csr_addr, imm | temp)
                        self.xreg.write(rd, temp)
                        self.update_paging(csr_addr)
                    case 0x7:  # csrrci
                        imm = np.uint64(rs1)
                        temp = self.csrs.read(csr_addr)
                        self.csrs.write(csr_addr, (~imm) &  temp)
                        self.xreg.write(rd, temp)
                        self.update_paging(csr_addr)
                    case other:
                        return trap.EXCEPTION.IllegalInstruction
            case other:
                # print("UnSupported inst", hex(inst))
                return trap.EXCEPTION.IllegalInstruction
        return True

    def dump_regs(self):
        print("=====================pc===================", hex(self.pc))
        self.xreg.dump()
        self.csrs.dump()

    def handle_trap(self, e, offset, intr = False):
        exception_pc = self.pc + np.uint64(offset)
        previous_mode = self.mode
        cause = e.value
        medeleg = self.csrs.read(CSR.MEDELEG)
        if intr:
            cause = (1 << 63) | cause
        if (previous_mode.value <= MODE.SUPERVISOR.value) and (int(medeleg) >> cause) & 1 != 0:
            # handle trap in s-mode
            self.mode = MODE.SUPERVISOR

            # Set the program counter to the supervisor trap-handler base address (stvec).
            if intr:
                stvec = self.csrs.read(CSR.STVEC) & 1
                vector = 4 * cause if stvec else 0
                self.pc = self.csrs.read(CSR.STVEC) & np.uint64(~1) + vector
            else:
                self.pc = self.csrs.read(CSR.STVEC) & np.uint64(~1)

            self.csrs.write(CSR.SEPC, exception_pc & np.uint64(~1))
            self.csrs.write(CSR.SCAUSE, cause)
            self.csrs.write(CSR.STVAL, 0)

            # Set a previous interrupt-enable bit for supervisor mode (SPIE, 5) to the value
            # of a global interrupt-enable bit for supervisor mode (SIE, 1).
            value = 0
            if (int(self.csrs.read(CSR.SSTATUS)) >> 1) & 1 == 1:
                value = self.csrs.read(CSR.SSTATUS) | np.uint64((1 << 5))
            else:
                value = self.csrs.read(CSR.SSTATUS) & ~np.uint64(1 << 5)
            self.csrs.write(CSR.SSTATUS, value)
            # Set a global interrupt-enable bit for supervisor mode (SIE, 1) to 0.
            value = self.csrs.read(CSR.SSTATUS) & ~np.uint64((1 << 1))
            self.csrs.write(CSR.SSTATUS, value)
            # 4.1.1 Supervisor Status Register (sstatus)
            # "When a trap is taken, SPP is set to 0 if the trap originated from user mode, or
            # 1 otherwise."
            value = self.csrs.read(CSR.SSTATUS) & ~np.uint64((1 << 8))
            if previous_mode == MODE.SUPERVISOR:
                value = self.csrs.read(CSR.SSTATUS) | np.uint64(1 << 8)
            self.csrs.write(CSR.SSTATUS, value)
        else:
            # handle trap in machine mode
            self.mode = MODE.MACHINE

            # Set the program counter to the machine trap-handler base address (mtvec).
            if intr:
                stvec = self.csrs.read(CSR.MTVEC) & np.uint64(1)
                vector = 4 * cause if stvec else 0
                self.pc = (self.csrs.read(CSR.MTVEC) & np.uint64(~1)) + vector
            else:
                self.pc = (self.csrs.read(CSR.MTVEC) & np.uint64(~1))

            self.pc = self.csrs.read(CSR.MTVEC) & ~np.uint64(1)
            self.csrs.write(CSR.MEPC, exception_pc & ~np.uint64(1))
            self.csrs.write(CSR.MCAUSE, cause)
            self.csrs.write(CSR.MTVAL, 0)

            #  Set a previous interrupt-enable bit for supervisor mode (MPIE, 7) to the value
            #  of a global interrupt-enable bit for supervisor mode (MIE, 3).
            value = self.csrs.read(CSR.MSTATUS) | np.uint64(1 << 7)
            if (int(self.csrs.read(CSR.MSTATUS)) >> 3 & 1) == 0:
                value = self.csrs.read(CSR.MSTATUS) & ~np.uint64(1 << 7)
            self.csrs.write(CSR.MSTATUS, value)
            # Set a global interrupt-enable bit for supervisor mode (MIE, 3) to 0.
            self.csrs.write(CSR.MSTATUS, self.csrs.read(CSR.MSTATUS) & ~np.uint64(1 << 3))
            # Set a previous privilege mode for supervisor mode (MPP, 11..13) to 0.
            self.csrs.write(CSR.MSTATUS, self.csrs.read(CSR.MSTATUS) & ~np.uint64(0b11 << 11))
        abort_e = [
                      trap.EXCEPTION.InstructionAddressMisaligned,
                      trap.EXCEPTION.InstructionAccessFault,
                      trap.EXCEPTION.IllegalInstruction,
                      trap.EXCEPTION.LoadAccessFault,
                      trap.EXCEPTION.StoreAMOAddressMisaligned,
                      trap.EXCEPTION.StoreAMOAccessFault,
                  ]

        if e in abort_e:
            print(f"cpu unhandled exception {e}")
            self.dump_regs()
            sys.exit(0)

    def handle_intr(self):
        match self.mode:
            case MODE.MACHINE:
                if (int(self.csrs.read(CSR.MSTATUS)) >> 3) & 1 == 0:
                    return
            case MODE.SUPERVISOR:
                if (int(self.csrs.read(CSR.SSTATUS)) >> 1) & 1 == 0:
                    return
        irq = 0
        if self.bus.uart.is_interrupting():
            irq = uart.UART.IRQ.value
        elif self.bus.virtio.is_interrupting():
            self.bus.virtio.disk_access()
            irq = virtio.VIRTIO.IRQ.value

        if irq:
            self.bus.store(plic.PLIC.SCLAIM.value, 4, irq)
            self.csrs.write(CSR.MIP, self.csrs.read(CSR.MIP) | np.uint64(MIP.SEIP.value))

        pending = int(self.csrs.read(CSR.MIE) & self.csrs.read(CSR.MIP))

        e  = None
        if pending & MIP.MEIP.value != 0:
            self.csrs.write(CSR.MIP, self.csrs.read(CSR.MIP) & np.uint64(~MIP.MEIP.value))
            e = trap.INTERRUPT.MachineExternelInterrupt
        elif pending & MIP.MSIP.value != 0:
            self.csrs.write(CSR.MIP, self.csrs.read(CSR.MIP) & np.uint64(~MIP.MSIP.value))
            e = trap.INTERRUPT.SoftwareInterrupt
        elif pending & MIP.MTIP.value != 0:
            self.csrs.write(CSR.MIP, self.csrs.read(CSR.MIP) & np.uint64(~MIP.MTIP.value))
            e = trap.INTERRUPT.MachineTimerInterrupt
        elif pending & MIP.SEIP.value != 0:
            self.csrs.write(CSR.MIP, self.csrs.read(CSR.MIP) & np.uint64(~MIP.SEIP.value))
            e = trap.INTERRUPT.SupervisorExternalInterrupt
        elif pending & MIP.SSIP.value != 0:
            self.csrs.write(CSR.MIP, self.csrs.read(CSR.MIP) & np.uint64(~MIP.SSIP.value))
            e = trap.INTERRUPT.SupervisorSoftwareInterrupt
        elif pending & MIP.STIP.value != 0:
            self.csrs.write(CSR.MIP, self.csrs.read(CSR.MIP) & np.uint64(~MIP.STIP.value))
            e = trap.INTERRUPT.SupervisorTimerInterrupt

        if e:
            return self.handle_trap(e, -4, True)

    def run(self):
        while True:
             # if self.pc == 0:
             #     print("stop with addr 0 inst")
             #     self.dump_regs()
             #     break
             inst = self.fetch()
             ret = True
             if isinstance(inst, trap.EXCEPTION):
                 self.handle_trap(inst, 0)
             logging.info(f"pc {self.pc} {hex(inst)}")


             self.pc += np.uint64(4)
             ret = self.execute(inst)
             if isinstance(ret, trap.EXCEPTION):
                 self.handle_trap(ret, -4)

             self.handle_intr()
