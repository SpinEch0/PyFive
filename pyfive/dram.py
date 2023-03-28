import logging
import numpy as np

class Memory():
    def __init__(self, size, dram_bin):
        self.ram = bytearray(size)
        self.size = size
        if dram_bin:
            with open(dram_bin, 'rb') as f:
                data = f.read()
                data_len = len(data) if len(data) < self.size else self.size
                self.store(0, data_len, data)

    def load(self, addr, size):
        addr = int(addr)
        # if addr == 0x3ff010:
        #     logging.info(f"load {self.ram[addr:addr+size]}")
        return self.ram[addr:addr+size]

    def store(self, addr, size, data):
        addr = int(addr)
        if addr == 0x3ff010:
            logging.info(f"store {data}")
        if isinstance(data, int) or isinstance(data, np.uint64):
            data = np.uint64(data).tobytes()
        self.ram[addr:addr+size] = data[:size]
        return True

