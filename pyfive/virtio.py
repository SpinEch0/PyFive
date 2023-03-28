from enum import Enum
from pyfive import dram
from pyfive import trap
from pyfive import bus
import logging
import numpy as np

class VIRTIO(Enum):
    MAGIC = 0x000
    VERSION = 0x004
    DEVICE_ID = 0x008
    VENDOR_ID = 0x00c
    DEVICE_FEATURES = 0x010
    DRIVER_FEATURES = 0x020
    GUEST_PAGE_SIZE = 0x028
    QUEUE_SEL = 0x030
    QUEUE_NUM_MAX = 0x034
    QUEUE_NUM = 0x038
    QUEUE_PFN = 0x040
    QUEUE_READY = 0x044
    QUEUE_NOTIFY = 0x050
    MMIO_INTERRUPT_STATUS = 0x060
    MMIO_INTERRUPT_ACK = 0x064
    STATUS = 0x070
    MMIO_QUEUE_DESC_LOW	 = 0x080  # physical address for descriptor table, write-only
    MMIO_QUEUE_DESC_HIGH = 0x084
    MMIO_DRIVER_DESC_LOW = 0x090  # physical address for available ring, write-only
    MMIO_DRIVER_DESC_HIGH = 0x094
    MMIO_DEVICE_DESC_LOW = 0x0a0  # physical address for used ring, write-only
    MMIO_DEVICE_DESC_HIGH = 0x0a4
    IRQ = 1

class Virtio():
    def __init__(self, size, bus, disk_bin):
        self.size = size  # not use
        self.bus = bus
        self.id = 0
        self.driver_features = 0
        self.page_size = 4096
        self.queue_sel = 0
        self.queue_num = 0
        self.queue_pfn = 0
        self.queue_notify = 1
        self.queue_rdy = 0
        self.status = 0
        self.intr_status = 0
        self.intr_ack = 0
        self.disk = dram.Memory(0x40_0000, disk_bin)  # 4M disk

    def load(self, addr, size):
        if size != 4:
            return trap.EXCEPTION.LoadAccessFault
        value = 0
        match VIRTIO(addr):
            case VIRTIO.MAGIC:
                value = 0x74726976
            case VIRTIO.VERSION:
                value = 0x2
            case VIRTIO.DEVICE_ID:
                value = 0x2
            case VIRTIO.VENDOR_ID:
                value = 0x554d4551
            case VIRTIO.DEVICE_FEATURES:
                value = 0
            case VIRTIO.DRIVER_FEATURES:
                value = self.driver_features
            case VIRTIO.QUEUE_NUM_MAX:
                value = 8
            case VIRTIO.QUEUE_PFN:
                value = self.queue_pfn
            case VIRTIO.QUEUE_READY:
                value = self.queue_rdy
            case VIRTIO.STATUS:
                value = self.status
            case VIRTIO.MMIO_INTERRUPT_STATUS:
                value = self.intr_status
            case VIRTIO.MMIO_INTERRUPT_ACK:
                value = self.intr_ack
            case other:
                pass
        return value

    def store(self, addr, size, data):
        if size != 4:
            return trap.EXCEPTION.StoreAMOPageFault
        if isinstance(data, bytes):
            data = int.from_bytes(data, byteorder='little', signed=False)
        match VIRTIO(addr):
            case VIRTIO.DEVICE_FEATURES:
                self.driver_features = data
            case VIRTIO.GUEST_PAGE_SIZE:
                self.page_size = data
            case VIRTIO.QUEUE_SEL:
                self.queue_sel = data
            case VIRTIO.QUEUE_NUM:
                self.queue_num = data
            case VIRTIO.QUEUE_PFN:
                self.queue_pfn = data
            case VIRTIO.QUEUE_NOTIFY:
                self.queue_notify = data
                logging.debug(f"quenum notify is {data}")
            case VIRTIO.QUEUE_READY:
                self.queue_rdy = data
            case VIRTIO.MMIO_INTERRUPT_STATUS:
                self.intr_status = data
            case VIRTIO.MMIO_INTERRUPT_ACK:
                self.intr_ack = data
            case VIRTIO.STATUS:
                self.status = data
            case VIRTIO.MMIO_QUEUE_DESC_LOW:
                self.queue_desc_low = data
            case VIRTIO.MMIO_QUEUE_DESC_HIGH:
                self.queue_desc_high = data
            case VIRTIO.MMIO_DRIVER_DESC_LOW:
                logging.debug(f"driver desc low addr {hex(data)}")
                self.driver_desc_low = data
            case VIRTIO.MMIO_DRIVER_DESC_HIGH:
                logging.debug(f"driver desc high addr {hex(data)}")
                self.driver_desc_high = data
            case VIRTIO.MMIO_DEVICE_DESC_LOW:
                self.device_desc_low = data
            case VIRTIO.MMIO_DEVICE_DESC_HIGH:
                self.device_desc_high = data

    def is_interrupting(self):
        if self.queue_notify == 0:
            self.queue_notify = 1
            return True
        return False

    def get_new_id(self):
        # self.id = (self.id + 1) % self.queue_num
        self.id = (self.id + 1)
        return self.id

    def read_disk(self, addr):
        return self.disk.load(addr, 1)


    def write_disk(self, addr, data):
        self.disk.store(addr, 1, data)


    def desc_addr(self):
        return int(np.uint64((self.queue_desc_high << 32) + self.queue_desc_low))

    def avail_addr(self):
        return int(np.uint64((self.driver_desc_high << 32) + self.driver_desc_low))

    def used_addr(self):
        return int(np.uint64((self.device_desc_high << 32) + self.device_desc_low))

    def disk_access(self):
        logging.debug("disk access")
        VRING_DESC_SIZE = 16
        desc_addr = self.desc_addr()
        avail_addr = self.avail_addr()
        used_addr = self.used_addr()

        offset = self.bus.loadint(avail_addr + 2, 2)
        # logging.debug(f"busload avail addr {hex(avail_addr)}  offset is {offset}")
        # ring
        index = self.bus.loadint(avail_addr + 4 + offset, 2)

        desc_addr0 = desc_addr + VRING_DESC_SIZE * index
        addr0 = self.bus.loadint(desc_addr0, 8)
        next0 = self.bus.loadint(desc_addr0 + 14, 2)

        desc_addr1 = desc_addr + VRING_DESC_SIZE * next0
        addr1 = self.bus.loadint(desc_addr1, 8)
        len1 = self.bus.loadint(desc_addr1 + 8, 4)
        flag1 = self.bus.loadint(desc_addr1 + 12, 2)

        blk_sector = self.bus.loadint(addr0 + 8, 8)

        match (int(flag1) & 2) == 0:
            case True:
                for i in range(len1):
                    data = self.bus.load(addr1 + i, 1)
                    self.write_disk(blk_sector * 512 + i, data)
            case False:
                for i in range(len1):
                    data = self.read_disk(blk_sector * 512 + i)
                    self.bus.store(addr1 + i, 1, data)

        # device write 0 on success
        next1 = self.bus.loadint(desc_addr1 + 14, 2)
        desc_addr2 = desc_addr + VRING_DESC_SIZE * next1
        addr2 = self.bus.loadint(desc_addr2, 8)
        logging.debug(f"next1 idx is {next1}")
        logging.debug(f"desc addr2  / info0 status addr is {hex(int(desc_addr2))}")
        logging.debug(f"write {hex(addr2)} to 0")
        self.bus.store(addr2, 2, 0)

        new_id = self.get_new_id()
        logging.debug(f"new id is {new_id}")
        self.bus.store(used_addr + 2, 2, new_id)
