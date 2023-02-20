# The plic module contains the platform-level interrupt controller (PLIC).
# The plic connects all external interrupts in the system to all hart
# contexts in the system, via the external interrupt source in each hart.
# It's the global interrupt controller in a RISC-V system.


import numpy as np
from enum import Enum

class PLIC(Enum):
    PENDING = 0x1000
    SENABLE = 0x2080
    SPRIORITY = 0x201000
    SCLAIM = 0x201004

class Plic():
    def __init__(self, size):
        self.pending = np.uint32(0)
        self.senable = np.uint32(0)
        self.spriority = np.uint32(0)
        self.sclaim = np.uint32(0)

    def load32(self, addr):
        match addr:
            case PLIC.PENDING:
                return self.pending
            case PLIC.SENABLE:
                return self.senable
            case PLIC.SPRIORITY:
                return self.spriority
            case PLIC.SCLAIM:
                return self.sclaim
            case other:
                return np.uint32(0)

    def store32(self, addr, value):
        match addr:
            case PLIC.PENDING:
                self.pending = np.uint32(value)
            case PLIC.SENABLE:
                self.senable = np.uint32(value)
            case PLIC.SPRIORITY:
                self.spriority = np.uint32(value)
            case PLIC.SCLAIM:
                self.sclaim = np.uint32(value)

    def load(self, addr, size):
        if size != 4:
            raise("loading plic size is not 4")
        return self.load32(addr).to_bytes(4, byteorder='little', singed='False')

    def store(self, addr, size, data):
        if size != 4:
            raise("storing plic size is not 4")
        val = int.from_bytes(data, byteorder='little', signed=False)
        self.store32(addr, val)
