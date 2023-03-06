from pyfive import clint
from pyfive import plic
from pyfive import dram
from pyfive import uart

DRAM_BASE=0x8000_0000
DRAM_SIZE=128*1024*1024

CLINT_BASE=0x200_0000
CLINT_SIZE=0x10000

PLIC_BASE=0xc00_0000
PLIC_SIZE=0x4000000

UART_BASE=0x1000_0000
UART_SIZE=0x100

class Bus():
    def __init__(self, size=DRAM_SIZE):
        self.ram = dram.Memory(size)
        self.clint = clint.Clint(CLINT_SIZE)
        self.plic = plic.Plic(PLIC_SIZE)
        self.uart = uart.Uart(UART_SIZE)

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
        elif addr >= UART_BASE and addr < UART_BASE + UART_SIZE:
            return self.uart.load(addr-UART_BASE, size)
        return None

    def store(self, addr, size, data):
        if addr >= DRAM_BASE and addr + size < DRAM_BASE + DRAM_SIZE:
            return self.ram.store(addr-DRAM_BASE, size, data)
        elif addr >= CLINT_BASE and addr + size < CLINT_BASE + CLINT_SIZE:
            return self.clint.store(addr-CLINT_BASE, size, data)
        elif addr >= PLIC_BASE and addr + size < PLIC_BASE + PLIC_SIZE:
            return self.plic.store(addr-PLIC_BASE, size, data)
        elif addr >= UART_BASE and addr < UART_BASE + UART_SIZE:
            return self.uart.store(addr-UART_BASE, size, data)
        return False
