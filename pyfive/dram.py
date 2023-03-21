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
        return self.ram[addr:addr+size] 

    def store(self, addr, size, data):
        addr = int(addr)
        self.ram[addr:addr+size] = data
        return True 

