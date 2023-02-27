class Memory():
    def __init__(self, size):
        self.ram = bytearray(size)
        self.size = size

    def load(self, addr, size):
        return self.ram[addr:addr+size] 

    def store(self, addr, size, data):
        self.ram[addr:addr+size] = data
        return True 

