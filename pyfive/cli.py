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
    if len(argv) > 2:
        mybus = bus.Bus(dram_bin=argv[1], disk_bin=argv[2])
    elif len(argv) > 1:
        mybus = bus.Bus(dram_bin=argv[1])
    else:
        logging.fatal("dram_bin must be specified!")
    emu = cpu.Cpu(mybus)
    emu.run()
if __name__ == "__main__":
    sys.exit(main(argv=sys.argv))
