import sys
from typing import List
from pyfive import cpu

def main(argv: List[str] = None) -> int:
    emu = cpu.Cpu()
    emu._bus.load_data("add-addi.bin") 
    emu.run()

if __name__ == "__main__":
    sys.exit(main(argv=sys.argv))
