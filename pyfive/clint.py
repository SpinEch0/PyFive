# The clint module contains the core-local interruptor (CLINT). The CLINT
# block holds memory-mapped control and status registers associated with
# software and timer interrupts. It generates per-hart software interrupts and timer.

import numpy as np
from enum import Enum

# The address of a mtimecmp register starts. A mtimecmp is a dram mapped machine mode timer
# compare register, used to trigger an interrupt when mtimecmp is greater than or equal to mtime.

class CLINT(Enum):
    MTIMECMP = 0x4000
    MTIME = 0xbff8

class Clint():
    def __init__(self, size):
        self.mtime = np.uint64(0)
        self.mtimecmp = np.uint64(0)

    def load64(self, addr):
        match addr:
            case CLINT.MTIMECMP:
                return self.mtimecmp
            case CLINT.MTIME:
                return self.mtime
            case other:
                return np.uint64(0)

    def store64(self, addr, value):
        match addr:
            case CLINT.MTIMECMP:
                self.mtimecmp = np.uint64(value)
            case CLINT.MTIME:
                self.mtime = np.uint64(value)

    def load(self, addr, size):
        if size != 8:
            raise("loading clint size is not 8")
        return self.load64(addr).to_bytes(8, byteorder='little', singed='False')

    def store(self, addr, size, data):
        if size != 8:
            raise("storing clint size is not 8")
        val = int.from_bytes(data, byteorder='little', signed=False)
        self.store64(addr, val)
