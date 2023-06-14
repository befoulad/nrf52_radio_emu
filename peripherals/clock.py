from core.peripheral import IPeripheral, Register


class Clock(IPeripheral):

    def __init__(self):
        self.base_address = 0x40000000
        self.register_list = [
            Register("TASKS_HFCLKSTART", self.base_address + 0x0),
            Register("TASKS_HFCLKSTOP", self.base_address + 0x4),
            Register("EVENTS_HFCLKSTARTED", self.base_address + 0x100, 1)
        ]
        self.populate_maps()
        
    def read(self, uc, address):
        val = self.get_reg_val(address)
        if val != None:
            uc.mem_write(address, val.to_bytes(4, 'little'))

    def write(self, uc, address, value):
        self.set_reg_val(address, value)
        if address == self.register_name_map['TASKS_HFCLKSTART'].address:
            self.register_name_map['EVENTS_HFCLKSTARTED'].value = 1
    
    def get_name(self):
        return "CLOCK"
    
    