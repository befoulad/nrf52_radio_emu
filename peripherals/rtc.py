from core.peripheral import IPeripheral, Register

class RTC1(IPeripheral):
    def __init__(self):
        self.base_address = 0x40011000
        self.register_list = [
            Register("TASKS_START", self.base_address + 0x0),
            Register("TASKS_STOP", self.base_address + 0x4),
            Register("TASKS_CLEAR", self.base_address + 0x8),            
        ]
        self.populate_maps()
    
    def read(self, uc, address):
        val = self.get_reg_val(address)
        if val != None:
            uc.mem_write(address, val.to_bytes(4, 'little'))

    def write(self, uc, address, value):
        self.set_reg_val(address, value)

    
    def get_name(self):
        return "RTC1"
    