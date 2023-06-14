from core.peripheral import IPeripheral, Register
from core.logger import logger

class GPIO(IPeripheral):   

    def __init__(self):
        self.base_address = 0x50000000
        self.register_list = [
            Register("OUTSET", self.base_address + 0x508),
            Register("OUTCLR", self.base_address + 0x50C),
            Register("PIN_CNF[15]", self.base_address + 0x73C)
        ]
        self.populate_maps()

    def read(self, uc, address):
        val = self.get_reg_val(address)
        if val != None:
            uc.mem_write(address, val.to_bytes(4, 'little'))
    
    def write(self, uc, address, value):
        self.set_reg_val(address, value)
        if address == self.get_reg_by_name('OUTSET').address or address == self.get_reg_by_name('OUTCLR').address:
            pins = []
            for i in range(0, 32):
                if value & (1 << i) != 0:
                    pins.append(i)
            if address == self.get_reg_by_name('OUTSET').address:
                logger.info("[*] these gpio pins were set to high: %s", pins)
            else:
                logger.info("[*] these gpio pins were cleared: %s", pins)
    def get_name(self):
        return "P0"