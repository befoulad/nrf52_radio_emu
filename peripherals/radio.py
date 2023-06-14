from core.peripheral import IPeripheral, Register
from unicorn.arm_const import *
from enum import Enum

from core.logger import logger

class RadioState(Enum):
    DISABLED = 0
    RXRU = 1
    RXIDLE = 2
    RX = 3
    RXDISABLED = 4
    TXRU = 9
    TXIDLE = 10
    TX = 11
    TXDISABLED = 12

class Radio(IPeripheral):
 
    def __init__(self) -> None:
        self.base_address =  0x40001000
        self.register_list = [
            Register("TASKS_TXEN", self.base_address + 0x0),
            Register("TASKS_RXEN", self.base_address + 0x4),
            Register("TASKS_START", self.base_address + 0x8),
            Register("TASKS_STOP", self.base_address + 0xC),
            Register("TASKS_DISABLE", self.base_address + 0x10),
            
            Register("EVENTS_READY", self.base_address + 0x100),
            Register("EVENTS_ADDRESS", self.base_address + 0x104),
            Register("EVENTS_PAYLOAD", self.base_address + 0x108),
            Register("EVENTS_END", self.base_address + 0x10C),
            Register("EVENTS_DISABLED", self.base_address + 0x110),

            Register("SHORTS", self.base_address + 0x200),
            Register("INTENSET", self.base_address + 0x304),
            Register("INTENCLR", self.base_address + 0x308),
            Register("CRCSTATUS", self.base_address + 0x400, 1),

            Register("PACKETPTR", self.base_address + 0x504),
            Register("FREQUENCY", self.base_address + 0x508),
            Register("TXPOWER", self.base_address + 0x50C),
            Register("MODE", self.base_address + 0x510),
            Register("PCNF0", self.base_address + 0x514),
            Register("PCNF1", self.base_address + 0x518),
            Register("BASE0", self.base_address + 0x51C),
            Register("BASE1", self.base_address + 0x520),
            Register("PREFIX0", self.base_address + 0x524),
            Register("PREFIX1", self.base_address + 0x528),
            Register("TXADDRESS", self.base_address + 0x52C),
            Register("RXADDRESS", self.base_address + 0x530),
            Register("CRCCNF", self.base_address + 0x534),
            Register("CRCPOLY", self.base_address + 0x538),
            Register("CRCINIT", self.base_address + 0x53C),

            Register("STATE", self.base_address + 0x550),
            Register("DATAWHITEIV", self.base_address + 0x554),
            Register("BCC", self.base_address + 0x560),

            Register("MODECFN0", self.base_address + 0x650),
            Register("POWER", self.base_address + 0xFFC),
        ]
        self.populate_maps()
        self.callbacks = {
            "rx_en": None,
            "tx_en": None
        }

    def read(self, uc, address):
        if address in self.register_address_map.keys():
            val = self.register_address_map[address].value
            uc.mem_write(address, val.to_bytes(4, 'little'))
    
    def write(self, uc, address, value):
        if address in self.register_address_map.keys():
            self.register_address_map[address].value = value
        # TASKS_TXEN
        if address == self.register_name_map['TASKS_TXEN'].address:
            data = uc.mem_read(self.get_pktptr(), 1)
            # first byte is payload size
            size = int.from_bytes(data, 'little', signed=False)
            payload = uc.mem_read(self.get_pktptr(), size + 1)
            logger.info("radio packet transmit requested by firmware, size: %d payload: %s", size, payload)
            cb = self.callbacks["tx_en"]
            if cb != None:
                cb()
        # TASKS_RXEN
        if address == self.register_name_map['TASKS_RXEN'].address:
            cb = self.callbacks["rx_en"]
            if cb != None:
                cb()
    
    def get_name(self):
        return "RADIO"
    
    def add_callback(self, name, cb):
        self.callbacks[name] = cb

    def set_state(self, state):
        self.get_reg_by_name('STATE').value = state.value
    
    def set_packet(self, pkt, uc):
        addr = self.get_reg_by_name('PACKETPTR').value
        if addr != 0:
            uc.mem_write(addr, pkt)
            logger.info("copied %d bytes to radio packet ptr at 0x%x", len(pkt), addr)
        else:
            logger.warn("[!] cannot set radio packet, packetptr is null")

    def get_pktptr(self):
        return self.get_reg_by_name('PACKETPTR').value
