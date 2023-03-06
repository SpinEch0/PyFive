from enum import Enum
import numpy as np
import threading
import sys
import time
import copy

class UART(Enum):
    RHR = 0
    THR = 0
    LCR = 3
    LSR = 5
    LSR_RX = 1
    LSR_TX = 1 << 5
    IRQ = 10

def keyboard_thread(uart):
    while True:
        c = sys.stdin.read(1)
        if len(c) == 0:
            print("keyboard exit")
            sys.exit(0)
        while (uart.regs[UART.LSR.value] & np.uint64(UART.LSR_RX.value)) == 1:
             uart.cond.acquire()
             uart.cond.wait()
             uart.cond.release()
        uart.mutex.acquire()
        uart.regs[UART.RHR.value] = np.uint64(ord(c))
        uart.regs[UART.LSR.value] |= np.uint64(UART.LSR_RX.value)
        uart.mutex.release()
        #print("keyboard get=====", ord(c))

class Uart():
    def __init__(self, size):
        self.regs = [np.uint64(0)] * size
        self.cond = threading.Condition()
        self.thread = threading.Thread(target=keyboard_thread,
                                       args=(self,))
        self.mutex = threading.Lock()
        self.thread.setDaemon(True)
        self.thread.start()

    def load(self, addr, size):
        if size != 1:
            print("uart load size error, size is ", size)
            sys.exit(0)
        match addr:
            case UART.RHR.value:
                self.mutex.acquire()
                self.regs[UART.LSR.value] &= ~(np.uint64(UART.LSR_RX.value))
                ret = copy.deepcopy(self.regs[UART.RHR.value])
                self.mutex.release()
                #print("uart get=====", ret)
                self.cond.acquire()
                self.cond.notify()
                self.cond.release()
                return ret
            case other:
                return self.regs[addr]

    def store(self, addr, size, data):
        if size != 1:
            print("uart store size error, size is ", size)
            sys.exit(0)
        data = int.from_bytes(data, byteorder='little', signed=False)
        match addr:
            case UART.THR.value:
                print(chr(data), end="")
            case other:
                self.regs[addr] = np.uint64(data)
