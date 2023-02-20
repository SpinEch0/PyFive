from pyfive import clint
from pyfive import plic

DRAM_BASE=0x8000_0000
DRAM_SIZE=128*1024*1024

CLINT_BASE=0x200_0000
CLINT_SIZE=0x10000

PLIC_BASE=0xc00_0000
PLIC_SIZE=0x4000000

class Memory():
    def __init__(self, size):
        self.ram = bytearray(size)
        self.size = size

    def load(self, addr, size):
        return self.ram[addr:addr+size] 

    def store(self, addr, size, data):
        self.ram[addr:addr+size] = data
        return True 


class Bus():
    def __init__(self, size=DRAM_SIZE):
        self.ram = Memory(size)
        self.clint = clint.Clint(CLINT_SIZE)
        self.plic = Memory(PLIC_SIZE)


    def load_data(self, file):
        with open(file, 'rb') as f:
            data = f.read()
            data_len = len(data) if len(data) < self.ram.size else self.size
            self.ram.store(0, data_len, data)

    def load(self, addr, size):
        if addr >= DRAM_BASE and addr < DRAM_BASE + DRAM_SIZE:
            return self.ram.load(addr-DRAM_BASE, size)
        elif addr >= CLINT_BASE and addr < CLINT_BASE + CLINT_SIZE:
            return self.clint.load(addr-CLINT_BASE, size)
        elif addr >= PLIC_BASE and addr < PLIC_BASE + PLIC_SIZE:
            return self.plic.load(addr-PLIC_BASE, size)
        return None

    def store(self, addr, size, data):
        if addr >= DRAM_BASE and addr + size < DRAM_BASE + DRAM_SIZE:
            return self.ram.store(addr-DRAM_BASE, size, data)
        elif addr >= CLINT_BASE and addr + size < CLINT_BASE + CLINT_SIZE:
            return self.clint.store(addr-CLINT_BASE, size, data)
        elif addr >= PLIC_BASE and addr + size < PLIC_BASE + PLIC_SIZE:
            return self.plic.store(addr-PLIC_BASE, size, data)
        return False
