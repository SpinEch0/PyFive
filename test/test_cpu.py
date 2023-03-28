import sys
import os
import numpy as np

dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f"{dir_path}/..")
from pyfive import cpu
from pyfive import bus
from pyfive import trap
# import logging

# LOG_FORMAT = "%(asctime)s - %(levelname)s - %(filename)s[:%(lineno)d] - %(message)s"
# logging.basicConfig(format=LOG_FORMAT)
# logging.getLogger().setLevel(logging.DEBUG)
class TestCpu():
    @classmethod
    def setup_class(cls):
        cls.mybus = bus.Bus()
        cls.mycpu = cpu.Cpu(cls.mybus)

    def setup_method(self, method):
        self.mybus = bus.Bus()
        self.mycpu = cpu.Cpu(self.mybus)

    def store_dram(self, val, size):
        self.mybus.store(bus.DRAM_BASE, size, bytes(np.uint64(val).tobytes()*size))

    def test_cpu_fetch(self):
        inst = self.mycpu.fetch()
        assert(inst == 0)

        self.store_dram(1, 1024)
        inst = self.mycpu.fetch()
        assert(inst == 0x01)

        self.mycpu.enable_paging = True
        inst = self.mycpu.fetch()
        assert(isinstance(inst, trap.EXCEPTION))

        self.store_dram(0x2000_00ff, 1024)
        self.mycpu.pc = bus.DRAM_BASE
        self.mycpu.page_table = bus.DRAM_BASE
        inst = self.mycpu.fetch()
        assert(inst == 0x2000_00ff)

    def test_cpu_load(self):
        data = self.mycpu.load(0, 8)
        assert(isinstance(data, trap.EXCEPTION))

        data = self.mycpu.load(bus.DRAM_BASE, 8)
        assert(int(data[0]) == 0)
        assert(len(data) == 8)

    def test_cpu_store(self):
        ret = self.mycpu.store(0, 8, None)
        assert(isinstance(ret, trap.EXCEPTION))
        ret = self.mycpu.store(bus.DRAM_BASE, 8, [0]*8)
        assert(ret)

    def test_cpu_loadint(self):
        self.store_dram(1023, 1024)
        data = self.mycpu.loadint(bus.DRAM_BASE + 8, 8)
        assert(data == 1023)

        data = self.mycpu.loadint(bus.DRAM_BASE + 16, 4)
        assert(data == 1023)

        data = self.mycpu.loadint(bus.DRAM_BASE + 12, 4)
        assert(data == 0)

        self.store_dram(0xffff_ffef_5dc3_f329, 1024)
        data = self.mycpu.loadint(bus.DRAM_BASE+4, 4)
        assert(data == 0xffff_ffff_ffff_ffef)

    def test_cpu_loaduint(self):
        self.store_dram(0xffff_ffef_5dc3_f329, 1024)
        data = self.mycpu.loaduint(bus.DRAM_BASE, 4)
        assert(data == 0x5dc3_f329)

        data = self.mycpu.loaduint(bus.DRAM_BASE+4, 4)
        assert(data == 0xffff_ffef)
