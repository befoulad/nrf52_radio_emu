from unicorn import *
from unicorn.arm_const import *
from capstone import *
from capstone.arm import *
from cmsis_svd.parser import SVDParser

from collections import OrderedDict
import struct

from core.peripheral import load_peripherals
from core.ic import interrupt_enter,interrupt_return
from core.logger import logger

RAM_START_ADDRESS = 0x20000000
RAM_SIZE = 0x40000
NRF52840_REGISTERS = {}
NRF52840_PERIPHERALS = {}
# NOTE: you'd need to handle mrs & msr properly in 
# firmware running on top of a RTOS
INSTRUCTIONS_TO_SKIP = ["vmsr", "mrs", "msr"]
RADIO_INT_RETURN = False

class VectorTable(OrderedDict):
    def __repr__(self) -> str:
        str = ""
        for key, value in self.items():
            str += key + ":" + hex(value) + "\n"
        return str

def get_uc_aligned_size(length):
    if length % (1024) == 0:
        return length
    return 1024*(length // 1024) + 1024

def skip_instr(mn, uc, address, size):
    #print("[!] skipping %s instruction" %mn)
    uc.reg_write(UC_ARM_REG_PC, (address + size) | 1)

def parse_vector_table(content):
    vector_table = VectorTable({
        "initial_sp" : 0,
        "reset_handler": 0,
        "nmi_handler": 0,
        "hardfault_handler": 0,
        "mgnmem_handler": 0,
        "busfault_handler": 0,
        "usefault_handler": 0,
        "reserved1": 0,
        "reserved2": 0,
        "reserved3": 0,
        "reserved4": 0,
        "svc_handler": 0,
        "dbgmon_handler": 0,
        "reserved5": 0,
        "pendsvc_handler": 0,
        "systick_handler": 0,
        "wdtirq_handler": 0,
        "radioirq_handler": 0
    })
    i = 0
    for name in vector_table.keys():
        vector_table[name] = struct.unpack('<I', content[i:i+4])[0]
        i += 4
    return vector_table

def load_registers_from_svd():
    clist = load_peripherals()
    for c in clist:
        instance = c()
        name = instance.get_name()
        NRF52840_PERIPHERALS[name] = instance
        logger.info("[*] instantiated %s peripheral", name)
    parser = SVDParser.for_xml_file('data/nrf52840.svd')
    device = parser.get_device()
    for p in device.peripherals:
        base_addr = p.base_address
        for reg in p.registers:
            addr = base_addr + reg.address_offset
            NRF52840_REGISTERS[addr] = (reg, p.name)


class Emulator:
    def __init__(self, fw_path, base_addr) -> None:
        self.uc = Uc(UC_ARCH_ARM, UC_MODE_LITTLE_ENDIAN)
        self.cs = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS | CS_MODE_LITTLE_ENDIAN)
        self.cs.detail = True
        self.base_addr = base_addr
        load_registers_from_svd()
        # setup flash      
        vector_table = None
        self.fw_size = None
        with open(fw_path, 'rb') as fp:
            content = fp.read()
            self.fw_size = len(content)
            self.vector_table = parse_vector_table(content)
            logger.debug("[*] loaded vector table:\n{%s}", self.vector_table)
            # map flash memory
            size = get_uc_aligned_size(len(content))    
            self.uc.mem_map(base_addr, size)
            self.uc.mem_write(base_addr, content)

        # setup SRAM and map peripherals
        self.uc.mem_map(RAM_START_ADDRESS, RAM_SIZE)
        self.uc.mem_map(0xf0000000, 0x1000)
        self.uc.mem_map(0xe0000000, 0x10000)
        self.uc.mem_map(0x10000000, 0x10000)
        self.uc.mem_map(0x40000000, 0x40000)
        self.uc.mem_map(0x50000000, 0x1000)

        # special value for EXC_RETURN
        self.uc.mem_map(0xfffff000, 0x1000)

        # setup uc hooks
        self.uc.hook_add(UC_HOOK_CODE, self.uc_code_cb, user_data={'fw_base_addr': base_addr})
        self.uc.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, self.uc_mem_cb)
        self.uc.hook_add(UC_HOOK_INTR, self.uc_intr_cb)        
        self.uc.hook_add(UC_HOOK_BLOCK, self.uc_mem_block_cb, begin=0xfffff000, end=0xffffffff)
   
    
    def start(self):
        # subscribe to TASKS_RXEN envet from radio
        NRF52840_PERIPHERALS['RADIO'].add_callback("rx_en", self.rx_enabled_cb)
        NRF52840_PERIPHERALS['RADIO'].add_callback("tx_en", self.tx_enabled_cb)
        self.uc.reg_write(UC_ARM_REG_MSP, self.vector_table['initial_sp'])
        self.uc.emu_start(self.vector_table['reset_handler'], self.fw_size + self.base_addr, 20 * UC_SECOND_SCALE , 0)
        # stop timer0 after UC timed out
        NRF52840_PERIPHERALS['TIMER0'].stop()

    def uc_code_cb(self, uc, addr, size, user_data):
        global RADIO_INT_RETURN       
        code = uc.mem_read(addr, size)
        lr = uc.reg_read(UC_ARM_REG_LR)
        for insr in self.cs.disasm(code, addr, 1):
            #print("0x%08x\t %s %s" %(addr, insr.mnemonic, insr.op_str))
            pass
        if insr.mnemonic in INSTRUCTIONS_TO_SKIP:
            skip_instr(insr.mnemonic, uc, addr, size)

        elif addr == 0x20aa and not RADIO_INT_RETURN:
            radio = NRF52840_PERIPHERALS['RADIO']
            radio.get_reg_by_name('EVENTS_END').value = 1
            packet = b'\x05\x00\x44\x00\x01\x02'
            radio.set_packet(packet, uc)
            interrupt_enter(0x11, uc, user_data['fw_base_addr'])
        elif addr == 0x20aa and RADIO_INT_RETURN:
            RADIO_INT_RETURN = False
        
        elif addr == 0x858:
            #logger.debug("device id: %x", uc.reg_read(UC_ARM_REG_R1))
            pass
        elif addr == 0x84a:
            ptr = uc.reg_read(UC_ARM_REG_R0)
            #logger.debug("msgptr: %x", ptr)
            pass
        #if addr == 0x178c:
        #    print("r0=%x r8=%x"%(uc.reg_read(UC_ARM_REG_R0), uc.reg_read(UC_ARM_REG_R8)))       
     
    def uc_mem_cb(self, uc, access, address, size, value, user_data):
        if address in NRF52840_REGISTERS.keys():
            reg, pname = NRF52840_REGISTERS[address]
            pc = self.uc.reg_read(UC_ARM_REG_PC)
            if access == UC_MEM_READ:
                #logger.debug("read access at %x to %x -> %s register of %s", pc, address, reg.name, pname)
                pass
            elif access == UC_MEM_WRITE:
                #logger.debug("write access at %x to %x value: %x -> %s register of %s", pc, address, value, reg.name, pname)
                pass
            if pname in NRF52840_PERIPHERALS.keys():
                peripheral = NRF52840_PERIPHERALS[pname]
                if access == UC_MEM_READ:
                    peripheral.read(uc, address)
                elif access == UC_MEM_WRITE:
                    peripheral.write(uc, address, value)       
    
    def uc_intr_cb(self, uc, exc_no):
        print("exception %d raised" %exc_no)

    def uc_mem_block_cb(self, uc, address, size, data):
        global RADIO_INT_RETURN       
        irq_num = uc.reg_read(UC_ARM_REG_IPSR)
        if irq_num == 17:
            RADIO_INT_RETURN = True
        interrupt_return(uc)

    def rx_enabled_cb(self):
        global RADIO_RX_ENABLED
        logger.debug("rx enabled cb called")
        RADIO_RX_ENABLED = True
    
    def tx_enabled_cb(self):
        global RADIO_TX_ENABLED
        logger.debug("tx enabled cb called")
        RADIO_TX_ENABLED = True