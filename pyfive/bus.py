
DRAM_BASE=0x8000_0000
DRAM_SIZE=128*1024*1024

class Bus():
    def __init__(self, size=DRAM_SIZE):
        self._ram = bytearray(size)
        self._size = size

    def load_data(self, file):
        with open(file, 'rb') as f:
            data = f.read()
            data_len = len(data) if len(data) < self._size else self._size
            self._ram[0:data_len] = data

    def load(self, addr, size):
        addr = addr - DRAM_BASE
        #print("load ", hex(addr), size)
        if addr + size > DRAM_BASE + DRAM_SIZE:
            raise("load overflow")
        #print("addr : size ", addr, addr+size)
        #print(self._ram[0:size])
        #print(self._ram[addr:addr+size+8])
        #print(len(self._ram[addr:addr+size]))
        return self._ram[addr:addr+size] 

    def store(self, addr, size, data):
        addr = addr - DRAM_BASE
        if addr + size > DRAM_BASE + DRAM_SIZE:
            raise("store overflow")
        print("store ", hex(addr), size, data)
        #print(type(addr), type(size), type(data))
        self._ram[addr:addr+size] = data
