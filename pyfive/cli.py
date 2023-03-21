import sys
from typing import List
from pyfive import cpu
from pyfive import bus
import logging

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(filename)s[%(lineno)d] - %(message)s"
logging.basicConfig(format=LOG_FORMAT)
logging.getLogger().setLevel(logging.DEBUG)
def main(argv: List[str] = None) -> int:
    mybus = bus.Bus(dram_bin="kernel", disk_bin="fs.img")
    emu = cpu.Cpu(mybus)
    emu.run()

if __name__ == "__main__":
    sys.exit(main(argv=sys.argv))
