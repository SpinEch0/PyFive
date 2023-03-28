import sys
from typing import List
from pyfive import cpu
from pyfive import bus
import logging
import signal

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(filename)s[%(lineno)d] - %(message)s"
logging.basicConfig(format=LOG_FORMAT)
logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger().setLevel(logging.INFO)

emu = None

def handler(*args):
    global emu
    emu.dump_regs()
    sys.exit(0)

def main(argv: List[str] = None) -> int:
    global emu
    signal.signal(signal.SIGINT, handler)
    mybus = bus.Bus(dram_bin="kernel", disk_bin="../xv6-riscv/fs.img")
    emu = cpu.Cpu(mybus)
    emu.run()
if __name__ == "__main__":
    sys.exit(main(argv=sys.argv))
