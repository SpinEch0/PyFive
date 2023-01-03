from array import array
import struct

class Bus():
    def __init__(self, size=0x10000):
        self._ram = array('B', [0] * size)
        self._size = size

    def load_data(self, file):
        with open(file, 'rb') as f:
            data = f.read()
            data_len = len(data) if len(data) < self._size else self._size
            self._ram[0:data_len] = array("B", struct.unpack("%iB" % data_len, data))

    def read(self, addr, size):
        return self._ram[addr:addr+size] 

    def write(self, addr, data, size):
        if isinstance(data, list):
            data = array('b', data)
        self._ram[addr:addt+size] = data
