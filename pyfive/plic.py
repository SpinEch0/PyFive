# The plic module contains the platform-level interrupt controller (PLIC).
# The plic connects all external interrupts in the system to all hart
# contexts in the system, via the external interrupt source in each hart.
# It's the global interrupt controller in a RISC-V system.


import numpy as np
from enum import Enum
import logging

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
        logging.debug(f"plic load {hex(addr)}")
        match PLIC(addr):
            case PLIC.PENDING:
                return self.pending
            case PLIC.SENABLE:
                return self.senable
            case PLIC.SPRIORITY:
                return self.spriority
            case PLIC.SCLAIM:
                return self.sclaim
            case other:
                logging.debug(f"plic load other {hex(addr)}")
                return np.uint32(0)

    def store32(self, addr, value):
        logging.debug(f"plic store {hex(addr)} val{value}")
        match addr:
            case PLIC.PENDING.value:
                self.pending = np.uint32(value)
            case PLIC.SENABLE.value:
                self.senable = np.uint32(value)
            case PLIC.SPRIORITY.value:
                self.spriority = np.uint32(value)
            case PLIC.SCLAIM.value:
                self.sclaim = np.uint32(value)
            case other:
                logging.debug("plic write some regs")

    def load(self, addr, size):
        if size != 4:
            raise("loading plic size is not 4")
        return int(self.load32(addr)).to_bytes(4, byteorder='little', signed=False)

    def store(self, addr, size, data):
        if size != 4:
            raise("storing plic size is not 4")
        if isinstance(data, bytes) or isinstance(data, bytearray):
            data = int.from_bytes(data, byteorder='little', signed=False)
        self.store32(addr, data)
