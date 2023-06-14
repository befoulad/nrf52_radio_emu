import os
import importlib

class IPeripheralRegistry(type):
    peripherals = []
    def __init__(cls, name, bases, attrs):
        if name != 'IPeripheral':
            IPeripheralRegistry.peripherals.append(cls)

class Register:
    def __init__(self, name, address, value=0):
        self.name = name
        self.address = address
        self.value = value
    
    def get_nth_bit(self, n):
        return (self.value & (1 << n) != 0)
    
    def get_range_bits(self, start, end):
        mask =  ((1 << (end - start + 1)) - 1) << start
        return (self.value & mask) >> (start - 1)

class IPeripheral(object, metaclass=IPeripheralRegistry):   
    def __init__(self) -> None:
        self.base_address = None
        self.register_list = []

    def get_name(self):
        return None
    
    def read(self, uc, address):
        pass

    def write(self, uc, address, value):
        pass

    def populate_maps(self):
        self.register_name_map = {register.name: register for register in self.register_list}
        self.register_address_map = {register.address: register for register in self.register_list}

    def get_reg_by_name(self, name):
        return self.register_name_map[name]
    
    def set_reg_val(self, reg_address, value):
        if reg_address in self.register_address_map.keys():
            register = self.register_address_map[reg_address]           
            register.value = value

    def get_reg_val(self, reg_address):
        if reg_address in self.register_address_map.keys():            
            return self.register_address_map[reg_address].value
        else:
            return None

def load_peripherals():
    for filename in os.listdir('peripherals'):        
        name, etx = os.path.splitext(filename)
        modname = f"peripherals.{name}"
        importlib.import_module(modname)
    return IPeripheralRegistry.peripherals