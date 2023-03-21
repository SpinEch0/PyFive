from enum import Enum
from pyfive import dram
from pyfive import trap
from pyfive import bus

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
    QUEUE_NOTIFY = 0x050
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
        self.status = 0
        self.disk = dram.Memory(0x40_0000, disk_bin)  # 4M disk

    def load(self, addr, size):
        if size != 4:
            return trap.EXCEPTION.LoadAccessFault
        value = 0
        match VIRTIO(addr):
            case VIRTIO.MAGIC:
                value = 0x74726976
            case VIRTIO.VERSION:
                value = 0x1
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
            case VIRTIO.STATUS:
                value = self.status
            case other:
                pass
        return value

    def store(self, addr, size, data):
        if size != 4:
            return trap.EXCEPTION.StoreAMOPageFault
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
            case VIRTIO.STATUS:
                self.status = data
            case VIRTIO.MMIO_QUEUE_DESC_LOW:
                self.queue_desc_low = data
            case VIRTIO.MMIO_QUEUE_DESC_HIGH:
                self.queue_desc_high = data
            case VIRTIO.MMIO_DRIVER_DESC_LOW:
                self.driver_desc_low = data
            case VIRTIO.MMIO_DRIVER_DESC_HIGH:
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
        self.id = (self.id + 1) % self.queue_num

    def read_disk(self, addr):
        return self.disk.load(addr, 1)


    def write_disk(self, addr, data):
        self.disk.store(addr, 1, data)


    def desc_addr(self):
        return int(np.uint64(self.queue_desc_high << 32 + self.queue_desc_low))

    def avail_addr(self):
        return int(np.uint64(self.driver_desc_high << 32 + self.driver_desc_low))

    def used_addr(self):
        return int(np.uint64(self.device_desc_high << 32 + self.device_desc_low))

    def disk_access():
        VRING_DESC_SIZE = 16
        desc_addr = self.desc_addr()
        avail_addr = self.avail_addr()
        used_addr = self.used_addr()

        offset = bus.load(avail_addr + 2, 2)
        # ring
        index = bus.load(avail_addr + 4 + offset, 2)

        desc_addr0 = desc_addr + VRING_DESC_SIZE * index
        addr0 = bus.load(desc_addr0, 8)
        next0 = bus.load(desc_addr0 + 14, 2)

        desc_addr1 = desc_addr + VRING_DESC_SIZE * next0
        addr1 = bus.load(desc_addr1, 8)
        len1 = bus.load(desc_addr1 + 8, 4)
        flag1 = bus.load(desc_addr1 + 12, 2)

        blk_sector = bus.load(addr0 + 8, 8)

        match (flag1 & 2) == 0:
            case True:
                for i in range(len1):
                    data = bus.load(adr1 + i, 1)
                    self.write_disk(blk_sector * 512 + i, data)
            case False:
                for i in range(len1):
                    data = self.read_disk(blk_sector * 512 + i)
                    bus.store(addr1 + i, 1, data)

        new_id = self.get_new_id()
        bus.store(used_addr + 2, 2, new_id)
